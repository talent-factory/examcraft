"""
Tests for Multi-Tenancy
Tests institution isolation, subscription limits, and tenant-aware queries
"""

import pytest

from models.auth import User, Role, Institution, UserStatus, UserRole
from models.document import Document, DocumentStatus
from models.question_review import QuestionReview, ReviewStatus
from services.auth_service import AuthService
from utils.tenant_utils import TenantFilter, SubscriptionLimits, get_tenant_context


@pytest.fixture(scope="function")
def db(test_db):
    """Use PostgreSQL test database from conftest.py"""
    # Create two test institutions
    institution1 = Institution(
        name="University A",
        slug="university-a",
        domain="university-a.edu",
        subscription_tier="free",
        max_users=5,
        max_documents=10,
        max_questions_per_month=50,
    )
    institution2 = Institution(
        name="University B",
        slug="university-b",
        domain="university-b.edu",
        subscription_tier="professional",
        max_users=100,
        max_documents=1000,
        max_questions_per_month=5000,
    )
    test_db.add(institution1)
    test_db.add(institution2)
    test_db.flush()

    # Get or create viewer role
    viewer_role = test_db.query(Role).filter(Role.name == UserRole.VIEWER.value).first()
    if not viewer_role:
        viewer_role = Role(
            name=UserRole.VIEWER.value,
            display_name="Viewer",
            description="Can view questions",
            permissions=["view_questions"],
            is_system_role=True,
        )
        test_db.add(viewer_role)
    test_db.commit()

    yield test_db


def create_user(db, email: str, institution_id: int, is_superuser: bool = False):
    """Helper to create user"""
    viewer_role = db.query(Role).filter(Role.name == UserRole.VIEWER.value).first()

    user = User(
        email=email,
        password_hash=AuthService.get_password_hash("testpassword123"),
        first_name="Test",
        last_name="User",
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
        is_superuser=is_superuser,
    )
    db.add(user)
    db.flush()

    user.roles.append(viewer_role)
    db.commit()
    db.refresh(user)

    return user


# ============================================================================
# Tenant Isolation Tests
# ============================================================================


def test_users_belong_to_institutions(db):
    """Test that users are correctly associated with institutions"""
    institution1 = (
        db.query(Institution).filter(Institution.slug == "university-a").first()
    )
    institution2 = (
        db.query(Institution).filter(Institution.slug == "university-b").first()
    )

    user1 = create_user(db, "user1@university-a.edu", institution1.id)
    user2 = create_user(db, "user2@university-b.edu", institution2.id)

    assert user1.institution_id == institution1.id
    assert user2.institution_id == institution2.id
    assert user1.institution.name == "University A"
    assert user2.institution.name == "University B"


def test_document_tenant_isolation(db):
    """Test that documents are isolated by institution"""
    institution1 = (
        db.query(Institution).filter(Institution.slug == "university-a").first()
    )
    institution2 = (
        db.query(Institution).filter(Institution.slug == "university-b").first()
    )

    user1 = create_user(db, "user1@university-a.edu", institution1.id)
    user2 = create_user(db, "user2@university-b.edu", institution2.id)

    # Create documents for each institution
    doc1 = Document(
        filename="doc1.pdf",
        file_path="/uploads/doc1.pdf",
        file_size=1000,
        mime_type="application/pdf",
        status=DocumentStatus.UPLOADED,
        user_id=user1.id,
        institution_id=institution1.id,
    )
    doc2 = Document(
        filename="doc2.pdf",
        file_path="/uploads/doc2.pdf",
        file_size=2000,
        mime_type="application/pdf",
        status=DocumentStatus.UPLOADED,
        user_id=user2.id,
        institution_id=institution2.id,
    )
    db.add(doc1)
    db.add(doc2)
    db.commit()

    # User 1 should only see documents from institution 1
    tenant_context1 = get_tenant_context(user1)
    query1 = db.query(Document)
    filtered_query1 = TenantFilter.filter_by_tenant(query1, Document, tenant_context1)
    docs1 = filtered_query1.all()

    assert len(docs1) == 1
    assert docs1[0].filename == "doc1.pdf"

    # User 2 should only see documents from institution 2
    tenant_context2 = get_tenant_context(user2)
    query2 = db.query(Document)
    filtered_query2 = TenantFilter.filter_by_tenant(query2, Document, tenant_context2)
    docs2 = filtered_query2.all()

    assert len(docs2) == 1
    assert docs2[0].filename == "doc2.pdf"


