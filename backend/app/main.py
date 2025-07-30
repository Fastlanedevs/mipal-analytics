import asyncio
import signal
import sys
import uuid
from contextlib import AsyncExitStack
from typing import Dict, List, Any, Optional

from omegaconf import OmegaConf

from app.tokens.service.service import TokensService
from app.tokens.repository.repository import TokensRepository
from app.analytics.repository.analytics_repository import AnalyticsRepository
from app.integrations.adapter.integration_client import IntegrationClient
from app.integrations.repository.integration_repository import IntegrationRepository
from app.integrations.service.integration_service import IntegrationService
from app.knowledge_base.adapter.integration_adapter import IntegrationAdapter
from app.knowledge_base.event_handler.handler import KnowledgeBaseEventHandler
from app.knowledge_base.event_handler.subscriber_worker import KnowledgeBaseWorker
from app.knowledge_base.repository.sql_repository import KnowledgeBaseRepository
from app.knowledge_base.service.ingestion_service import KnowledgeIngestionService
from conf.config import AppConfig
from pkg.db_util.neo4j_conn import Neo4jConnection
from pkg.db_util.types import DatabaseConfig, PostgresConfig
from pkg.db_util.postgres_conn import PostgresConnection
from pkg.db_util.sql_alchemy.initializer import DatabaseInitializer
from pkg.llm_provider.llm_client import LLMClient
from pkg.log.logger import Logger
from pkg.pub_sub.publisher import Publisher
from pkg.pub_sub.subscriber import Subscriber
from pkg.sqs.client import SQSClient
from app.analytics.service.postgres_service import PostgresService
from app.knowledge_base.repository.neo4j_repository import Neo4jRepository

class WorkerServer:
    """Worker server with graceful shutdown handling"""

    def __init__(self, config_path: str = "conf/config.yaml"):
        self.config_path = config_path
        self.logger = Logger()
        self.shutdown_event = asyncio.Event()
        self.exit_stack = AsyncExitStack()
        self.worker: Optional[KnowledgeBaseWorker] = None
        self.connections = []  # Track connections for cleanup
        self.knowledge_ingestion_service = None

    async def initialize(self) -> None:
        """Initialize all server components"""
        self.logger.info("Initializing worker server...")

        # Load configuration
        cfg = OmegaConf.load(self.config_path)
        schema = OmegaConf.structured(AppConfig)
        config = OmegaConf.merge(schema, cfg)



        # Initialize Neo4j connection
        db_config = DatabaseConfig(
            uri=config.neo4j.uri,
            username=config.neo4j.user,
            password=config.neo4j.password,
            max_pool_size=config.neo4j.max_pool_size,
            max_retries=config.neo4j.max_retries,
            retry_delay=config.neo4j.retry_delay,
        )
        db_conn = Neo4jConnection(db_config=db_config, logger=self.logger)
        self.connections.append(db_conn)

        # Initialize Postgres connection
        postgres_config = PostgresConfig(
            host=config.postgres.host,
            port=config.postgres.port,
            username=config.postgres.user,
            password=config.postgres.password,
            database=config.postgres.database,
        )

        sql_db_conn = PostgresConnection(
            db_config=postgres_config,
            logger=self.logger,
        )
        self.connections.append(sql_db_conn)

        # Initialize database tables
        db_initializer = DatabaseInitializer(
            postgres_conn=sql_db_conn,
            logger=self.logger,
        )
        await db_initializer.initialize_tables(check_first=True)

        # Initialize SQS client with typed config - using our new implementation
        sqs_client_sync_documents = SQSClient(
            aws_access_key=config.aws.aws_access_key_id,
            aws_secret_key=config.aws.aws_secret_access_key,
            region=config.aws.aws_region,
            queue_name=config.queue.sync_documents,
            logger=self.logger,
        )

        # Register SQS client with exit stack for cleanup
        await self.exit_stack.enter_async_context(sqs_client_sync_documents)

        # Initialize publisher - using our enhanced implementation
        publisher = Publisher(
            sqs_client=sqs_client_sync_documents,
            logger=self.logger,
            batch_size=10,  # Adjust batch size as needed
            enable_retries=True
        )

        # Initialize subscriber - using our enhanced implementation
        sync_documents_subscriber = Subscriber(
            sqs_client=sqs_client_sync_documents,
            logger=self.logger,
            max_concurrent_tasks=50,  # Adjust as needed
            visibility_timeout=300,
            max_retries=3
        )

        # Initialize service components
        tokens_repository = TokensRepository(sql_db_conn, self.logger)
        tokens_service = TokensService(tokens_repository, self.logger,)
        integration_client = IntegrationClient( self.logger)
        integration_repo = IntegrationRepository(sql_db_conn, publisher, self.logger)
        integration_service = IntegrationService(
            integration_client, integration_repo, self.logger
        )
        knowledge_repository = KnowledgeBaseRepository( sql_db_conn, self.logger)
        neo4j_repository = Neo4jRepository(db_conn, self.logger)
        llm_client = LLMClient(
            config.openai.openai_api_key, config.openai.groq_api_key,
            config.openai.gemini_api_key, self.logger, tokens_service
        )
        integration_adapter = IntegrationAdapter(
            integration_service, self.logger
        )
        analytics_repository = AnalyticsRepository(db_conn, self.logger)
        postgres_service = PostgresService(analytics_repository, self.logger)

        # Initialize knowledge ingestion service
        knowledge_ingestion_service = KnowledgeIngestionService(
            self.logger,
            knowledge_repository,
            integration_adapter,
            postgres_service,
        )
        self.knowledge_ingestion_service = knowledge_ingestion_service

        # Initialize event handler and worker
        knowledge_base_handler = KnowledgeBaseEventHandler(
            knowledge_ingestion_service, self.logger,
            enable_detailed_logging=True
        )


        self.worker = KnowledgeBaseWorker(
            knowledge_base_handler, sync_documents_subscriber, self.logger,
            shutdown_timeout=30  # Timeout for graceful shutdown
        )

        self.logger.info("Worker server initialization complete")

    async def run(self) -> None:
        user_id = "3a0f8588dd814d25a44220e7824447da"
        sync_id = uuid.UUID("43f3d04e-bc3e-497e-8a00-52422af34936")
        await self.knowledge_ingestion_service.sync_integration(user_id,sync_id)


async def main() -> None:
    """Main entry point with graceful shutdown handling"""
    # Create and run the worker server
    server = WorkerServer()
    await server.initialize()

    try:
        await server.run()
    except Exception as e:
        print(f"Fatal error: {e!s}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    # Use asyncio.run for proper event loop management
    asyncio.run(main())