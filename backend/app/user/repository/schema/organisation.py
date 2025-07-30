from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from neomodel import (
    DateTimeProperty,
    JSONProperty,
    RelationshipFrom,
    StringProperty,
    StructuredNode,
    UniqueIdProperty,
)

if TYPE_CHECKING:
    from app.user.repository.schema.user import User


class Organisation(StructuredNode):
    uid: str = UniqueIdProperty()
    name: str = StringProperty(required=True)
    domain: str = StringProperty()
    website: str = StringProperty()
    phone: str = StringProperty()
    address: str = StringProperty()
    logo: str = StringProperty()
    admin_position: str = StringProperty()
    created_at: datetime = DateTimeProperty(default=datetime.utcnow)
    updated_at: datetime = DateTimeProperty(default=datetime.utcnow)
    created_by: str = StringProperty(required=True)  # User UID

    # Use string references for relationships
    members: Optional["User"] = RelationshipFrom(".user.User", "MEMBER_OF")
    join_requests: Optional["User"] = RelationshipFrom(".user.User", "REQUESTED_JOIN")
    invitations: list[dict[str, Any]] = JSONProperty(
        default=[]
    )  # Store pending invitations as {email, token, expiry}
