"""
Logging module for CRISK CLI.
Logs to ~/.crisk/crisk.log for debugging.
"""

import logging
import os
from pathlib import Path
from datetime import datetime

# Config directory
CRISK_DIR = Path.home() / ".crisk"
LOG_FILE = CRISK_DIR / "crisk.log"


def setup_logger() -> logging.Logger:
    """Set up and return the CRISK logger."""
    # Ensure directory exists
    CRISK_DIR.mkdir(exist_ok=True)

    # Create logger
    logger = logging.getLogger("crisk")
    logger.setLevel(logging.DEBUG)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    # File handler - detailed logs
    file_handler = logging.FileHandler(LOG_FILE, mode='a')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger


# Global logger instance
logger = setup_logger()


def log_separator():
    """Log a separator for new sessions."""
    logger.info("=" * 60)
    logger.info(f"CRISK Session Started")
    logger.info("=" * 60)


def log_request(method: str, url: str, headers: dict = None, payload_size: int = None):
    """Log an outgoing HTTP request."""
    logger.info(f"REQUEST: {method} {url}")
    if headers:
        # Redact authorization header
        safe_headers = {k: (v[:20] + '...' if k.lower() == 'authorization' else v) for k, v in headers.items()}
        logger.debug(f"  Headers: {safe_headers}")
    if payload_size:
        logger.debug(f"  Payload size: {payload_size} bytes")


def log_response(status_code: int, response_text: str = None, error: str = None):
    """Log an HTTP response."""
    if error:
        logger.error(f"RESPONSE: Error - {error}")
    else:
        logger.info(f"RESPONSE: {status_code}")
        if response_text and len(response_text) < 500:
            logger.debug(f"  Body: {response_text}")
        elif response_text:
            logger.debug(f"  Body (truncated): {response_text[:500]}...")


def log_cache(action: str, key: str, hit: bool = None):
    """Log cache operations."""
    if hit is not None:
        status = "HIT" if hit else "MISS"
        logger.info(f"CACHE {status}: {action} - {key}")
    else:
        logger.info(f"CACHE: {action} - {key}")


def log_error(message: str, exception: Exception = None):
    """Log an error."""
    logger.error(f"ERROR: {message}")
    if exception:
        logger.exception(f"  Exception: {exception}")


def log_info(message: str):
    """Log an info message."""
    logger.info(message)


def log_debug(message: str):
    """Log a debug message."""
    logger.debug(message)
