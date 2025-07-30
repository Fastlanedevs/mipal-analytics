from datetime import datetime

from pydantic import BaseModel


class UserInviteDTO(BaseModel):
    email: str


class InvitationAcceptDTO(BaseModel):
    token: str


class RoleUpdateDTO(BaseModel):
    role: str


class OrganisationMemberDTO(BaseModel):
    user_id: str
    email: str
    role: str


class OrganisationDetailsDTO(BaseModel):
    id: str
    name: str
    domain: str
    address: str
    phone: str
    website: str
    logo: str
    created_at: datetime
    updated_at: datetime


class OrganisationCreateDTO(BaseModel):
    name: str
    address: str = ""
    phone: str = ""
    website: str = ""
    admin_position: str = ""
    logo: str = ""


class CreateOrganisationResponseDTO(BaseModel):
    id: str
    name: str
    domain: str
    address: str
    phone: str
    website: str
    admin_position: str
    logo: str
    created_at: datetime
    updated_at: datetime


class OrganisationUpdateDTO(BaseModel):
    name: str | None = None
    address: str | None = None
    phone: str | None = None
    website: str | None = None
    admin_position: str | None = None
    logo: str | None = None


class UserProfileUpdateDTO(BaseModel):
    phone: str | None = None
    name: str | None = None
    image_url: str | None = None
    job_role: str | None = None


class UserProfileCreateDTO(BaseModel):
    phone: str | None = None
    name: str | None = None
    image_url: str | None = None
    job_role: str | None = None


class OrganisationDetailUserProfileDTO(BaseModel):
    id: str

    admin: str


class GetUserProfileDTO(BaseModel):
    user_id: str
    email: str
    phone: str
    name: str
    joined_org: bool
    image_url: str
    auth_provider: str
    is_profile_created: bool
    job_role: str
    created_at: datetime
    organisation: OrganisationDetailUserProfileDTO | None = None
    role: str = ""
    profile_colour: str = ""


class FileUploadResponseDTO(BaseModel):
    file_id: str
    filename: str
    file_size: int
    mime_type: str
    upload_date: datetime
    presigned_url: str
    expiration: datetime
    is_encrypted: bool


class JoinOrganisationRequest(BaseModel):
    organization_id: str


class GetUserSettingsDTO(BaseModel):
    user_id: str
    theme: str
    language: str
    timezone: str
    date_format: str
    pinned_sidebar: bool = False


class UpdateUserSettingsDTO(BaseModel):
    theme: str | None = None
    language: str | None = None
    timezone: str | None = None
    date_format: str | None = None
    pinned_sidebar: bool | None = None


class UpdateUserGuideTourDTO(BaseModel):
    analytics_tour: bool | None = None
    knowledge_pal_tour: bool | None = None
    integrations_tour: bool | None = None
    home: bool | None = None
    dashboard: bool | None = None
    search: bool | None = None
    sourcing: bool | None = None
    rfp: bool | None = None
    rfp_template: bool | None = None

class GetUserGuideTourDTO(BaseModel):
    analytics_tour: bool
    knowledge_pal_tour: bool
    integrations_tour: bool
    home: bool
    dashboard: bool
    search: bool
    sourcing: bool
    rfp: bool
    rfp_template: bool