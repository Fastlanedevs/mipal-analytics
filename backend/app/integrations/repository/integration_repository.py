import uuid
from uuid import UUID
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator, Optional

from sqlalchemy import delete, select, update, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.entity.entity import (
    SyncIntegration,
    SyncIntegrationEvent,
    UserIntegration,
)
from app.integrations.entity.value_object import (
    IntegrationMetadata,
    IntegrationProvider,
    IntegrationType,
    SyncStatus,
)
from app.integrations.repository.sql_schema.integration import (
    IntegrationModel,
    IntegrationSyncModel,
)
from app.integrations.service.integration_service import IIntegrationRepository
from pkg.db_util.postgres_conn import PostgresConnection
from pkg.log.logger import Logger
from pkg.pub_sub.publisher import Publisher


class IntegrationRepository(IIntegrationRepository):
    def __init__(
        self, sql_db_conn: PostgresConnection, publisher: Publisher, logger: Logger
    ):
        self.db_conn = sql_db_conn
        self.publisher = publisher
        self.logger = logger

    async def create_user_integration(
        self,
        user_id: str,
        user_integration: UserIntegration,
    ) -> UserIntegration:
        """Creates a new user integration record in the database."""
        integration_model = IntegrationModel.from_entity(user_integration)
        integration_model.user_id = user_id

        async with self.db_conn.get_session() as session:
            session.add(integration_model)
            await session.commit()
            await session.refresh(integration_model)
            return integration_model.to_entity()

    async def get_all_active_user_integration(self, user_id: str,
                                              integration_type: Optional[IntegrationType] = None) -> list[UserIntegration]:

        """Retrieves all active integrations for a given user."""
        if integration_type:
            stmt = select(IntegrationModel).where(
                IntegrationModel.user_id == user_id,
                IntegrationModel.integration_type == integration_type.value,
                IntegrationModel.is_active == True
            )
        else:
            stmt = select(IntegrationModel).where(
                IntegrationModel.user_id == user_id,
                IntegrationModel.is_active == True
            )
        async with self.db_conn.get_session() as session:
            result = await session.execute(stmt)
            integrations = result.scalars().all()
            return [integration.to_entity() for integration in integrations]

    async def get_user_integration(
        self, user_id: str, integration_id: UUID
    ) -> UserIntegration | None:
        """Retrieves a specific integration for a user by type."""
        stmt = select(IntegrationModel).where(
            IntegrationModel.user_id == user_id,
            IntegrationModel.id == integration_id,
        )
        async with self.db_conn.get_session() as session:
            result = await session.execute(stmt)
            integration = result.scalar_one_or_none()
            return integration.to_entity() if integration else None

    async def update_user_integration(
        self, user_id: str, user_integration: UserIntegration
    ) -> UserIntegration:

        async with self.db_conn.get_session() as session:
            stmt = select(IntegrationModel).where(
                IntegrationModel.id == user_integration.integration_id,
                IntegrationModel.user_id == user_id
            )
            result = await session.execute(stmt)
            integration_model = result.scalar_one_or_none()

            if not integration_model:
                raise NoResultFound(
                    f"Integration not found for user {user_id} with id {user_integration.integration_id}"
                )

            integration_model.credential = user_integration.credential
            integration_model.expires_at = user_integration.expires_at
            integration_model.settings = user_integration.settings
            integration_model.is_active = user_integration.is_active

            await session.commit()
            await session.refresh(integration_model)
            return integration_model.to_entity()

    async def update_latest_checkpoint_integration(self,user_id: str, integration_id: UUID, checkpoint: str,) -> bool:
        """
        Atomically updates settings['checkpoint'] *without* touching
        other keys.  Returns True iff one row was updated.
        """
        stmt = (
            update(IntegrationModel)
            .where(
                IntegrationModel.id == integration_id,
                IntegrationModel.user_id == user_id,
            )
            .values(
                settings=func.jsonb_set(
                    (IntegrationModel.settings.cast(JSONB)),
                    ['checkpoint'],
                    func.to_jsonb(checkpoint),
                    True,
                )
            )
            .execution_options(synchronize_session="fetch")
        )

        async with self.db_conn.get_session() as session:
            try:
                result = await session.execute(stmt)
                await session.commit()
                return result.rowcount == 1
            except SQLAlchemyError as e:
                self.logger.error(f"Failed to update checkpoint{e}")
                await session.rollback()
                return False

    async def get_latest_checkpoint_integration(
        self, user_id: str, integration_id: UUID
    ) -> Optional[str]:
        """
        Fetches settings['checkpoint'] in one round-trip.
        """
        stmt = (
            select(
                (IntegrationModel.settings['checkpoint']).as_string()  # -> TEXT
            )
            .where(
                IntegrationModel.id == integration_id,
                IntegrationModel.user_id == user_id,
            )
        )

        async with self.db_conn.get_session() as session:
            checkpoint = (await session.scalar(stmt))
            return checkpoint  # returns None if key or row is missing

    async def delete_user_integration(self, user_id: str, integration_id: UUID) -> bool:
        """
        Hard-deletes the integration and commits in the same transaction.
        """
        stmt = (
            delete(IntegrationModel)
            .where(
                IntegrationModel.id == integration_id,
                IntegrationModel.user_id == user_id,
            )
            .execution_options(synchronize_session="fetch")
        )

        async with self.db_conn.get_session() as session:
            result = await session.execute(stmt)
            await session.commit()

        if result.rowcount == 0:
            self.logger.warning(f"Delete failed - not found or unauthorized (user={user_id}, id={integration_id})")
            return False
        return True

    async def create_sync(self, sync_integration: SyncIntegration) -> SyncIntegration:

        async with self.db_conn.get_session() as session:
             stmt = select(IntegrationModel.id).where(
                 IntegrationModel.id == sync_integration.integration_id,
                 IntegrationModel.user_id == sync_integration.user_id
             )
             result = await session.execute(stmt)
             if result.scalar_one_or_none() is None:
                 raise Exception(f"Integration with id {sync_integration.integration_id} not found for user {sync_integration.user_id}")

             try:
                 publish_data = SyncIntegrationEvent(
                     user_id=sync_integration.user_id,
                     sync_id=str(sync_integration.sync_id),
                 )
                 await self.publisher.publish(publish_data.__dict__)
             except Exception as e:
                 self.logger.error(f"Publisher error during sync creation: {e!s}")
                 raise Exception(f"Publisher error: {e!s}") from e

             sync_model = IntegrationSyncModel.from_entity(sync_integration)
             sync_model.integration_id = sync_integration.integration_id

             session.add(sync_model)
             await session.commit()
             await session.refresh(sync_model)
             return sync_model.to_entity()

    async def get_last_sync(
        self, user_id: str, integration_id: UUID
    ) -> SyncIntegration | None:
        """Retrieves the most recent sync record for a user and integration ID."""
        stmt = (
            select(IntegrationSyncModel)
            .where(
                IntegrationSyncModel.user_id == user_id,
                IntegrationSyncModel.integration_id == integration_id,
            )
            .order_by(IntegrationSyncModel.created_at.desc())
        )
        async with self.db_conn.get_session() as session:
            result = await session.execute(stmt)
            sync_model = result.scalars().first()
            return sync_model.to_entity() if sync_model else None

    async def get_last_successful_sync(
        self, user_id: str, integration_id: UUID
    ) -> SyncIntegration | None:
        """Retrieves the most recent successful sync record for a specific integration ID."""
        stmt = (
            select(IntegrationSyncModel)
            .where(
                IntegrationSyncModel.user_id == user_id,
                IntegrationSyncModel.integration_id == integration_id,
                IntegrationSyncModel.status == SyncStatus.COMPLETED,
            )
            .order_by(IntegrationSyncModel.created_at.desc())
        )
        async with self.db_conn.get_session() as session:
            result = await session.execute(stmt)
            sync_model = result.scalars().first()
            return sync_model.to_entity() if sync_model else None

    async def get_sync_by_id(self, user_id: str, sync_id: UUID) -> SyncIntegration | None:
        try:
            stmt = select(IntegrationSyncModel).where(
                IntegrationSyncModel.id == sync_id,
                IntegrationSyncModel.user_id == user_id
            )
            async with self.db_conn.get_session() as session:
                result = await session.execute(stmt)
                sync_model = result.scalar_one_or_none()
                if not sync_model:
                    self.logger.warning(
                        f"Sync integration not found for user {user_id} with id {sync_id}"
                    )
                    return None
                return sync_model.to_entity()
        except NoResultFound as e:
            self.logger.warning(f"Sync integration not found: {e!s}")
            return None
        except Exception as e:
            self.logger.error(f"Error retrieving sync integration: {e!s}")
            raise e

    async def update_sync(self, sync_integration: SyncIntegration) -> SyncIntegration:
        """Updates an existing sync record."""
        if not sync_integration.sync_id:
             raise ValueError("Sync ID is required for updates.")

        async with self.db_conn.get_session() as session:
             stmt = select(IntegrationSyncModel).where(
                 IntegrationSyncModel.id == sync_integration.sync_id,
                 IntegrationSyncModel.user_id == sync_integration.user_id
             )
             result = await session.execute(stmt)
             sync_model = result.scalar_one_or_none()

             if not sync_model:
                 raise NoResultFound(
                     f"Sync integration not found for user {sync_integration.user_id} with id {sync_integration.sync_id}"
                 )

             sync_model.status = sync_integration.status
             sync_model.error_message = sync_integration.error_message
             sync_model.completed_at = sync_integration.completed_at

             await session.commit()
             await session.refresh(sync_model)
             return sync_model.to_entity()

    async def get_user_integration_by_id(
        self, user_id: str, integration_id: UUID
    ) -> UserIntegration | None:
        """Retrieves a specific integration for a user by its ID."""
        stmt = select(IntegrationModel).where(
            IntegrationModel.id == integration_id,
            IntegrationModel.user_id == user_id
        )
        async with self.db_conn.get_session() as session:
            result = await session.execute(stmt)
            integration_model = result.scalar_one_or_none()
            return integration_model.to_entity() if integration_model else None
