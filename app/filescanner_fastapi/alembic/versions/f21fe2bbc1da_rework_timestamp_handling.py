"""rework timestamp handling

Revision ID: f21fe2bbc1da
Revises: dd585b5873d5
Create Date: 2026-09-17 22:37:24.760287

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import migration_types


# revision identifiers, used by Alembic.
revision: str = 'f21fe2bbc1da'
down_revision: Union[str, Sequence[str], None] = 'dd585b5873d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
