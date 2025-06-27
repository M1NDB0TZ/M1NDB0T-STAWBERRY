# core/logging_config.py

import os
import logging
import logging.config
from typing import Dict, Any
import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time

def configure_logging(service_name: str, log_level: str = "INFO", enable_json: bool = False):
    """
    Configures structured logging for the application using structlog.
    
    Args:
        service_name: The name of the service, used for log filtering.
        log_level: The minimum log level to output (e.g., "DEBUG", "INFO").
        enable_json: If True, logs will be formatted as JSON.
    """
    log_level = log_level.upper()
    
    # Define processors for structlog
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    # Configure structlog
    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Define formatters for standard logging
    formatter = "json" if enable_json else "console"
    
    # Define logging configuration dictionary
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.processors.JSONRenderer(),
                "foreign_pre_chain": shared_processors,
            },
            "console": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.dev.ConsoleRenderer(colors=True),
                "foreign_pre_chain": shared_processors,
            },
        },
        "handlers": {
            "default": {
                "level": log_level,
                "class": "logging.StreamHandler",
                "formatter": formatter,
            },
        },
        "loggers": {
            "": {"handlers": ["default"], "level": log_level, "propagate": True},
            "uvicorn.error": {"level": "INFO"},
            "uvicorn.access": {"handlers": [], "propagate": False}, # Disable uvicorn access logs
        }
    }
    
    logging.config.dictConfig(logging_config)
    logger = structlog.get_logger("logging_config")
    logger.info("Logging configured", service=service_name, level=log_level, json=enable_json)

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware to log HTTP requests and responses.
    """
    async def dispatch(self, request: Request, call_next: callable) -> Response:
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            path=request.url.path,
            method=request.method,
            client_host=request.client.host,
        )
        
        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
            process_time = time.perf_counter() - start_time
            structlog.contextvars.bind_contextvars(
                status_code=response.status_code,
                process_time=round(process_time, 4)
            )
            logger = structlog.get_logger("api.access")
            logger.info("Request completed")
        except Exception as e:
            process_time = time.perf_counter() - start_time
            structlog.contextvars.bind_contextvars(
                status_code=500,
                process_time=round(process_time, 4)
            )
            logger = structlog.get_logger("api.error")
            logger.exception("Unhandled exception")
            raise e
            
        return response
