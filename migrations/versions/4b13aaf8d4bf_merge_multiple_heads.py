"""merge multiple heads

Revision ID: 4b13aaf8d4bf
Revises: 1c11b26cc472, 7745bfc1243f
Create Date: 2025-01-29 11:58:27.400684

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4b13aaf8d4bf'
down_revision = ('1c11b26cc472', '7745bfc1243f')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
