import json
import logging
import sys
import time
from typing import Any, Dict, Optional
from app.config import settings

class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs log records as single-line JSON.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Capture context extra arguments
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_data.update(record.extra_data)
            
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)


def get_logger(name: str) -> logging.Logger:
    """
    Configure and retrieve a logger by name.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers if already initialized
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    
    if settings.ENVIRONMENT in ["docker", "production"]:
        # Structured JSON logs
        handler.setFormatter(JSONFormatter())
    else:
        # Readable local logs
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        
    logger.addHandler(handler)
    return logger


# Main Application Loggers
logger = get_logger("enterprise_assistant")
agent_logger = get_logger("agent_orchestration")
db_logger = get_logger("database_service")
