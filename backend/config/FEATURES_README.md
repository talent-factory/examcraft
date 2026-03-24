# Feature-Flag-System (TF-149)

ExamCraft AI nutzt ein Feature-basiertes Zugriffskontrollsystem basierend auf Subscription Tiers gemäß der **TF-116 Monetarisierungsstrategie**.

## 📋 Übersicht

### Subscription Tiers

| Tier | Monatlich | Features | Quotas |
|------|-----------|----------|--------|
| **Free** | €0 | Basic Features | 5 Docs, 20 Questions/Monat, 1 User |
| **Starter** | €19 | + RAG, Templates | 50 Docs, 200 Questions/Monat, 3 Users |
| **Professional** | €49 | + ChatBot, Analytics | Unlimited Docs, 1000 Questions/Monat, 10 Users |
| **Enterprise** | €149 | + SSO, API, Custom | Unlimited Everything |

### Verfügbare Features

```python
# Core Features (Free Tier)
Feature.DOCUMENT_UPLOAD
Feature.BASIC_QUESTION_GENERATION
Feature.DOCUMENT_LIBRARY

# Starter Tier
Feature.RAG_GENERATION
Feature.PROMPT_TEMPLATES
Feature.BATCH_PROCESSING

# Professional Tier
Feature.DOCUMENT_CHATBOT              # TF-111
Feature.ADVANCED_PROMPT_MANAGEMENT    # TF-122
Feature.ANALYTICS_DASHBOARD
Feature.QUESTION_REVIEW_WORKFLOW      # TF-60
Feature.EXPORT_FORMATS

# Enterprise Tier
Feature.SSO_INTEGRATION
Feature.CUSTOM_BRANDING
Feature.API_ACCESS
Feature.LDAP_INTEGRATION
Feature.AUDIT_LOGS
Feature.MULTI_ORGANIZATION
```

## 🔧 Nutzung

### 1. Feature-Gate via Decorator

```python
from fastapi import APIRouter, Depends
from backend.middleware.feature_gate import require_feature
from backend.config.features import Feature

@router.post("/chatbot/query")
@require_feature(Feature.DOCUMENT_CHATBOT)
async def chatbot_query(user: User = Depends(get_current_user)):
    # Nur für Professional+ Tier
    return {"response": "..."}
```

**Resultat bei Free-Tier User:**
```json
{
  "detail": "Feature 'document_chatbot' ist nicht in Ihrem aktuellen Plan (free) verfügbar. Bitte upgraden Sie Ihren Plan."
}
```

### 2. Manuelle Feature-Prüfung

```python
from backend.middleware.feature_gate import check_feature_access, get_user_tier

@router.get("/dashboard")
async def dashboard(user: User = Depends(get_current_user)):
    tier = get_user_tier(user)

    # Zeige unterschiedliche Inhalte basierend auf Tier
    if check_feature_access(user, Feature.ANALYTICS_DASHBOARD):
        return {"advanced_analytics": {...}}
    else:
        return {"basic_stats": {...}}
```

### 3. Quota-Check

```python
from backend.middleware.feature_gate import require_quota

@router.post("/documents/upload")
@require_quota("max_documents")
async def upload_document(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Automatischer Quota-Check
    return {"message": "Document uploaded"}
```

**Resultat bei Quota-Überschreitung:**
```json
{
  "detail": "Quota 'max_documents' überschritten: 5/5 verwendet. Ihr aktueller Plan: free. Bitte upgraden Sie Ihren Plan für höhere Limits."
}
```

### 4. Batch-Operationen mit Custom Increment

```python
from backend.middleware.feature_gate import check_quota, get_current_usage

@router.post("/batch-generate")
async def batch_generate(
    count: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Manuelle Quota-Prüfung für mehrere Items
    current_usage = get_current_usage(db, user, "max_questions_per_month")
    check_quota(user, "max_questions_per_month", current_usage, increment=count)

    # Generiere Fragen...
    return {"generated": count}
```

## 🗄️ Datenbank-Schema

### Institution Model

```python
class Institution(Base):
    # Subscription
    subscription_tier = Column(String, default="free")  # free, starter, professional, enterprise
    features_enabled = Column(ARRAY(String))  # Optional: Manuelle Feature-Overrides

    # Quotas
    max_documents = Column(Integer, default=5)
    max_questions_per_month = Column(Integer, default=20)
    max_users = Column(Integer, default=1)

    # Helper Methods
    def has_feature(self, feature: str) -> bool:
        """Prüft Feature-Zugriff (Tier + manuelle Overrides)"""

    def get_quota(self, quota_name: str) -> int:
        """Gibt Quota-Limit zurück"""
```

