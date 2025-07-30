from dependency_injector import containers, providers
from omegaconf import DictConfig, OmegaConf


from app.analytics.service.chart_queue_service import ChartQueueService
from app.auth.api.handlers import AuthHandler
from app.auth.service.auth_service import AuthService
from app.chat.adapter.llm_client import LLMAdapter
from app.chat.api.handlers import ChatHandler
from app.chat.repository.chat_repository import ChatRepository
from app.chat.service.chat_service import ChatService
from app.chat.service.completion_service import ChatCompletionService

from app.integrations.adapter.integration_client import IntegrationClient
from app.integrations.api.handlers import IntegrationHandler
from app.integrations.repository.integration_repository import IntegrationRepository
from app.integrations.service.integration_service import IntegrationService

from app.knowledge_base.adapter.integration_adapter import IntegrationAdapter
from app.knowledge_base.repository.sql_repository import KnowledgeBaseRepository
from app.knowledge_base.repository.neo4j_repository import Neo4jRepository
from app.knowledge_base.service.ingestion_service import KnowledgeIngestionService

from app.pal.analytics.analytics_workflow import AnalyticsPAL
from app.user.api.handlers import UserHandler
from app.user.repository.user_repository import UserRepository
from app.user.service.user_service import UserService
from pkg.auth_token_client.client import TokenClient
from conf.config import AppConfig
from pkg.db_util.neo4j_conn import Neo4jConnection
from pkg.db_util.postgres_conn import PostgresConnection
from pkg.db_util.types import DatabaseConfig, PostgresConfig
from pkg.kms.kms_client import KMSClient
from pkg.llm_provider.llm_client import LLMClient, LLMModel
from pkg.log.logger import Logger
from pkg.pub_sub.publisher import Publisher
from pkg.smtp_client.client import EmailClient, EmailConfig
from pkg.sqs.client import SQSClient
from pkg.redis.client import RedisClient

from app.analytics.repository.analytics_repository import AnalyticsRepository
from app.analytics.repository.storage.s3_client import SchemaS3Client
from app.analytics.service.postgres_service import PostgresService
from app.analytics.service.analytics_service import AnalyticsService
from app.pal.analytics.adapters.analytics_repository_adapter import AnalyticsRepositoryAdapter
from app.analytics.service.chart_service import ChartService
from app.analytics.service.code_executor_service import CodeExecutorService
from app.analytics.service.chart_generation_service import ChartGenerationService
from app.analytics.repository.chart_repository import ChartRepository
from app.analytics.api.handlers import DashboardHandler, DashboardCollaborationHandler, AnalyticsHandler
from app.pal.analytics.executors.sql_executor import SQLExecutor
from app.pal.analytics.executors.csv_executor import CSVExecutor
from app.pal.analytics.executors.python_executor import PythonExecutor
from app.analytics.service.dashboard_service import DashboardService
from app.analytics.service.dashboard_collaboration_service import DashboardCollaborationService
from app.tokens.service.service import TokensService
from app.tokens.repository.repository import TokensRepository
from app.tokens.api.handler import TokensHandler

from pkg.db_util.sql_alchemy.initializer import DatabaseInitializer
from app.analytics.repository.dashboard_repository import DashboardRepository

