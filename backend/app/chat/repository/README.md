# Conversation Caching System

This document outlines the conversation caching system implemented in the chat repository.

## Overview

The caching system allows for efficient retrieval of conversation data by storing frequently accessed conversations in Redis. This reduces database load and improves response times for users accessing their recent conversations.

## Key Components

### 1. Cache Implementation

The caching system is implemented in `chat_repository.py` and includes methods for:

- Caching conversations in Redis
- Retrieving cached conversations
- Invalidating cache entries when conversations are updated or deleted

### 2. Redis Integration

The system uses an optional Redis client that can be provided during repository initialization. If Redis is not available, the system gracefully falls back to database queries.

### 3. JSON Serialization

Conversation entities are serialized to JSON before being stored in Redis. A custom JSON encoder (`DateTimeEncoder`) handles the serialization of datetime objects, which are not natively serializable in JSON.

## Recent Changes

### DateTime Serialization Fix

A custom JSON encoder class `DateTimeEncoder` was implemented to handle datetime serialization when caching conversations. This resolved the error:

```
Object of type datetime is not JSON serializable
```

The encoder converts datetime objects to ISO format strings during JSON serialization:

```python
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)
```

### Implementation Details

The serialization is used in the `get_conversation` method when caching the conversation data:

```python
# Use the custom encoder to handle datetime objects
serialized_data = json.dumps(conversation_entity.model_dump(), cls=DateTimeEncoder)
await self.cache_conversation(conversation_id, serialized_data)
```

## Usage

The caching system is used automatically by the `get_conversation` method:

1. First attempts to retrieve from cache
2. If not found or error occurs, falls back to database query
3. After database query, caches results for future requests

Cache invalidation occurs when conversations are updated or deleted to ensure data consistency.

## Benefits

- Reduced database load
- Improved response times for frequently accessed conversations
- Graceful fallback when Redis is unavailable
- Proper handling of complex data types during serialization