### Migration

```bash
# Migration anwenden (via Docker oder lokal)
docker-compose exec backend alembic upgrade head

# Oder lokal:
cd backend
alembic upgrade head
```

## 🎨 Frontend-Integration

### Feature-Visibility im React-Frontend

```typescript
// frontend/src/hooks/useFeatureAccess.ts
export const useFeatureAccess = (feature: Feature) => {
  const { user } = useAuth();

  const hasAccess = useMemo(() => {
    if (!user?.institution) return false;
    return checkFeatureAccess(user.institution.subscription_tier, feature);
  }, [user, feature]);

  return hasAccess;
};

// Usage in Component:
const ChatBotButton = () => {
  const hasAccess = useFeatureAccess(Feature.DOCUMENT_CHATBOT);

  if (!hasAccess) {
    return <UpgradePrompt feature="ChatBot" requiredTier="professional" />;
  }

  return <Button onClick={openChatBot}>ChatBot öffnen</Button>;
};
```

## 🔄 Tier-Upgrades

### Upgrade durchführen

```python
# backend/api/billing.py
@router.post("/upgrade")
async def upgrade_tier(
    new_tier: SubscriptionTier,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    institution = user.institution

    # Update Tier
    institution.subscription_tier = new_tier.value

    # Update Quotas basierend auf Tier
    from backend.config.features import TIER_QUOTAS
    quotas = TIER_QUOTAS[new_tier]
    institution.max_documents = quotas["max_documents"]
    institution.max_questions_per_month = quotas["max_questions_per_month"]
    institution.max_users = quotas["max_users"]

    db.commit()

    return {"message": f"Upgraded to {new_tier.value}"}
```

## 🧪 Testing

```python
# backend/tests/test_feature_gate.py
import pytest
from backend.config.features import SubscriptionTier, Feature, has_feature

def test_free_tier_features():
    # Free Tier hat nur Basic Features
    assert has_feature(SubscriptionTier.FREE, Feature.DOCUMENT_UPLOAD)
    assert not has_feature(SubscriptionTier.FREE, Feature.DOCUMENT_CHATBOT)

def test_professional_tier_features():
    # Professional hat ChatBot
    assert has_feature(SubscriptionTier.PROFESSIONAL, Feature.DOCUMENT_CHATBOT)
    assert has_feature(SubscriptionTier.PROFESSIONAL, Feature.ANALYTICS_DASHBOARD)

def test_enterprise_tier_has_all():
    # Enterprise hat alle Features
    assert has_feature(SubscriptionTier.ENTERPRISE, Feature.SSO_INTEGRATION)
    assert has_feature(SubscriptionTier.ENTERPRISE, Feature.CUSTOM_BRANDING)
```

## 📊 Analytics & Tracking

### Feature-Usage Tracking

```python
# backend/services/analytics_service.py
async def track_feature_usage(
    user: User,
    feature: Feature,
    db: Session
):
    """Trackt Feature-Nutzung für Analytics"""
    from backend.models.analytics import FeatureUsageLog

    log = FeatureUsageLog(
        user_id=user.id,
        institution_id=user.institution_id,
        feature=feature.value,
        tier=user.institution.subscription_tier
    )
    db.add(log)
    db.commit()
```

## 🔐 Manuelle Feature-Overrides (Enterprise)

Enterprise-Kunden können individuelle Features freischalten:

```python
# Admin-Interface: Feature manuell freischalten
institution.features_enabled = ["custom_feature_alpha", "beta_feature_xyz"]
db.commit()

# Prüfung berücksichtigt Overrides:
institution.has_feature("custom_feature_alpha")  # True, auch wenn nicht in Tier
```

## 🚀 Deployment Notes

### Environment Variables

```bash
# .env
SUBSCRIPTION_TIER_DEFAULT=free  # Für neue Institutionen
```

### Open Source vs. SaaS

**Open Source (GitHub):**
- Default: `FREE` Tier
- Features können manuell freigeschaltet werden (via DB)

**SaaS (Render.com):**
- Stripe-Integration für Tier-Upgrades
- Automatisches Feature-Gating
- Usage-Tracking für Billing

## 📚 Weitere Dokumentation

- **TF-116**: Monetarisierungsstrategie
- **TF-149**: Dynamisches RBAC-System
- **TF-113**: Render.com Freemium Setup
