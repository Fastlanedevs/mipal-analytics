# Integration System: PostgreSQL Integration Flow

## Overview

This document details the process flow for integrating a PostgreSQL database with the system. The integration allows users to connect their PostgreSQL databases to utilize advanced features such as data analysis, visualization, and other services provided by the application.

## Integration Flow

### 1. User Integration Creation

The user integration flow starts when a user submits their PostgreSQL credentials through the API endpoint:

```
POST /integrations
```

The request requires the following data:

```json
{
  "integration_type": "POSTGRESQL",
  "credential": {
    "host": "database-hostname.example.com",
    "port": 5432,
    "username": "database_user",
    "password": "user_password",
    "database_name": "target_database"
  }
}
```

### 2. Credential Validation

When credentials are submitted:

1. The system identifies the integration type as `POSTGRESQL`
2. The `IntegrationClient.validate_postgres_credentials()` method verifies the credentials by:
   - Checking for required fields: host, username, and database_name
   - Attempting to establish a connection to the database
   - Setting a short timeout (5 seconds) to quickly validate connectivity
   - Returning a boolean indicating success or failure

### 3. Integration Record Creation

If validation is successful:

1. The system creates a `UserIntegration` entity with:

   - A unique integration_id (UUID)
   - The user's credentials
   - Integration metadata with type `POSTGRESQL`
   - Timestamps for creation and updates

2. The `integration_repository.create_user_integration()` method persists this entity

### 4. Synchronization Process

After successful integration creation:

1. A synchronization process is initiated automatically through `create_integration_sync()`
2. This creates a `SyncIntegration` entity with:

   - A unique sync_id
   - Reference to the integration_id
   - Initial status of `STARTED`
   - Timestamps for tracking the sync process

3. The synchronization process runs asynchronously to:
   - Map the database schema (tables, columns, relationships)
   - Record database metadata
   - Make the database available for querying within the system

### 5. Asynchronous Processing Architecture

The `create_integration_sync` method uses a publish-subscribe (pub/sub) pattern implemented with AWS SQS to enable asynchronous processing:

#### 5.1 Message Publication

When `create_integration_sync` is called:

1. It first checks if there's already an ongoing sync to prevent duplicate processing
2. If no ongoing sync exists, it generates a unique `sync_id` using UUID
3. It creates a new `SyncIntegration` entity with status `STARTED`
4. This entity is persisted via `integration_repository.create_sync()`
5. Inside this method, a message is published to AWS SQS:
   ```python
   publish_data = SyncIntegrationEvent(
       user_id=sync_integration.user_id,
       sync_id=sync_integration.sync_id,
   )
   await self.publisher.publish(publish_data.__dict__)
   ```

#### 5.2 AWS SQS Queue

The system uses AWS Simple Queue Service (SQS) for reliable message delivery:

1. The `Publisher` class encapsulates interaction with the SQS queue
2. Messages are sent to a configured queue (e.g., "mipal-sync-documents-queue")
3. SQS provides:
   - Guaranteed at-least-once delivery
   - Message persistence for reliability
   - Visibility timeouts to prevent duplicate processing
   - Dead-letter queue support for problematic messages

#### 5.3 Worker Service

A separate worker service runs continuously to process integration sync tasks:

1. The `KnowledgeBaseWorker` initializes a `Subscriber` that listens to the SQS queue
2. The subscriber polls for messages using configurable parameters:
   - Batch size for retrieving multiple messages
   - Wait time for long polling
   - Visibility timeout to lock messages during processing
3. Each message is processed concurrently up to a configured limit (`max_concurrent_tasks`)
4. For long-running operations, visibility timeout extension is handled automatically

#### 5.4 Message Processing

When a sync message is received:

1. The `KnowledgeBaseEventHandler.handle_integration_document_sync()` method processes the message
2. It extracts the user_id and sync_id from the message
3. It then calls `KnowledgeIngestionService.sync_integration()` to execute the actual synchronization
4. For PostgreSQL integrations, the flow is:
   - The status is updated to `PROCESSING`
   - The database connection is established using the stored credentials
   - Database metadata is captured and stored
   - Upon successful completion, the status is updated to `COMPLETED`
   - If errors occur, the status is updated to `FAILED` with error details

#### 5.5 Fault Tolerance and Error Handling

The architecture includes several fault tolerance mechanisms:

1. If message processing fails, the message becomes visible in the queue again for retry
2. Exponential backoff is used when receiving messages encounters errors
3. Long-running operations have their visibility timeout extended periodically to prevent timeout
4. Failed messages can be sent to a dead-letter queue after exceeding maximum retries
5. All operations are logged with structured data for monitoring and debugging

### 6. Architecture Diagram

Below is a sequence diagram illustrating the flow of the integration sync process:

