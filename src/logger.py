"""
Logging configuration for TheScraper
"""

import sys
from loguru import logger

def setup_logger(level: str = "INFO"):
    """
    Configure loguru logger with custom format
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    
    # Remove default handler
    logger.remove()
    
    # Add custom handler with format
    logger.add(
        sys.stdout,
        format="<level>{time:YYYY-MM-DD HH:mm:ss}</level> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=level,
        colorize=True,
    )
    
    # Add file handler
    logger.add(
        "logs/thescraper.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=level,
        rotation="500 MB",
        retention="7 days",
    )
    
    return logger

# Initialize logger
log = setup_logger()
