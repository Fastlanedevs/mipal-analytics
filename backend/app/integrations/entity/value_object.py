from enum import Enum

from pydantic import BaseModel


class IntegrationType(str, Enum):
    """Enum representing different integration services"""

    GOOGLE_CALENDAR = "GOOGLE_CALENDAR"
    GOOGLE_DRIVE = "GOOGLE_DRIVE"
    GOOGLE_GMAIL = "GOOGLE_GMAIL"
    MICROSOFT_TEAMS = "MICROSOFT_TEAMS"
    MICROSOFT_ONEDRIVE = "MICROSOFT_ONEDRIVE"
    MICROSOFT_OUTLOOK = "MICROSOFT_OUTLOOK"
    MICROSOFT_CALENDER = "MICROSOFT_CALENDER"
    SLACK_CHAT = "SLACK_CHAT"
    POSTGRESQL = "POSTGRESQL"

    @classmethod
    def get_all_integration_types(cls) -> list:
        return [integration_type for integration_type in cls]


class CommunicationIntegrations(str, Enum):
    MAIL = "MAIL"
    SLACK_CHAT = "SLACK_CHAT"


class IntegrationProvider(Enum):
    """Enum representing different authentication providers"""

    GOOGLE = "GOOGLE"
    MICROSOFT = "MICROSOFT"
    SLACK = "SLACK"
    GITHUB = "GITHUB"
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
            IntegrationType.GOOGLE_CALENDAR: IntegrationMetadata(
                type=IntegrationType.GOOGLE_CALENDAR,
                integration_provider=IntegrationProvider.GOOGLE,
                scopes=["https://www.googleapis.com/auth/calendar"],
                display_name="Google Calendar",
                icon="calendar-icon",
            ),
            IntegrationType.GOOGLE_DRIVE: IntegrationMetadata(
                type=IntegrationType.GOOGLE_DRIVE,
                integration_provider=IntegrationProvider.GOOGLE,
                scopes=["https://www.googleapis.com/auth/drive"],
                display_name="Google Drive",
                icon="drive-icon",
            ),
            IntegrationType.GOOGLE_GMAIL: IntegrationMetadata(
                type=IntegrationType.GOOGLE_GMAIL,
                integration_provider=IntegrationProvider.GOOGLE,
                scopes=["https://www.googleapis.com/auth/gmail.readonly"],
                display_name="Google Gmail",
                icon="gmail-icon",
            ),
            IntegrationType.MICROSOFT_TEAMS: IntegrationMetadata(
                type=IntegrationType.MICROSOFT_TEAMS,
                integration_provider=IntegrationProvider.MICROSOFT,
                scopes=["https://graph.microsoft.com/Teams.ReadWrite"],
                display_name="Microsoft Teams",
                icon="teams-icon",
            ),
            IntegrationType.MICROSOFT_ONEDRIVE: IntegrationMetadata(
                type=IntegrationType.MICROSOFT_ONEDRIVE,
                integration_provider=IntegrationProvider.MICROSOFT,
                scopes=["https://graph.microsoft.com/Files.ReadWrite"],
                display_name="Microsoft OneDrive",
                icon="onedrive-icon",
            ),
            IntegrationType.SLACK_CHAT: IntegrationMetadata(
                type=IntegrationType.SLACK_CHAT,
                integration_provider=IntegrationProvider.SLACK,
                scopes=["chat:write", "chat:read"],
                display_name="Slack Chat",
                icon="slack-icon",
            ),
            IntegrationType.MICROSOFT_OUTLOOK: IntegrationMetadata(
                type=IntegrationType.MICROSOFT_OUTLOOK,
                integration_provider=IntegrationProvider.MICROSOFT,
                scopes=["https://graph.microsoft.com/Mail.Read"],
                display_name="Microsoft Outlook",
                icon="outlook-icon",
            ),
            IntegrationType.MICROSOFT_CALENDER: IntegrationMetadata(
                type=IntegrationType.MICROSOFT_CALENDER,
                integration_provider=IntegrationProvider.MICROSOFT,
                scopes=["https://graph.microsoft.com/Calendars.Read"],
                display_name="Microsoft Calendar",
                icon="calendar-icon",
            ),
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
