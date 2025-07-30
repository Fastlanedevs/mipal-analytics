from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile

from app.middleware import get_token_detail
from app.user.api.dependencies import UserHandlerDep
from app.user.api.dto import (
    GetUserProfileDTO,
    GetUserSettingsDTO,
    JoinOrganisationRequest,
    OrganisationCreateDTO,
    OrganisationMemberDTO,
    OrganisationUpdateDTO,
    UpdateUserSettingsDTO,
    UserProfileCreateDTO,
    UserProfileUpdateDTO,
    GetUserGuideTourDTO,
    UpdateUserGuideTourDTO
)

user_router = APIRouter(prefix="/user", tags=["Users"])


# Organisation Management Routes
@user_router.post("/organizations")
async def create_organisation(org_data: OrganisationCreateDTO, response: Response,
                              token_detail: Annotated[str, Depends(get_token_detail)], handler: UserHandlerDep):
    """Create a new organisation"""
    return await handler.create_organisation(org_data, token_detail.user_id)


@user_router.get("/domain-organization")
async def get_user_domain_org(
        token_detail: Annotated[str, Depends(get_token_detail)], handler: UserHandlerDep
):
    """Create a new organisation"""
    return await handler.get_user_domain_org(token_detail.user_id)


# @user_router.get("/organisations")
# async def list_organisations(token_detail: Annotated[str, Depends(get_token_detail)],
#         handler: UserHandlerDep):
#     """List user's organisations"""
#     return await handler.list_organisations(token_detail.user_id)
#


@user_router.get("/organization")
async def get_organisation(
        token_detail: Annotated[str, Depends(get_token_detail)], handler: UserHandlerDep
):
    # if org_id not exist raise exception
    if not token_detail.joined_org:
        raise HTTPException(
            status_code=400, detail="Organisation should be created or joined"
        )
    return await handler.get_organisation(token_detail.org_id, token_detail.user_id)


@user_router.patch("/organization")
async def update_organisation(
        org_data: OrganisationUpdateDTO,
        token_detail: Annotated[str, Depends(get_token_detail)],
        handler: UserHandlerDep,
):
    if not token_detail.joined_org:
        raise HTTPException(
            status_code=400, detail="Organisation should be created or joined"
        )
    """Update organisation details"""
    return await handler.update_organisation(
        token_detail.org_id,
        token_detail.user_id,
        org_data,
    )


@user_router.post("/organizations/{organization_id}")
async def join_organisation_with_domain(
        organization_id: str,
        token_detail: Annotated[str, Depends(get_token_detail)],
        handler: UserHandlerDep,
):
    return await handler.join_organisation_with_domain(
        token_detail.user_id, organization_id
    )


# Organisation join using invite
@user_router.post("/organization/join")
async def join_organisation(
        data: JoinOrganisationRequest,
        token_detail: Annotated[str, Depends(get_token_detail)],
        handler: UserHandlerDep,
):
    if not token_detail.joined_org:
        raise HTTPException(
            status_code=400, detail="Organisation should be created or joined"
        )

    return await handler.join_organisation(token_detail.user_id, data)


# Member Management Routes
@user_router.get("/organizations/members")
async def list_organisation_members(
        org_id: str,
        token_detail: Annotated[str, Depends(get_token_detail)],
        handler: UserHandlerDep,
) -> list[OrganisationMemberDTO]:
    """List organisation members"""
    return await handler.list_organisation_members(org_id, token_detail.user_id)


# User Profile Routes
@user_router.get("/profile")
async def get_profile(
        token_detail: Annotated[str, Depends(get_token_detail)], handler: UserHandlerDep
) -> GetUserProfileDTO:
    """Get user profile"""
    return await handler.get_profile(token_detail.user_id)


@user_router.post("/profile")
async def create_profile(
        profile_data: UserProfileCreateDTO,
        token_detail: Annotated[str, Depends(get_token_detail)],
        handler: UserHandlerDep,
) -> GetUserProfileDTO:
    """Update user profile"""
    return await handler.create_profile(profile_data, token_detail.user_id)


@user_router.patch("/profile")
async def update_profile(
        profile_data: UserProfileUpdateDTO,
        token_detail: Annotated[str, Depends(get_token_detail)],
        handler: UserHandlerDep,
) -> GetUserProfileDTO:
    """Update user profile"""
    return await handler.update_profile(profile_data, token_detail.user_id)


@user_router.post("/upload/")
async def upload_file(
        token_detail: Annotated[str, Depends(get_token_detail)],
        handler: UserHandlerDep,
        file: UploadFile = File(...),
):
    """Update user profile"""
    return await handler.upload_file(file, token_detail.user_id)


@user_router.get("/settings")
async def get_settings(
        token_detail: Annotated[str, Depends(get_token_detail)], handler: UserHandlerDep
) -> GetUserSettingsDTO:
    return await handler.get_settings(token_detail.user_id)


@user_router.patch("/settings")
async def update_settings(
        request: UpdateUserSettingsDTO,
        token_detail: Annotated[str, Depends(get_token_detail)],
        handler: UserHandlerDep,
) -> GetUserSettingsDTO:
    return await handler.update_settings(token_detail.user_id, request)


@user_router.patch("/guide-tour")
async def update_guide_tour(request: UpdateUserGuideTourDTO, token_detail: Annotated[str, Depends(get_token_detail)],
                            handler: UserHandlerDep
                            ) -> GetUserGuideTourDTO:
    return await handler.update_guide_tour(token_detail.user_id, request)


@user_router.get("/guide-tour")
async def get_guide_tour(token_detail: Annotated[str, Depends(get_token_detail)], handler: UserHandlerDep
                         ) -> GetUserGuideTourDTO:
    return await handler.get_guide_tour(token_detail.user_id)
