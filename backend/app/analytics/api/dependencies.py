from typing import Annotated

from fastapi import Depends, Request

from app.analytics.api.handlers import AnalyticsHandler, DashboardCollaborationHandler, DashboardHandler
from app.analytics.service.chart_service import ChartService
from app.analytics.service.chart_queue_service import ChartQueueService


def get_analytics_handler(request: Request) -> AnalyticsHandler:
    return request.app.state.container.analytics_handler()


# Type aliases for cleaner dependency injection
AnalyticsHandlerDep = Annotated[AnalyticsHandler, Depends(get_analytics_handler)]


def get_dashboard_collaboration_handler(request: Request) -> DashboardCollaborationHandler:
    return request.app.state.container.dashboard_collaboration_handler()


# Type aliases for cleaner dependency injection
DashboardCollaborationHandlerDep = Annotated[
    DashboardCollaborationHandler, Depends(get_dashboard_collaboration_handler)]


def get_dashboard_handler(request: Request) -> DashboardHandler:
    return request.app.state.container.dashboard_handler()


# Type aliases for cleaner dependency injection
DashboardHandlerDep = Annotated[DashboardHandler, Depends(get_dashboard_handler)]


def get_chart_service(request: Request) -> ChartService:
    return request.app.state.container.chart_service()


# Type aliases for cleaner dependency injection
ChartServiceDep = Annotated[ChartService, Depends(get_chart_service)]


def get_chart_queue_service(request: Request) -> ChartQueueService:
    return request.app.state.container.chart_queue_service()


# Type aliases for cleaner dependency injection
ChartQueueServiceDep = Annotated[ChartQueueService, Depends(get_chart_queue_service)]
