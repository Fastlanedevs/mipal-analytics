from app.integrations.entity.entity import (
    GoogleWatchChannelRequest,
    GoogleWatchChannelResponse,
)
from app.integrations.service.integration_service import IIntegrationClient
from integration_clients.g_suite.client import GSuiteClient
from integration_clients.g_suite.types import GoogleOAuthToken
from pkg.log.logger import Logger
import asyncpg


class IntegrationClient(IIntegrationClient):
    def __init__(self, g_suite_client: GSuiteClient, logger: Logger):
        self.logger = logger
        self.g_suite_client = g_suite_client

    async def validate_google_credentials(self, integration_credentials: dict) -> (bool,str):
        try:
            token = GoogleOAuthToken(
                access_token=integration_credentials.get("access_token"),
                refresh_token=integration_credentials.get("refresh_token"),
                scope=integration_credentials.get("scope"),
                token_type=integration_credentials.get("token_type"),
                expiry_date=integration_credentials.get("expiry_date"),
            )
            credentials = await self.g_suite_client.make_user_credentials(token)
            return True, credentials.account
        except Exception as e:
            self.logger.error(f"Error validating Google credentials: {e!s}")
            return False, ""

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
