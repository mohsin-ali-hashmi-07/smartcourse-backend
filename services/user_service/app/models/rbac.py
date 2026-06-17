from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Role(Base):
    """
    Lookup table — one row per role definition.
    Seeded at migration time: admin, instructor, student.
    """
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    user_roles: Mapped[list["UserRole"]] = relationship("UserRole", back_populates="role_ref")


class UserRole(Base):
    """
    Join table — many-to-many between users and roles.
    Composite PK (user_id, role_id) — no surrogate id needed.
    """
    __tablename__ = "user_roles"

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_role"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )

    role_ref: Mapped["Role"] = relationship("Role", back_populates="user_roles")