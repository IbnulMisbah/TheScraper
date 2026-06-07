"""
Utility functions for TheScraper
"""

import time
import random
from typing import Optional
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from fake_useragent import UserAgent
from .logger import log
from .exceptions import ScraperException

ua = UserAgent()


def get_random_user_agent() -> str:
    """Get a random user agent string"""
    try:
        return ua.random
    except Exception as e:
        log.warning(f"Failed to get random user agent: {e}")
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def add_delay(min_delay: float = 1, max_delay: float = 5) -> None:
    """
    Add random delay between requests to avoid detection
    
    Args:
        min_delay: Minimum delay in seconds
        max_delay: Maximum delay in seconds
    """
    delay = random.uniform(min_delay, max_delay)
    log.debug(f"Adding delay: {delay:.2f}s")
    time.sleep(delay)


def extract_page_id(url: str) -> Optional[str]:
    """
    Extract Facebook page ID from URL
    
    Args:
        url: Facebook page URL
        
    Returns:
        Page ID or None
    """
    try:
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        
        # Handle different URL formats
        if len(path_parts) > 0:
            potential_id = path_parts[-1]
            if potential_id.isdigit():
                return potential_id
            # If it's a username, we'll need to resolve it
            return potential_id
        
        return None
    except Exception as e:
        log.error(f"Failed to extract page ID from {url}: {e}")
        return None


def extract_twitter_handle(url: str) -> Optional[str]:
    """
    Extract Twitter handle from URL
    
    Args:
        url: Twitter profile URL
        
    Returns:
        Twitter handle or None
    """
    try:
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        
        if len(path_parts) > 0:
            handle = path_parts[-1]
            return handle.lstrip('@')
        
        return None
    except Exception as e:
        log.error(f"Failed to extract Twitter handle from {url}: {e}")
        return None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to be safe for filesystem
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename


def format_timestamp(timestamp: datetime) -> str:
    """
    Format timestamp in a readable way
    
    Args:
        timestamp: Datetime object
        
    Returns:
        Formatted timestamp string
    """
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")


def clean_text(text: str) -> str:
    """
    Clean and normalize text content
    
    Args:
        text: Raw text
        
    Returns:
        Cleaned text
    """
    # Remove extra whitespace
    text = ' '.join(text.split())
    # Remove special characters that might cause issues
    text = text.replace('\x00', '')
    return text.strip()


def truncate_text(text: str, max_length: int = 200) -> str:
    """
    Truncate text to maximum length
    
    Args:
        text: Original text
        max_length: Maximum length
        
    Returns:
        Truncated text with ellipsis
    """
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text


def validate_url(url: str) -> bool:
    """
    Validate if URL is properly formatted
    
    Args:
        url: URL string
        
    Returns:
        True if valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def is_facebook_url(url: str) -> bool:
    """Check if URL is a Facebook URL"""
    return 'facebook.com' in url or 'fb.me' in url


def is_twitter_url(url: str) -> bool:
    """Check if URL is a Twitter/X URL"""
    return 'twitter.com' in url or 'x.com' in url or 't.co' in url


def retry_on_exception(max_attempts: int = 3, backoff_factor: float = 2.0):
    """
    Decorator for retry logic
    
    Args:
        max_attempts: Maximum number of attempts
        backoff_factor: Exponential backoff factor
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            attempt = 0
            delay = 1
            
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        raise
                    
                    log.warning(
                        f"Attempt {attempt} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    delay *= backoff_factor
        
        return wrapper
    return decorator
