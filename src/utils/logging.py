"""
Centralized logging configuration for the Discord bot.
Provides consistent logging across all modules.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

def setup_logger(
    name: str = "discord_bot",
    level: str = "INFO",
    log_file: Optional[str] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Set up a logger with consistent formatting.
    
    Args:
        name: Logger name (default: "discord_bot")
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for file logging
        format_string: Optional custom format string
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Default format
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    formatter = logging.Formatter(format_string)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    
    # If logger has no handlers, configure it with defaults
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Use the same format as the main logger
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        formatter = logging.Formatter(format_string)
        
        # Add console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Add file handler to the main log file
        log_file = "logs/discord_bot.log"
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

# Create default logger for the bot
bot_logger = setup_logger(
    name="discord_bot",
    level="INFO",
    log_file="logs/discord_bot.log"
)

# Log level shortcuts
def debug(msg: str, *args, **kwargs):
    """Log a debug message."""
    bot_logger.debug(msg, *args, **kwargs)

def info(msg: str, *args, **kwargs):
    """Log an info message."""
    bot_logger.info(msg, *args, **kwargs)

def warning(msg: str, *args, **kwargs):
    """Log a warning message."""
    bot_logger.warning(msg, *args, **kwargs)

def error(msg: str, *args, **kwargs):
    """Log an error message."""
    bot_logger.error(msg, *args, **kwargs)

def critical(msg: str, *args, **kwargs):
    """Log a critical message."""
    bot_logger.critical(msg, *args, **kwargs)