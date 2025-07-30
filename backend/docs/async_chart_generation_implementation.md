# Asynchronous Chart Generation Implementation

## Overview

This document outlines the implementation of an asynchronous chart generation system to solve the gateway timeout issues and improve user experience. The system processes chart generation tasks in the background and provides real-time status updates.

## Architecture

### Components

1. **ChartTask Entity** - Represents a chart generation task with status tracking
2. **ChartQueueService** - Manages the Redis-based task queue and status updates
3. **AnalyticsHandler** - Handles async chart API endpoints
4. **ChartGenerationWorker** - Background worker for processing tasks
5. **WebSocket/SSE Routes** - Real-time status updates
6. **Message Index** - Redis-based indexing for task lookup by message

### Flow

```
User Request → API → Queue Task → Worker → Generate Chart → Update Status → Notify User
```

## Implementation Details

### 1. Entity Models

#### ChartTask

```python
class ChartTask(BaseModel):
    task_id: str
    chart_id: Optional[str] = None  # Set when chart is created
    message_id: UUID
    user_id: str
    org_id: Optional[str]
    status: ChartStatus
    progress: int = 0  # 0-100
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None

    # Chart generation parameters
    visibility: ChartVisibility
    force_create: bool
    adjustment_query: Optional[str] = None

    # Progress tracking
    current_step: str = "queued"  # e.g., "data_extraction", "llm_generation", "schema_creation"
    step_progress: Optional[Dict[str, int]] = {}  # Progress per step

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            UUID: str,
            datetime: lambda dt: dt.isoformat() if dt else None
        }
```

#### ChartStatus Enum

```python
class ChartStatus(str, Enum):
    PENDING = "PENDING"      # Task queued, waiting to be processed
    PROCESSING = "PROCESSING" # Currently being generated
    COMPLETED = "COMPLETED"   # Successfully generated
    FAILED = "FAILED"        # Generation failed
    CANCELLED = "CANCELLED"  # User cancelled
```

### 2. Queue Service

The `ChartQueueService` manages:

- Task enqueueing/dequeueing with Redis
- Status updates with Redis pub/sub
- Progress tracking with step-by-step updates
- Task completion handling
- Message-based task indexing
- Queue statistics and monitoring

Key methods:

- `enqueue_chart_task()` - Add task to queue with message indexing
- `dequeue_chart_task()` - Get next task for processing
- `update_task_progress()` - Update progress and publish updates
- `complete_task()` - Mark task as completed/failed with chart_id
- `get_task_status()` - Get current task status
- `get_task_data()` - Get raw task data without reconstruction
- `cancel_task()` - Cancel pending or processing tasks
- `get_active_tasks_by_message_id()` - Get active tasks for a message
- `get_queue_stats()` - Get queue statistics
- `cleanup_expired_tasks()` - Clean up old task data

### 3. API Endpoints

#### Async Chart Creation

```http
POST /api/v1/analytics/charts/async
Content-Type: application/json

{
  "message_id": "uuid",
  "visibility": "PRIVATE",
  "force_create": false,
  "adjustment_query": "optional"
}
```

Response:

```json
{
  "task_id": "uuid",
  "message_id": "uuid",
  "status": "PENDING",
  "progress": 0,
  "current_step": "queued",
  "error_message": null,
  "created_at": "2024-01-01T00:00:00Z",
  "started_at": null,
  "completed_at": null,
  "estimated_completion": null,
  "message": "Chart generation queued successfully"
}
```

#### Status Check

```http
GET /api/v1/analytics/charts/async/{task_id}/status
```

#### Get Result

```http
GET /api/v1/analytics/charts/async/{task_id}/result
```

#### Cancel Task

```http
DELETE /api/v1/analytics/charts/async/{task_id}
```

#### Get Charts and Active Tasks by Message

```http
GET /api/v1/analytics/charts/by-message/{message_id}
```

Response:

```json
{
  "charts": [...],
  "active_tasks": [...],
  "has_active_tasks": true
}
```

### 4. Real-time Updates

#### Server-Sent Events (SSE)

```http
GET /api/v1/analytics/charts/stream/{task_id}
```

The SSE endpoint polls for updates every 2 seconds and sends status updates in real-time format.

#### WebSocket

```http
WS /api/v1/analytics/charts/ws/{task_id}
```

The WebSocket endpoint subscribes to Redis pub/sub channels for real-time updates without polling. It sends initial status immediately upon connection and then listens for updates.

### 5. Background Worker

The `ChartGenerationWorker` runs as a separate process and:

- Polls the Redis queue for new tasks
- Processes tasks using existing chart generation logic
- Updates progress with detailed step information
- Handles errors gracefully with proper status updates
- Supports graceful shutdown

Key features:

- Asynchronous task processing
- Progress tracking with step updates
- Error handling and recovery
- Graceful shutdown handling

### 6. Message Indexing

The system maintains a Redis-based index to efficiently lookup tasks by message ID:

- Index key: `message_tasks:{message_id}:{user_id}`
- 24-hour TTL for automatic cleanup
- Enables quick retrieval of active tasks for a message
- Supports multiple active tasks per message

## Usage Examples

### Frontend Integration

#### 1. Create Chart Asynchronously

```javascript
// Start chart generation
const response = await fetch("/api/v1/analytics/charts/async", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    message_id: "message-uuid",
    visibility: "PRIVATE",
  }),
});

const task = await response.json();
const taskId = task.task_id;

// Show progress UI
showProgressIndicator(taskId);
```

#### 2. Monitor Progress with SSE

