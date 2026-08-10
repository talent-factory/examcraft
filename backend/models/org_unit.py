"""Organisationseinheiten unterhalb der Institution (z.B. Abteilung, Team).

Selbstreferenzierende, beliebig tiefe Hierarchie via ``parent_org_unit_id``.
``unit_type`` ist ein freier String statt Enum, damit neue Ebenen (z.B.
"team" unterhalb von "abteilung") ohne Schema-Aenderung moeglich sind.

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

# Fuer Stufe 0 unterstuetzte unit_type-Werte. Bewusst kein DB-Enum/Constraint
# (siehe Modul-Docstring) -- eine neue Ebene hinzuzufuegen bleibt eine
# Ein-Zeilen-Aenderung hier, keine Migration. Validiert wird dieser Katalog
# an der API-Grenze (api/org_units.py::OrgUnitCreateIn), nicht hier im Modell
# oder im Service -- interne/zukuenftige Aufrufer (z.B. Stufe-1-Piloten) duerfen
# weiterhin beliebige Werte direkt setzen.
KNOWN_UNIT_TYPES = ("abteilung", "team")


class OrgUnit(Base):
    """Ein Knoten in der Organisationshierarchie (Abteilung, Team, ...)."""

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

    def __repr__(self):
        return (
            f"<OrgUnit(id={self.id}, unit_type='{self.unit_type}', name='{self.name}')>"
        )


class UserOrgUnit(Base):
    """M:N-Mitgliedschaft: eine Person kann mehreren OrgUnits angehoeren."""

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
