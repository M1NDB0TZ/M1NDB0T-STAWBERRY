"""
Centralized logging configuration for MindBot services
Provides structured logging with consistent formatting across all services
"""

import os
import logging
import logging.config
from typing import Dict, Any
import structlog
from structlog.stdlib import LoggingFactory


def configure_logging(
    service_name: str,
    log_level: str = "INFO",
    log_file: str = None,
    enable_json: bool = False
) -> None:
    """
    Configure structured logging for MindBot services
    
    Args:
        service_name: Name of the service (e.g., "auth-service", "time-service")
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
        enable_json: Whether to output JSON formatted logs
    """
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.processors.JSONRenderer() if enable_json else structlog.dev.ConsoleRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=LoggingFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging
    logging_config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.processors.JSONRenderer(),
            },
            "console": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.dev.ConsoleRenderer(colors=True),
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json" if enable_json else "console",
                "level": log_level,
            },
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["console"],
                "level": log_level,
                "propagate": False,
            },
            service_name: {
                "handlers": ["console"],
                "level": log_level,
                "propagate": False,
            },
            "uvicorn": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
            "fastapi": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }
    
    # Add file handler if log_file is specified
    if log_file:
        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        logging_config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": log_file,
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "json",
            "level": log_level,
        }
        
        # Add file handler to all loggers
        for logger_config in logging_config["loggers"].values():
            logger_config["handlers"].append("file")
    
    logging.config.dictConfig(logging_config)
    
    # Get logger for this module
    logger = structlog.get_logger(service_name)
    logger.info(
        "Logging configured",
        service=service_name,
        level=log_level,
        json_output=enable_json,
        log_file=log_file,
    )


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance
    
    Args:
        name: Logger name (defaults to calling module)
        
    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)


# Request logging middleware for FastAPI
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log HTTP requests and responses
    """
    
    def __init__(self, app, logger_name: str = "http"):
        super().__init__(app)
        self.logger = get_logger(logger_name)
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request
        self.logger.info(
            "HTTP request started",
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params),
            client_ip=request.client.host if request.client else None,
        )
        
        # Process request
        try:
            response: Response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            self.logger.info(
                "HTTP request completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                process_time_seconds=round(process_time, 3),
            )
            
            # Add process time header
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            
            self.logger.error(
                "HTTP request failed",
                method=request.method,
                path=request.url.path,
                error=str(e),
                process_time_seconds=round(process_time, 3),
                exc_info=True,
            )
            raise


# Error tracking for production
class ErrorTracker:
    """
    Error tracking and alerting for production environments
    """
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = get_logger(f"{service_name}.errors")
        self.error_counts = {}
    
    def track_error(self, error: Exception, context: Dict[str, Any] = None):
        """
        Track and log an error with context
        
        Args:
            error: The exception that occurred
            context: Additional context information
        """
        error_type = type(error).__name__
        
        # Increment error count
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Log error with context
        self.logger.error(
            "Error occurred",
            error_type=error_type,
            error_message=str(error),
            error_count=self.error_counts[error_type],
            service=self.service_name,
            context=context or {},
            exc_info=True,
        )
        
        # Alert if error rate is high
        if self.error_counts[error_type] > 10:  # Configurable threshold
            self.logger.critical(
                "High error rate detected",
                error_type=error_type,
                count=self.error_counts[error_type],
                service=self.service_name,
            )
    
    def get_error_summary(self) -> Dict[str, int]:
        """Get summary of error counts"""
        return self.error_counts.copy()


# Usage example:
if __name__ == "__main__":
    # Configure logging for a service
    configure_logging(
        service_name="example-service",
        log_level="DEBUG",
        log_file="/var/log/mindbot/example.log",
        enable_json=True
    )
    
    # Get logger and test
    logger = get_logger("example")
    logger.info("This is a test log message", user_id=123, action="test")
    logger.warning("This is a warning", details={"key": "value"})
    
    # Test error tracker
    error_tracker = ErrorTracker("example-service")
    try:
        raise ValueError("Test error")
    except Exception as e:
        error_tracker.track_error(e, {"user_id": 123, "operation": "test"})