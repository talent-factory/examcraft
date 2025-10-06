# ExamCraft AI - Production Architecture auf Render.com

## 🏗️ Architektur-Übersicht

```
┌─────────────────────────────────────────────────────────────┐
│                    Render.com Cloud                          │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                  Frontend Service                       │ │
│  │  ┌──────────────────────────────────────────────────┐  │ │
│  │  │  React 18 Static Site                            │  │ │
│  │  │  - Nginx Server                                  │  │ │
│  │  │  - Optimized Build                               │  │ │
│  │  │  - CDN Delivery                                  │  │ │
│  │  └──────────────────────────────────────────────────┘  │ │
│  │         ↓ HTTPS                                         │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                  Backend Service                        │ │
│  │  ┌──────────────────────────────────────────────────┐  │ │
│  │  │  FastAPI Application                             │  │ │
│  │  │  - Python 3.11                                   │  │ │
│  │  │  - Uvicorn ASGI Server                           │  │ │
│  │  │  - 2 Workers                                     │  │ │
│  │  │  - Auto-Scaling                                  │  │ │
│  │  └──────────────────────────────────────────────────┘  │ │
│  │         ↓                ↓                ↓              │ │
│  └─────────┼────────────────┼────────────────┼─────────────┘ │
│            │                │                │               │
│  ┌─────────▼──────┐  ┌──────▼──────┐  ┌─────▼──────────┐   │
│  │  PostgreSQL    │  │   Redis     │  │  Qdrant Cloud  │   │
│  │  Database      │  │   Cache     │  │  (External)    │   │
│  │  - 256MB RAM   │  │  - 25MB     │  │  - Vector DB   │   │
│  │  - Persistent  │  │  - LRU      │  │  - Embeddings  │   │
│  └────────────────┘  └─────────────┘  └────────────────┘   │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              External Integrations                      │ │
│  │  ┌──────────────────────────────────────────────────┐  │ │
│  │  │  Claude API (Anthropic)                          │  │ │
│  │  │  - Question Generation                           │  │ │
│  │  │  - Rate Limiting: 50 RPM                         │  │ │
│  │  │  - Cost Tracking                                 │  │ │
│  │  └──────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 Request Flow

### 1. Document Upload Flow

```
User → Frontend → Backend API → Document Service
                                      ↓
                              Docling Processing
                                      ↓
                              Text Extraction
                                      ↓
                              Chunking
                                      ↓
                              Embedding Generation
                                      ↓
                              Qdrant Storage
                                      ↓
                              PostgreSQL Metadata
```

### 2. Question Generation Flow

```
User → Frontend → Backend API → RAG Service
                                      ↓
                              Vector Search (Qdrant)
                                      ↓
                              Context Retrieval
                                      ↓
                              Claude API Call
                                      ↓
                              Question Generation
                                      ↓
                              Response to User
```

## 🌐 Network Architecture

### Service Communication

```yaml
Frontend (Static Site):
  - URL: https://examcraft-frontend.onrender.com
  - Protocol: HTTPS
  - CDN: Render Global CDN
  - Caching: Browser + CDN

Backend (Web Service):
  - URL: https://examcraft-backend.onrender.com
  - Protocol: HTTPS
  - Port: Dynamic ($PORT)
  - Workers: 2 (Uvicorn)
  - Health Check: /api/v1/health

PostgreSQL:
  - Internal URL: postgresql://...
  - Connection Pooling: SQLAlchemy
  - SSL: Enabled
  - Backups: Daily (Render)

Redis:
  - Internal URL: redis://...
  - Persistence: RDB Snapshots
  - Eviction: allkeys-lru

Qdrant Cloud:
  - External URL: https://cluster.qdrant.io:6333
  - Protocol: HTTPS
  - API Key: Optional
  - Collections: examcraft_documents
```

## 🔐 Security Architecture

### 1. Network Security

```
Internet → Render Load Balancer → SSL/TLS Termination
                                        ↓
                                   Service Mesh
                                        ↓
                            Internal Service Network
```

### 2. Authentication & Authorization

```yaml
API Security:
  - CORS: Configured Origins
  - Rate Limiting: Claude API (50 RPM)
  - API Keys: Environment Variables
  - Secrets: Render Secret Management

Database Security:
  - SSL Connections: Enforced
  - Credentials: Auto-Rotated
  - Network: Private VPC
  - Backups: Encrypted
