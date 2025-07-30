from datetime import datetime

from neomodel import (
    BooleanProperty,
    DateTimeProperty,
    StringProperty,
    StructuredNode,
    UniqueIdProperty,
)


class UserSettings(StructuredNode):
    uid: str = UniqueIdProperty()
    user_id: str = StringProperty()
    theme: str = StringProperty()
    language: str = StringProperty()
    timezone: str = StringProperty()
    date_format: str = StringProperty()
    pinned_sidebar: bool = BooleanProperty()
    created_at: datetime = DateTimeProperty()
    updated_at: datetime = DateTimeProperty()
