import uuid
from abc import ABC, abstractmethod
from typing import Any

from fastapi import HTTPException

from app.user.entities.aggregate import UserAggregate
from app.user.entities.entity import (
    Organisation,
    UpdateOrganisation,
    UpdateUser,
    UserSettingsEntity,
    GuideTour,
UpdateUserGuideTour
)
from app.user.entities.value_objects import UserRole
from pkg.auth_token_client.client import TokenClient, TokenPayload
from pkg.log.logger import Logger
from pkg.util.generate_colour import generate_profile_color
from pkg.util.vaidate_email import get_domain, is_company_email


class IUserRepository(ABC):
    @abstractmethod
    async def create_user(
            self,
            email: str,
            password_hash: str,
            is_email_verified: bool,
            name: str,
            auth_provider: str = "email",
            auth_provider_detail: dict = None,
            profile_colour="",
    ) -> UserAggregate:
        pass

    @abstractmethod
    async def get_user_by_email(self, email: str) -> UserAggregate | None:
        pass

    @abstractmethod
    async def get_user_by_id(self, user_id: str) -> UserAggregate | None:
        pass

    @abstractmethod
    async def update_email_verification(
            self, user_id: str, is_verified: bool
    ) -> UserAggregate:
        pass

    @abstractmethod
    async def create_organisation(self, organisation: Organisation) -> Organisation:
        pass

    @abstractmethod
    async def get_organisation_by_id(self, org_id: str) -> Organisation | None:
        pass

    @abstractmethod
    async def get_organisation_member(
            self, org_id: str, user_id: str
    ) -> dict[str, Any] | None:
        pass

    @abstractmethod
    async def list_organisation_members(self, org_id: str) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    async def request_join_organisation(self, user_id: str, org_id: str):
        pass

    @abstractmethod
    async def get_user_organisation(self, user_id: str) -> Organisation:
        pass

    @abstractmethod
    async def get_pending_join_requests(self, user_id: str) -> list[Organisation]:
        pass

    @abstractmethod
    async def update_user(self, user_id: str, update_data: UpdateUser) -> UserAggregate:
        pass

    @abstractmethod
    async def update_organisation(self, user_id: str, org_id: str,
                                  update_data: UpdateOrganisation) -> Organisation | None:
        pass

    @abstractmethod
    async def get_domain_org(self, domain: str) -> Organisation:
        pass

    @abstractmethod
    async def join_organisation_with_domain(
            self, user_id: str, org_id: str
    ) -> Organisation:
        pass


    @abstractmethod
    async def get_user_settings(self, user_id: str) -> UserSettingsEntity:
        pass

    @abstractmethod
    async def update_user_settings(
            self, user_id: str, update_data: UserSettingsEntity
    ) -> UserSettingsEntity:
        pass

    @abstractmethod
    async def create_user_settings(
            self, user_id: str, user_settings: UserSettingsEntity
    ) -> UserSettingsEntity:
        pass

    @abstractmethod
    async def create_guide_tour(self, user_id: str, guide_tour: GuideTour) -> GuideTour:
        pass

    @abstractmethod
    async def get_guide_tour(self, user_id: str) -> GuideTour:
        pass

    @abstractmethod
    async def update_guide_tour(self, user_id: str, guide_tour_update: UpdateUserGuideTour) -> GuideTour:
        pass

    @abstractmethod
    async def update_user_password(self, user_id: str, password_hash: str) -> UserAggregate:
        """Update user password hash"""
        pass




