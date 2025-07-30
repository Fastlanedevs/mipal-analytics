from enum import Enum

from pydantic import BaseModel


class IntegrationType(str, Enum):
    """Enum representing different integration services"""

    POSTGRESQL = "POSTGRESQL"

    @classmethod
    def get_all_integration_types(cls) -> list:
        return [integration_type for integration_type in cls]


class CommunicationIntegrations(str, Enum):
    MAIL = "MAIL"


class IntegrationProvider(Enum):
    """Enum representing different authentication providers"""

    POSTGRESQL = "POSTGRESQL"


class IntegrationMetadata(BaseModel):
    """Dataclass to store integration metadata"""

    type: IntegrationType
    integration_provider: IntegrationProvider
    scopes: list[str]
    display_name: str = ""
    icon: str = ""


class IntegrationConfig:
    """Class to manage integration metadata and relationships"""

    def __init__(self):
        self.integration_metadata: dict[IntegrationType, IntegrationMetadata] = {
            
            IntegrationType.POSTGRESQL: IntegrationMetadata(
                type=IntegrationType.POSTGRESQL,
                integration_provider=IntegrationProvider.POSTGRESQL,
                scopes=[],
                display_name="PostgreSQL",
                icon="postgresql-icon",
            ),
        }

    def get_provider_for_integration(
            self, integration_type: IntegrationType
    ) -> IntegrationProvider:
        """Get the auth provider for a specific integration"""
        return self.integration_metadata[integration_type].auth_provider

    def get_integrations_by_provider(
            self, integration_provider: IntegrationProvider
    ) -> list[IntegrationType]:
        """Get all integrations that use a specific auth provider"""
        return [
            metadata.type
            for metadata in self.integration_metadata.values()
            if metadata.integration_provider == integration_provider
        ]

    def get_required_scopes(self, integration_types: list[IntegrationType]) -> set[str]:
        """Get all required scopes for a list of integrations"""
        scopes = set()
        for integration_type in integration_types:
            metadata = self.integration_metadata[integration_type]
            scopes.update(metadata.scopes)
        return scopes

    def get_integration_metadata(self, integration_type: IntegrationType) -> IntegrationMetadata:
        """Get metadata for a specific integration"""
        return self.integration_metadata[integration_type]

    def get_all_integration_types(self) -> list[str]:
        """Get all integration types"""
        return [integration_type.value for integration_type in IntegrationType]

    def get_all_integration_providers(self) -> list[str]:
        """Get all integration providers"""
        return [auth_provider.value for auth_provider in AuthProvider]


class SyncStatus(Enum):
    STARTED = "STARTED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

    @classmethod
    def get_all_sync_statuses(cls):
        return [sync_status.value for sync_status in cls]
