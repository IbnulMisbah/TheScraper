"""
TheScraper - Advanced Social Media Scraper
A robust tool to scrape posts from social media platforms and convert to Markdown
"""

__version__ = "1.0.0"
__author__ = "IbnulMisbah"

from .logger import setup_logger
from .exceptions import ScraperException, FacebookException, TwitterException

__all__ = [
    "setup_logger",
    "ScraperException",
    "FacebookException",
    "TwitterException",
]
