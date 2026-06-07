"""
Base scraper class with common functionality
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from .logger import log
from .exceptions import ScraperException, ConfigurationException
from .config import Config
from .utils import add_delay, get_random_user_agent


@dataclass
class Post:
    """Data class representing a social media post"""
    platform: str
    post_id: str
    author: str
    content: str
    timestamp: datetime
    images: List[str]
    video_url: Optional[str] = None
    external_links: List[str] = None
    likes: int = 0
    comments: int = 0
    shares: int = 0
    comment_list: List[Dict[str, str]] = None
    url: Optional[str] = None
    
    def __post_init__(self):
        if self.external_links is None:
            self.external_links = []
        if self.comment_list is None:
            self.comment_list = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert post to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class BaseScraper(ABC):
    """
    Abstract base class for all scrapers
    Provides common functionality and interface
    """
    
    def __init__(self, config: Config = None):
        """
        Initialize base scraper
        
        Args:
            config: Configuration object
        """
        self.config = config or Config
        self.session = None
        self.posts: List[Post] = []
        self.headers = {
            'User-Agent': get_random_user_agent(),
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        log.info(f"Initialized {self.__class__.__name__}")
    
    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with the platform
        
        Returns:
            True if authentication successful, False otherwise
        """
        pass
    
    @abstractmethod
    def scrape_posts(self, page_identifier: str, max_posts: int = None) -> List[Post]:
        """
        Scrape posts from a page
        
        Args:
            page_identifier: Page ID, URL, or handle
            max_posts: Maximum number of posts to scrape
            
        Returns:
            List of Post objects
        """
        pass
    
    @abstractmethod
    def get_post_details(self, post_id: str) -> Optional[Post]:
        """
        Get detailed information about a specific post
        
        Args:
            post_id: Post ID
            
        Returns:
            Post object or None
        """
        pass
    
    def sort_posts_chronological(self, reverse: bool = False) -> List[Post]:
        """
        Sort posts chronologically
        
        Args:
            reverse: If True, sort newest first; if False, sort oldest first
            
        Returns:
            Sorted list of posts
        """
        self.posts.sort(
            key=lambda x: x.timestamp,
            reverse=reverse
        )
        log.info(f"Sorted {len(self.posts)} posts chronologically")
        return self.posts
    
    def filter_posts_by_date(self, start_date: datetime, end_date: datetime) -> List[Post]:
        """
        Filter posts by date range
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            Filtered list of posts
        """
        filtered = [
            post for post in self.posts
            if start_date <= post.timestamp <= end_date
        ]
        log.info(f"Filtered to {len(filtered)} posts within date range")
        return filtered
    
    def add_delay_between_requests(self) -> None:
        """Add delay between requests to avoid rate limiting"""
        add_delay(
            min_delay=self.config.RATE_LIMIT_DELAY * 0.5,
            max_delay=self.config.RATE_LIMIT_DELAY * 2
        )
    
    def update_headers(self) -> None:
        """Update headers with fresh user agent"""
        self.headers['User-Agent'] = get_random_user_agent()
    
    def close(self) -> None:
        """Close scraper session"""
        if self.session:
            self.session.close()
            log.info(f"Closed session for {self.__class__.__name__}")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
