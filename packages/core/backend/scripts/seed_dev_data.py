"""
Development Seed Script für ExamCraft AI
Erstellt Test-Daten für lokale Entwicklung:
- Talent Factory Institution (Premium Tier)
- Admin User mit allen Rollen
- RBAC System-Daten (falls noch nicht vorhanden)
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.auth import User, Role, Institution, UserStatus
from models.rbac import RBACRole, SubscriptionTier, Feature
from services.auth_service import AuthService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_talent_factory_institution(db):
    """
    Erstellt Talent Factory Institution mit Premium Tier
    Domain: talent-factory.ch für Auto-Assignment
    """
    logger.info("🏢 Seeding Talent Factory Institution...")

    # Check if already exists
    existing = (
        db.query(Institution).filter(Institution.slug == "talent-factory").first()
    )

    if existing:
        logger.info(f"   ✅ Institution already exists: {existing.name}")
        # Update to ensure Premium tier
        if existing.subscription_tier != "professional":
            existing.subscription_tier = "professional"
            existing.max_users = -1  # Unlimited
            existing.max_documents = -1  # Unlimited
            existing.max_questions_per_month = 1000
            db.commit()
            logger.info("   ✅ Updated to Professional tier")
        return existing

    # Create new institution
    institution = Institution(
        name="Talent Factory",
        slug="talent-factory",
        domain="talent-factory.ch",  # Auto-assign users with @talent-factory.ch
        subscription_tier="professional",  # Premium tier
        max_users=-1,  # Unlimited
        max_documents=-1,  # Unlimited
        max_questions_per_month=1000,
        is_active=True,
    )

    db.add(institution)
    db.commit()
    db.refresh(institution)

    logger.info(f"   ✅ Created: {institution.name} (ID: {institution.id})")
    logger.info(f"   📧 Domain: {institution.domain}")
    logger.info(f"   💎 Tier: {institution.subscription_tier}")

    return institution


def seed_admin_user(db, institution):
    """
    Erstellt Admin-User für Development
    Email: admin@talent-factory.ch
    Password: admin123 (nur für Development!)
    """
    logger.info("👤 Seeding Admin User...")

    admin_email = "admin@talent-factory.ch"

    # Check if already exists
    existing = db.query(User).filter(User.email == admin_email).first()

    if existing:
        logger.info(f"   ✅ Admin user already exists: {existing.email}")
        return existing

    # Get all roles
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    dozent_role = db.query(Role).filter(Role.name == "dozent").first()
    assistant_role = db.query(Role).filter(Role.name == "assistant").first()

    if not admin_role:
        logger.warning("   ⚠️  Admin role not found - run seed_rbac_data.py first!")
        return None

    # Create admin user
    admin_user = User(
        email=admin_email,
        password_hash=AuthService.get_password_hash("admin123"),  # Development only!
        first_name="Admin",
        last_name="User",
        institution_id=institution.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=True,  # Superuser privileges
        is_email_verified=True,
    )

    db.add(admin_user)
    db.flush()  # Get user.id

    # Assign all roles
    if admin_role:
        admin_user.roles.append(admin_role)
    if dozent_role:
        admin_user.roles.append(dozent_role)
    if assistant_role:
        admin_user.roles.append(assistant_role)

    db.commit()
    db.refresh(admin_user)

    logger.info(f"   ✅ Created: {admin_user.email} (ID: {admin_user.id})")
    logger.info("   🔑 Password: admin123 (DEVELOPMENT ONLY!)")
    logger.info(f"   👑 Superuser: {admin_user.is_superuser}")
    logger.info(f"   🎭 Roles: {[r.name for r in admin_user.roles]}")

    return admin_user


def seed_rbac_data_if_needed(db):
    """
    Seeded RBAC-Daten falls noch nicht vorhanden
    Ruft seed_rbac_data.py auf
    """
    logger.info("🔐 Checking RBAC data...")

    # Check if roles exist
    role_count = db.query(RBACRole).count()
    tier_count = db.query(SubscriptionTier).count()
    feature_count = db.query(Feature).count()

    if role_count > 0 and tier_count > 0 and feature_count > 0:
        logger.info(
            f"   ✅ RBAC data already seeded ({role_count} roles, {tier_count} tiers, {feature_count} features)"
        )
        return

    logger.info("   🌱 Seeding RBAC data...")

    # Import and run RBAC seed script
    try:
        from scripts.seed_rbac_data import (
            seed_features,
            seed_rbac_roles,
            seed_role_features,
            seed_subscription_tiers,
            seed_tier_quotas,
            seed_tier_features,
        )

        seed_features(db)
        seed_rbac_roles(db)
        seed_role_features(db)
        seed_subscription_tiers(db)
        seed_tier_quotas(db)
        seed_tier_features(db)

        logger.info("   ✅ RBAC data seeded successfully")
    except Exception as e:
        logger.error(f"   ❌ Error seeding RBAC data: {e}")
        raise


def seed_default_roles_if_needed(db):
    """
    Seeded Default Roles (auth.Role) falls noch nicht vorhanden
    """
    logger.info("🎭 Checking default roles...")

    # Check if roles exist
    role_count = db.query(Role).count()

    if role_count > 0:
        logger.info(f"   ✅ Default roles already seeded ({role_count} roles)")
        return

    logger.info("   🌱 Seeding default roles...")

    # Import and run role seed script
    try:
        from utils.seed_roles import seed_default_roles

        created, updated = seed_default_roles(db)
        logger.info(f"   ✅ Default roles seeded: {created} created, {updated} updated")
    except Exception as e:
        logger.error(f"   ❌ Error seeding default roles: {e}")
        raise


def main():
    """
    Hauptfunktion zum Seeden aller Development-Daten
    """
    print("\n" + "=" * 60)
    print("🌱 ExamCraft AI - Development Data Seeding")
    print("=" * 60 + "\n")

    db = SessionLocal()
    try:
        # 1. Seed RBAC data (if needed)
        seed_rbac_data_if_needed(db)

        # 2. Seed default roles (if needed)
        seed_default_roles_if_needed(db)

        # 3. Seed Talent Factory Institution
        institution = seed_talent_factory_institution(db)

        # 4. Seed Admin User
        if institution:
            seed_admin_user(db, institution)

        print("\n" + "=" * 60)
        print("✅ Development Data Seeding Complete!")
        print("=" * 60)
        print("\n📋 Summary:")
        print("   - Institution: Talent Factory (Professional Tier)")
        print("   - Domain: talent-factory.ch (Auto-Assignment)")
        print("   - Admin User: admin@talent-factory.ch")
        print("   - Password: admin123 (DEVELOPMENT ONLY!)")
        print("\n💡 Next Steps:")
        print("   1. Login with admin@talent-factory.ch / admin123")
        print("   2. Any user with @talent-factory.ch email will be auto-assigned")
        print("   3. OAuth users with @talent-factory.ch will join this institution")
        print("\n")

    except Exception as e:
        logger.error(f"\n❌ Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
