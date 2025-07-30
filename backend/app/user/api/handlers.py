from typing import Any

from fastapi import HTTPException, Response, UploadFile

from app.user.api.dto import (
    CreateOrganisationResponseDTO,
    FileUploadResponseDTO,
    GetUserProfileDTO,
    GetUserSettingsDTO,
    InvitationAcceptDTO,
    OrganisationCreateDTO,
    OrganisationDetailsDTO,
    OrganisationDetailUserProfileDTO,
    OrganisationMemberDTO,
    OrganisationUpdateDTO,
    UpdateUserSettingsDTO,
    UserInviteDTO,
    UserProfileCreateDTO,
    UserProfileUpdateDTO,
    UpdateUserGuideTourDTO,
    GetUserGuideTourDTO
)
from app.user.entities.aggregate import UserAggregate
from app.user.entities.entity import (
    Organisation,
    UpdateOrganisation,
    UpdateUser,
    UserSettingsEntity,
UpdateUserGuideTour
)
from app.user.service.user_service import UserService
from pkg.log.logger import Logger


class UserHandler:
    def __init__(self, user_service: UserService, logger: Logger) -> None:
        self.user_service = user_service
        self.logger = logger

    async def get_user_domain_org(self, user_id: str) -> OrganisationDetailsDTO | None:
        result: Organisation = await self.user_service.get_user_domain_org(user_id)

        return OrganisationDetailsDTO(
            id=result.id,
            name=result.name,
            domain=result.domain,
            address=result.address,
            phone=result.phone,
            website=result.website,
            logo=result.logo,
            created_at=result.created_at,
            updated_at=result.updated_at,
        )

    async def create_organisation(
            self, org_data: OrganisationCreateDTO, current_user_id: str
    ) -> dict[str, Any]:
        org_entity = model_create_organisation_dto_to_entity(org_data)
        result, tokens = await self.user_service.create_organisation(
            user_id=current_user_id, organisation=org_entity
        )

        return {
            "organisation": CreateOrganisationResponseDTO(
                id=result.id,
                name=result.name,
                address=result.address,
                phone=result.phone,
                website=result.website,
                admin_position=result.admin_position,
                logo=result.logo,
                domain=result.domain,
                created_at=result.created_at,
                updated_at=result.updated_at,
            ),
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": "bearer",
        }

    async def list_organisations(
            self, current_user_id: str
    ) -> list[OrganisationCreateDTO]:
        result = await self.user_service.list_user_organisations(current_user_id)
        list_organisations_dto = [OrganisationCreateDTO()]
        return list_organisations_dto

    async def get_organisation(self, org_id: str, user_id: str) -> OrganisationDetailsDTO:
        org = await self.user_service.get_organisation(org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organisation not found")
        organisation_details_dto = OrganisationDetailsDTO(
            id=org.id,
            name=org.name,
            domain=org.domain,
            address=org.address,
            phone=org.phone,
            website=org.website,
            logo=org.logo,
            created_at=org.created_at,
            updated_at=org.updated_at,
        )
        return organisation_details_dto

    async def update_organisation(
            self, org_id: str, use_id: str, org_update_dto: OrganisationUpdateDTO
    ):
        org_update_entity = UpdateOrganisation(
            name=org_update_dto.name,
            address=org_update_dto.address,
            phone=org_update_dto.phone,
            website=org_update_dto.website,
            admin_position=org_update_dto.admin_position,
            logo=org_update_dto.logo,
        )

        org = await self.user_service.update_organisation(
            use_id, org_id, org_update_entity
        )
        if not org:
            raise HTTPException(status_code=404, detail="Organisation not found")
        organisation_details_dto = OrganisationDetailsDTO(
            id=org.id,
            name=org.name,
            domain=org.domain,
            address=org.address,
            phone=org.phone,
            website=org.website,
            logo=org.logo,
            created_at=org.created_at,
            updated_at=org.updated_at,
        )
        return organisation_details_dto

    async def join_organisation_with_domain(
            self, user_id: str, org_id: str
    ) -> dict[str, Any]:
        result, tokens = await self.user_service.join_organisation_with_domain(
            user_id=user_id, org_id=org_id
        )

        return {
            "organisation": CreateOrganisationResponseDTO(
                id=result.id,
                name=result.name,
                address=result.address,
                phone=result.phone,
                website=result.website,
                admin_position=result.admin_position,
                logo=result.logo,
                domain=result.domain,
                created_at=result.created_at,
                updated_at=result.updated_at,
            ),
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": "bearer",
        }

    async def invite_to_organisation(
            self, org_id: str, invite_data: UserInviteDTO, current_user_id: str
    ) -> dict:
        return await self.user_service.invite_user(
            org_id=org_id, inviter_id=current_user_id, email=invite_data.email
        )

    async def accept_invitation(
            self, org_id: str, accept_data: InvitationAcceptDTO, current_user_id: str
    ) -> dict:
        return await self.user_service.accept_invitation(
            org_id=org_id, user_id=current_user_id, token=accept_data.token
        )

    async def request_join_organisation(
            self, org_id: str, current_user_id: str
    ) -> dict:
        return await self.user_service.request_join_organisation(
            org_id=org_id, user_id=current_user_id
        )

    async def list_join_requests(self, org_id: str, current_user_id: str) -> list[str]:
        return await self.user_service.list_join_requests(org_id)

    async def approve_join_request(
            self, org_id: str, user_id: str, current_user_id: str
    ) -> dict:
        return await self.user_service.approve_join_request(
            org_id=org_id, approver_id=current_user_id, user_id=user_id
        )

    async def reject_join_request(
            self, org_id: str, user_id: str, current_user_id: str
    ) -> dict:
        return await self.user_service.reject_join_request(
            org_id=org_id, rejector_id=current_user_id, user_id=user_id
        )

    async def list_organisation_members(
            self, org_id: str, current_user_id: str
    ) -> list[OrganisationMemberDTO]:
        return await self.user_service.list_organisation_members(org_id, current_user_id)

    async def get_profile(self, current_user_id: str) -> GetUserProfileDTO:
        user_result: UserAggregate = await self.user_service.get_user_profile(
            current_user_id
        )
        return model_user_profile_entity_to_dto(user_result)

    async def update_profile(
            self, profile_data: UserProfileUpdateDTO, current_user_id: str
    ) -> GetUserProfileDTO:
        update_user = UpdateUser(
            name=profile_data.name,
            phone=profile_data.phone,
            image_url=profile_data.image_url,
            job_role=profile_data.job_role,
        )
        result = await self.user_service.update_user(current_user_id, update_user)

        return model_user_profile_entity_to_dto(result)

    async def create_profile(
            self, profile_data: UserProfileCreateDTO, user_id: str
    ) -> GetUserProfileDTO:
        update_user = UpdateUser(
            name=profile_data.name,
            phone=profile_data.phone,
            image_url=profile_data.image_url,
            job_role=profile_data.job_role,
        )
        result = await self.user_service.update_user(user_id, update_user)
        return model_user_profile_entity_to_dto(result)


    async def get_settings(self, user_id: str) -> GetUserSettingsDTO:
        result = await self.user_service.get_user_settings(user_id)
        return GetUserSettingsDTO(
            user_id=user_id,
            theme=result.theme,
            language=result.language,
            timezone=result.timezone,
            date_format=result.date_format,
            pinned_sidebar=result.pinned_sidebar,
        )

    async def update_settings(
            self, user_id: str, update_data: UpdateUserSettingsDTO
    ) -> GetUserSettingsDTO:
        update_data = UserSettingsEntity(
            user_id=user_id,
            theme=update_data.theme,
            language=update_data.language,
            timezone=update_data.timezone,
            date_format=update_data.date_format,
            pinned_sidebar=update_data.pinned_sidebar,
        )
        result = await self.user_service.update_user_settings(user_id, update_data)
        return GetUserSettingsDTO(
            user_id=user_id,
            theme=result.theme,
            language=result.language,
            timezone=result.timezone,
            date_format=result.date_format,
            pinned_sidebar=result.pinned_sidebar,
        )

    async def update_guide_tour(self, user_id: str, request: UpdateUserGuideTourDTO) -> GetUserGuideTourDTO:
        guide_tour_update = UpdateUserGuideTour(
            analytics_tour=request.analytics_tour,
            knowledge_pal_tour=request.knowledge_pal_tour,
            integrations_tour=request.integrations_tour,
            home=request.home,
            dashboard=request.dashboard,
            search=request.search,
            sourcing=request.sourcing,
            rfp=request.rfp,
            rfp_template=request.rfp_template
        )
        guide_tour = await self.user_service.update_guide_tour(user_id, guide_tour_update)
        return GetUserGuideTourDTO(
            analytics_tour=guide_tour.analytics_tour,
            knowledge_pal_tour=guide_tour.knowledge_pal_tour,
            integrations_tour=guide_tour.integrations_tour,
            home=guide_tour.home,
            dashboard=guide_tour.dashboard,
            search=guide_tour.search,
            sourcing=guide_tour.sourcing,
            rfp=guide_tour.rfp,
            rfp_template=guide_tour.rfp_template
        )

    async def get_guide_tour(self, user_id: str) -> GetUserGuideTourDTO:
        guide_tour = await self.user_service.get_guide_tour(user_id)
        return GetUserGuideTourDTO(
            analytics_tour=guide_tour.analytics_tour,
            knowledge_pal_tour=guide_tour.knowledge_pal_tour,
            integrations_tour=guide_tour.integrations_tour,
            home=guide_tour.home,
            dashboard=guide_tour.dashboard,
            search=guide_tour.search,
            sourcing=guide_tour.sourcing,
            rfp=guide_tour.rfp,
            rfp_template=guide_tour.rfp_template
        )

    def _set_auth_cookies(self, response: Response, tokens: dict):
        response.set_cookie(
            key="access_token",
            value=tokens["access_token"],
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=1800,  # 30 minutes
        )
        response.set_cookie(
            key="refresh_token",
            value=tokens["refresh_token"],
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=604800,  # 7 days
        )


def model_user_profile_entity_to_dto(
        user_profile_entity: UserAggregate,
) -> GetUserProfileDTO:
    dto = GetUserProfileDTO(
        user_id=user_profile_entity.user.id,
        email=user_profile_entity.user.email,
        phone=user_profile_entity.user.phone,
        name=user_profile_entity.user.name,
        joined_org=user_profile_entity.user.joined_org,
        image_url=user_profile_entity.user.image_url,
        job_role=user_profile_entity.user.job_role,
        is_profile_created=user_profile_entity.user.is_profile_created,
        auth_provider=user_profile_entity.user.auth_provider,
        created_at=user_profile_entity.user.created_at,
        profile_colour=user_profile_entity.user.profile_colour,
    )
    if user_profile_entity.user.joined_org:
        dto.role = user_profile_entity.user.org.role
        org = OrganisationDetailUserProfileDTO(
            id=user_profile_entity.user.org.organisation_id,
            admin=user_profile_entity.user.org.owner_id,
        )
        dto.organisation = org

    return dto


def model_create_organisation_dto_to_entity(
        data: OrganisationCreateDTO,
) -> Organisation:
    return Organisation(
        name=data.name,
        address=data.address,
        phone=data.phone,
        website=data.website,
        admin_position=data.admin_position,
        logo=data.logo,
    )
