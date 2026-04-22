"""
E2E Test Data Setup Script for ExamCraft AI
Creates test user and test documents for Playwright E2E tests

Usage:
    python scripts/setup_e2e_test_data.py
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.auth import User, Role, Institution, UserStatus
from models.document import Document, DocumentStatus
from services.auth_service import AuthService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# E2E Test credentials (must match e2e/fixtures/auth.ts)
E2E_TEST_USER = {
    "email": "e2e-test@example.com",
    "password": "E2ETestPassword123",  # pragma: allowlist secret
    "first_name": "E2E",
    "last_name": "Testuser",
}


def setup_e2e_institution(db):
    """Create E2E Test Institution"""
    logger.info("Setting up E2E Test Institution...")

    existing = db.query(Institution).filter(Institution.slug == "e2e-test").first()

    if existing:
        logger.info(f"   Institution already exists: {existing.name}")
        return existing

    institution = Institution(
        name="E2E Test Institution",
        slug="e2e-test",
        domain="examcraft.test",
        subscription_tier="professional",  # Full feature access for testing
        max_users=-1,
        max_documents=-1,
        max_questions_per_month=-1,
        is_active=True,
    )

    db.add(institution)
    db.commit()
    db.refresh(institution)

    logger.info(f"   Created institution: {institution.name} (ID: {institution.id})")
    return institution


def setup_e2e_user(db, institution):
    """Create E2E Test User"""
    logger.info("Setting up E2E Test User...")

    existing = db.query(User).filter(User.email == E2E_TEST_USER["email"]).first()

    if existing:
        logger.info(f"   User already exists: {existing.email}")
        # Update password to ensure it matches
        existing.password_hash = AuthService.get_password_hash(
            E2E_TEST_USER["password"]
        )
        db.commit()
        return existing

    # Get dozent role for test user
    dozent_role = db.query(Role).filter(Role.name == "dozent").first()

    user = User(
        email=E2E_TEST_USER["email"],
        password_hash=AuthService.get_password_hash(E2E_TEST_USER["password"]),
        first_name=E2E_TEST_USER["first_name"],
        last_name=E2E_TEST_USER["last_name"],
        institution_id=institution.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
        is_email_verified=True,
    )

    db.add(user)
    db.flush()

    if dozent_role:
        user.roles.append(dozent_role)

    db.commit()
    db.refresh(user)

    logger.info(f"   Created user: {user.email} (ID: {user.id})")
    return user


def setup_e2e_documents(db, user, institution):
    """Create test documents for E2E tests"""
    logger.info("Setting up E2E Test Documents...")

    # Check if test document already exists
    existing = (
        db.query(Document)
        .filter(
            Document.user_id == user.id,
            Document.original_filename == "e2e-test-document.pdf",
        )
        .first()
    )

    if existing:
        logger.info(f"   Test document already exists: {existing.original_filename}")
        return [existing]

    # Create a test document (simulated, no actual file needed)
    doc = Document(
        filename="e2e-test-document.pdf",
        original_filename="e2e-test-document.pdf",
        file_path="/tmp/e2e-test-document.pdf",
        file_size=1024,
        mime_type="application/pdf",
        status=DocumentStatus.COMPLETED,
        user_id=user.id,
        institution_id=institution.id,
        content_preview="Dies ist ein Test-Dokument für E2E Tests. "
        "Es enthält Informationen über Datenstrukturen wie Heapsort, "
        "Priority Queues und Binäre Suchbäume.",
        has_vectors=False,  # No actual vectors needed for basic E2E tests
    )

    db.add(doc)
    db.commit()
    db.refresh(doc)

    logger.info(f"   Created test document: {doc.original_filename} (ID: {doc.id})")
    return [doc]


def cleanup_e2e_data(db):
    """Remove all E2E test data (optional cleanup)"""
    logger.info("Cleaning up E2E Test Data...")

    user = db.query(User).filter(User.email == E2E_TEST_USER["email"]).first()
    if user:
        # Delete user's documents
        db.query(Document).filter(Document.user_id == user.id).delete()
        # Delete user
        db.delete(user)

    institution = db.query(Institution).filter(Institution.slug == "e2e-test").first()
    if institution:
        db.delete(institution)

    db.commit()
    logger.info("   E2E data cleaned up")


def main():
    """Main function to setup E2E test data"""
    print("\n" + "=" * 60)
    print("ExamCraft AI - E2E Test Data Setup")
    print("=" * 60 + "\n")

    db = SessionLocal()
    try:
        # 1. Setup Institution
        institution = setup_e2e_institution(db)

        # 2. Setup User
        user = setup_e2e_user(db, institution)

        # 3. Setup Documents
        documents = setup_e2e_documents(db, user, institution)

        print("\n" + "=" * 60)
        print("E2E Test Data Setup Complete!")
        print("=" * 60)
        print("\nTest Credentials:")
        print(f"   Email: {E2E_TEST_USER['email']}")
        print(f"   Password: {E2E_TEST_USER['password']}")
        print(f"\nTest Documents: {len(documents)} document(s) created")
        print("\nRun E2E tests with:")
        print("   just e2e")
        print("   just e2e-ui  (interactive mode)")
        print("\n")

    except Exception as e:
        logger.error(f"\nError during setup: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="E2E Test Data Setup")
    parser.add_argument("--cleanup", action="store_true", help="Remove E2E test data")
    args = parser.parse_args()

    if args.cleanup:
        db = SessionLocal()
        try:
            cleanup_e2e_data(db)
        finally:
            db.close()
    else:
        main()
