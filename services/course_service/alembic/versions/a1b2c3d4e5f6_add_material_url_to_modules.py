"""add material_url to modules

Revision ID: a1b2c3d4e5f6
Revises: d529cff0f36c
Create Date: 2026-05-24 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "d529cff0f36c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "modules",
        sa.Column("material_url", sa.String(512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("modules", "material_url")
