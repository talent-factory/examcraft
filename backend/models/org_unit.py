"""Organizational units below the institution (e.g. department, team).

Self-referencing, arbitrarily deep hierarchy via ``parent_org_unit_id``.
``unit_type`` is a free string instead of an enum, so a new level (e.g.
"team" below "abteilung") is possible without a schema change.

Design: docs/superpowers/specs/2026-08-07-org-unit-hierarchie-design.md
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base

# unit_type values supported for level 0. Deliberately no DB enum/constraint
# (see module docstring) -- adding a new level stays a one-line change here,
# no migration needed. This catalog is validated at the API boundary
# (api/org_units.py::OrgUnitCreateIn), not here in the model or the service --
# internal/future callers (e.g. level-1 pilots) may still set arbitrary
# values directly.
KNOWN_UNIT_TYPES = ("abteilung", "team")


class OrgUnit(Base):
    """A node in the organizational hierarchy (department, team, ...)."""

    __tablename__ = "org_units"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_org_unit_id = Column(
        Integer,
        ForeignKey("org_units.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    unit_type = Column(String(50), nullable=False)
    name = Column(String(200), nullable=False)
    # Granted Role (TF-637): the Role this OrgUnit grants to its *direct*
    # members. Additive to their own direct role assignments, and does NOT
    # cascade through the composite hierarchy the way access-scope does --
    # see docs/adr/0003-granted-role-not-cascading.md. Consumed by
    # User.has_permission() (models/auth.py), not by anything in this file.
    role_id = Column(
        Integer,
        ForeignKey("roles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    institution = relationship("Institution", back_populates="org_units")
    parent = relationship("OrgUnit", remote_side=[id], back_populates="children")
    children = relationship(
        "OrgUnit", back_populates="parent", cascade="all, delete-orphan"
    )
    memberships = relationship(
        "UserOrgUnit", back_populates="org_unit", cascade="all, delete-orphan"
    )
    role = relationship("Role")

    def __repr__(self):
        return (
            f"<OrgUnit(id={self.id}, unit_type='{self.unit_type}', name='{self.name}')>"
        )


class UserOrgUnit(Base):
    """M:N membership: a person can belong to multiple OrgUnits."""

    __tablename__ = "user_org_units"

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    org_unit_id = Column(
        Integer, ForeignKey("org_units.id", ondelete="CASCADE"), primary_key=True
    )
    role = Column(String(50), nullable=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User", back_populates="org_unit_memberships")
    org_unit = relationship("OrgUnit", back_populates="memberships")

    def __repr__(self):
        return f"<UserOrgUnit(user_id={self.user_id}, org_unit_id={self.org_unit_id})>"