```
┌────────────┐          ┌───────────────┐          ┌───────────┐          ┌──────────┐          ┌──────────────┐
│    API     │          │ Integration   │          │   SQS     │          │  Worker  │          │ Knowledge    │
│  Service   │          │  Repository   │          │  Queue    │          │ Service  │          │ Ingestion    │
└─────┬──────┘          └───────┬───────┘          └─────┬─────┘          └────┬─────┘          └──────┬───────┘
      │                         │                        │                     │                       │
      │ create_integration()    │                        │                     │                       │
      │───────────────────────►│                        │                     │                       │
      │                         │                        │                     │                       │
      │                         │ create_sync()          │                     │                       │
      │                         │◄───────────────────────│                     │                       │
      │                         │                        │                     │                       │
      │                         │ publish(sync_event)    │                     │                       │
      │                         │─────────────────────────────────────────────►│                       │
      │                         │                        │                     │                       │
      │ return integration      │                        │                     │                       │
      │◄───────────────────────┤                        │                     │                       │
      │                         │                        │                     │                       │
      │                         │                        │ receive_messages()  │                       │
      │                         │                        │◄────────────────────│                       │
      │                         │                        │                     │                       │
      │                         │                        │ deliver message     │                       │
      │                         │                        │─────────────────────►                       │
      │                         │                        │                     │                       │
      │                         │                        │                     │ handle_integration_   │
      │                         │                        │                     │ document_sync()      │
      │                         │                        │                     │──────────────────────►│
      │                         │                        │                     │                       │
      │                         │                        │                     │                       │ sync_integration()
      │                         │                        │                     │                       │───────────┐
      │                         │                        │                     │                       │           │
      │                         │                        │                     │                       │           │ Process DB
      │                         │                        │                     │                       │           │ Connection
      │                         │                        │                     │                       │           │
      │                         │ update_sync_status()   │                     │                       │◄──────────┘
      │                         │◄──────────────────────────────────────────────────────────────────────
      │                         │                        │                     │                       │
      │                         │                        │                     │                       │
┌─────┴──────┐          ┌───────┴───────┐          ┌─────┴─────┐          ┌────┴─────┐          ┌──────┴───────┐
│    API     │          │ Integration   │          │   SQS     │          │  Worker  │          │ Knowledge    │
│  Service   │          │  Repository   │          │  Queue    │          │ Service  │          │ Ingestion    │
└────────────┘          └───────────────┘          └───────────┘          └──────────┘          └──────────────┘
```

## PostgreSQL Credential Requirements

The following fields are required for establishing a PostgreSQL connection:

| Field         | Description                             | Required                    |
| ------------- | --------------------------------------- | --------------------------- |
| host          | Database server hostname or IP address  | Yes                         |
| port          | Database server port (defaults to 5432) | No (default value provided) |
| username      | Database username                       | Yes                         |
| password      | Database user password                  | Yes                         |
| database_name | Target database name                    | Yes                         |

## Error Handling

The integration flow includes robust error handling:

1. If credentials are invalid, a 400 Bad Request error is returned with details
2. If the database connection fails, appropriate error messages are provided
3. Synchronization status is tracked and errors during sync are captured

## Integration Status Management

Users can check their PostgreSQL integration status through:

```
GET /integrations/POSTGRESQL
```

And monitor synchronization status via:

```
GET /integrations/POSTGRESQL/sync
```

## Security Considerations

- Database credentials are securely stored and never exposed in API responses
- Connections use standard PostgreSQL security protocols
- Credentials can be updated or disabled through the API

## Usage After Integration

After successful integration, users can:

1. Query their database through the application
2. Analyze database structure and content
3. Create visualizations and reports
4. Utilize AI-powered analysis on their database data

## System Configuration and Resource Considerations

### AWS SQS Configuration

For optimal performance and reliability of the integration system, consider the following SQS configuration guidelines:

1. **Queue Settings**:

   - Message retention period: 4-14 days (default is 4)
   - Visibility timeout: 5 minutes (configured to 300 seconds)
   - Receive message wait time: 20 seconds (for long polling)
   - Maximum message size: 256KB

2. **Worker Process Configuration**:

   - The `max_concurrent_tasks` parameter (default: 50) controls how many messages are processed simultaneously
   - For resource-intensive operations like PostgreSQL integration, consider limiting to 10-20 concurrent tasks
   - The `batch_size` parameter (default: 10) determines how many messages are retrieved in a single API call
   - Visibility timeout extensions occur every 60 seconds for long-running operations

3. **Dead Letter Queue**:
   - Configure a dead letter queue for messages that fail processing multiple times
   - Recommended maximum receives: 3-5 before sending to DLQ
   - Use separate monitoring for the DLQ to identify systematic issues

### Scaling Considerations

1. **Horizontal Scaling**:

   - The worker process can be deployed across multiple instances for higher throughput
   - SQS automatically handles distributing messages across consumers

2. **Database Connections**:

   - Each active sync operation establishes a connection to the target PostgreSQL database
   - Set connection pool limits based on expected concurrent synchronizations
   - Consider timeouts for idle connections to free resources

3. **Memory Requirements**:
   - Large database schema analysis may require significant memory
   - For PostgreSQL integrations with many tables or large datasets, allocate at least 1GB of memory per worker

### Monitoring and Alerting

1. **Key Metrics to Monitor**:

   - SQS queue depth (ApproximateNumberOfMessages)
   - Message age (ApproximateAgeOfOldestMessage)
   - Failed sync operations (sync.status = FAILED)
   - Worker process memory and CPU usage

2. **Recommended Alerts**:

   - Queue depth exceeding normal thresholds
   - Messages older than 1 hour in the queue
   - High rate of failed synchronizations
   - Worker process restarts or crashes

3. **Logging Configuration**:
   - The system uses structured logging with user_id, sync_id, and error information
   - Consider setting up log aggregation and analysis for troubleshooting

### Performance Tuning

1. **Optimizing PostgreSQL Integration**:

   - Adjust worker concurrency based on resource utilization
   - For very large databases, consider incremental sync strategies
   - Add indexes to frequently queried tables in the metadata store

2. **Timeout Configurations**:
   - Adjust visibility timeouts based on average processing times
   - Set appropriate connection timeouts for database operations
   - Configure automatic retry with exponential backoff for transient errors
