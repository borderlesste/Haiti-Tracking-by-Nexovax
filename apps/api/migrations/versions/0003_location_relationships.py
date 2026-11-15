"""Add location relationships and local-name aliases without rewriting existing records."""
from alembic import op
from app.core import ensure_location_relationships

revision = "0003_location_relationships"
down_revision = "0002_territories"
branch_labels = None
depends_on = None


def upgrade():
    ensure_location_relationships(op.get_bind())


def downgrade():
    # Older code ignores these additive fields; retain relations and aliases instead of deleting data.
    pass