class UserService:
    def __init__(
            self,
            user_repository: IUserRepository,
            logger: Logger,
            token_client: TokenClient,
    ):
        self.user_repository = user_repository
        self.logger = logger
        self.token_client = token_client

    async def create_user(
            self,
            email: str,
            password_hash: str,
            name: str,
            is_email_verified: bool,
            auth_provider: str = "email",
            auth_provider_detail: dict = None,
    ) -> UserAggregate:
        """Create a new user"""
        existing_user = await self.get_user_by_email(email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        profile_colour = generate_profile_color()
        user = await self.user_repository.create_user(
            email=email,
            password_hash=password_hash,
            auth_provider=auth_provider,
            name=name,
            is_email_verified=is_email_verified,
            auth_provider_detail=auth_provider_detail,
            profile_colour=profile_colour,
        )

        return user

    async def get_user_by_email(self, email: str) -> UserAggregate | None:
        """Get user by email"""
        return await self.user_repository.get_user_by_email(email)

    async def get_user_by_id(self, user_id: str) -> UserAggregate | None:
        """Get user by ID"""
        return await self.user_repository.get_user_by_id(user_id)

    async def get_user_domain_org(self, user_id: str) -> Organisation:
        try:
            user = await self.user_repository.get_user_by_id(user_id)
        except HTTPException:
            raise HTTPException(status_code=404, detail="User not found")
        domain = get_domain(user.user.email)

        return await self.user_repository.get_domain_org(domain)

    async def update_email_verification(
            self, user_id: str, is_verified: bool = True
    ) -> None:
        """Update user's email verification status"""
        await self.user_repository.update_email_verification(user_id, is_verified)
        return

    async def create_organisation(
            self, user_id: str, organisation: Organisation
    ) -> tuple[Organisation, dict[str, str]]:
        try:
            user = await self.user_repository.get_user_by_id(user_id)
        except HTTPException:
            raise HTTPException(status_code=404, detail="User not found")

        if is_company_email(user.user.email):
            organisation.domain = get_domain(user.user.email)

        organisation.owner_id = user_id
        org = await self.user_repository.create_organisation(organisation)

        # Get updated user info to get role
        role = "ADMIN"

        # Create new tokens with updated org info
        payload = TokenPayload(
            user_id=user_id, joined_org=True, role=role, org_id=org.id
        )
        tokens = self.token_client.create_tokens(payload)

        return org, tokens

    async def get_organisation(self, org_id: str) -> Organisation | None:
        org = await self.user_repository.get_organisation_by_id(org_id)
        if org:
            return org
        return None

    async def get_user_organisation(self, user_id: str) -> Organisation | None:
        org = await self.user_repository.get_user_organisation(user_id)
        if org:
            return org
        return None

    async def update_organisation(
            self, user_id: str, org_id: str, org_update: UpdateOrganisation
    ) -> Organisation:
        if not await self._can_manage_organisation(org_id, user_id):
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        org = await self.user_repository.update_organisation(
            user_id, org_id, org_update
        )
        return org

    async def invite_user(
            self, org_id: str, inviter_id: str, email: str
    ) -> dict[str, Any]:
        if not await self._can_manage_organisation(org_id, inviter_id):
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        return await self.user_repository.create_invitation(org_id, email)

    async def accept_invitation(
            self, org_id: str, user_id: str, token: str
    ) -> dict[str, Any]:
        return await self.user_repository.accept_invitation(org_id, user_id, token)

    async def _can_manage_organisation(self, org_id: str, user_id: str) -> bool:
        member = await self.user_repository.get_organisation_member(org_id, user_id)
        return member and member["role"] in [UserRole.ADMIN]

    async def list_organisation_members(self, org_id: str, current_user_id: str) -> list[dict[str, Any]]:
        """List all members of an organisation"""
        # First, check if the user is a member of this organization
        member = await self.user_repository.get_organisation_member(org_id, current_user_id)
        if not member:
            raise HTTPException(status_code=403, detail="You are not a member of this organization")

        # Retrieve all members from the organisation
        members = await self.user_repository.list_organisation_members(org_id)

        # Omit the current user from the list of members
        members = [member for member in members if member["user_id"] != current_user_id]
        return members

    async def get_user_profile(self, user_id: str) -> UserAggregate:
        user = await self.user_repository.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    async def update_user(self, user_id: str, update_data: UpdateUser) -> UserAggregate:
        # Update user through repository
        try:
            updated_user = await self.user_repository.update_user(user_id, update_data)
            return updated_user
        except Exception as e:
            self.logger.error(f"Error updating user: {e!s}")
            raise HTTPException(status_code=500, detail="Error updating user")

    async def update_user_password(self, user_id: str, password_hash: str) -> UserAggregate:
        """Update user's password hash"""
        try:
            user = await self.user_repository.update_user_password(user_id, password_hash)
            return user
        except Exception as e:
            self.logger.error(f"Error updating user password: {e!s}")
            raise HTTPException(status_code=500, detail="Failed to update password")

    async def get_user_settings(self, user_id: str) -> UserSettingsEntity:
        try:
            user_settings = await self.user_repository.get_user_settings(user_id)
            if not user_settings:
                # Create new settings
                user_settings = UserSettingsEntity(
                    id=uuid.uuid4().hex,
                    user_id=user_id,
                    theme="dark",
                    language="en",
                    timezone="UTC",
                    date_format="DD/MM/YYYY",
                    pinned_sidebar=False,
                )
                await self.user_repository.create_user_settings(user_id, user_settings)
            return user_settings
        except Exception as e:
            self.logger.error(f"Error getting user settings: {e!s}")
            raise HTTPException(status_code=500, detail="Error getting user settings")

    async def update_user_settings(
            self, user_id: str, update_data: UserSettingsEntity
    ) -> UserSettingsEntity:
        return await self.user_repository.update_user_settings(user_id, update_data)

    async def create_user_settings(
            self, user_id: str, user_settings: UserSettingsEntity
    ) -> UserSettingsEntity:
        try:
            return await self.user_repository.create_user_settings(
                user_id, user_settings
            )
        except Exception as e:
            self.logger.error(f"Error creating user settings: {e!s}")
            raise HTTPException(status_code=500, detail="Error creating user settings")

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user"""
        try:
            return await self.user_repository.delete_user(user_id)
        except Exception as e:
            self.logger.error(f"Error deleting user: {e!s}")
            raise HTTPException(status_code=500, detail="Failed to delete user")

    async def get_guide_tour(self, user_id: str) -> GuideTour:
        try:
            guide_tour = await self.user_repository.get_guide_tour(user_id)
            if not guide_tour:
                # Create new guide tour
                guide_tour = GuideTour(
                    analytics_tour=False,
                    knowledge_pal_tour=False,
                    integrations_tour=False,
                    home=False,
                    dashboard=False,
                    search=False,
                    sourcing=False,
                    rfp=False,
                    rfp_template=False
                )
                await self.user_repository.create_guide_tour(user_id, guide_tour)
            return guide_tour
        except Exception as e:
            self.logger.error(f"Error getting guide tour: {e!s}")
            raise HTTPException(status_code=500, detail="Error getting guide tour")

    async def update_guide_tour(
            self, user_id: str, update_data: UpdateUserGuideTour
    ) -> GuideTour:
        return await self.user_repository.update_guide_tour(user_id, update_data)

    async def join_organisation_with_domain(
            self, user_id: str, org_id: str
    ) -> tuple[Organisation, dict[str, str]]:
        try:
            user = await self.user_repository.get_user_by_id(user_id)
        except HTTPException:
            raise HTTPException(status_code=404, detail="User not found")
        domain = get_domain(user.user.email)

        org = await self.user_repository.get_domain_org(domain)
        if org.id != org_id:
            raise HTTPException(
                status_code=400, detail="User is not in this organisation"
            )

        joined_org = await self.user_repository.join_organisation_with_domain(
            user_id, org_id
        )
        # Get updated user info to get role
        role = "MEMBER"

        # Create new tokens with updated org info
        payload = TokenPayload(
            user_id=user_id, joined_org=True, role=role, org_id=joined_org.id
        )
        tokens = self.token_client.create_tokens(payload)

        return joined_org, tokens



