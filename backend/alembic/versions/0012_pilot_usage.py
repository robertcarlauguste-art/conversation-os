"""Owner-scoped daily pilot consumption; active storage is counted from recordings."""

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE pilot_usage (
        owner_id varchar(255) NOT NULL,
        day date NOT NULL,
        uploads integer NOT NULL DEFAULT 0 CHECK (uploads >= 0),
        audio_seconds integer NOT NULL DEFAULT 0 CHECK (audio_seconds >= 0),
        ai integer NOT NULL DEFAULT 0 CHECK (ai >= 0),
        retries integer NOT NULL DEFAULT 0 CHECK (retries >= 0),
        PRIMARY KEY(owner_id, day)
    )""")


def downgrade():
    op.drop_table("pilot_usage")
