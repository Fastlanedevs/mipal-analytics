from datetime import datetime
from typing import Any

from pydantic import BaseModel

from .entity import Role, User


class UserAggregate(BaseModel):
    user: User
    events: list[str] = []

    def change_role(self, new_role: Role) -> None:
        self.user = self.user.copy(
            update={"role": new_role, "updated_at": datetime.utcnow()}
        )
        self.events.append("UserRoleChanged")

    def change_organisation_id(self, new_organisation_id: Any) -> None:
        self.user = self.user.copy(
            update={
                "organisation_id": new_organisation_id,
                "updated_at": datetime.utcnow(),
            }
        )
        self.events.append("UserOrganisationChanged")
