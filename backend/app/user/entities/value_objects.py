from enum import Enum


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"

    @classmethod
    def get_all_roles(cls) -> list[str]:
        """Returns a list of all possible user roles."""
        return [role.value for role in cls]


class Scope(str, Enum):
    FREE = "FREE"
    ENTERPRISE = "ENTERPRISE"