def test_question_tenant_isolation(db):
    """Test that questions are isolated by institution"""
    institution1 = (
        db.query(Institution).filter(Institution.slug == "university-a").first()
    )
    institution2 = (
        db.query(Institution).filter(Institution.slug == "university-b").first()
    )

    user1 = create_user(db, "user1@university-a.edu", institution1.id)
    user2 = create_user(db, "user2@university-b.edu", institution2.id)

    # Create questions for each institution
    q1 = QuestionReview(
        question_text="Question from Institution 1?",
        question_type="multiple_choice",
        difficulty="medium",
        topic="Math",
        language="en",
        review_status=ReviewStatus.PENDING.value,
        institution_id=institution1.id,
        created_by=user1.id,
    )
    q2 = QuestionReview(
        question_text="Question from Institution 2?",
        question_type="multiple_choice",
        difficulty="medium",
        topic="Science",
        language="en",
        review_status=ReviewStatus.PENDING.value,
        institution_id=institution2.id,
        created_by=user2.id,
    )
    db.add(q1)
    db.add(q2)
    db.commit()

    # User 1 should only see questions from institution 1
    tenant_context1 = get_tenant_context(user1)
    query1 = db.query(QuestionReview)
    filtered_query1 = TenantFilter.filter_by_tenant(
        query1, QuestionReview, tenant_context1
    )
    questions1 = filtered_query1.all()

    assert len(questions1) == 1
    assert questions1[0].topic == "Math"

    # User 2 should only see questions from institution 2
    tenant_context2 = get_tenant_context(user2)
    query2 = db.query(QuestionReview)
    filtered_query2 = TenantFilter.filter_by_tenant(
        query2, QuestionReview, tenant_context2
    )
    questions2 = filtered_query2.all()

    assert len(questions2) == 1
    assert questions2[0].topic == "Science"


def test_superuser_can_see_all_data(db):
    """Test that superuser can see data from all institutions"""
    institution1 = (
        db.query(Institution).filter(Institution.slug == "university-a").first()
    )
    institution2 = (
        db.query(Institution).filter(Institution.slug == "university-b").first()
    )

    user1 = create_user(db, "user1@university-a.edu", institution1.id)
    superuser = create_user(db, "admin@system.com", institution1.id, is_superuser=True)

    # Create documents for both institutions
    doc1 = Document(
        filename="doc1.pdf",
        file_path="/uploads/doc1.pdf",
        file_size=1000,
        mime_type="application/pdf",
        status=DocumentStatus.UPLOADED,
        user_id=user1.id,
        institution_id=institution1.id,
    )
    doc2 = Document(
        filename="doc2.pdf",
        file_path="/uploads/doc2.pdf",
        file_size=2000,
        mime_type="application/pdf",
        status=DocumentStatus.UPLOADED,
        user_id=user1.id,
        institution_id=institution2.id,
    )
    db.add(doc1)
    db.add(doc2)
    db.commit()

    # Superuser should see all documents
    tenant_context = get_tenant_context(superuser)
    query = db.query(Document)
    filtered_query = TenantFilter.filter_by_tenant(
        query, Document, tenant_context, allow_superuser_access=True
    )
    docs = filtered_query.all()

    assert len(docs) == 2  # Superuser sees both


# ============================================================================
# Subscription Limit Tests
# ============================================================================


def test_user_limit_enforcement(db):
    """Test that user limit is enforced"""
    institution = (
        db.query(Institution).filter(Institution.slug == "university-a").first()
    )

    # Create max_users (5) active users
    for i in range(5):
        create_user(db, f"user{i}@university-a.edu", institution.id)

    # Try to add one more user should fail
    with pytest.raises(Exception) as exc_info:
        SubscriptionLimits.check_user_limit(institution, db)

    assert "user limit" in str(exc_info.value).lower()


def test_document_limit_enforcement(db):
    """Test that document limit is enforced"""
    institution = (
        db.query(Institution).filter(Institution.slug == "university-a").first()
    )
    user = create_user(db, "user@university-a.edu", institution.id)

    # Create max_documents (10) documents
    for i in range(10):
        doc = Document(
            filename=f"doc{i}.pdf",
            file_path=f"/uploads/doc{i}.pdf",
            file_size=1000,
            mime_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            user_id=user.id,
            institution_id=institution.id,
        )
        db.add(doc)
    db.commit()

    # Try to add one more document should fail
    with pytest.raises(Exception) as exc_info:
        SubscriptionLimits.check_document_limit(institution, db)

    assert "document limit" in str(exc_info.value).lower()


def test_question_limit_enforcement(db):
    """Test that monthly question limit is enforced"""
    institution = (
        db.query(Institution).filter(Institution.slug == "university-a").first()
    )
    user = create_user(db, "user@university-a.edu", institution.id)

    # Create max_questions_per_month (50) questions
    for i in range(50):
        q = QuestionReview(
            question_text=f"Question {i}?",
            question_type="multiple_choice",
            difficulty="medium",
            topic="Test",
            language="en",
            review_status=ReviewStatus.PENDING.value,
            institution_id=institution.id,
            created_by=user.id,
        )
        db.add(q)
    db.commit()

    # Try to add one more question should fail
    with pytest.raises(Exception) as exc_info:
        SubscriptionLimits.check_question_limit(institution, db)

    assert "question limit" in str(exc_info.value).lower()


def test_professional_tier_has_higher_limits(db):
    """Test that professional tier has higher limits than free tier"""
    free_institution = (
        db.query(Institution).filter(Institution.slug == "university-a").first()
    )
    pro_institution = (
        db.query(Institution).filter(Institution.slug == "university-b").first()
    )

    assert free_institution.subscription_tier == "free"
    assert pro_institution.subscription_tier == "professional"

    # Professional should have higher limits
    assert pro_institution.max_users > free_institution.max_users
    assert pro_institution.max_documents > free_institution.max_documents
    assert (
        pro_institution.max_questions_per_month
        > free_institution.max_questions_per_month
    )
