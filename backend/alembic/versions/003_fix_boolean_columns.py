from alembic import op

revision = '003_fix_boolean_columns'
down_revision = '002_add_email_verified'
branch_labels = None
depends_on = None

def upgrade():
    op.execute('ALTER TABLE users ALTER COLUMN is_active TYPE boolean USING is_active::boolean')

def downgrade():
    op.execute('ALTER TABLE users ALTER COLUMN is_active TYPE integer USING is_active::integer')
