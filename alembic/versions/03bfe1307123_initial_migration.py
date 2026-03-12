"""initial migration

Revision ID: 03bfe1307123
Revises: 
Create Date: 2026-03-08 13:24:56.156632

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '03bfe1307123'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('focus', sa.Column('report_url', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('focus', 'report_url')