```javascript
// Connect to SSE stream
const eventSource = new EventSource(
  `/api/v1/analytics/charts/stream/${taskId}`
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === "status_update") {
    updateProgressUI(data.data);

    if (data.data.status === "COMPLETED") {
      eventSource.close();
      showChartResult(taskId);
    } else if (data.data.status === "FAILED") {
      eventSource.close();
      showError(data.data.error_message);
    }
  }
};
```

#### 3. Monitor Progress with WebSocket

```javascript
const ws = new WebSocket(`ws://localhost/api/v1/analytics/charts/ws/${taskId}`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  updateProgressUI(data);

  if (data.status === "COMPLETED") {
    ws.close();
    showChartResult(taskId);
  }
};
```

#### 4. Get Final Result

```javascript
async function showChartResult(taskId) {
  const response = await fetch(
    `/api/v1/analytics/charts/async/${taskId}/result`
  );
  const chart = await response.json();

  // Display the chart
  renderChart(chart);
}
```

#### 5. Get Charts and Active Tasks for a Message

```javascript
async function getMessageCharts(messageId) {
  const response = await fetch(
    `/api/v1/analytics/charts/by-message/${messageId}`
  );
  const data = await response.json();

  // Display completed charts
  data.charts.forEach((chart) => renderChart(chart));

  // Show active tasks
  if (data.has_active_tasks) {
    data.active_tasks.forEach((task) => showProgressIndicator(task.task_id));
  }
}
```

#### 6. Cancel a Task

```javascript
async function cancelChartTask(taskId) {
  const response = await fetch(`/api/v1/analytics/charts/async/${taskId}`, {
    method: "DELETE",
  });

  if (response.ok) {
    console.log("Task cancelled successfully");
  }
}
```

## Benefits

1. **No Gateway Timeouts** - Chart generation happens in background
2. **Real-time Progress** - Users see progress updates with detailed steps
3. **Better UX** - Users can continue using the app while charts generate
4. **Scalability** - Multiple workers can process tasks
5. **Error Handling** - Graceful error handling with user feedback
6. **Cancellation** - Users can cancel long-running tasks
7. **Message Indexing** - Efficient lookup of tasks by message
8. **Redis Pub/Sub** - Real-time updates without polling
9. **Data Integrity** - Raw data storage prevents corruption
10. **Monitoring** - Queue statistics and task tracking

## Deployment

### 1. Start Chart Worker

```bash
cd cmd_server/worker
python main.py
```

### 2. Update Dependencies

Add the new services to your dependency injection container:

```python
# In your container configuration
container.wire(modules=[
    "app.analytics.service.chart_queue_service",
    "app.analytics.api.handlers"
])
```

### 3. Environment Variables

Ensure Redis is configured and accessible:

```bash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=optional
```

## Monitoring

### Queue Statistics

The system provides queue statistics through the `get_queue_stats()` method:

- Queue length
- Processing count
- Updated timestamp

### Task Cleanup

The system automatically cleans up old task data:

- Task data: 24 hours TTL
- Status data: 1 hour TTL
- Message index: 24 hours TTL
- Queue data: Persistent until processed

### Error Handling

- Comprehensive error logging
- Graceful degradation
- User-friendly error messages
- Task state recovery

## Recent Improvements

### 1. Enhanced Data Storage

- Raw task data storage to prevent corruption
- Separate status and task data storage
- Cache management for data consistency

### 2. Message Indexing

- Redis-based message-to-task indexing
- Efficient lookup of active tasks by message
- Automatic cleanup with TTL

### 3. Improved Error Handling

- Better error messages and logging
- Graceful error recovery
- User access validation

### 4. Real-time Updates

- Both SSE and WebSocket support
- Redis pub/sub for immediate updates
- Polling fallback for SSE
- Automatic connection cleanup

### 5. Task Management

- Task cancellation support
- Progress tracking with steps
- Completion verification
- User access validation
- Raw data storage to prevent corruption

### 6. API Enhancements

- New endpoint for message-based chart retrieval
- Combined charts and active tasks response
- Better response DTOs with status information
- Proper HTTP status codes and error handling
- Authentication and authorization checks

## Future Enhancements

1. **Multiple Workers** - Scale horizontally with multiple worker instances
2. **Priority Queue** - Support for high-priority chart generation
3. **Retry Logic** - Automatic retry for failed tasks
4. **Progress Estimation** - Better ETA calculations
5. **Resource Limits** - Prevent resource exhaustion
6. **Metrics** - Detailed performance metrics
7. **Task Scheduling** - Delayed task execution
8. **Batch Processing** - Multiple charts in one request
9. **Task Dependencies** - Chart generation dependencies
10. **Advanced Monitoring** - Dashboard for queue management

## Current Implementation Status

### ✅ Implemented Features

- Complete async chart generation pipeline
- Real-time progress updates via SSE and WebSocket
- Task cancellation and management
- Message-based task indexing
- Queue statistics and monitoring
- Error handling and recovery
- User access validation
- Raw data storage for integrity

### 🔄 In Progress

- Enhanced monitoring and metrics
- Performance optimizations
- Additional error recovery mechanisms

### 📋 Known Limitations

- Single worker instance (can be scaled horizontally)
- No priority queue support yet
- Limited retry logic for failed tasks
- No task scheduling capabilities

## Migration Strategy

1. **Phase 1** - Deploy async endpoints alongside existing sync endpoints
2. **Phase 2** - Update frontend to use async endpoints
3. **Phase 3** - Deprecate sync endpoints
4. **Phase 4** - Remove sync endpoints

This implementation provides a robust, scalable solution for asynchronous chart generation while maintaining backward compatibility and providing excellent user experience.
