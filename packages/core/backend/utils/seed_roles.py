"""
Seed default roles into the database
"""

from sqlalchemy.orm import Session
from models.auth import Role, UserRole
import logging

logger = logging.getLogger(__name__)


def seed_default_roles(db: Session):
    """
    Create default system roles if they don't exist

    Roles:
    - Admin: Full system access
    - Dozent: Create and manage questions/exams
    - Assistant: Review and edit questions
    - Viewer: View-only access
    """

    roles_data = [
        {
            "name": UserRole.ADMIN.value,
            "display_name": "Administrator",
            "description": "Full system access with all permissions",
            "permissions": [
                "manage_users",
                "manage_roles",
                "manage_institutions",
                "create_questions",
                "edit_questions",
                "delete_questions",
                "review_questions",
                "create_exams",
                "edit_exams",
                "delete_exams",
                "view_questions",
                "view_exams",
                "view_analytics",
                "manage_settings",
                "documents:read",
                "create_documents",
                "delete_documents",
            ],
            "is_system_role": True,
        },
        {
            "name": UserRole.DOZENT.value,
            "display_name": "Dozent",
            "description": "Create and manage questions, exams, and documents",
            "permissions": [
                "create_questions",
                "edit_questions",
                "delete_questions",
                "review_questions",
                "create_exams",
                "edit_exams",
                "delete_exams",
                "view_questions",
                "view_exams",
                "view_analytics",
                "documents:read",
                "create_documents",
                "delete_documents",
            ],
            "is_system_role": True,
        },
        {
            "name": UserRole.ASSISTANT.value,
            "display_name": "Assistant",
            "description": "Review and edit questions, create and manage documents",
            "permissions": [
                "edit_questions",
                "review_questions",
                "view_questions",
                "view_exams",
                "documents:read",
                "create_documents",
                "delete_documents",
            ],
            "is_system_role": True,
        },
        {
            "name": UserRole.VIEWER.value,
            "display_name": "Viewer",
            "description": "View-only access to questions and exams",
            "permissions": ["view_questions", "view_exams"],
            "is_system_role": True,
        },
    ]

    created_count = 0
    updated_count = 0

    for role_data in roles_data:
        existing_role = db.query(Role).filter(Role.name == role_data["name"]).first()

        if existing_role:
            # Update existing role
            existing_role.display_name = role_data["display_name"]
            existing_role.description = role_data["description"]
            existing_role.permissions = role_data["permissions"]
            existing_role.is_system_role = role_data["is_system_role"]
            updated_count += 1
            logger.info(f"Updated role: {role_data['name']}")
        else:
            # Create new role
            new_role = Role(
                name=role_data["name"],
                display_name=role_data["display_name"],
                description=role_data["description"],
                permissions=role_data["permissions"],
                is_system_role=role_data["is_system_role"],
            )
            db.add(new_role)
            created_count += 1
            logger.info(f"Created role: {role_data['name']}")

    db.commit()

    logger.info(f"Roles seeded: {created_count} created, {updated_count} updated")

    return created_count, updated_count


if __name__ == "__main__":
    # Run seed script directly
    from database import SessionLocal

    logging.basicConfig(level=logging.INFO)

    db = SessionLocal()
    try:
        created, updated = seed_default_roles(db)
        print(f"✅ Roles seeded successfully: {created} created, {updated} updated")
    except Exception as e:
        print(f"❌ Error seeding roles: {e}")
        db.rollback()
    finally:
        db.close()
