
from app.integrations.service.integration_service import IIntegrationClient
from pkg.log.logger import Logger
import asyncpg


class IntegrationClient(IIntegrationClient):
    def __init__(self,  logger: Logger):
        self.logger = logger


    async def validate_postgres_credentials(self, integration_credentials: dict) -> bool:
        try:
            self.logger.info(f"validating postgres credentials: {integration_credentials}")
            # Extract credential fields
            host = integration_credentials.get('host')
            port = integration_credentials.get('port', 5432)
            username = integration_credentials.get('username')
            password = integration_credentials.get('password')
            database_name = integration_credentials.get('database_name')

            # Validate required fields
            if not all([host, username, database_name]):
                self.logger.error("Missing required PostgreSQL credentials", extra=integration_credentials)
                return False

            # Test connection with short timeout
            conn = await asyncpg.connect(
                host=host,
                port=port,
                user=username,
                password=password,
                database=database_name,
                timeout=5.0
            )
            await conn.close()
            self.logger.info(f"connection successful and closed")
            return True

        except Exception as e:
            self.logger.error(f"Error validating PostgreSQL credentials: {e!s}")
            return False
