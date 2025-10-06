# Qdrant auf Render.com deployen

## 🎯 Übersicht

Es gibt drei Optionen, um Qdrant für ExamCraft AI zu verwenden:

1. **Qdrant als Render.com Web Service** (empfohlen für Konsistenz)
2. **Qdrant Cloud** (empfohlen für Production)
3. **Mock Service** (nur für Testing)

## Option 1: Qdrant als Render.com Web Service

### Manuelles Setup im Dashboard

Da der Render MCP Server keine Docker-Image Deployments unterstützt, müssen Sie Qdrant manuell im Dashboard erstellen:

#### Schritt 1: Neuen Web Service erstellen

1. Gehe zu https://dashboard.render.com
2. Klicke auf "New +" → "Web Service"
3. Verbinde dein ExamCraft Repository

#### Schritt 2: Service konfigurieren

```yaml
Name: examcraft-qdrant
Region: Frankfurt
Branch: feature/tf-108-render-deployment

Runtime: Docker
Dockerfile Path: docker/Qdrant.Dockerfile
Docker Context: .

Plan: Starter ($7/month)
# Hinweis: Qdrant benötigt persistenten Storage, daher kein Free Tier
```

#### Schritt 3: Environment Variables

```bash
QDRANT__SERVICE__HTTP_PORT=6333
QDRANT__SERVICE__GRPC_PORT=6334
QDRANT__LOG_LEVEL=INFO
```

#### Schritt 4: Disk Storage hinzufügen

**Wichtig**: Qdrant benötigt persistenten Storage!

```yaml
Mount Path: /qdrant/storage
Size: 1 GB (Free) oder mehr
```

Im Dashboard:
1. Gehe zu Service Settings
2. "Disks" Tab
3. "Add Disk"
   - Name: `qdrant-storage`
   - Mount Path: `/qdrant/storage`
   - Size: `1` GB

#### Schritt 5: Backend Service aktualisieren

Nach dem Qdrant-Deployment, aktualisiere die Backend Environment Variables:

```bash
# Im Backend Service (srv-d3hn0nggjchc73akgbb0):
QDRANT_URL=https://examcraft-qdrant.onrender.com
VECTOR_SERVICE_TYPE=qdrant
```

### Automatisches Setup via render.yaml

Alternativ können Sie die `render.yaml` erweitern:

```yaml
# In render.yaml hinzufügen:
services:
  # ... existing services ...
  
  # Qdrant Vector Database
  - type: web
    name: examcraft-qdrant
    runtime: docker
    plan: starter
    region: frankfurt
    branch: feature/tf-108-render-deployment
    dockerfilePath: ./docker/Qdrant.Dockerfile
    dockerContext: .
    disk:
      name: qdrant-storage
      mountPath: /qdrant/storage
      sizeGB: 1
    envVars:
      - key: QDRANT__SERVICE__HTTP_PORT
        value: 6333
      - key: QDRANT__SERVICE__GRPC_PORT
        value: 6334
      - key: QDRANT__LOG_LEVEL
        value: INFO
    healthCheckPath: /
```

Dann Blueprint neu deployen.

## Option 2: Qdrant Cloud (Empfohlen für Production)

### Vorteile
- ✅ Managed Service (keine Wartung)
- ✅ Automatische Backups
- ✅ Bessere Performance
- ✅ Kostenloser Tier verfügbar
- ✅ Multi-AZ Redundanz

### Setup

#### Schritt 1: Qdrant Cloud Account

1. Gehe zu https://cloud.qdrant.io
2. Registriere dich (kostenlos)
3. Erstelle neuen Cluster:
   - Name: `examcraft-production`
   - Region: `EU-Central` (Frankfurt)
   - Plan: `Free` (1GB) oder `Starter`

#### Schritt 2: Cluster URL kopieren

Nach Erstellung erhältst du:
```
Cluster URL: https://abc-xyz-123.qdrant.io:6333
API Key: qdr_xxxxxxxxxxxxxxxxxxxxxxxx
```

#### Schritt 3: Backend konfigurieren

Im Render.com Backend Service Environment:

```bash
QDRANT_URL=https://abc-xyz-123.qdrant.io:6333
QDRANT_API_KEY=qdr_xxxxxxxxxxxxxxxxxxxxxxxx
VECTOR_SERVICE_TYPE=qdrant
```

#### Schritt 4: Qdrant Service Code anpassen

Die `backend/services/qdrant_vector_service.py` unterstützt bereits API Keys:

```python
# Wird automatisch aus Environment geladen:
qdrant_url = os.getenv("QDRANT_URL")
api_key = os.getenv("QDRANT_API_KEY")  # Optional
```

## Option 3: Mock Service (Nur Testing)

Für schnelles Testing ohne Qdrant:

```bash
# Im Backend Service:
VECTOR_SERVICE_TYPE=mock
```

**Hinweis**: Mock Service hat keine echte Vector Search, nur für UI-Tests!

## Vergleich der Optionen

| Feature | Render Service | Qdrant Cloud | Mock |
|---------|---------------|--------------|------|
| **Kosten** | $7/Monat | Free - $25/Monat | Kostenlos |
| **Setup** | Manuell | 5 Minuten | Sofort |
| **Performance** | Gut | Sehr gut | N/A |
| **Wartung** | Selbst | Managed | N/A |
| **Backups** | Manuell | Automatisch | N/A |
| **Skalierung** | Manuell | Automatisch | N/A |
| **Production** | ✅ Ja | ✅ Ja | ❌ Nein |

## Empfehlung

### Für Development/Testing
→ **Mock Service** oder **Qdrant Cloud Free Tier**

### Für Production
→ **Qdrant Cloud** (einfacher, zuverlässiger, managed)

### Für Self-Hosted Production
→ **Render.com Web Service** (volle Kontrolle, aber mehr Wartung)

## Troubleshooting

### Qdrant Service startet nicht auf Render

**Problem**: Docker Build schlägt fehl

**Lösung**:
```bash
# Prüfe Dockerfile Syntax
docker build -f docker/Qdrant.Dockerfile .

# Stelle sicher, dass Disk Storage konfiguriert ist
```

### Connection zu Qdrant fehlgeschlagen

**Problem**: Backend kann Qdrant nicht erreichen

**Lösung**:
```bash
# Prüfe QDRANT_URL Format:
# Render Service: https://examcraft-qdrant.onrender.com
# Qdrant Cloud: https://cluster-id.qdrant.io:6333

# Teste Verbindung:
curl https://your-qdrant-url/collections
```

### Qdrant Daten gehen verloren

**Problem**: Nach Restart sind Collections weg

**Lösung**:
```bash
# Stelle sicher, dass Disk Storage gemountet ist:
# Mount Path: /qdrant/storage
# Size: mindestens 1GB

# Prüfe in Qdrant Logs ob Storage erkannt wird
```

## Migration von lokalem Qdrant zu Cloud

Falls Sie bereits Daten in lokalem Qdrant haben:

```bash
# 1. Lokale Daten exportieren
python scripts/export_qdrant_data.py

# 2. Zu Qdrant Cloud hochladen
python scripts/import_to_qdrant_cloud.py \
  --url https://your-cluster.qdrant.io:6333 \
  --api-key your_api_key \
  --data-file qdrant_export.json
```

---

**Empfehlung**: Starten Sie mit **Qdrant Cloud Free Tier** für schnelles Setup, upgraden Sie später bei Bedarf.

