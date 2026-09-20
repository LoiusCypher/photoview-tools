"""rework timestamp handling

Revision ID: f21fe2bbc1da
Revises: dd585b5873d5
Create Date: 2026-09-17 22:37:24.760287

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = 'f21fe2bbc1da'
down_revision: str | Sequence[str] | None = 'dd585b5873d5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""


def downgrade() -> None:
    """Downgrade schema."""
