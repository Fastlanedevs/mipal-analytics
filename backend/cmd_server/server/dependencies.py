# cmd_server/server/dependencies.py
from dependency_injector import providers

# Import necessary types directly without importing the container itself initially
from pkg.log.logger import Logger
from pkg.redis.client import RedisClient
from app.pal.deep_research.repository.interface import IDeepResearchRepository
# Import Container type hint carefully if needed, but prefer avoiding it here

# Define the getter functions here
def get_logger(container = providers.DependenciesContainer()) -> Logger:
    """Retrieves the logger instance from the container."""
    return container.logger()

def get_redis_client(container = providers.DependenciesContainer()) -> RedisClient:
    """Retrieves the RedisClient instance from the container."""
    return container.redis_client()

def get_deep_research_repo(container = providers.DependenciesContainer()) -> IDeepResearchRepository:
    """Retrieves the IDeepResearchRepository instance from the container."""
    return container.deep_research_repository()

def get_log_cleaner_factory(container = providers.DependenciesContainer()) -> providers.Factory["LogCleaningAgent"]:
    """Retrieves the LogCleaningAgent factory from the container."""
    # Avoid direct type import here to prevent potential circular deps if LogCleaningAgent imports things
    # that might indirectly pull back to the container setup.
    return container.log_cleaner_agent()

# You might add other dependency getters here as needed 