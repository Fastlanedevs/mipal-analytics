import sys
import os
from typing import Any, Dict, Optional

from dependency_injector import containers, providers
from omegaconf import DictConfig, OmegaConf

from pkg.log.logger import Logger
from pkg.db_util.postgres_conn import PostgresConnection
from pkg.db_util.types import PostgresConfig
from pkg.redis.client import RedisClient
from pkg.kms.kms_client import KMSClient
from conf.config import AppConfig
from app.code_execution.repository.execution_repository import ExecutionRepository
from app.code_execution.service.execution_service import ExecutionService
from app.code_execution.service.queue_service import QueueService
from app.code_execution.api.handlers import CodeExecutionHandler


class Container(containers.DeclarativeContainer):
    config: DictConfig = providers.Configuration()

    logger: Logger = providers.Singleton(Logger)

    kms_client = providers.Singleton(
        KMSClient,
        kms_key_id=config.aws.kms_key_id,
        aws_access_key_id=config.aws.aws_access_key_id,
        aws_secret_access_key=config.aws.aws_secret_access_key,
        logger=logger,
    )

    postgres_config = providers.Singleton(PostgresConfig,
                                          host=config.postgres.host,
                                          port=config.postgres.port,
                                          username=config.postgres.user,
                                          password=config.postgres.password,
                                          database=config.postgres.database)
    postgres_conn = providers.Singleton(PostgresConnection, db_config=postgres_config, logger=logger)

    redis_client = providers.Singleton(
        RedisClient,
        host=config.redis.host,
        port=config.redis.port,
        password=config.redis.password,
        logger=logger,
    )

    # --- Repositories ---
    execution_repository = providers.Singleton(
        ExecutionRepository,
        sql_db_conn=postgres_conn,
        logger=logger,
    )



    # --- Services ---
    queue_service = providers.Singleton(
        QueueService,
        redis_client=redis_client,
        logger=logger,
    )


    execution_service = providers.Singleton(
        ExecutionService,
        execution_repository=execution_repository,
        queue_service=queue_service,
        redis_client=redis_client,
        logger=logger,
    )

    # --- API Handlers ---
    code_execution_handler = providers.Singleton(CodeExecutionHandler, execution_service=execution_service,
                                                 queue_service=queue_service, logger=logger,
                                                 )


def create_container(cfg: DictConfig) -> Container:
    """Create and configure the dependency injection container."""
    container_obj = Container()

    # Create structured config with defaults
    schema = OmegaConf.structured(AppConfig)

    # Merge with provided config
    config = OmegaConf.merge(schema, cfg)

    # Convert to dict and resolve interpolations
    config_dict = OmegaConf.to_container(config, resolve=True)

    # Update container config
    container_obj.config.from_dict(config_dict)

    return container_obj
