"""One editable saved draft per conversation and message format."""

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE followup_drafts (
        conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
        channel varchar(5) NOT NULL CHECK (channel IN ('email', 'text')),
        subject varchar(200) NOT NULL,
        body varchar(5000) NOT NULL CHECK (length(trim(body)) > 0),
        version integer NOT NULL CHECK (version > 0),
        updated_at timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY(conversation_id, channel)
    )""")


def downgrade():
    op.drop_table("followup_drafts")
