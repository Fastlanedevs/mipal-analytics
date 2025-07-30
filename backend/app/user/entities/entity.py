from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class Entity(BaseModel):
    id: str = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Role(Entity):
    name: str
    permissions: list[str]


class Organisation(Entity):
    name: str
    website: str
    address: str
    admin_position: str
    phone: str = ""
    logo: str
    owner_id: str = ""
    domain: str = ""  # For organisation's email domain


class UserOrgDetail(BaseModel):
    organisation_id: str
    role: str
    owner_id: str = ""


class User(Entity):
    email: str
    password_hash: str

    joined_org: bool = False
    org: UserOrgDetail = None
    name: str = ""
    is_active: bool = True
    auth_provider: str = "email"
    phone: str = ""
    job_role: str | None = ""
    is_profile_created: bool = False
    is_email_verified: bool = False
    image_url: str = ""
    profile_colour: str = ""


class UpdateUser(BaseModel):
    name: str | None = None
    phone: str | None = None
    image_url: str | None = None
    job_role: str | None = None


class UpdateOrganisation(BaseModel):
    name: str | None = None
    address: str | None = None
    phone: str | None = None
    website: str | None = None
    admin_position: str | None = None
    logo: str | None = None



class UserSettingsEntity(BaseModel):
    id: str | None = None
    user_id: str
    theme: str | None = None
    language: str | None = None
    timezone: str | None = None
    date_format: str | None = None
    pinned_sidebar: bool | None = None


class UpdateUserGuideTour(BaseModel):
    analytics_tour: bool | None = None
    knowledge_pal_tour: bool | None = None
    integrations_tour: bool | None = None
    home: bool | None = None
    dashboard: bool | None = None
    search: bool | None = None
    sourcing: bool | None = None
    rfp: bool | None = None
    rfp_template: bool | None = None

class GuideTour(BaseModel):
    analytics_tour: bool
    knowledge_pal_tour: bool
    integrations_tour: bool
    home: bool
    dashboard: bool
    search: bool
    sourcing: bool
    rfp: bool
    rfp_template: bool