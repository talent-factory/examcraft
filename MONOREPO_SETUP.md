# ExamCraft AI - Monorepo Setup Guide

## 📦 Repository Structure

```
examcraft/
├── .gitmodules                 # Git Submodules Configuration
├── packages/
│   ├── core/                   # ✅ Open Source (MIT License)
│   │   ├── backend/            # FastAPI Backend
│   │   ├── frontend/           # React Frontend
│   │   └── README.md
│   ├── premium/                # 🔒 Private Submodule (Proprietary)
│   │   ├── backend/            # Premium Backend Features
│   │   ├── frontend/           # Premium Frontend Components
│   │   └── README.md
│   └── enterprise/             # 🔒 Private Submodule (Proprietary)
│       ├── backend/            # Enterprise Backend Features
│       ├── frontend/           # Enterprise Frontend Components
│       └── README.md
├── docker-compose.yml          # Core Services
├── docker-compose.premium.yml  # Premium Extension
├── docker-compose.enterprise.yml # Enterprise Extension
├── start-dev.sh                # Start Core Only
├── start-dev-premium.sh        # Start Core + Premium
├── start-dev-enterprise.sh     # Start All Packages
└── .env.example                # Environment Configuration Template
```

## 🚀 Quick Start

### 1. Clone Repository

**For Core (Open Source) Development:**
```bash
git clone https://github.com/talent-factory/examcraft.git
cd examcraft
```

**For Premium/Enterprise Development (Requires Access):**
```bash
git clone --recurse-submodules https://github.com/talent-factory/examcraft.git
cd examcraft
```

Or initialize submodules after cloning:
```bash
git submodule update --init --recursive
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Start Development Environment

**Core Only (Free Tier):**
```bash
./start-dev.sh
```

**Core + Premium (Starter/Professional Tier):**
```bash
./start-dev-premium.sh
```

**All Features (Enterprise Tier):**
```bash
./start-dev-enterprise.sh
```

## 📋 Package Details

### Core Package (Open Source)

**License:** MIT  
**Repository:** Main Repository  
**Features:**
- Document Upload (max 5)
- Basic Question Generation (20/month)
- Document Library
- Question Review
- User Management (1 user)
- RBAC System
- GDPR Compliance

**Tech Stack:**
- Backend: FastAPI, PostgreSQL, Redis
- Frontend: React 18, TypeScript, Tailwind CSS
- Auth: JWT, bcrypt

### Premium Package (Closed Source)

**License:** Proprietary  
**Repository:** git@github.com:talent-factory/examcraft-premium.git  
**Tiers:** Starter (€19/month), Professional (€49/month)

**Features:**
- RAG Question Generation (Starter+)
- Document ChatBot (Professional+)
- Advanced Prompt Management (Professional+)
- Semantic Search (Starter+)
- Batch Processing (Starter+)

**Tech Stack:**
- Vector DB: ChromaDB / Qdrant
- RAG: sentence-transformers
- LLM: Claude API (Anthropic)

### Enterprise Package (Closed Source)

**License:** Proprietary  
**Repository:** git@github.com:talent-factory/examcraft-enterprise.git  
**Tier:** Enterprise (€149/month)

**Features:**
- SSO/SAML Integration
- OAuth (Google, Microsoft)
- Custom Branding
- API Access Management
- Advanced Analytics
- LDAP Integration
- On-Premise Deployment

**Tech Stack:**
- SSO: python-saml
- OAuth: authlib
- Analytics: Custom BI Integration

## 🔧 Development Workflow

### Working with Submodules

**Update Submodules:**
```bash
git submodule update --remote --merge
```

**Commit Changes in Submodule:**
```bash
cd packages/premium
git add .
git commit -m "feat: new feature"
git push

cd ../..
git add packages/premium
git commit -m "chore: update premium submodule"
git push
```

**Pull Latest Changes:**
```bash
git pull
git submodule update --init --recursive
```

### Docker Compose Commands

**Core Only:**
```bash
docker-compose up -d
docker-compose logs -f
docker-compose down
```

**Core + Premium:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.premium.yml up -d
docker-compose -f docker-compose.yml -f docker-compose.premium.yml logs -f
docker-compose -f docker-compose.yml -f docker-compose.premium.yml down
```

**All Packages:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.premium.yml -f docker-compose.enterprise.yml up -d
docker-compose -f docker-compose.yml -f docker-compose.premium.yml -f docker-compose.enterprise.yml logs -f
docker-compose -f docker-compose.yml -f docker-compose.premium.yml -f docker-compose.enterprise.yml down
```

## 🧪 Testing

**Core Tests:**
```bash
cd packages/core/backend
pytest

cd ../frontend
npm test
```

**Premium Tests (Requires Submodule Access):**
```bash
cd packages/premium/backend
pytest

cd ../frontend
npm test
```

## 📚 Documentation

- **Core Documentation:** packages/core/README.md
- **Premium Documentation:** packages/premium/README.md (Private)
- **Enterprise Documentation:** packages/enterprise/README.md (Private)
- **API Documentation:** http://localhost:8000/docs (when running)

## 🔐 Access Control

### Public Repository (Core)
- Anyone can clone and use
- MIT License
- Community contributions welcome

### Private Submodules (Premium/Enterprise)
- Requires SSH key access
- Proprietary License
- Internal development only

### Granting Access to Submodules

```bash
# Add collaborator to private repositories
gh repo add-collaborator talent-factory/examcraft-premium <username>
gh repo add-collaborator talent-factory/examcraft-enterprise <username>
```

## 🐛 Troubleshooting

**Submodule not initialized:**
```bash
git submodule update --init --recursive
```

**Permission denied (publickey):**
```bash
# Ensure SSH key is added to GitHub
ssh-add ~/.ssh/id_rsa
ssh -T git@github.com
```

**Docker containers not starting:**
```bash
# Check logs
docker-compose logs

# Rebuild containers
docker-compose build --no-cache
docker-compose up -d
```

## 📞 Support

- **Core (Open Source):** GitHub Issues
- **Premium/Enterprise:** support@talent-factory.ch

---

© 2025 Talent Factory - ExamCraft AI
