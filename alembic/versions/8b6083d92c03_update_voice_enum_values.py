"""update voice enum values

Revision ID: 8b6083d92c03
Revises: 0060aecea436
Create Date: 2025-11-28 21:50:38.475600

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "8b6083d92c03"
down_revision: Union[str, Sequence[str], None] = "0060aecea436"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE voicepreset RENAME TO voicepreset_old")
    op.execute("CREATE TYPE voicepreset AS ENUM('af_heart', 'af_bella', 'af_nicole')")
    op.execute(
        (
            "ALTER TABLE videos ALTER COLUMN voice TYPE voicepreset "
            "USING 'af_heart'::voicepreset"
        )
    )
    op.execute("DROP TYPE voicepreset_old")


def downgrade() -> None:
    op.execute("ALTER TYPE voicepreset RENAME TO voicepreset_new")
    op.execute("CREATE TYPE voicepreset AS ENUM('rogue', 'knight', 'wizard')")
    op.execute(
        (
            "ALTER TABLE videos ALTER COLUMN voice TYPE voicepreset "
            "USING 'rogue'::voicepreset"
        )
    )
    op.execute("DROP TYPE voicepreset_new")
