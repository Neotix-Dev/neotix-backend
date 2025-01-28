"""add_gpu_score_column

Revision ID: 7745bfc1243f
Revises: 1c11b26cc472
Create Date: 2025-01-16 19:06:57.868544

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7745bfc1243f'
down_revision = '1c11b26cc472'
branch_labels = None
depends_on = None


def upgrade():
    # Add gpu_score column using batch operations to handle existing table
    with op.batch_alter_table('gpu_listings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('gpu_score', sa.Float(), nullable=True))
    
    # Update existing rows with computed scores
    op.execute("""
        UPDATE gpu_listings
        SET gpu_score = COALESCE(gpu_memory, 0) * gpu_count
        WHERE gpu_score IS NULL
    """)


def downgrade():
    with op.batch_alter_table('gpu_listings', schema=None) as batch_op:
        batch_op.drop_column('gpu_score')
