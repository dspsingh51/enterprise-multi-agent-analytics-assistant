import json
import time
import threading
from typing import Any, Dict, List, Optional
import redis
from app.config import settings
from app.observability.logger import db_logger

class RedisMemoryManager:
    """
    Manages conversational memory and key-value state.
    Uses Redis when available, falling back to a thread-safe in-memory cache.
    """
    def __init__(self):
        self.client = None
        self.in_memory_db = {}
        self.lock = threading.Lock()
        self._init_redis()

    def _init_redis(self):
        if settings.ENVIRONMENT == "docker" or settings.REDIS_HOST != "localhost":
            db_logger.info(f"Attempting connection to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}...")
            try:
                self.client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    decode_responses=True,
                    socket_connect_timeout=3
                )
                self.client.ping()
                db_logger.info("Successfully connected to Redis cache.")
                return
            except (redis.ConnectionError, Exception) as e:
                db_logger.warning(f"Redis connection failed: {e}. Falling back to in-memory memory.")
                self.client = None

        db_logger.info("Initializing Thread-Safe In-Memory database for storage fallback...")

    def set_val(self, key: str, value: Any, expire_seconds: Optional[int] = None) -> bool:
        """
        Set key-value in database. Value is serialized to JSON.
        """
        serialized = json.dumps(value)
        if self.client:
            try:
                if expire_seconds:
                    self.client.setex(key, expire_seconds, serialized)
                else:
                    self.client.set(key, serialized)
                return True
            except Exception as e:
                db_logger.error(f"Redis set failed: {e}. Falling back to in-memory.")

        # Fallback to In-Memory
        with self.lock:
            self.in_memory_db[key] = serialized
            return True

    def get_val(self, key: str) -> Optional[Any]:
        """
        Get key-value from database. Value is deserialized from JSON.
        """
        serialized = None
        if self.client:
            try:
                serialized = self.client.get(key)
            except Exception as e:
                db_logger.error(f"Redis get failed: {e}. Falling back to in-memory.")

        # Fallback to In-Memory
        if serialized is None:
            with self.lock:
                serialized = self.in_memory_db.get(key)

        if serialized is None:
            return None

        try:
            return json.loads(serialized)
        except Exception:
            return serialized

    def delete_val(self, key: str) -> bool:
        """
        Delete key from database.
        """
        if self.client:
            try:
                self.client.delete(key)
                return True
            except Exception as e:
                db_logger.error(f"Redis delete failed: {e}. Falling back to in-memory.")

        # Fallback to In-Memory
        with self.lock:
            if key in self.in_memory_db:
                del self.in_memory_db[key]
                return True
            return False

    def add_chat_message(self, session_id: str, role: str, content: str, additional_data: Optional[Dict[str, Any]] = None):
        """
        Appends a chat message to a session's history list.
        """
        key = f"chat_history:{session_id}"
        history = self.get_val(key) or []
        
        message = {
            "role": role,
            "content": content,
            "timestamp": time.time()
        }
        if additional_data:
            message["metadata"] = additional_data

        history.append(message)
        self.set_val(key, history)

    def get_chat_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves the list of chat messages for a session.
        """
        key = f"chat_history:{session_id}"
        return self.get_val(key) or []

    def clear_chat_history(self, session_id: str) -> bool:
        """
        Clears the list of chat messages for a session.
        """
        key = f"chat_history:{session_id}"
        return self.delete_val(key)

# Global memory manager
memory_manager = RedisMemoryManager()
