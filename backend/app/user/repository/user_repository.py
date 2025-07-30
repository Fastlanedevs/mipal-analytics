from typing import Any
from uuid import UUID

from fastapi import HTTPException

from app.user.entities.aggregate import UserAggregate
from app.user.entities.entity import Organisation as OrganisationEntity
from app.user.entities.entity import (
    UpdateOrganisation,
    UpdateUser,
    UserOrgDetail,
    UserSettingsEntity, GuideTour as GuideTourEntity, UpdateUserGuideTour
)
from app.user.entities.entity import User as UserEntity
from app.user.repository.schema.organisation import Organisation
from app.user.repository.schema.user import User, GuideTour
from app.user.repository.schema.user_settings import UserSettings
from app.user.service.user_service import IUserRepository
from pkg.db_util.neo4j_conn import Neo4jConnection
from pkg.log.logger import Logger
from pkg.util.generate_colour import generate_profile_color
import base64


class UserRepository(IUserRepository):
    def __init__(self, db_conn: Neo4jConnection, logger: Logger):
        self.db_conn = db_conn
        self.logger = logger

    async def create_user(
            self,
            email: str,
            password_hash: str,
            is_email_verified: bool,
            name: str,
            auth_provider: str = "email",
            auth_provider_detail: dict = None,
            profile_colour: str = "",
    ) -> UserAggregate:
        """Create a new user"""
        if auth_provider_detail is None:
            auth_provider_detail = {}
        try:
            user = User(
                email=email,
                password_hash=password_hash,
                auth_provider=auth_provider,
                auth_provider_detail=auth_provider_detail,
                name=name,
                phone="",
                image_url="",
                job_role="",
                is_email_verified=is_email_verified,
                profile_colour=profile_colour,
            ).save()

            user_entity = UserEntity(
                id=user.uid,
                email=user.email,
                password_hash=user.password_hash,
                auth_provider=user.auth_provider,
                is_email_verified=user.is_email_verified,
                job_role=user.job_role,
                created_at=user.created_at,
                updated_at=user.updated_at,
                profile_colour=profile_colour,
            )

            return UserAggregate(user=user_entity, events=["UserCreated"])

        except Exception as e:
            self.logger.error(f"Error creating user: {e!s}")
            raise

    async def get_user_by_email(self, email: str) -> UserAggregate | None:
        """Get user by email"""
        try:
            user = User.nodes.get_or_none(email=email)
            if not user:
                return None
            # get if any orgs related to user

            user_entity = UserEntity(
                id=user.uid,
                email=user.email,
                password_hash=user.password_hash,
                auth_provider=user.auth_provider,
                job_role=user.job_role,
                image_url=user.image_url,
                is_profile_created=user.is_profile_created,
                is_email_verified=user.is_email_verified,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
            if len(user.member_of) == 0:
                return UserAggregate(user=user_entity)
            org = user.member_of[0]
            member_of_relation = user.member_of.relationship(org)
            user_org = UserOrgDetail(
                organisation_id=org.uid,
                role=member_of_relation.role,
                owner_id=org.created_by,
            )
            user_entity.joined_org = True
            user_entity.org = user_org
            return UserAggregate(user=user_entity)

        except Exception as e:
            self.logger.error(f"Error getting user by email: {e!s}")
            raise

    async def get_user_by_id(self, user_id: str) -> UserAggregate | None:
        """Get user by ID"""
        try:
            user = User.nodes.get_or_none(uid=user_id)
            if not user:
                return None
            if user.profile_colour is None:
                user.profile_colour = generate_profile_color()
                user.save()
            user_entity = UserEntity(
                id=user.uid,
                email=user.email,
                password_hash=user.password_hash,
                auth_provider=user.auth_provider,
                is_email_verified=user.is_email_verified,
                name=user.name,
                phone=user.phone,
                image_url=user.image_url,
                is_profile_created=user.is_profile_created,
                job_role=user.job_role,
                profile_colour=user.profile_colour,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
            if len(user.member_of) == 0:
                return UserAggregate(user=user_entity)
            org = user.member_of[0]
            member_of_relation = user.member_of.relationship(org)
            user_org = UserOrgDetail(
                organisation_id=org.uid,
                role=member_of_relation.role,
                owner_id=org.created_by,
            )
            user_entity.joined_org = True
            user_entity.org = user_org
            return UserAggregate(user=user_entity)

        except Exception as e:
            self.logger.error(f"Error getting user by ID: {e!s}")
            raise e

    async def update_email_verification(
            self, user_id: str, is_verified: bool
    ) -> UserAggregate:
        """Update email verification status"""
        try:
            user = User.nodes.get(uid=user_id)
            user.is_email_verified = is_verified
            user.save()

            user_entity = UserEntity(
                id=user.uid,
                email=user.email,
                password_hash=user.password_hash,
                auth_provider=user.auth_provider,
                is_email_verified=user.is_email_verified,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )

            return UserAggregate(user=user_entity, events=["EmailVerificationUpdated"])

        except User.DoesNotExist:
            self.logger.error(f"User not found with ID: {user_id}")
            raise

    async def update_user_password(self, user_id: str, password_hash: str) -> UserAggregate:
        """Update user password hash"""
        try:
            user = User.nodes.get(uid=user_id)
            
            # Only allow password updates for email auth providers
            if user.auth_provider != "email":
                raise HTTPException(
                    status_code=400, 
                    detail=f"Cannot update password for {user.auth_provider} authentication"
                )
                
            # Update password hash
            user.password_hash = password_hash
            user.save()
            
            # Return updated user
            user_entity = UserEntity(
                id=user.uid,
                email=user.email,
                password_hash=user.password_hash,
                auth_provider=user.auth_provider,
                is_email_verified=user.is_email_verified,
                name=user.name,
                phone=user.phone,
                image_url=user.image_url,
                is_profile_created=user.is_profile_created,
                job_role=user.job_role,
                profile_colour=user.profile_colour,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
            
            # Add org details if present
            if len(user.member_of) > 0:
                org = user.member_of[0]
                member_of_relation = user.member_of.relationship(org)
                user_org = UserOrgDetail(
                    organisation_id=org.uid,
                    role=member_of_relation.role,
                    owner_id=org.created_by,
                )
                user_entity.joined_org = True
                user_entity.org = user_org
                
            return UserAggregate(user=user_entity, events=["PasswordUpdated"])
            
        except User.DoesNotExist:
            self.logger.error(f"User not found with ID: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        except Exception as e:
            self.logger.error(f"Error updating user password: {e!s}")
            raise HTTPException(status_code=500, detail="Failed to update password")

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user"""
        try:
            user = User.nodes.get(uid=user_id)
            user.delete()
            return True
        except User.DoesNotExist:
            self.logger.error(f"User not found with ID: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        except Exception as e:
            self.logger.error(f"Error deleting user: {e!s}")
            raise HTTPException(status_code=500, detail="Failed to delete user")

    async def create_organisation(
            self, organisation: OrganisationEntity
    ) -> OrganisationEntity:
        """Create a new organisation"""
        try:
            # First check if user exists and is already linked to an organization
            user = User.nodes.get(uid=organisation.owner_id)
            existing_orgs = user.member_of.all()

            if existing_orgs:
                raise HTTPException(
                    status_code=400, detail="User is already linked to an organization"
                )

            # Create new organization
            org = Organisation(
                name=organisation.name,
                domain=organisation.domain,
                website=organisation.website,
                phone=organisation.phone,
                address=organisation.address,
                logo=organisation.logo,
                admin_position=organisation.admin_position,
                created_by=organisation.owner_id,
            ).save()

            # Connect owner as member
            user.member_of.connect(org, {"role": "ADMIN"})

            user.save()

            org_entity = OrganisationEntity(
                id=org.uid,
                name=org.name,
                address=org.address,
                phone=org.phone,
                website=org.website,
                logo=org.logo,
                admin_position=org.admin_position,
            )

            return org_entity

        except User.DoesNotExist:
            self.logger.error(f"User not found with ID: {organisation.owner_id}")
            raise HTTPException(status_code=404, detail="User not found")
        except Exception as e:
            self.logger.error(f"Error creating organisation: {e!s}")
            raise

    async def get_organisation_by_id(self, org_id: str) -> OrganisationEntity | None:
        """Get organisation by ID"""
        try:
            org = Organisation.nodes.get(uid=org_id)

            org_entity = OrganisationEntity(
                id=org.uid,
                name=org.name,
                address=org.address,
                website=org.website,
                phone=org.phone,
                logo=org.logo,
                admin_position=org.admin_position,
                owner_id=org.created_by,
                crated_at=org.created_at,
                updated_at=org.updated_at,
            )

            return org_entity

        except Organisation.DoesNotExist:
            return None

    async def get_organisation_member(
            self, org_id: str, user_id: str
    ) -> dict[str, Any] | None:
        """Get organisation member details"""
        try:
            org = Organisation.nodes.get(uid=org_id)
            user = User.nodes.get(uid=user_id)
            member_of_relation = user.member_of.relationship(org)
            if member_of_relation:
                return {"user_id": str(user_id), "role": member_of_relation.role}
            return None
        except (Organisation.DoesNotExist, User.DoesNotExist):
            return None

    async def list_organisation_members(self, org_id: str) -> list[dict[str, Any]]:
        """List all members of an organisation"""
        try:
            org = Organisation.nodes.get(uid=org_id)
            members = []

            # Get all users that are members of this organisation
            for user in org.members:
                member_of_relation = user.member_of.relationship(org)
                member_info = {
                    "user_id": user.uid,
                    "email": user.email,
                    "role": member_of_relation.role
                }
                members.append(member_info)

            return members
        except Organisation.DoesNotExist:
            return []
        except Exception as e:
            self.logger.error(f"Error listing organisation members: {e!s}")
            raise e

    async def request_join_organisation(self, user_id: str, org_id: str) -> None:
        """Request to join organisation"""
        try:
            user = User.nodes.get(uid=user_id)
            org = Organisation.nodes.get(uid=org_id)
            org.pending_requests.connect(user)
        except (User.DoesNotExist, Organisation.DoesNotExist):
            pass

    async def get_user_organisation(self, user_id: str) -> OrganisationEntity | None:
        """Get organisations user is member of"""
        try:
            user = User.nodes.get(uid=user_id)
            if len(user.member_of) == 0:
                return None
            org = user.member_of[0]
            org_entity = OrganisationEntity(
                id=org.uid,
                name=org.name,
                address=org.address,
                website=org.website,
                phone=org.phone,
                logo=org.logo,
                admin_position=org.admin_position,
                owner_id=org.created_by,
                updated_at=org.updated_at,
            )
            return org_entity

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def update_organisation(self, user_id: str, org_id: str,
                                  update_data: UpdateOrganisation ) -> OrganisationEntity | None:
        """Update organisation details"""
        try:
            user = User.nodes.get_or_none(uid=user_id)
            if not user:
                return None
            if len(user.member_of) == 0:
                raise HTTPException(status_code=404, detail="Org not found")
            org = user.member_of[0]

            if org.uid != org_id:
                raise HTTPException(status_code=403, detail="Not Authorized")

            org = Organisation.nodes.get_or_none(uid=org_id)
            if not org:
                raise HTTPException(status_code=404, detail="Organisation not found")

            # Update fields if provided in update_data
            if update_data.name is not None:
                org.name = update_data.name
            if update_data.address is not None:
                org.address = update_data.address
            if update_data.website is not None:
                org.website = update_data.website
            if update_data.phone is not None:
                org.phone = update_data.phone
            if update_data.logo is not None:
                # Convert Base64 to binary
                binary_data = base64.b64decode(update_data.logo)
                org.logo = binary_data
            if update_data.admin_position is not None:
                org.admin_position = update_data.admin_position

            org.save()

            # Convert to entity
            org_entity = OrganisationEntity(
                id=org.uid,
                name=org.name,
                address=org.address,
                website=org.website,
                phone=org.phone,
                logo=org.logo,
                admin_position=org.admin_position,
                owner_id=org.created_by,
                created_at=org.created_at,
                updated_at=org.updated_at,
            )

            return org_entity

        except Exception as e:
            self.logger.error(f"Error updating organisation: {e!s}")
            raise

    async def get_pending_join_requests(
            self, user_id: UUID
    ) -> list[OrganisationEntity]:
        """Get organisations user has requested to join"""
        try:
            user = User.nodes.get(uid=user_id)
            orgs = user.requested_orgs.all()
            return [
                OrganisationAggregate(
                    organisation=OrganisationEntity(
                        id=org.uid,
                        name=org.name,
                        description=org.description,
                        owner_id=org.owner_id,
                    ),
                    events=[],
                )
                for org in orgs
            ]
        except User.DoesNotExist:
            return []

    async def update_user(self, user_id: str, update_data: UpdateUser) -> UserAggregate:
        try:
            user = User.nodes.get_or_none(uid=user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            if update_data.name is not None:
                user.name = update_data.name
            if update_data.phone is not None:
                user.phone = update_data.phone
            if update_data.image_url is not None:
                # Convert Base64 to binary
                user.image_url = update_data.image_url
            if update_data.job_role is not None:
                user.job_role = update_data.job_role

            user.is_profile_created = True

            user.save()

            user_entity = UserEntity(
                id=user.uid,
                email=user.email,
                name=user.name,
                password_hash=user.password_hash,
                auth_provider=user.auth_provider,
                image_url=user.image_url,
                is_email_verified=user.is_email_verified,
                is_profile_created=user.is_profile_created,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )

            # Add org details if user belongs to one
            if len(user.member_of) > 0:
                org = user.member_of[0]
                member_of_relation = user.member_of.relationship(org)
                user_org = UserOrgDetail(
                    organisation_id=org.uid,
                    role=member_of_relation.role,
                    owner_id=org.created_by,
                )
                user_entity.joined_org = True
                user_entity.org = user_org

            return UserAggregate(user=user_entity, events=["UserUpdated"])

        except Exception as e:
            self.logger.error(f"Error updating user: {e!s}")
            raise e

    async def get_domain_org(self, domain: str) -> Organisation:
        try:
            org = Organisation.nodes.get_or_none(domain=domain)
            if not org:
                raise HTTPException(status_code=404, detail="Domain not found")
            org_entity = OrganisationEntity(
                id=org.uid,
                name=org.name,
                address=org.address,
                website=org.website,
                phone=org.phone,
                logo=org.logo,
                admin_position=org.admin_position,
                owner_id=org.created_by,
                created_at=org.created_at,
                updated_at=org.updated_at,
            )

            return org_entity
        except Exception as e:
            self.logger.error(f"Error getting user domain org: {e!s}")
            raise e

    async def join_organisation_with_domain(
            self, user_id: str, org_id: str
    ) -> OrganisationEntity:
        try:
            user = User.nodes.get(uid=user_id)
            org = Organisation.nodes.get(uid=org_id)
            user.member_of.connect(org, {"role": "MEMBER"})
            user.save()

            org_entity = OrganisationEntity(
                id=org.uid,
                name=org.name,
                address=org.address,
                phone=org.phone,
                website=org.website,
                logo=org.logo,
                domain=org.domain,
                admin_position=org.admin_position,
            )

            return org_entity

        except Exception as e:
            self.logger.error(f"Error joining organisation with domain: {e!s}")
            raise e

    async def create_guide_tour(self, user_id: str, guide_tour: GuideTourEntity) -> GuideTourEntity:
        try:
            guide_tour = GuideTour(
                user_id=user_id,
                analytics_tour=guide_tour.analytics_tour,
                knowledge_pal_tour=guide_tour.knowledge_pal_tour,
                integrations_tour=guide_tour.integrations_tour,
                home=guide_tour.home,
                dashboard=guide_tour.dashboard,
                search=guide_tour.search,
                sourcing=guide_tour.sourcing,
                rfp=guide_tour.rfp,
                rfp_template=guide_tour.rfp_template
            ).save()
            return map_guide_tour_to_entity(guide_tour)
        except Exception as e:
            self.logger.error(f"Error creating guide tour: {e!s}")
            raise e

    async def get_guide_tour(self, user_id: str) -> GuideTourEntity:
        try:
            guide_tour = GuideTour.nodes.get_or_none(user_id=user_id)
            if not guide_tour:
                return None
            return map_guide_tour_to_entity(guide_tour)
        except Exception as e:
            self.logger.error(f"Error getting guide tour: {e!s}")
            raise e

    async def update_guide_tour(self, user_id: str, guide_tour_update: UpdateUserGuideTour) -> GuideTourEntity:
        try:
            guide_tour = GuideTour.nodes.get_or_none(user_id=user_id)
            if not guide_tour:
                raise HTTPException(status_code=404, detail="Guide tour not found")
            if guide_tour_update.analytics_tour is not None:
                guide_tour.analytics_tour = guide_tour_update.analytics_tour
            if guide_tour_update.knowledge_pal_tour is not None:
                guide_tour.knowledge_pal_tour = guide_tour_update.knowledge_pal_tour
            if guide_tour_update.integrations_tour is not None:
                guide_tour.integrations_tour = guide_tour_update.integrations_tour
            if guide_tour_update.home is not None:
                guide_tour.home = guide_tour_update.home
            if guide_tour_update.dashboard is not None:
                guide_tour.dashboard = guide_tour_update.dashboard
            if guide_tour_update.search is not None:
                guide_tour.search = guide_tour_update.search
            if guide_tour_update.sourcing is not None:
                guide_tour.sourcing = guide_tour_update.sourcing
            if guide_tour_update.rfp is not None:
                guide_tour.rfp = guide_tour_update.rfp
            if guide_tour_update.rfp_template is not None:
                guide_tour.rfp_template = guide_tour_update.rfp_template
            guide_tour.save()
            return map_guide_tour_to_entity(guide_tour)
        except Exception as e:
            self.logger.error(f"Error updating guide tour: {e!s}")
            raise e

    async def get_user_settings(self, user_id: str) -> UserSettingsEntity | None:
        try:
            user_settings = UserSettings.nodes.get_or_none(user_id=user_id)
            if not user_settings:
                return None
            return map_user_settings_to_entity(user_settings)
        except Exception as e:
            self.logger.error(f"Error getting user settings: {e!s}")
            raise e

    async def update_user_settings(
            self, user_id: str, update_data: UserSettings
    ) -> UserSettingsEntity:
        try:
            user_settings = UserSettings.nodes.get_or_none(user_id=user_id)
            if not user_settings:
                raise HTTPException(status_code=404, detail="User settings not found")
            if update_data.theme is not None:
                user_settings.theme = update_data.theme
            if update_data.language is not None:
                user_settings.language = update_data.language
            if update_data.timezone is not None:
                user_settings.timezone = update_data.timezone
            if update_data.date_format is not None:
                user_settings.date_format = update_data.date_format
            if update_data.pinned_sidebar is not None:
                user_settings.pinned_sidebar = update_data.pinned_sidebar
            user_settings.save()
            return map_user_settings_to_entity(user_settings)
        except Exception as e:
            self.logger.error(f"Error updating user settings: {e!s}")
            raise e

    async def create_user_settings(
            self, user_id: str, user_settings: UserSettingsEntity
    ) -> UserSettingsEntity:
        try:
            user_settings = UserSettings(
                uid=user_settings.id,
                user_id=user_id,
                theme=user_settings.theme,
                language=user_settings.language,
                timezone=user_settings.timezone,
                date_format=user_settings.date_format,
                pinned_sidebar=user_settings.pinned_sidebar,
            ).save()
            return map_user_settings_to_entity(user_settings)
        except Exception as e:
            self.logger.error(f"Error creating user settings: {e!s}")
            raise e




def map_user_settings_to_entity(user_settings: UserSettings) -> UserSettingsEntity:
    return UserSettingsEntity(
        id=user_settings.uid,
        user_id=user_settings.user_id,
        theme=user_settings.theme,
        language=user_settings.language,
        timezone=user_settings.timezone,
        date_format=user_settings.date_format,
        pinned_sidebar=user_settings.pinned_sidebar,
    )


def map_guide_tour_to_entity(guide_tour: GuideTour) -> GuideTourEntity:
    return GuideTourEntity(
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
