"""drop completion_percentage from progress

Revision ID: b3c4d5e6f7a8
Revises: 3a64b5382772
Create Date: 2026-05-25 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "3a64b5382772"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("progress", "completion_percentage")


def downgrade() -> None:
    op.add_column(
        "progress",
        sa.Column("completion_percentage", sa.Float(), nullable=False, server_default="0.0"),
    )
