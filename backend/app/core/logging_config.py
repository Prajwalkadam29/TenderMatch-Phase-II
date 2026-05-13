import json
import logging
import sys
from datetime import datetime
from contextvars import ContextVar
import uuid

# ContextVar to hold the unique request ID across async tasks
request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="-")

class JSONFormatter(logging.Formatter):
    """Production structured JSON logger formatter."""
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx_var.get(),
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    # Remove existing handlers to avoid duplicates
    root_logger.handlers = []
    root_logger.addHandler(handler)

    # Configure uvicorn and fastapi loggers
    for logger_name in ["uvicorn", "uvicorn.access", "fastapi"]:
        l = logging.getLogger(logger_name)
        l.handlers = [handler]
        l.propagate = False
