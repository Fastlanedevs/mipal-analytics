from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from neomodel import (
    BooleanProperty,
    DateTimeProperty,
    JSONProperty,
    RelationshipTo,
    StringProperty,
    StructuredNode,
    StructuredRel,
    UniqueIdProperty,
)

# Only import Organisation for type hints if type checking
if TYPE_CHECKING:
    from app.user.repository.schema.organisation import Organisation


class OrganisationRel(StructuredRel):
    role: str = StringProperty(default="MEMBER")
    created_at: datetime = DateTimeProperty(default=datetime.utcnow)
    updated_at: datetime = DateTimeProperty(default=datetime.utcnow)


class User(StructuredNode):
    uid: str = UniqueIdProperty()
    email: str = StringProperty(unique_index=True, required=True)
    password_hash: str = StringProperty()
    auth_provider: str = StringProperty(default="email")  # 'email' or 'google'
    auth_provider_detail: dict[str, Any] = JSONProperty()
    name: str = StringProperty()
    phone: str = StringProperty()
    image_url: str = StringProperty()
    job_role: str = StringProperty()
    is_email_verified: bool = BooleanProperty(default=False)
    is_profile_created: bool = BooleanProperty(default=False)
    profile_colour: str = StringProperty()
    created_at: datetime = DateTimeProperty(default=datetime.utcnow)
    updated_at: datetime = DateTimeProperty(default=datetime.utcnow)

    # Use string references for relationships
    member_of: Optional["Organisation"] = RelationshipTo(
        ".organisation.Organisation", "MEMBER_OF", model=OrganisationRel
    )
    requested_orgs: Optional["Organisation"] = RelationshipTo(
        ".organisation.Organisation", "REQUESTED_JOIN", model=OrganisationRel
    )


class GuideTour(StructuredNode):
    uid: str = UniqueIdProperty()
    user_id: str = StringProperty()
    analytics_tour: bool = BooleanProperty(default=False)
    knowledge_pal_tour: bool = BooleanProperty(default=False)
    integrations_tour: bool = BooleanProperty(default=False)
    home: bool = BooleanProperty(default=False)
    dashboard: bool = BooleanProperty(default=False)
    search: bool = BooleanProperty(default=False)
    sourcing: bool = BooleanProperty(default=False)
    rfp: bool = BooleanProperty(default=False)
    rfp_template: bool = BooleanProperty(default=False)
    created_at: datetime = DateTimeProperty(default=datetime.utcnow)
    updated_at: datetime = DateTimeProperty(default=datetime.utcnow)
