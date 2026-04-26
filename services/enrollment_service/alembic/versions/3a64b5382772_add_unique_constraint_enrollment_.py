"""add unique constraint enrollment student course

Revision ID: 3a64b5382772
Revises: 7a9237e4655a
Create Date: 2026-04-26 16:09:51.559778

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a64b5382772'
down_revision: Union[str, Sequence[str], None] = '7a9237e4655a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_enrollment_student_course",
        "enrollments",
        ["student_id", "course_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_enrollment_student_course", "enrollments")
