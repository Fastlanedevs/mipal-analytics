from typing import Optional, Any, List, Dict, Union, overload, Tuple, Set
from redis import Redis, ConnectionPool
from redis.client import PubSub
from redis.exceptions import RedisError
import json
from pkg.log.logger import Logger
from datetime import timedelta, datetime
from redis.client import Pipeline as RedisPipeline


class RedisClient:
    """
    Enhanced Redis client with connection pooling and performance optimizations.
    """

    def __init__(self, logger: Logger, host: str = "localhost", port: int = 6379, password: Optional[str] = None):
        self.logger = logger
        self._redis: Optional[Redis] = None
        self._pool: Optional[ConnectionPool] = None
        self.host = host
        self.port = port
        self.password = password

        # Cache for frequently accessed values
        self._local_cache = {}
        self._cache_ttl = {}
        self._max_cache_items = 1000

        # Connect on initialization for better user experience
        self.connect()

    def connect(self) -> None:
        """Establish connection pool to Redis"""
        try:
            # Use connection pool for better performance
            self._pool = ConnectionPool(
                host=self.host,
                port=self.port,
                password=self.password,
                max_connections=20,  # Limit connections for resource efficiency
                decode_responses=True,  # Auto-decode responses for convenience
                socket_timeout=5.0,  # Socket timeout in seconds
                socket_connect_timeout=5.0,  # Connection timeout
                retry_on_timeout=True  # Auto-retry on timeout
            )

            self._redis = Redis(connection_pool=self._pool)
            self._redis.ping()  # Test connection
            self.logger.info(f"Successfully connected to Redis pool at {self.host}:{self.port}")
        except RedisError as e:
            self.logger.error(f"Failed to connect to Redis: {str(e)}")
            raise

    @property
    def client(self) -> Redis:
        """Get Redis client instance"""
        if self._redis is None:
            self.connect()
        return self._redis

    def close(self) -> None:
        """Close Redis connection pool"""
        if self._pool is not None:
            self._pool.disconnect()
            self._redis = None
            self._pool = None
            self.logger.info("Redis connection pool closed")

    # Basic Operations
    def set_value(self, key: str, value: Any, expiry: Optional[Union[int, timedelta]] = None) -> bool:
        """
        Set a key-value pair, optionally with expiry

        Args:
            key: Key to set
            value: Value to set (will be JSON serialized if not string)
            expiry: Expiry time in seconds or timedelta
        """
        try:
            if not isinstance(value, (str, int, float, bool)):
                value = json.dumps(value)
            if isinstance(expiry, timedelta):
                expiry = int(expiry.total_seconds())

            # Update local cache
            if key in self._local_cache:
                self._local_cache[key] = value
                if expiry:
                    self._cache_ttl[key] = datetime.now() + timedelta(seconds=expiry)

            return self.client.set(key, value, ex=expiry)
        except RedisError as e:
            self.logger.error(f"Error setting key {key}: {str(e)}")
            raise

    def set_values_batch(self, key_values: Dict[str, Any], expiry: Optional[Union[int, timedelta]] = None) -> int:
        """
        Set multiple key-value pairs in a single operation.
        Returns number of successful operations.

        Args:
            key_values: Dictionary of key-value pairs to set
            expiry: Optional expiration time in seconds or timedelta
        """
        if not key_values:
            return 0

        # Convert timedelta to seconds if needed
        if isinstance(expiry, timedelta):
            expiry = int(expiry.total_seconds())

        try:
            # Serialize values if needed
            serialized = {}
            for k, v in key_values.items():
                if not isinstance(v, (str, int, float, bool)):
                    serialized[k] = json.dumps(v)
                else:
                    serialized[k] = v

            # Use pipeline for batch operation
            successful = 0
            with self.client.pipeline() as pipe:
                for key, value in serialized.items():
                    if expiry:
                        pipe.set(key, value, ex=expiry)
                    else:
                        pipe.set(key, value)

                # Execute all commands and count successes
                results = pipe.execute()
                successful = sum(1 for r in results if r)

                # Update local cache for successful sets
                if successful > 0:
                    idx = 0
                    cache_expiry = None
                    if expiry:
                        cache_expiry = datetime.now() + timedelta(seconds=expiry)

                    for key in serialized.keys():
                        if results[idx]:
                            self._local_cache[key] = serialized[key]
                            if cache_expiry:
                                self._cache_ttl[key] = cache_expiry
                        idx += 1

                # Manage cache size
                self._check_cache_size()

            return successful

        except RedisError as e:
            self.logger.error(f"Error in batch set operation: {str(e)}")
            raise

    def get_value(self, key: str, default: Any = None, bypass_cache: bool = False) -> Any:
        """
        Get value for a key, checking local cache first unless bypass_cache is True

        Args:
            key: Key to retrieve
            default: Default value if key doesn't exist
            bypass_cache: If True, always fetch from Redis and update cache

        Returns:
            The value if found, deserialized from JSON if possible,
            otherwise the default value
        """
        # If bypass_cache is False, check cache first
        if not bypass_cache and key in self._local_cache:
            # Check if cache entry has expired
            if key in self._cache_ttl and datetime.now() > self._cache_ttl[key]:
                del self._local_cache[key]
                del self._cache_ttl[key]
            else:
                value = self._local_cache[key]
                try:
                    if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                        return json.loads(value)
                    return value
                except (TypeError, json.JSONDecodeError):
                    return value

        # Not in cache or bypass_cache is True, query Redis
        try:
            value: Optional[str] = self.client.get(key)
            if value is None:
                return default

            # Cache the value for future use
            self._local_cache[key] = value
            self._check_cache_size()

            try:
                if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                    return json.loads(value)
                return value
            except (TypeError, json.JSONDecodeError):
                return value
        except RedisError as e:
            self.logger.error(f"Error getting key {key}: {str(e)}")
            raise

    def get_values_batch(self, keys: List[str]) -> Dict[str, Any]:
        """
        Get multiple values in a single operation

        Args:
            keys: List of keys to retrieve

        Returns:
            Dictionary mapping keys to their values
        """
        if not keys:
            return {}

        # Check which keys are in cache
        result = {}
        keys_to_fetch = []

        for key in keys:
            if key in self._local_cache:
                # Check if cache entry has expired
                if key in self._cache_ttl and datetime.now() > self._cache_ttl[key]:
                    del self._local_cache[key]
                    del self._cache_ttl[key]
                    keys_to_fetch.append(key)
                else:
                    result[key] = self._local_cache[key]
            else:
                keys_to_fetch.append(key)

        # Fetch remaining keys from Redis
        if keys_to_fetch:
            try:
                # Use mget for batch retrieval
                values = self.client.mget(keys_to_fetch)

                for i, key in enumerate(keys_to_fetch):
                    value = values[i]
                    if value is not None:
                        # Cache the value
                        self._local_cache[key] = value

                        # Try to deserialize
                        try:
                            if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                                result[key] = json.loads(value)
                            else:
                                result[key] = value
                        except (TypeError, json.JSONDecodeError):
                            result[key] = value

                # Manage cache size
                self._check_cache_size()

            except RedisError as e:
                self.logger.error(f"Error in batch get operation: {str(e)}")
                raise

        # Process values for return (deserialize JSON)
        for key, value in result.items():
            if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                try:
                    result[key] = json.loads(value)
                except (TypeError, json.JSONDecodeError):
                    pass  # Keep as string if can't deserialize

        return result

    # List Operations
    def list_push(self, key: str, *values: Any) -> int:
        """Push values to a list"""
        try:
            serialized = [json.dumps(v) if not isinstance(v, (str, int, float)) else v for v in values]
            # Invalidate cache for this key since it's changing
            if key in self._local_cache:
                del self._local_cache[key]
                if key in self._cache_ttl:
                    del self._cache_ttl[key]
            return self.client.rpush(key, *serialized)
        except RedisError as e:
            self.logger.error(f"Error pushing to list {key}: {str(e)}")
            raise

    def list_push_batch(self, key: str, values: List[Any]) -> int:
        """
        Push multiple values to the end of a list in a single operation.
        Returns list length after push.
        """
        if not values:
            return 0

        try:
            # Serialize values
            serialized = [json.dumps(v) if not isinstance(v, (str, int, float)) else v for v in values]

            # Invalidate cache for this key
            if key in self._local_cache:
                del self._local_cache[key]
                if key in self._cache_ttl:
                    del self._cache_ttl[key]

            # Push all values at once
            return self.client.rpush(key, *serialized)
        except RedisError as e:
            self.logger.error(f"Error in batch push to list {key}: {str(e)}")
            raise

    def list_range(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """Get range of values from a list"""
        try:
            values = self.client.lrange(key, start, end)
            # Cache the result for future use
            if start == 0 and end == -1:  # Only cache full list retrievals
                self._local_cache[key] = values
                self._check_cache_size()

            return [
                json.loads(v) if isinstance(v, str) and (v.startswith('{') or v.startswith('[')) else v
                for v in values
            ]
        except RedisError as e:
            self.logger.error(f"Error getting range from list {key}: {str(e)}")
            raise

    # Hash Operations
    def hash_set(self, name: str, mapping: Dict[str, Any]) -> int:
        """
        Set multiple hash fields

        Args:
            name: Hash name
            mapping: Dictionary of field-value pairs to set

        Returns:
            int: Number of fields that were added
        """
        try:
            serialized = {
                k: json.dumps(v) if not isinstance(v, (str, int, float)) else v
                for k, v in mapping.items()
            }
            # Invalidate cache for this hash
            if name in self._local_cache:
                del self._local_cache[name]
                if name in self._cache_ttl:
                    del self._cache_ttl[name]

            return self.client.hset(name, mapping=serialized)  # Returns number of fields set
        except RedisError as e:
            self.logger.error(f"Error setting hash {name}: {str(e)}")
            raise e

    def hash_set_batch(self, hash_maps: Dict[str, Dict[str, Any]]) -> int:
        """
        Set multiple hashes in a single operation.
        Returns total number of fields that were added.

        Args:
            hash_maps: Dictionary where keys are hash keys and values are field mappings
        """
        if not hash_maps:
            return 0

        try:
            total_fields = 0

            # Serialize values in each hash
            serialized_maps = {}
            for hash_key, mapping in hash_maps.items():
                serialized = {
                    k: json.dumps(v) if not isinstance(v, (str, int, float)) else v
                    for k, v in mapping.items()
                }
                serialized_maps[hash_key] = serialized

                # Invalidate cache for these hashes
                if hash_key in self._local_cache:
                    del self._local_cache[hash_key]
                    if hash_key in self._cache_ttl:
                        del self._cache_ttl[hash_key]

            # Use Redis pipeline for batched operations
            with self.client.pipeline() as pipe:
                for hash_key, mapping in serialized_maps.items():
                    if mapping:
                        pipe.hset(hash_key, mapping=mapping)

                # Execute all commands and sum the results
                results = pipe.execute()
                total_fields = sum(r for r in results if isinstance(r, int))

            return total_fields

        except RedisError as e:
            self.logger.error(f"Error in batch hash set operation: {str(e)}")
            raise

    def hash_get(self, name: str, key: str) -> Any:
        """Get value of a hash field"""
        # Check if we have the whole hash cached
        if name in self._local_cache and isinstance(self._local_cache[name], dict):
            # Check if cache expired
            if name in self._cache_ttl and datetime.now() > self._cache_ttl[name]:
                del self._local_cache[name]
                del self._cache_ttl[name]
            else:
                # Return from cache if the key exists
                cached_hash = self._local_cache[name]
                if key in cached_hash:
                    value = cached_hash[key]
                    try:
                        if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                            return json.loads(value)
                        return value
                    except (TypeError, json.JSONDecodeError):
                        return value

        try:
            value = self.client.hget(name, key)
            if value is None:
                return None

            try:
                if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                    return json.loads(value)
                return value
            except (TypeError, json.JSONDecodeError):
                return value
        except RedisError as e:
            self.logger.error(f"Error getting hash field {key} from {name}: {str(e)}")
            raise

    def hash_get_all(self, name: str) -> Dict[str, Any]:
        """Get all fields and values in a hash"""
        # Check cache first
        if name in self._local_cache and isinstance(self._local_cache[name], dict):
            # Check if cache expired
            if name in self._cache_ttl and datetime.now() > self._cache_ttl[name]:
                del self._local_cache[name]
                del self._cache_ttl[name]
            else:
                # Process cached values (deserialize JSON)
                cached_hash = self._local_cache[name]
                result = {}
                for k, v in cached_hash.items():
                    try:
                        if isinstance(v, str) and (v.startswith('{') or v.startswith('[')):
                            result[k] = json.loads(v)
                        else:
                            result[k] = v
                    except (TypeError, json.JSONDecodeError):
                        result[k] = v
                return result

        try:
            result = self.client.hgetall(name)

            # Cache the result for future use
            self._local_cache[name] = result.copy()
            self._check_cache_size()

            # Process values (deserialize JSON)
            processed = {}
            for k, v in result.items():
                try:
                    if isinstance(v, str) and (v.startswith('{') or v.startswith('[')):
                        processed[k] = json.loads(v)
                    else:
                        processed[k] = v
                except (TypeError, json.JSONDecodeError):
                    processed[k] = v

            return processed
        except RedisError as e:
            self.logger.error(f"Error getting all hash fields from {name}: {str(e)}")
            raise

    def hash_get_batch(self, names: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get multiple hashes in a single operation

        Args:
            names: List of hash names to retrieve

        Returns:
            Dictionary mapping hash names to their field-value mappings
        """
        if not names:
            return {}

        # Check which hashes are in cache
        result = {}
        names_to_fetch = []

        for name in names:
            if name in self._local_cache and isinstance(self._local_cache[name], dict):
                # Check if cache expired
                if name in self._cache_ttl and datetime.now() > self._cache_ttl[name]:
                    del self._local_cache[name]
                    del self._cache_ttl[name]
                    names_to_fetch.append(name)
                else:
                    # Process cached values (deserialize JSON)
                    cached_hash = self._local_cache[name]
                    processed = {}
                    for k, v in cached_hash.items():
                        try:
                            if isinstance(v, str) and (v.startswith('{') or v.startswith('[')):
                                processed[k] = json.loads(v)
                            else:
                                processed[k] = v
                        except (TypeError, json.JSONDecodeError):
                            processed[k] = v
                    result[name] = processed
            else:
                names_to_fetch.append(name)

        # Fetch remaining hashes from Redis
        if names_to_fetch:
            try:
                # Use pipeline for efficiency
                with self.client.pipeline() as pipe:
                    for name in names_to_fetch:
                        pipe.hgetall(name)

                    # Execute all commands
                    pipe_results = pipe.execute()

                    # Process results
                    for i, name in enumerate(names_to_fetch):
                        hash_data = pipe_results[i]
                        if hash_data:
                            # Cache the result
                            self._local_cache[name] = hash_data.copy()

                            # Process values (deserialize JSON)
                            processed = {}
                            for k, v in hash_data.items():
                                try:
                                    if isinstance(v, str) and (v.startswith('{') or v.startswith('[')):
                                        processed[k] = json.loads(v)
                                    else:
                                        processed[k] = v
                                except (TypeError, json.JSONDecodeError):
                                    processed[k] = v

                            result[name] = processed

                # Manage cache size
                self._check_cache_size()

            except RedisError as e:
                self.logger.error(f"Error in batch hash get operation: {str(e)}")
                raise

        return result

    # Set Operations
    def set_add(self, key: str, *values: Any) -> int:
        """Add values to a set"""
        try:
            serialized = [json.dumps(v) if not isinstance(v, (str, int, float)) else v for v in values]
            # Invalidate cache
            if key in self._local_cache:
                del self._local_cache[key]
                if key in self._cache_ttl:
                    del self._cache_ttl[key]
            return self.client.sadd(key, *serialized)
        except RedisError as e:
            self.logger.error(f"Error adding to set {key}: {str(e)}")
            raise

    def set_add_batch(self, key: str, values: Set[Any]) -> int:
        """
        Add multiple values to a set in a single operation

        Args:
            key: Set key
            values: Values to add

        Returns:
            Number of values added to the set
        """
        if not values:
            return 0

        try:
            # Serialize values
            serialized = [json.dumps(v) if not isinstance(v, (str, int, float)) else v for v in values]

            # Invalidate cache
            if key in self._local_cache:
                del self._local_cache[key]
                if key in self._cache_ttl:
                    del self._cache_ttl[key]

            # Add all values at once
            return self.client.sadd(key, *serialized)
        except RedisError as e:
            self.logger.error(f"Error in batch add to set {key}: {str(e)}")
            raise

    def set_members(self, key: str, bypass_cache: bool = False) -> set:
        """Get all members of a set"""
        # If bypass_cache is False, check cache first
        if not bypass_cache and key in self._local_cache and isinstance(self._local_cache[key], set):
            # Check if cache expired
            if key in self._cache_ttl and datetime.now() > self._cache_ttl[key]:
                del self._local_cache[key]
                del self._cache_ttl[key]
            else:
                return self._local_cache[key]

        try:
            values = self.client.smembers(key)

            # Cache the result for future use
            self._local_cache[key] = values
            self._check_cache_size()

            # Process values (deserialize JSON)
            processed = set()
            for v in values:
                try:
                    if isinstance(v, str) and (v.startswith('{') or v.startswith('[')):
                        processed.add(json.loads(v))
                    else:
                        processed.add(v)
                except (TypeError, json.JSONDecodeError):
                    processed.add(v)

            return processed
        except RedisError as e:
            self.logger.error(f"Error getting members from set {key}: {str(e)}")
            raise

    # Pub/Sub Operations
    def create_pubsub(self) -> PubSub:
        """Create a publish/subscribe object"""
        return self.client.pubsub()

    def publish(self, channel: str, message: Any) -> int:
        """Publish message to a channel"""
        try:
            if not isinstance(message, (str, int, float)):
                message = json.dumps(message)
            return self.client.publish(channel, message)
        except RedisError as e:
            self.logger.error(f"Error publishing to channel {channel}: {str(e)}")
            raise

    # Key Operations
    def delete(self, *keys: str) -> int:
        """Delete one or more keys"""
        try:
            # Invalidate cache
            for key in keys:
                if key in self._local_cache:
                    del self._local_cache[key]
                    if key in self._cache_ttl:
                        del self._cache_ttl[key]
            return self.client.delete(*keys)
        except RedisError as e:
            self.logger.error(f"Error deleting keys: {str(e)}")
            raise

    def delete_batch(self, keys: List[str]) -> int:
        """
        Delete multiple keys in a single operation

        Args:
            keys: List of keys to delete

        Returns:
            Number of keys deleted
        """
        if not keys:
            return 0

        try:
            # Invalidate cache
            for key in keys:
                if key in self._local_cache:
                    del self._local_cache[key]
                    if key in self._cache_ttl:
                        del self._cache_ttl[key]

            # Delete all keys at once
            return self.client.delete(*keys)
        except RedisError as e:
            self.logger.error(f"Error in batch delete operation: {str(e)}")
            raise

    def exists(self, *keys: str) -> int:
        """Check if one or more keys exist"""
        try:
            return self.client.exists(*keys)
        except RedisError as e:
            self.logger.error(f"Error checking key existence: {str(e)}")
            raise

    def keys(self, pattern: str) -> List[str]:
        """Get keys matching a pattern"""
        try:
            return self.client.keys(pattern)
        except RedisError as e:
            self.logger.error(f"Error getting keys with pattern {pattern}: {str(e)}")
            raise

    def expire(self, key: str, seconds: Union[int, timedelta]) -> bool:
        """Set a key's time to live in seconds"""
        try:
            if isinstance(seconds, timedelta):
                seconds = int(seconds.total_seconds())

            # Update cache TTL if key is cached
            if key in self._local_cache:
                self._cache_ttl[key] = datetime.now() + timedelta(seconds=seconds)

            return self.client.expire(key, seconds)
        except RedisError as e:
            self.logger.error(f"Error setting expiry for key {key}: {str(e)}")
            raise

    # Lock Management
    def acquire_lock(self, lock_name: str, timeout: int = 10) -> Optional[str]:
        """
        Acquire a distributed lock with timeout.
        Returns a lock identifier if successful, None otherwise.
        """
        import uuid
        lock_id = str(uuid.uuid4())

        try:
            # Use SET with NX option for atomic lock acquisition
            acquired = self.client.set(f"lock:{lock_name}", lock_id, nx=True, ex=timeout)

            if acquired:
                self.logger.debug(f"Acquired lock {lock_name} with ID {lock_id}")
                return lock_id
            else:
                self.logger.debug(f"Failed to acquire lock {lock_name}")
                return None
        except RedisError as e:
            self.logger.error(f"Error acquiring lock {lock_name}: {str(e)}")
            return None

    def release_lock(self, lock_name: str, lock_id: str) -> bool:
        """
        Release a distributed lock if it matches the lock ID.
        Returns True if the lock was released, False otherwise.
        """
        # Use Lua script to ensure atomic check-and-delete
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        try:
            result = self.client.eval(script, 1, f"lock:{lock_name}", lock_id)
            success = result == 1

            if success:
                self.logger.debug(f"Released lock {lock_name} with ID {lock_id}")
            else:
                self.logger.debug(f"Failed to release lock {lock_name} with ID {lock_id} (not owner)")

            return success
        except RedisError as e:
            self.logger.error(f"Error releasing lock {lock_name}: {str(e)}")
            return False

    # Pipeline Operations
    def pipeline(self) -> RedisPipeline:
        """
        Create a pipeline for batching multiple Redis commands

        Returns:
            Pipeline: Redis pipeline object
        """
        return self.client.pipeline()

    def with_pipeline(self):
        """
        Get a Redis pipeline for executing multiple commands in a single network round-trip.
        Use with the 'with' statement for proper resource management.

        Example:
            with redis_client.with_pipeline() as pipe:
                pipe.set("key1", "value1")
                pipe.get("key2")
                results = pipe.execute()
        """
        return self.client.pipeline()

    def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment the value of a key by the given amount.
        Returns the new value or None if error.
        """
        try:
            # Invalidate cache for this key
            if key in self._local_cache:
                del self._local_cache[key]
                if key in self._cache_ttl:
                    del self._cache_ttl[key]

            result = self.client.incrby(key, amount)
            self.logger.debug(f"Incremented key {key} by {amount}, new value: {result}")
            return result
        except RedisError as e:
            self.logger.error(f"Error incrementing key {key}: {str(e)}")
            raise

    # Cache management methods
    def _check_cache_size(self) -> None:
        """Ensure the cache doesn't grow too large"""
        if len(self._local_cache) > self._max_cache_items:
            # Remove expired entries first
            now = datetime.now()
            expired_keys = [k for k, v in self._cache_ttl.items() if now > v]
            for k in expired_keys:
                if k in self._local_cache:
                    del self._local_cache[k]
                del self._cache_ttl[k]

            # If still too many items, remove oldest (approximated by iteration order)
            while len(self._local_cache) > self._max_cache_items:
                try:
                    key = next(iter(self._local_cache))
                    del self._local_cache[key]
                    if key in self._cache_ttl:
                        del self._cache_ttl[key]
                except (StopIteration, RuntimeError):
                    break  # No more items or dictionary changed size during iteration

    def clear_cache(self) -> None:
        """Clear the local cache"""
        self._local_cache.clear()
        self._cache_ttl.clear()
        self.logger.debug("Local cache cleared")

    def set_max_cache_items(self, max_items: int) -> None:
        """Set the maximum number of items to keep in the cache"""
        self._max_cache_items = max(100, max_items)  # Minimum 100 items
        self._check_cache_size()  # Apply new limit immediately

    def __enter__(self):
        """Context manager enter"""
        if self._redis is None:
            self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


class Pipeline:
    """Wrapper for Redis Pipeline with type-safe methods"""

    def __init__(self, pipeline: RedisPipeline):
        self._pipeline = pipeline

    def set(self, key: str, value: Any, expiry: Optional[Union[int, timedelta]] = None) -> 'Pipeline':
        """Set a key-value pair with optional expiry"""
        if not isinstance(value, (str, int, float, bool)):
            value = json.dumps(value)
        if isinstance(expiry, timedelta):
            expiry = int(expiry.total_seconds())
        self._pipeline.set(key, value, ex=expiry)
        return self

    def get(self, key: str) -> 'Pipeline':
        """Get a key's value"""
        self._pipeline.get(key)
        return self

    def rpush(self, key: str, value: Any) -> 'Pipeline':
        """Add value to the end of a list"""
        if not isinstance(value, (str, int, float, bool)):
            value = json.dumps(value)
        self._pipeline.rpush(key, value)
        return self

    def lpush(self, key: str, value: Any) -> 'Pipeline':
        """Add value to the beginning of a list"""
        if not isinstance(value, (str, int, float, bool)):
            value = json.dumps(value)
        self._pipeline.lpush(key, value)
        return self

    def hincrby(self, name: str, key: str, amount: int = 1) -> 'Pipeline':
        """Increment the integer value of a hash field by the given number"""
        self._pipeline.hincrby(name, key, amount)
        return self

    def hset(self, name: str, key: str, value: Any) -> 'Pipeline':
        """Set a hash field to a value"""
        if not isinstance(value, (str, int, float, bool)):
            value = json.dumps(value)
        self._pipeline.hset(name, key, value)
        return self

    def hget(self, name: str, key: str) -> 'Pipeline':
        """Get value of a hash field"""
        self._pipeline.hget(name, key)
        return self

    def delete(self, key: str) -> 'Pipeline':
        """Delete a key"""
        self._pipeline.delete(key)
        return self

    def expire(self, key: str, seconds: Union[int, timedelta]) -> 'Pipeline':
        """Set a key's time to live in seconds"""
        if isinstance(seconds, timedelta):
            seconds = int(seconds.total_seconds())
        self._pipeline.expire(key, seconds)
        return self

    def sadd(self, key: str, member: Any) -> 'Pipeline':
        """Add a member to a set"""
        if not isinstance(member, (str, int, float, bool)):
            member = json.dumps(member)
        self._pipeline.sadd(key, member)
        return self

    def incrby(self, key: str, amount: int = 1) -> 'Pipeline':
        """Increment the value of a key"""
        self._pipeline.incrby(key, amount)
        return self

    def execute(self) -> List[Any]:
        """Execute all commands in the pipeline"""
        return self._pipeline.execute()