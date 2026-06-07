"""
Facebook page scraper implementation using Requests + BeautifulSoup
Simple and reliable scraping without browser dependencies
"""

from typing import List, Optional
from datetime import datetime
import json
import re
import requests
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, Post
from .logger import log
from .exceptions import FacebookException, AuthenticationException
from .config import Config
from .utils import clean_text, extract_page_id, add_delay


class FacebookScraper(BaseScraper):
    """
    Facebook page scraper using Requests library
    Supports cookie-based authentication
    """
    
    FACEBOOK_BASE_URL = "https://www.facebook.com"
    
    def __init__(self, config: Config = None):
        """Initialize Facebook scraper"""
        super().__init__(config)
        self.cookies = {}
        self.page_id = None
        self.session = requests.Session()
        
    def authenticate(self) -> bool:
        """Authenticate with Facebook using cookies"""
        log.info("Starting Facebook authentication...")
        
        try:
            # Load cookies from env
            self.config.load_facebook_cookies()
            
            if not self.config.FACEBOOK_COOKIES:
                raise AuthenticationException(
                    "❌ No Facebook cookies provided.\n"
                    "Please set FACEBOOK_COOKIES_JSON in GitHub Secrets"
                )
            
            self.cookies = self.config.FACEBOOK_COOKIES
            self.session.cookies.update(self.cookies)
            
            log.info(f"🔐 Loaded {len(self.cookies)} cookies")
            log.success("✅ Cookie-based authentication successful!")
            return True
        
        except Exception as e:
            log.error(f"Facebook authentication failed: {e}")
            return False
    
    def scrape_posts(self, page_identifier: str, max_posts: int = None) -> List[Post]:
        """
        Scrape posts from a Facebook page
        
        Args:
            page_identifier: Page URL, ID, or name
            max_posts: Maximum number of posts to scrape
            
        Returns:
            List of Post objects
        """
        if not max_posts:
            max_posts = self.config.MAX_POSTS
        
        try:
            log.info(f"Starting to scrape Facebook page: {page_identifier}")
            
            self.page_id = extract_page_id(page_identifier)
            if not self.page_id:
                raise FacebookException(f"Could not extract page ID from: {page_identifier}")
            
            log.info(f"Extracted page ID: {self.page_id}")
            
            # Scrape posts
            posts = self._scrape_posts_with_requests(max_posts)
            
            # Sort chronologically (oldest first)
            self.sort_posts_chronological(reverse=False)
            
            log.success(f"Successfully scraped {len(posts)} posts")
            return self.posts
        
        except Exception as e:
            log.error(f"Failed to scrape Facebook page: {e}")
            raise FacebookException(f"Scraping failed: {e}")
    
    def _scrape_posts_with_requests(self, max_posts: int) -> List[Post]:
        """
        Scrape posts using requests library
        
        Args:
            max_posts: Maximum posts to scrape
            
        Returns:
            List of Post objects
        """
        posts = []
        
        try:
            urls = [
                f"{self.FACEBOOK_BASE_URL}/{self.page_id}",
                f"{self.FACEBOOK_BASE_URL}/{self.page_id}/posts",
            ]
            
            for url in urls:
                try:
                    log.info(f"Attempting to fetch: {url}")
                    
                    response = self.session.get(
                        url,
                        headers=self.headers,
                        cookies=self.cookies,
                        timeout=self.config.TIMEOUT_SECONDS,
                        allow_redirects=True
                    )
                    
                    if response.status_code == 200:
                        log.success(f"✅ Successfully fetched page")
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Find all post containers
                        post_elements = soup.find_all('div', {'data-ft': True})
                        
                        if post_elements:
                            log.info(f"Found {len(post_elements)} potential posts")
                            
                            for post_elem in post_elements[:max_posts]:
                                try:
                                    post = self._parse_post_element(post_elem)
                                    if post and post.content.strip():
                                        posts.append(post)
                                        self.posts.append(post)
                                        log.debug(f"✅ Parsed post")
                                except Exception as e:
                                    log.debug(f"Failed to parse post: {e}")
                                    continue
                                
                                add_delay(min_delay=1, max_delay=3)
                        
                        if posts:
                            break
                
                except Exception as e:
                    log.warning(f"Failed with URL {url}: {e}")
                    continue
            
            if not posts:
                log.warning("⚠️ No posts found. Page might be private.")
            
            return posts
        
        except Exception as e:
            log.error(f"Scraping failed: {e}")
            raise FacebookException(f"Failed to scrape posts: {e}")
    
    def _parse_post_element(self, element) -> Optional[Post]:
        """Parse a post element from Facebook"""
        try:
            # Extract post ID
            post_id_str = element.get('data-ft', '{}')
            try:
                post_data = json.loads(post_id_str)
                post_id = post_data.get('mf_story_key', f'post_{id(element)}')
            except:
                post_id = f'post_{id(element)}'
            
            # Extract content
            text_parts = []
            for p in element.find_all('p'):
                text = p.get_text(strip=True)
                if text:
                    text_parts.append(text)
            
            content = ' '.join(text_parts)
            if not content:
                # Try alternative method
                for div in element.find_all('div', class_=True):
                    text = div.get_text(strip=True)
                    if text and len(text) > 10:
                        content = text[:500]
                        break
            
            if not content:
                return None
            
            content = clean_text(content)
            
            # Extract timestamp
            time_elem = element.find('a', {'data-utime': True})
            if time_elem and time_elem.get('data-utime'):
                try:
                    timestamp = datetime.fromtimestamp(int(time_elem['data-utime']))
                except:
                    timestamp = datetime.now()
            else:
                timestamp = datetime.now()
            
            # Extract images
            images = []
            for img in element.find_all('img'):
                src = img.get('src')
                if src and 'http' in src:
                    images.append(src)
            
            # Extract engagement metrics
            likes = self._extract_metric(element, 'like')
            comments = self._extract_metric(element, 'comment')
            shares = self._extract_metric(element, 'share')
            
            # Create Post object
            post = Post(
                platform='facebook',
                post_id=str(post_id),
                author=self.page_id,
                content=content,
                timestamp=timestamp,
                images=images[:3],
                likes=likes,
                comments=comments,
                shares=shares,
                url=f"{self.FACEBOOK_BASE_URL}/{self.page_id}"
            )
            
            return post
        
        except Exception as e:
            log.debug(f"Error parsing post: {e}")
            return None
    
    def _extract_metric(self, element, metric_type: str) -> int:
        """Extract engagement metric"""
        try:
            text = element.get_text().lower()
            pattern = rf'(\d+(?:[.,]\d+)?)\s*([KMB]?)\s*{metric_type}'
            match = re.search(pattern, text)
            
            if match:
                number = float(match.group(1).replace(',', '.'))
                suffix = match.group(2)
                
                if suffix == 'K':
                    return int(number * 1000)
                elif suffix == 'M':
                    return int(number * 1000000)
                else:
                    return int(number)
        except:
            pass
        
        return 0
    
    def get_post_details(self, post_id: str) -> Optional[Post]:
        """Get detailed information about a specific post"""
        for post in self.posts:
            if post.post_id == post_id:
                return post
        return None
    
    def close(self):
        """Close session"""
        if self.session:
            self.session.close()
            log.info("Session closed")
