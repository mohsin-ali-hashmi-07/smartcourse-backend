"""normalize_roles: introduce roles lookup table, rebuild user_roles as join table

Revision ID: f1a2b3c4d5e6
Revises: e4f5a6b7c8d9
Create Date: 2026-06-12 00:00:00.000000

What this migration does:
  1. Drops the old user_roles table (had id, user_id, role string, permissions JSON)
  2. Creates `roles` lookup table — one row per role, seeded with admin/instructor/student
  3. Creates new `user_roles` join table — (user_id, role_id) composite PK, no duplicated strings
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e4f5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop old denormalized table
    op.drop_index("ix_user_roles_user_id", table_name="user_roles")
    op.drop_table("user_roles")

    # 2. Create roles lookup table
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
    )

    # 3. Seed the three built-in roles
    roles_table = sa.table("roles", sa.column("name", sa.String))
    op.bulk_insert(roles_table, [
        {"name": "admin"},
        {"name": "instructor"},
        {"name": "student"},
    ])

    # 4. Create new normalized user_roles join table
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_role"),
    )


def downgrade() -> None:
    op.drop_table("user_roles")
    op.drop_table("roles")

    # Restore old user_roles table
    op.create_table(
        "user_roles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.UniqueConstraint("user_id", "role", name="uq_user_role"),
    )
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"], unique=False)
