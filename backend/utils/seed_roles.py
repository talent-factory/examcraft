"""Seed default roles into the database.

Re-running this seeder is safe: existing roles get a set-merge of
permissions (defaults are added without removing any admin-added extras
from the live DB). Display name and description are kept in sync with
the seed data so a renamed role label updates on next deploy.
"""

import json
import logging

from sqlalchemy.orm import Session

from models.auth import Role, UserRole

logger = logging.getLogger(__name__)


def _parse_existing_permissions(value) -> list[str]:
    """Parse the on-disk permissions blob into a list.

    Roles stored in PG carry permissions either as a JSON array string
    or, in some legacy installs, as a Postgres ``set``-formatted string
    (``{a,b,c}``). Both shapes round-trip through this helper.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return list(value)
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
            if isinstance(decoded, list):
                return decoded
        except (json.JSONDecodeError, TypeError):
            pass
        if value.startswith("{") and value.endswith("}"):
            return [p.strip() for p in value[1:-1].split(",") if p.strip()]
    return []


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
                "prompt:create",
                "prompt:read",
                "prompt:update",
                "prompt:delete",
                "submissions:read",
                "submissions:import",
                "submissions:grade",
                # TF-421: delete a result-import to allow a clean re-import.
                "submissions:delete",
                # TF-435: push graded feedback (points + comments) back to Moodle.
                "submissions:moodle_feedback_push",
                # TF-335: Admin manages institution-scoped Grading-
                # Schemes; System schemes stay read-only via the API.
                "grading_schemes:manage",
                # TF-336: Admin pflegt Studierenden-Stammdaten und Klassen
                # sowie Moodle-Web-Service-Verbindungen.
                "students:manage",
                "moodle:configure",
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
                "prompt:create",
                "prompt:read",
                "prompt:update",
                "prompt:delete",
                # Lehrperson can import results and approve grades.
                "submissions:read",
                "submissions:import",
                "submissions:grade",
                # TF-421: Lehrperson can delete a result-import (clean re-import).
                "submissions:delete",
                # TF-435: Lehrperson pushes graded feedback back to Moodle.
                "submissions:moodle_feedback_push",
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
                "prompt:create",
                "prompt:read",
                # TF-336: Reviewer-Rolle bekommt Lese- + Bewertungs-
                # Permission. Importieren bleibt der Lehrperson
                # vorbehalten, weil dort auch das Quota-Buchen passiert.
                "submissions:read",
                "submissions:grade",
            ],
            "is_system_role": True,
        },
        {
            "name": UserRole.VIEWER.value,
            "display_name": "Viewer",
            "description": "View-only access to questions and exams, can upload and manage documents",
            "permissions": [
                "view_questions",
                "view_exams",
                "documents:read",
                "create_documents",
                "delete_documents",
                "prompt:read",
            ],
            "is_system_role": True,
        },
    ]

    created_count = 0
    updated_count = 0

    for role_data in roles_data:
        existing_role = db.query(Role).filter(Role.name == role_data["name"]).first()

        if existing_role:
            existing_role.display_name = role_data["display_name"]
            existing_role.description = role_data["description"]
            existing_role.is_system_role = role_data["is_system_role"]

            # Set-merge permissions: defaults become a floor, extras
            # added by an admin via the management UI survive re-seeds.
            existing_perms = set(_parse_existing_permissions(existing_role.permissions))
            seed_perms = set(role_data["permissions"])
            added = seed_perms - existing_perms
            preserved_extras = existing_perms - seed_perms
            merged = sorted(existing_perms | seed_perms)
            existing_role.permissions = merged

            updated_count += 1
            logger.info(
                "Updated role %s — added %d default(s), preserved %d "
                "admin-added permission(s)",
                role_data["name"],
                len(added),
                len(preserved_extras),
            )
        else:
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
