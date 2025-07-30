from typing import Optional
from fastapi import HTTPException, status

class AnalyticsError(Exception):
    """Base class for analytics errors"""
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

    def to_http_exception(self) -> HTTPException:
        """Convert to FastAPI HTTPException"""
        return HTTPException(
            status_code=self.status_code,
            detail=self.message
        )

class DatabaseNotFoundError(AnalyticsError):
    """Raised when a database is not found"""
    def __init__(self, database_name: str):
        super().__init__(
            message=f"Database '{database_name}' not found",
            status_code=status.HTTP_404_NOT_FOUND
        )

class TableNotFoundError(AnalyticsError):
    """Raised when a table is not found"""
    def __init__(self, table_name: str, database_name: Optional[str] = None):
        message = f"Table '{table_name}' not found"
        if database_name:
            message += f" in database '{database_name}'"
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND
        )

class UnauthorizedError(AnalyticsError):
    """Raised when user is not authorized"""
    def __init__(self, message: str = "Not authorized to perform this action"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN
        )

class DatabaseConnectionError(AnalyticsError):
    """Raised when database connection fails"""
    def __init__(self, message: str):
        super().__init__(
            message=f"Database connection error: {message}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )

class SchemaValidationError(AnalyticsError):
    """Raised when schema validation fails"""
    def __init__(self, message: str):
        super().__init__(
            message=f"Schema validation error: {message}",
            status_code=status.HTTP_400_BAD_REQUEST
        )

class StorageError(AnalyticsError):
    """Raised when storage operations fail"""
    def __init__(self, message: str):
        super().__init__(
            message=f"Storage error: {message}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )

class InvalidOperationError(AnalyticsError):
    """Raised when operation is invalid"""
    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST
        )

class DuplicateResourceError(AnalyticsError):
    """Raised when attempting to create a duplicate resource"""
    def __init__(self, resource_type: str, identifier: str):
        super().__init__(
            message=f"{resource_type} with identifier '{identifier}' already exists",
            status_code=status.HTTP_409_CONFLICT
        )

class ResourceStateError(AnalyticsError):
    """Raised when resource is in invalid state for operation"""
    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT
        )

# Chart-related errors
class ChartError(Exception):
    """Base class for chart-related errors"""
    pass

class ChartNotFoundError(ChartError):
    """Raised when a chart is not found"""
    pass

class ChartAccessDeniedError(ChartError):
    """Raised when a user doesn't have permission to access a chart"""
    pass

class MessageNotFoundError(ChartError):
    """Raised when a message associated with a chart is not found"""
    pass

class ChartCreationError(ChartError):
    """Raised when there's an error creating a chart"""
    pass

class ChartUpdateError(ChartError):
    """Raised when there's an error updating a chart"""
    pass

class ChartRefreshError(ChartError):
    """Raised when there's an error refreshing chart data"""
    pass

class InvalidChartDataError(ChartError):
    """Raised when chart data is invalid or cannot be processed"""
    pass

class CodeExecutionError(AnalyticsError):
    """Exception raised when there's an error executing code."""
    pass

# Dashboard-related errors
class DashboardError(Exception):
    """Base class for dashboard-related errors"""
    pass

class DashboardNotFoundError(DashboardError):
    """Raised when a dashboard is not found"""
    def __init__(self, dashboard_id: str):
        self.dashboard_id = dashboard_id
        self.message = f"Dashboard with ID '{dashboard_id}' not found"
        super().__init__(self.message)

class DashboardAccessDeniedError(DashboardError):
    """Raised when a user doesn't have permission to access a dashboard"""
    def __init__(self, message: str = "You don't have permission to access this dashboard"):
        self.message = message
        super().__init__(self.message)

class DashboardCreationError(DashboardError):
    """Raised when there's an error creating a dashboard"""
    def __init__(self, message: str = "Error creating dashboard"):
        self.message = message
        super().__init__(self.message)

class DashboardUpdateError(DashboardError):
    """Raised when there's an error updating a dashboard"""
    def __init__(self, message: str = "Error updating dashboard"):
        self.message = message
        super().__init__(self.message)

class InsufficientPermissionError(DashboardError):
    """Raised when a user has access but not the required permission level"""
    def __init__(self, message: str = "You need higher permission level for this operation"):
        self.message = message
        super().__init__(self.message)

# Dataframe-related errors
class DataframeError(Exception):
    """Base class for dataframe-related errors"""
    pass

class DataframeCreationError(DataframeError):
    """Raised when there's an error creating a dataframe"""
    def __init__(self, message: str = "Error creating dataframe"):
        self.message = message
        super().__init__(self.message)

class DataframeNotFoundError(DataframeError):
    """Raised when a dataframe is not found"""
    def __init__(self, dataframe_id: str):
        self.dataframe_id = dataframe_id
        self.message = f"Dataframe with ID '{dataframe_id}' not found"
        super().__init__(self.message)

class DataframeUpdateError(DataframeError):
    """Raised when there's an error updating a dataframe"""
    def __init__(self, message: str = "Error updating dataframe"):
        self.message = message
        super().__init__(self.message)

class InvalidFileFormatError(AnalyticsError):
    """Error raised when an invalid file format is provided"""
    def __init__(self, message: str = "Invalid file format"):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST) 