"""
Seed Script für RBAC System-Daten
Erstellt System-Rollen, Features, Subscription Tiers und Default-Mappings
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.rbac import (
    Feature, RBACRole, RoleFeature,
    SubscriptionTier, TierQuota, TierFeature
)


def seed_features(db):
    """Erstellt alle Feature-Definitionen"""
    features = [
        # Generation Features
        ('feat_question_gen_ai', 'question_generation_ai', 'KI-Prüfung erstellen', 
         'Generierung von Prüfungsfragen mit Claude AI', 'generation'),
        ('feat_doc_upload', 'document_upload', 'Dokumente hochladen', 
         'Upload von PDF, DOCX, Markdown Dokumenten', 'management'),
        ('feat_doc_library', 'document_library', 'Dokumentenbibliothek', 
         'Verwaltung und Durchsuchung von Dokumenten', 'management'),
        ('feat_rag_gen', 'rag_generation', 'RAG-Prüfung erstellen', 
         'RAG-basierte Prüfungserstellung aus Dokumenten', 'generation'),
        ('feat_chatbot', 'document_chatbot', 'Dokument ChatBot', 
         'Interaktive Konversation mit Dokumenten (NotebookLM-Style)', 'generation'),
        ('feat_review', 'question_review', 'Question Review', 
         'Review und Approval Workflow für generierte Fragen', 'management'),
        ('feat_prompts', 'prompt_management', 'Prompt Management', 
         'Verwaltung der Prompt Knowledge Base', 'administration'),
        ('feat_users', 'user_management', 'Benutzerverwaltung', 
         'Verwaltung von Benutzern und Rollen', 'administration'),
        ('feat_config', 'system_configuration', 'System-Konfiguration', 
         'Konfiguration von System-Einstellungen', 'administration'),
        ('feat_analytics', 'analytics_dashboard', 'Analytics Dashboard', 
         'Berichte und Statistiken', 'management'),
        ('feat_api', 'api_access', 'API Zugriff', 
         'Zugriff auf REST API', 'integration'),
        ('feat_sso', 'sso_integration', 'SSO Integration', 
         'SAML/SSO Single Sign-On', 'integration'),
        ('feat_branding', 'custom_branding', 'Custom Branding', 
         'White-Label Branding', 'integration'),
    ]
    
    for feat_id, name, display_name, description, category in features:
        existing = db.query(Feature).filter(Feature.id == feat_id).first()
        if not existing:
            feature = Feature(
                id=feat_id,
                name=name,
                display_name=display_name,
                description=description,
                category=category,
                is_active=True
            )
            db.add(feature)
    
    db.commit()
    print(f"✅ {len(features)} Features erstellt")


def seed_rbac_roles(db):
    """Erstellt System-Rollen"""
    roles = [
        ('role_admin', 'admin', 'Administrator', 
         'Vollzugriff auf alle Funktionen und Einstellungen', True),
        ('role_dozent', 'dozent', 'Dozent', 
         'Erstellt Prüfungen, verwaltet Dokumente, nutzt KI-Features', True),
        ('role_assistant', 'assistant', 'Assistent', 
         'Unterstützt bei Prüfungserstellung, limitierter Zugriff', True),
        ('role_viewer', 'viewer', 'Betrachter', 
         'Nur Lesezugriff, keine Änderungen', True),
    ]
    
    for role_id, name, display_name, description, is_system in roles:
        existing = db.query(RBACRole).filter(RBACRole.id == role_id).first()
        if not existing:
            role = RBACRole(
                id=role_id,
                name=name,
                display_name=display_name,
                description=description,
                is_system_role=is_system,
                is_active=True
            )
            db.add(role)
    
    db.commit()
    print(f"✅ {len(roles)} RBAC-Rollen erstellt")


def seed_role_features(db):
    """Erstellt Role-Feature Mappings"""
    # Admin: Alle Features
    admin_features = db.query(Feature).all()
    for feature in admin_features:
        existing = db.query(RoleFeature).filter(
            RoleFeature.role_id == 'role_admin',
            RoleFeature.feature_id == feature.id
        ).first()
        if not existing:
            db.add(RoleFeature(role_id='role_admin', feature_id=feature.id))
    
    # Dozent: Generation + Management Features
    dozent_features = [
        'feat_question_gen_ai', 'feat_doc_upload', 'feat_doc_library',
        'feat_rag_gen', 'feat_chatbot', 'feat_review', 'feat_prompts', 'feat_analytics'
    ]
    for feat_id in dozent_features:
        existing = db.query(RoleFeature).filter(
            RoleFeature.role_id == 'role_dozent',
            RoleFeature.feature_id == feat_id
        ).first()
        if not existing:
            db.add(RoleFeature(role_id='role_dozent', feature_id=feat_id))
    
    # Assistant: Limitierte Features
    assistant_features = ['feat_doc_library', 'feat_review', 'feat_analytics']
    for feat_id in assistant_features:
        existing = db.query(RoleFeature).filter(
            RoleFeature.role_id == 'role_assistant',
            RoleFeature.feature_id == feat_id
        ).first()
        if not existing:
            db.add(RoleFeature(role_id='role_assistant', feature_id=feat_id))
    
    # Viewer: Nur Lesezugriff
    viewer_features = ['feat_doc_library', 'feat_analytics']
    for feat_id in viewer_features:
        existing = db.query(RoleFeature).filter(
            RoleFeature.role_id == 'role_viewer',
            RoleFeature.feature_id == feat_id
        ).first()
        if not existing:
            db.add(RoleFeature(role_id='role_viewer', feature_id=feat_id))
    
    db.commit()
    print("✅ Role-Feature Mappings erstellt")


def seed_subscription_tiers(db):
    """Erstellt Subscription Tiers"""
    tiers = [
        ('tier_free', 'free', 'Free', 'Kostenloser Basis-Zugang', 0.00, 0.00, 1),
        ('tier_starter', 'starter', 'Starter', 'Für einzelne Dozenten', 19.00, 190.00, 2),
        ('tier_professional', 'professional', 'Professional', 'Für kleine Teams', 49.00, 490.00, 3),
        ('tier_enterprise', 'enterprise', 'Enterprise', 'Für Organisationen', 149.00, 1490.00, 4),
    ]
    
    for tier_id, name, display_name, description, price_monthly, price_yearly, sort_order in tiers:
        existing = db.query(SubscriptionTier).filter(SubscriptionTier.id == tier_id).first()
        if not existing:
            tier = SubscriptionTier(
                id=tier_id,
                name=name,
                display_name=display_name,
                description=description,
                price_monthly=price_monthly,
                price_yearly=price_yearly,
                is_active=True,
                sort_order=sort_order
            )
            db.add(tier)
    
    db.commit()
    print(f"✅ {len(tiers)} Subscription Tiers erstellt")


def seed_tier_quotas(db):
    """Erstellt Tier-Quotas"""
    quotas = [
        # Free Tier
        ('tier_free', 'documents', 5),
        ('tier_free', 'questions_per_month', 20),
        ('tier_free', 'users', 1),
        ('tier_free', 'storage_mb', 100),
        # Starter Tier
        ('tier_starter', 'documents', 50),
        ('tier_starter', 'questions_per_month', 200),
        ('tier_starter', 'users', 3),
        ('tier_starter', 'storage_mb', 1000),
        # Professional Tier
        ('tier_professional', 'documents', -1),  # Unlimited
        ('tier_professional', 'questions_per_month', 1000),
        ('tier_professional', 'users', 10),
        ('tier_professional', 'storage_mb', 10000),
        # Enterprise Tier (Unlimited)
        ('tier_enterprise', 'documents', -1),
        ('tier_enterprise', 'questions_per_month', -1),
        ('tier_enterprise', 'users', -1),
        ('tier_enterprise', 'storage_mb', -1),
    ]
    
    for tier_id, resource_type, quota_limit in quotas:
        existing = db.query(TierQuota).filter(
            TierQuota.tier_id == tier_id,
            TierQuota.resource_type == resource_type
        ).first()
        if not existing:
            quota = TierQuota(
                tier_id=tier_id,
                resource_type=resource_type,
                quota_limit=quota_limit
            )
            db.add(quota)
    
    db.commit()
    print(f"✅ {len(quotas)} Tier-Quotas erstellt")


def seed_tier_features(db):
    """Erstellt Tier-Feature Mappings"""
    # Free: Basis Features
    free_features = ['feat_question_gen_ai', 'feat_doc_upload', 'feat_doc_library']
    for feat_id in free_features:
        existing = db.query(TierFeature).filter(
            TierFeature.tier_id == 'tier_free',
            TierFeature.feature_id == feat_id
        ).first()
        if not existing:
            db.add(TierFeature(tier_id='tier_free', feature_id=feat_id))
    
    # Starter: Free + RAG + Review
    starter_features = free_features + ['feat_rag_gen', 'feat_review']
    for feat_id in starter_features:
        existing = db.query(TierFeature).filter(
            TierFeature.tier_id == 'tier_starter',
            TierFeature.feature_id == feat_id
        ).first()
        if not existing:
            db.add(TierFeature(tier_id='tier_starter', feature_id=feat_id))
    
    # Professional: Starter + ChatBot + Prompts + Analytics
    professional_features = starter_features + ['feat_chatbot', 'feat_prompts', 'feat_analytics']
    for feat_id in professional_features:
        existing = db.query(TierFeature).filter(
            TierFeature.tier_id == 'tier_professional',
            TierFeature.feature_id == feat_id
        ).first()
        if not existing:
            db.add(TierFeature(tier_id='tier_professional', feature_id=feat_id))
    
    # Enterprise: Alle Features
    enterprise_features = db.query(Feature).all()
    for feature in enterprise_features:
        existing = db.query(TierFeature).filter(
            TierFeature.tier_id == 'tier_enterprise',
            TierFeature.feature_id == feature.id
        ).first()
        if not existing:
            db.add(TierFeature(tier_id='tier_enterprise', feature_id=feature.id))
    
    db.commit()
    print("✅ Tier-Feature Mappings erstellt")


def main():
    """Hauptfunktion zum Seeden aller RBAC-Daten"""
    print("🌱 Starte RBAC Seed-Prozess...")
    
    db = SessionLocal()
    try:
        seed_features(db)
        seed_rbac_roles(db)
        seed_role_features(db)
        seed_subscription_tiers(db)
        seed_tier_quotas(db)
        seed_tier_features(db)
        
        print("\n✅ RBAC Seed-Prozess erfolgreich abgeschlossen!")
    except Exception as e:
        print(f"\n❌ Fehler beim Seeden: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

