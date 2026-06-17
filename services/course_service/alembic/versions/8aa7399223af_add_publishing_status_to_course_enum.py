"""add publishing status to course enum

Revision ID: 8aa7399223af
Revises: a1b2c3d4e5f6
Create Date: 2026-06-02 19:10:01.661566

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8aa7399223af'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ADD VALUE cannot run inside a transaction in PostgreSQL.
    # Manually commit the open transaction first, then run the DDL.
    op.execute(sa.text("COMMIT"))
    op.execute(
        sa.text("ALTER TYPE course_status_enum ADD VALUE IF NOT EXISTS 'publishing' BEFORE 'published'")
    )


def downgrade() -> None:
    op.execute(sa.text("COMMIT"))
    op.execute(sa.text("""
        ALTER TABLE courses ALTER COLUMN status TYPE VARCHAR(20);
        DROP TYPE course_status_enum;
        CREATE TYPE course_status_enum AS ENUM ('draft', 'published', 'archived');
        ALTER TABLE courses ALTER COLUMN status TYPE course_status_enum USING status::course_status_enum;
    """))