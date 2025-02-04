"""add stripe customer id to users

Revision ID: 529a9408f2ac
Revises: 2bb892826b8a
Create Date: 2025-01-30 20:39:35.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '529a9408f2ac'
down_revision = '2bb892826b8a'
branch_labels = None
depends_on = None


def upgrade():
    # Add stripe_customer_id column to users table
    op.add_column('users', sa.Column('stripe_customer_id', sa.String(255), unique=True, nullable=True))


def downgrade():
    # Remove stripe_customer_id column from users table
    op.drop_column('users', 'stripe_customer_id')
