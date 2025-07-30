class DatabaseError(Exception):
    """Base exception for database operations"""

    pass


class DBConnectionError(DatabaseError):
    """Raised when connection fails"""

    pass


class SchemaError(DatabaseError):
    """Raised when schema operations fail"""

    pass
