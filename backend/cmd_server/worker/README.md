# Main Worker with Chart Generation Support

This worker now includes both knowledge base document processing and chart generation capabilities in a single process.

## Features

### Knowledge Base Processing

- Processes document sync tasks from SQS queue
- Handles GSuite integration and document ingestion
- Uses Neo4j for graph-based knowledge storage
- Supports real-time document processing

### Chart Generation Processing

- Processes chart generation tasks from Redis queue
- Handles async chart creation with progress tracking
- Supports chart adjustments and modifications
- Uses LLM agents for intelligent chart generation

## Architecture

The worker runs two main processing loops:

1. **Knowledge Base Worker**: Handles SQS-based document sync tasks
2. **Chart Processing Loop**: Handles Redis-based chart generation tasks

Both loops run concurrently and share the same resource management and graceful shutdown handling.

## Dependencies

### Core Dependencies

- Redis client for chart queue management
- SQS client for document sync
- Neo4j connection for graph operations
- PostgreSQL connection for relational data
- LLM client for chart generation

### Chart-Specific Dependencies

- ChartQueueService: Manages chart task queue
- ChartService: Handles chart creation and management
- ChartGenerationService: LLM-based chart schema generation
- CodeExecutorService: Executes SQL/Python code for data processing

## Configuration

The worker uses the same configuration as the main application:

```yaml
redis:
  host: localhost
  port: 6379
  password: ""

aws:
  aws_access_key_id: ""
  aws_secret_access_key: ""
  aws_region: ""

queue:
  sync_documents: "document-sync-queue"

openai:
  openai_api_key: ""
  groq_api_key: ""
  gemini_api_key: ""
```

## Running the Worker

```bash
cd cmd_server/worker
python main.py
```

## Graceful Shutdown

The worker handles graceful shutdown for both processing loops:

1. Stops chart processing task
2. Stops knowledge base worker
3. Closes all database connections
4. Cleans up resources using AsyncExitStack

## Monitoring

The worker provides comprehensive logging for both processing loops:

- Task processing status
- Error handling and recovery
- Resource usage metrics
- Health check information

## Migration from Separate Chart Worker

The chart worker functionality has been integrated into the main worker to:

- Reduce resource overhead
- Simplify deployment
- Improve resource sharing
- Provide unified monitoring and logging

The chart worker (`cmd_server/chart_worker/`) has been removed as its functionality is now part of the main worker.
