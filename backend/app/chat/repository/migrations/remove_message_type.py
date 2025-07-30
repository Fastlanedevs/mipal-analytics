"""
Migration script to remove the message_type column from the messages table.
"""
from typing import List, Optional
import asyncio
from datetime import datetime
import uuid

from sqlalchemy import Column, String, text
from sqlalchemy.ext.asyncio import AsyncSession
from alembic import op
import sqlalchemy as sa


# Revision identifiers
revision = f'{uuid.uuid4()}'
down_revision = None
depends_on = None


async def upgrade() -> None:
    """Remove the message_type column from the messages table."""
    op.drop_column('messages', 'message_type')


async def downgrade() -> None:
    """Add the message_type column back to the messages table."""
    op.add_column('messages', sa.Column('message_type', sa.String(), nullable=False, server_default='text'))


def run_upgrade() -> None:
    """Entry point for running the upgrade."""
    asyncio.run(upgrade())


def run_downgrade() -> None:
    """Entry point for running the downgrade."""
    asyncio.run(downgrade())


if __name__ == "__main__":
    # This can be run standalone if needed
    run_upgrade() 