```

### 3. Data Security

```yaml
Data at Rest:
  - PostgreSQL: Encrypted Storage
  - Redis: Memory-only (Cache)
  - Qdrant: HTTPS Transport

Data in Transit:
  - All Services: HTTPS/TLS 1.3
  - Internal: Encrypted Mesh
  - API Calls: HTTPS Only
```

## 📊 Monitoring & Observability

### 1. Health Checks

```yaml
Backend Health Check:
  - Endpoint: /api/v1/health
  - Interval: 30s
  - Timeout: 10s
  - Checks:
    - Database Connection
    - Redis Connection
    - Qdrant Connection
    - Claude API Status

Frontend Health Check:
  - Endpoint: /health
  - Interval: 30s
  - Timeout: 3s
  - Check: HTTP 200 Response
```

### 2. Metrics Collection

```yaml
Render Metrics:
  - CPU Usage
  - Memory Usage
  - Request Count
  - Response Time
  - Error Rate
  - Bandwidth

Application Metrics:
  - Claude API Usage
  - Document Processing Time
  - Vector Search Latency
  - Question Generation Time
```

### 3. Logging

```yaml
Log Levels:
  - Production: INFO
  - Development: DEBUG

Log Destinations:
  - Render Dashboard
  - Stdout (Structured JSON)

Log Retention:
  - Free Tier: 7 days
  - Paid Tier: 30+ days
```

## 🚀 Deployment Pipeline

### 1. CI/CD Flow

```
Git Push → GitHub/GitLab → Render Webhook
                                  ↓
                          Build Trigger
                                  ↓
                          Docker Build
                                  ↓
                          Run Tests
                                  ↓
                          Deploy (Blue/Green)
                                  ↓
                          Health Check
                                  ↓
                          Traffic Switch
```

### 2. Rollback Strategy

```yaml
Automatic Rollback:
  - Health Check Fails: Yes
  - Build Fails: Yes
  - Timeout: 10 minutes

Manual Rollback:
  - Render Dashboard: One-Click
  - Previous Versions: Available
  - Instant Switch: < 30s
```

## 📈 Scaling Strategy

### 1. Horizontal Scaling

```yaml
Backend Service:
  - Min Instances: 1
  - Max Instances: 3
  - Scale Trigger: CPU > 70%
  - Scale Down: CPU < 30%

Frontend:
  - Static Site: Auto-CDN
  - No Instance Limit
```

### 2. Vertical Scaling

```yaml
Resource Tiers:
  Starter:
    - RAM: 512MB
    - CPU: 0.5 vCPU
    - Cost: $7/month

  Standard:
    - RAM: 2GB
    - CPU: 1 vCPU
    - Cost: $25/month

  Pro:
    - RAM: 4GB
    - CPU: 2 vCPU
    - Cost: $85/month
```

## 🔧 Configuration Management

### Environment Variables

```yaml
Backend:
  Required:
    - CLAUDE_API_KEY
    - DATABASE_URL (auto)
    - REDIS_URL (auto)
    - QDRANT_URL

  Optional:
    - CORS_ORIGINS
    - CLAUDE_MAX_RPM
    - VECTOR_SERVICE_TYPE

Frontend:
  Required:
    - REACT_APP_API_URL (auto)

  Optional:
    - REACT_APP_ENVIRONMENT
```

## 💾 Data Persistence

### 1. Database Backups

```yaml
PostgreSQL:
  - Frequency: Daily
  - Retention: 7 days (Free), 30 days (Paid)
  - Type: Full Backup
  - Restore: Point-in-Time

Redis:
  - Frequency: Hourly (RDB)
  - Retention: 24 hours
  - Type: Snapshot
  - Restore: Latest Snapshot
```

### 2. Vector Database

```yaml
Qdrant Cloud:
  - Backups: Managed by Qdrant
  - Replication: Multi-AZ
  - Snapshots: On-Demand
  - Export: API Available
```

## 🌍 Geographic Distribution

```yaml
Render Regions:
  Primary: Frankfurt (EU)
  Fallback: Oregon (US)

CDN:
  - Global Edge Locations
  - Automatic Routing
  - Low Latency

Qdrant:
  - Region: EU-Central
  - Latency: < 50ms
```

---

**Architecture Version**: 1.0.0
**Last Updated**: 2025-10-06
**Status**: Production Ready

