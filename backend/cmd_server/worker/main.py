import asyncio
import signal
import sys
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

# Add chart-related imports
from app.analytics.service.chart_queue_service import ChartQueueService
from app.analytics.service.chart_service import ChartService
from app.analytics.repository.chart_repository import ChartRepository
from app.analytics.service.code_executor_service import CodeExecutorService
from app.analytics.service.chart_generation_service import ChartGenerationService
from app.chat.service.chat_service import ChatService
from app.pal.analytics.executors.sql_executor import SQLExecutor
from app.pal.analytics.executors.csv_executor import CSVExecutor
from app.pal.analytics.executors.python_executor import PythonExecutor
from app.code_execution.client.http_client import CodeExecutionClient
from pkg.auth_token_client.client import TokenClient
from app.analytics.repository.storage.s3_client import SchemaS3Client
from pkg.kms.kms_client import KMSClient
from app.analytics.entity.chart import ChartStatus
from pkg.llm_provider.llm_client import LLMModel

class WorkerServer:
    """Worker server with graceful shutdown handling and chart generation support"""

    def __init__(self, config_path: str = "conf/config.yaml"):
        self.config_path = config_path
        self.logger = Logger()
        self.shutdown_event = asyncio.Event()
        self.exit_stack = AsyncExitStack()
        self.worker: KnowledgeBaseWorker = None  # type: ignore
        self.connections = []  # Track connections for cleanup
        
        # Chart processing state
        self.chart_processing_task: Optional[asyncio.Task] = None
        self.chart_queue_service: ChartQueueService = None  # type: ignore
        self.chart_service: ChartService = None  # type: ignore

    async def initialize(self) -> None:
        """Initialize all server components"""
        self.logger.info("Initializing worker server...")
        # Load configuration
        cfg = OmegaConf.load(self.config_path)
        schema = OmegaConf.structured(AppConfig)
        config = OmegaConf.merge(schema, cfg)

        # Register signal handlers
        self._setup_signal_handlers()

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
        tokens_service = TokensService(tokens_repository, self.logger)
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

        # Initialize event handler and worker
        knowledge_base_handler = KnowledgeBaseEventHandler(
            knowledge_ingestion_service, self.logger,
            enable_detailed_logging=True
        )

        self.worker = KnowledgeBaseWorker(
            knowledge_base_handler, sync_documents_subscriber, self.logger,
            shutdown_timeout=30  # Timeout for graceful shutdown
        )
        llm_adapter = LLMAdapter(self.logger, llm_client)

        # Initialize chart-related services
        await self._initialize_chart_services(config, db_conn, sql_db_conn, llm_client, tokens_service, llm_adapter)

        self.logger.info("Worker server initialization complete")

    async def _initialize_chart_services(self, config, db_conn, sql_db_conn, llm_client, tokens_service, llm_adapter):
        """Initialize chart-related services using dependency injection container"""
        try:
            # Create container and get dependencies (same as chart worker)
            from cmd_server.server.container import create_container
            self.container = create_container(config)
            self.container.wire(modules=[__name__])
            
            # Get services from container
            self.chart_queue_service = ChartQueueService(self.container.redis_client(), self.logger)
            self.chart_service = self.container.chart_service()

            self.logger.info("Chart services initialized successfully")

        except Exception as e:
            self.logger.error(f"Error initializing chart services: {str(e)}")
            raise

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown"""
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(
                    self._handle_signal(s),
                    name=f"signal_handler_{s.name}"
                )
            )
            self.logger.info(f"Registered signal handler for {sig.name}")

    async def _handle_signal(self, sig: signal.Signals) -> None:
        """Handle termination signals for graceful shutdown"""
        self.logger.info(f"Received {sig.name}, initiating graceful shutdown...")
        self.shutdown_event.set()

    async def process_chart_task(self, task_data: Dict[str, Any]):
        """Process a single chart generation task"""
        task_id = task_data["task_id"]
        user_id = task_data["user_id"]
        
        try:
            self.logger.info(f"Processing chart task {task_id}")
            
            # Update status to processing
            await self.chart_queue_service.update_task_progress(
                task_id, 20, "data_extraction"
            )
            
            # Extract data from message
            await self.chart_queue_service.update_task_progress(
                task_id, 40, "llm_generation"
            )
            
            # Generate chart using existing service
            chart = await self.chart_service.create_chart(
                message_id=task_data["message_id"],
                user_id=user_id,
                org_id=task_data.get("org_id") or "",
                visibility=task_data["visibility"],
                force_create=task_data["force_create"],
                adjustment_query=task_data.get("adjustment_query")
            )

            self.logger.info(f"Chart created: {chart}")
            
            # Update status to completed
            await self.chart_queue_service.complete_task(
                task_id=task_id,
                chart_id=chart.uid
            )
            
            self.logger.info(f"Chart task {task_id} completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error processing chart task {task_id}: {str(e)}")
            
            # Update status to failed
            await self.chart_queue_service.complete_task(
                task_id=task_id,
                error_message=str(e)
            )

    async def _chart_processing_loop(self):
        """Main chart processing loop"""
        self.logger.info("Chart processing loop started")
        
        # Add periodic logging to show the loop is running
        last_log_time = 0
        log_interval = 30  # Log every 30 seconds
        
        while not self.shutdown_event.is_set():
            try:
                current_time = asyncio.get_event_loop().time()
                
                # Periodic logging to show the loop is alive
                if current_time - last_log_time >= log_interval:
                    self.logger.info("Chart processing loop is running - checking for tasks...")
                    last_log_time = current_time
                
                # Get next task from queue
                task_data = await self.chart_queue_service.dequeue_chart_task()
                
                if task_data:
                    self.logger.info(f"Found chart task: {task_data.get('task_id', 'unknown')}")
                    # Process task asynchronously
                    asyncio.create_task(self.process_chart_task(task_data))
                else:
                    # No tasks, wait briefly
                    await asyncio.sleep(1)
                    
            except Exception as e:
                self.logger.error(f"Error in chart processing loop: {str(e)}")
                await asyncio.sleep(5)
        
        self.logger.info("Chart processing loop stopped")

    async def run(self) -> None:
        """Run the worker server until shutdown"""
        try:
            # Start both workers concurrently
            self.logger.info("Starting workers...")
            
            # Create tasks for both workers
            tasks = []
            
            # Start knowledge base worker task
            if self.worker:
                self.logger.info("Starting knowledge base worker...")
                kb_task = asyncio.create_task(
                    self.worker.start(),
                    name="knowledge_base_worker"
                )
                tasks.append(kb_task)
            
            # Start chart processing task
            if self.chart_queue_service and self.chart_service:
                self.logger.info("Starting chart processing task...")
                chart_task = asyncio.create_task(
                    self._chart_processing_loop(),
                    name="chart_processing_loop"
                )
                tasks.append(chart_task)
                self.chart_processing_task = chart_task

            # Wait for shutdown signal
            self.logger.info("Worker server running, press Ctrl+C to stop")
            await self.shutdown_event.wait()

        except Exception as e:
            self.logger.error(f"Error in worker server: {e!s}")
            raise
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """Perform graceful shutdown of all components"""
        self.logger.info("Shutting down worker server...")

        # Stop the chart processing task first
        if self.chart_processing_task and not self.chart_processing_task.done():
            try:
                self.chart_processing_task.cancel()
                await self.chart_processing_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                self.logger.error(f"Error stopping chart processing task: {e!s}")

        # Stop the knowledge base worker
        if self.worker:
            try:
                await self.worker.stop()
            except Exception as e:
                self.logger.error(f"Error stopping knowledge base worker: {e!s}")

        # Close all connections using exit stack
        try:
            await self.exit_stack.aclose()
        except Exception as e:
            self.logger.error(f"Error closing resources: {e!s}")

        # Close any additional connections
        for conn in self.connections:
            try:
                if hasattr(conn, 'close') and callable(conn.close):
                    if asyncio.iscoroutinefunction(conn.close):
                        await conn.close()
                    else:
                        conn.close()
            except Exception as e:
                self.logger.error(f"Error closing connection {conn}: {e!s}")

        self.logger.info("Worker server shutdown complete")


async def main() -> None:
    """Main entry point with graceful shutdown handling"""
    # Create and run the worker server
    server = WorkerServer()

    try:
        await server.initialize()
        await server.run()
    except Exception as e:
        print(f"Fatal error: {e!s}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    # Use asyncio.run for proper event loop management
    asyncio.run(main())