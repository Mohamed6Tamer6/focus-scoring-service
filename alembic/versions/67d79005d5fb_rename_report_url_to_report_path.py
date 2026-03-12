"""rename_report_url_to_report_path

Revision ID: 67d79005d5fb
Revises: e1afe212e183
Create Date: 2026-03-10 14:54:09.187451

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '67d79005d5fb'
down_revision: Union[str, None] = 'e1afe212e183'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('focus', 'report_url', new_column_name='report_path')


def downgrade() -> None:
    op.alter_column('focus', 'report_path', new_column_name='report_url')