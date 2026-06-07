"""
Custom exceptions for TheScraper
"""


class ScraperException(Exception):
    """Base exception for all scraper errors"""
    pass


class FacebookException(ScraperException):
    """Facebook-specific exceptions"""
    pass


class TwitterException(ScraperException):
    """Twitter/X-specific exceptions"""
    pass


class AuthenticationException(ScraperException):
    """Authentication-related exceptions"""
    pass


class RateLimitException(ScraperException):
    """Rate limit exceeded exception"""
    pass


class NetworkException(ScraperException):
    """Network connectivity exceptions"""
    pass


class ParseException(ScraperException):
    """HTML parsing exceptions"""
    pass


class ConfigurationException(ScraperException):
    """Configuration-related exceptions"""
    pass
