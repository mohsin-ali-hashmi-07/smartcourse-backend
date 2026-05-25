"""drop role column from users table

Revision ID: e4f5a6b7c8d9
Revises: d88342a1e77d
Create Date: 2026-05-25 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, None] = "d88342a1e77d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("users", "role")
    op.execute("DROP TYPE IF EXISTS user_role_enum")


def downgrade() -> None:
    op.execute("CREATE TYPE user_role_enum AS ENUM ('admin', 'instructor', 'student')")
    op.add_column(
        "users",
        sa.Column("role", sa.Enum("admin", "instructor", "student", name="user_role_enum"), nullable=False, server_default="student"),
    )
