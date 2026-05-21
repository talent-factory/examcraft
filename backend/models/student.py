"""Student master data — pseudonym-first.

``external_id`` (Moodle user id, email, or student number) is required;
``display_name`` is optional. Real names are not persisted by default.

Students are upserted by ``(institution_id, external_id)`` during CSV
import.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class Student(Base):
    """Pseudonymisiertes Studierenden-Stammdatum, scoped pro Institution."""

    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    external_id = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    institution = relationship("Institution", back_populates="students")
    memberships = relationship(
        "StudentClassMembership",
        back_populates="student",
        cascade="all, delete-orphan",
    )
    submissions = relationship(
        "Submission",
        back_populates="student",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "institution_id", "external_id", name="uq_students_institution_external"
        ),
    )

    def __repr__(self):
        return (
            f"<Student(id={self.id}, institution_id={self.institution_id}, "
            f"external_id='{self.external_id}')>"
        )


class StudentClass(Base):
    """A class/cohort label scoped to an institution (e.g. 'INF-23a')."""

    __tablename__ = "student_classes"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
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

    institution = relationship("Institution", back_populates="student_classes")
    memberships = relationship(
        "StudentClassMembership",
        back_populates="student_class",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "institution_id", "name", name="uq_student_classes_institution_name"
        ),
    )

    def __repr__(self):
        return f"<StudentClass(id={self.id}, name='{self.name}')>"


class StudentClassMembership(Base):
    """M:N zwischen Student und StudentClass."""

    __tablename__ = "student_class_memberships"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    class_id = Column(
        Integer,
        ForeignKey("student_classes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    added_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    student = relationship("Student", back_populates="memberships")
    student_class = relationship("StudentClass", back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("student_id", "class_id", name="uq_student_class_memberships"),
    )

    def __repr__(self):
        return (
            f"<StudentClassMembership(student_id={self.student_id}, "
            f"class_id={self.class_id})>"
        )
