"""
Logging configuration for all pipelines.
Supports file, console, and structured logging.
"""

import logging
import logging.handlers
import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """
    Format logs as JSON for better parsing and analysis.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add custom fields if present
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
        
        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """
    Format logs with colors for console output.
    """
    
    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[35m",   # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        color = self.COLORS.get(record.levelname, "")
        reset = self.RESET
        
        record.levelname = f"{color}{record.levelname}{reset}"
        return super().format(record)


def setup_logging(
    name: str,
    level: str = "INFO",
    log_file: Optional[str] = None,
    log_dir: str = "logs",
    json_format: bool = False,
    console_output: bool = True,
) -> logging.Logger:
    """
    Set up logging for a module.
    
    Args:
        name: Logger name (typically __name__)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        log_dir: Directory for log files
        json_format: Use JSON format instead of text
        console_output: Include console handler
    
    Returns:
        Configured logger instance
    
    Example:
        logger = setup_logging(__name__, level="INFO")
        logger.info("Application started")
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Avoid adding duplicate handlers
    if logger.handlers:
        return logger
    
    # Create log directory if needed
    if log_file:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        
        if json_format:
            formatter = JSONFormatter()
        else:
            formatter = ColoredFormatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        log_path = Path(log_dir) / log_file
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=10485760,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(getattr(logging, level.upper()))
        
        if json_format:
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def log_with_data(
    logger: logging.Logger,
    level: str,
    message: str,
    **extra_data
) -> None:
    """
    Log message with additional structured data.
    
    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **extra_data: Additional fields to include in log
    
    Example:
        log_with_data(logger, "info", "Processing document",
                     document_id="doc123", pages=5, confidence=0.87)
    """
    log_level = getattr(logging, level.upper())
    record = logging.LogRecord(
        name=logger.name,
        level=log_level,
        pathname="",
        lineno=0,
        msg=message,
        args=(),
        exc_info=None
    )
    record.extra_data = extra_data
    logger.handle(record)


class LogContext:
    """
    Context manager for adding context to logs.
    
    Example:
        with LogContext(logger, operation="transcribe"):
            # All logs in this block include operation="transcribe"
            logger.info("Processing audio file")
    """
    
    def __init__(self, logger: logging.Logger, **context_data):
        self.logger = logger
        self.context_data = context_data
        self.old_filters = []
    
    def __enter__(self):
        """Add context filter."""
        class ContextFilter(logging.Filter):
            def __init__(self, context):
                self.context = context
            
            def filter(self, record):
                for key, value in self.context.items():
                    setattr(record, key, value)
                return True
        
        filter_obj = ContextFilter(self.context_data)
        for handler in self.logger.handlers:
            self.old_filters.append((handler, handler.filters.copy() if hasattr(handler, 'filters') else []))
            handler.addFilter(filter_obj)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Remove context filter."""
        pass


# Module-level convenience functions
def get_logger(name: str) -> logging.Logger:
    """Get or create logger for a module."""
    return logging.getLogger(name)


# Default configuration for pipelines
def configure_pipeline_logging(
    pipeline_name: str,
    level: str = "INFO",
    json_logs: bool = False
) -> logging.Logger:
    """
    Configure logging for a pipeline module.
    
    Args:
        pipeline_name: Name of pipeline (audio_pipeline, ocr_pipeline, etc.)
        level: Logging level
        json_logs: Use JSON format
    
    Returns:
        Configured logger
    """
    log_file = f"{pipeline_name}.log"
    return setup_logging(
        name=f"careficient.{pipeline_name}",
        level=level,
        log_file=log_file,
        json_format=json_logs,
        console_output=True
    )
