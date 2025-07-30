from datetime import datetime
from typing import Any

from neomodel import (
    ArrayProperty,
    BooleanProperty,
    DateTimeProperty,
    JSONProperty,
    StringProperty,
    StructuredNode,
    UniqueIdProperty,
)


class Integration(StructuredNode):
    uid: str = UniqueIdProperty()
    integration_type: str = StringProperty(required=True)
    credential: dict[str, Any] = JSONProperty()
    integration_provider = StringProperty()
    scopes: str = ArrayProperty(StringProperty())
    created_at: datetime = DateTimeProperty(default=datetime.utcnow)
    updated_at: datetime = DateTimeProperty(default=datetime.utcnow)
    expires_at: datetime | None = DateTimeProperty()
    user_id: str = StringProperty(required=True)
    settings: dict[str, Any] | None = JSONProperty()
    is_active: bool = BooleanProperty()


class IntegrationSync(StructuredNode):
    uid = UniqueIdProperty()
    user_id = StringProperty(required=True)
    integration_id = StringProperty(required=True)
    integration_type = StringProperty(required=True)
    status = StringProperty(required=True)
    created_at = DateTimeProperty(required=True)
    completed_at = DateTimeProperty()
    updated_at = DateTimeProperty(required=True)
    is_active: bool = BooleanProperty(default=True)
    error_message = StringProperty()