from app.code_execution.client.http_client import CodeExecutionClient


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    # Core dependencies
    logger = providers.Singleton(Logger)

    kms_client = providers.Singleton(
        KMSClient,
        kms_key_id=config.aws.kms_key_id,
        aws_access_key_id=config.aws.aws_access_key_id,
        aws_secret_access_key=config.aws.aws_secret_access_key,
        logger=logger,
    )

    db_config = providers.Singleton(
        DatabaseConfig,
        uri=config.neo4j.uri,
        username=config.neo4j.user,
        password=config.neo4j.password,
        max_pool_size=config.neo4j.max_pool_size,
        max_retries=config.neo4j.max_retries,
        retry_delay=config.neo4j.retry_delay,
    )

    db_conn = providers.Singleton(Neo4jConnection, db_config=db_config, logger=logger)

    postgres_config = providers.Singleton(PostgresConfig,
                                          host=config.postgres.host,
                                          port=config.postgres.port,
                                          username=config.postgres.user,
                                          password=config.postgres.password,
                                          database=config.postgres.database)
    postgres_conn = providers.Singleton(PostgresConnection, db_config=postgres_config, logger=logger)
    db_initializer = providers.Singleton(
        DatabaseInitializer,
        postgres_conn=postgres_conn,
        logger=logger
    )
    email_config = providers.Singleton(
        EmailConfig,
        smtp_server=config.smtp.smtp_server,
        smtp_port=config.smtp.smtp_port,
        username=config.smtp.username,
        password=config.smtp.password,
    )

    smtp_client = providers.Singleton(EmailClient, email_config)

    token_client = providers.Singleton(
        TokenClient,
        secret_key=config.jwt_auth.super_secret_key,
        refresh_secret_key=config.jwt_auth.refresh_secret_key,
    )
    tokens_repository = providers.Singleton(
        TokensRepository,
        sql_db_conn=postgres_conn,
        logger=logger,
    )



    tokens_service = providers.Singleton(
        TokensService,
        tokens_repository=tokens_repository,
        logger=logger,
    )

    tokens_handler = providers.Singleton(
        TokensHandler,
        tokens_service=tokens_service,
        logger=logger,
    )


    llm_client = providers.Singleton(
        LLMClient,
        openai_api_key=config.openai.openai_api_key,
        groq_api_key=config.openai.groq_api_key,
        google_api_key=config.openai.gemini_api_key,
        logger=logger,
        tokens_service=tokens_service,
    )

    code_execution_client = providers.Singleton(
        CodeExecutionClient,
        base_url=config.service_url.code_execution_url,
        token_client=token_client
    )

    s3_client = providers.Singleton(
        SchemaS3Client,
        aws_access_key_id=config.aws.access_key_id,
        aws_secret_access_key=config.aws.secret_access_key,
        region_name=config.aws.region,
        bucket_name=config.aws.s3_bucket_name,
        logger=logger,
        kms_key_id=config.aws.kms_key_id
    )

    redis_client = providers.Singleton(
        RedisClient,
        host=config.redis.host,
        port=config.redis.port,
        password=config.redis.password,
        logger=logger
    )
    
    # Define LLM adapter first
    llm_adapter = providers.Singleton(LLMAdapter, llm_client=llm_client, logger=logger)
    


    # Define sourcing_service after llm_adapter is available

    # User
    user_repository = providers.Singleton(
        UserRepository,
        db_conn=db_conn,
        logger=logger,
    )


    user_service = providers.Singleton(
        UserService,
        user_repository=user_repository,
        logger=logger,
        token_client=token_client,
    )

    user_handler = providers.Singleton(
        UserHandler, user_service=user_service, logger=logger
    )

  

    # Auth
    auth_service = providers.Singleton(
        AuthService,
        user_service=user_service,
        smtp_client=smtp_client,
        token_client=token_client,
        redis_client=redis_client,
        logger=logger,
    )

    auth_handler = providers.Singleton(
        AuthHandler, auth_service=auth_service, logger=logger
    )
    sqs_client_doc_sync = providers.Singleton(
        SQSClient,
        aws_access_key=config.aws.aws_access_key_id,
        aws_secret_key=config.aws.aws_secret_access_key,
        region=config.aws.aws_region,
        queue_name=config.queue.sync_documents,
        logger=logger,
    )
    sync_document_publisher = providers.Singleton(
        Publisher, sqs_client=sqs_client_doc_sync, logger=logger
    )
    # Integrations
    integration_repository = providers.Singleton(
        IntegrationRepository,
        sql_db_conn=postgres_conn,
        publisher=sync_document_publisher,
        logger=logger,
    )


    integration_client = providers.Singleton(
        IntegrationClient, logger=logger
    )

    integration_service = providers.Singleton(
        IntegrationService,
        integrations_client=integration_client,
        integration_repository=integration_repository,
        logger=logger,
    )
    integration_handler = providers.Singleton(
        IntegrationHandler, integration_service=integration_service, logger=logger
    )

    # Knowledge Base dependencies
    knowledge_base_repository = providers.Singleton(
        KnowledgeBaseRepository, sql_db_conn=postgres_conn, logger=logger
    )
    
    # Neo4j repository for graph operations
    neo4j_repository = providers.Singleton(
        Neo4jRepository, neo4j_conn=db_conn, logger=logger
    )
    
    integration_adapter = providers.Singleton(
        IntegrationAdapter, integration_service, logger
    )


    # Analytics dependencies
    analytics_repository = providers.Singleton(
        AnalyticsRepository,
        db=db_conn,
        logger=logger,
        s3_client=s3_client
    )

    # PostgreSQL service - used by both Analytics and Knowledge Base services
    postgres_service = providers.Singleton(
        PostgresService,
        analytics_repository=analytics_repository,
        logger=logger
    )

    knowledge_ingestion_service = providers.Singleton(
        KnowledgeIngestionService,
        logger=logger,
        repository=knowledge_base_repository,
        integration_adapter=integration_adapter,  # Using existing integration adapter

        postgres_service=postgres_service,  # Add the missing postgres_service parameter
    )

    chat_repository = providers.Singleton(
        ChatRepository, db_conn=postgres_conn, logger=logger,
    )

    # Add AnalyticsRepositoryAdapter
    analytics_repository_adapter = providers.Singleton(
        AnalyticsRepositoryAdapter,
        repository=analytics_repository,
        logger=logger,
        redis_client=redis_client,
        schema_cache_ttl=3600
    )

    analytics_service = providers.Singleton(
        AnalyticsService,
        analytics_repository=analytics_repository,
        postgres_service=postgres_service,
        logger=logger,
        s3_client=s3_client,
        llm_client=llm_client,
        redis_client=redis_client,
    )


    analytics_pal = providers.Singleton(
        AnalyticsPAL,
        llm_client=llm_client,
        chat_repository=chat_repository,
        s3_client=s3_client,
        redis_client=redis_client,
        tokens_service=tokens_service,
        logger=logger,
        analytics_repository=analytics_repository_adapter,
        analytics_service=analytics_service,
        model=LLMModel.GPT_4_1_MINI,  # Direct value for now to ensure it works
        dev_mode=True,
        dev_log_dir="./logs/analytics",
        code_execution_client=code_execution_client
    )


    chat_service = providers.Singleton(ChatService, chat_repository=chat_repository, logger=logger,
                                       redis_client=redis_client, llm_adapter=llm_adapter)
    chat_completion_service = providers.Singleton(ChatCompletionService, chat_service=chat_service,
                                              logger=logger,
                                                  analytics_pal=analytics_pal)

    chat_handler = providers.Singleton(
        ChatHandler,
        chat_service=chat_service,
        logger=logger,
        completion_service=chat_completion_service,
    )

    # Chart-related dependencies
    chart_repository = providers.Singleton(
        ChartRepository,
        db_conn=db_conn,
        logger=logger
    )
    sql_executor = providers.Factory(
        SQLExecutor,
        analytics_repository=analytics_repository_adapter,  # Use adapter instead of direct repository
        logger=logger
    )
    csv_executor = providers.Factory(
        CSVExecutor,
        s3_client=s3_client,
        analytics_repository=analytics_repository,
        logger=logger
    )

    python_executor = providers.Factory(
        PythonExecutor,
        timeout=30,
        logger=logger
    )

    code_executor_service = providers.Singleton(
        CodeExecutorService,
        sql_executor=sql_executor, analytics_repository=analytics_repository, python_executor=python_executor,
        code_executor=code_execution_client,
        logger=logger
    )

    chart_generation_service = providers.Singleton(
        ChartGenerationService,
        logger=logger,
        config=config,
        llm_client=llm_client,
        chart_generation_model=LLMModel.GPT_4_1_MINI,
        chart_adjustment_model=LLMModel.GPT_4_1_MINI,
        tokens_service=tokens_service
    )

    chart_service = providers.Singleton(
        ChartService,
        chart_repository=chart_repository,
        code_executor_service=code_executor_service,
        chart_generation_service=chart_generation_service,
        chat_service=chat_service,
        logger=logger
    )

    # Chart queue service
    chart_queue_service = providers.Singleton(
        ChartQueueService,
        redis_client=redis_client,
        logger=logger
    )

    # Analytics handler
    analytics_handler = providers.Singleton(
        AnalyticsHandler,
        analytics_service=analytics_service,
        logger=logger,
        chart_queue_service=chart_queue_service,
        chart_service=chart_service
    )


    dashboard_repository = providers.Singleton(
        DashboardRepository,
        logger=logger
    )

    dashboard_service = providers.Singleton(
        DashboardService,
        logger=logger,
        dashboard_repository=dashboard_repository,
        chat_service=chat_service,
        analytics_repository=analytics_repository_adapter,
        chart_repository=chart_repository
    )
    dashboard_collaboration_service = providers.Singleton(
        DashboardCollaborationService,
        logger=logger,
        dashboard_service=dashboard_service
    )
    dashboard_handler = providers.Singleton(
        DashboardHandler,
        dashboard_service=dashboard_service,
        logger=logger,
        chart_service=chart_service
    )
    dashboard_collaboration_handler = providers.Singleton(
        DashboardCollaborationHandler,
        collaboration_service=dashboard_collaboration_service,
        logger=logger
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
    container_obj.config.from_dict(config_dict)  # type: ignore

    return container_obj


if __name__ == "__main__":
    container = create_container(cfg=OmegaConf.load("../../conf/config.yaml"))  # type: ignore
