"""
Facebook page scraper implementation
Handles authentication and post scraping from Facebook pages
"""

import requests
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .base_scraper import BaseScraper, Post
from .logger import log
from .exceptions import FacebookException, AuthenticationException
from .config import Config
from .utils import add_delay, clean_text, extract_page_id, sanitize_filename


class FacebookScraper(BaseScraper):
    """
    Facebook page scraper using Selenium and requests
    Supports both cookie-based and credential-based authentication
    """
    
    FACEBOOK_BASE_URL = "https://www.facebook.com"
    FACEBOOK_GRAPH_URL = "https://graph.facebook.com"
    
    def __init__(self, config: Config = None):
        """Initialize Facebook scraper"""
        super().__init__(config)
        self.driver = None
        self.cookies = {}
        self.access_token = None
        self.page_id = None
        
    def authenticate(self) -> bool:
        """
        Authenticate with Facebook using cookies or credentials
        
        Returns:
            True if authentication successful, False otherwise
        """
        log.info("Starting Facebook authentication...")
        
        try:
            # Try loading cookies first
            if self.config.FACEBOOK_COOKIES:
                log.info("Attempting cookie-based authentication")
                return self._authenticate_with_cookies()
            
            # Fall back to credential-based authentication
            elif self.config.FACEBOOK_EMAIL and self.config.FACEBOOK_PASSWORD:
                log.info("Attempting credential-based authentication")
                return self._authenticate_with_credentials()
            
            else:
                raise AuthenticationException(
                    "No Facebook credentials or cookies provided. "
                    "Set FACEBOOK_EMAIL/PASSWORD or FACEBOOK_COOKIES_JSON"
                )
        
        except Exception as e:
            log.error(f"Facebook authentication failed: {e}")
            return False
    
    def _authenticate_with_cookies(self) -> bool:
        """
        Authenticate using saved cookies
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.cookies = self.config.FACEBOOK_COOKIES
            
            # Verify cookies by making a test request
            headers = self.headers.copy()
            response = requests.get(
                f"{self.FACEBOOK_BASE_URL}/me",
                headers=headers,
                cookies=self.cookies,
                timeout=self.config.TIMEOUT_SECONDS
            )
            
            if response.status_code == 200:
                log.success("Cookie-based authentication successful")
                return True
            else:
                log.warning("Cookies appear to be invalid or expired")
                return False
        
        except Exception as e:
            log.error(f"Cookie authentication failed: {e}")
            return False
    
    def _authenticate_with_credentials(self) -> bool:
        """
        Authenticate using email and password with Selenium
        
        Returns:
            True if successful, False otherwise
        """
        try:
            log.info("Launching Selenium browser for login...")
            
            # Setup Chrome options
            options = webdriver.ChromeOptions()
            if self.config.HEADLESS:
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument(f"user-agent={self.headers['User-Agent']}")
            
            # Initialize driver
            self.driver = webdriver.Chrome(options=options)
            
            # Navigate to Facebook
            log.info("Navigating to Facebook login page...")
            self.driver.get(f"{self.FACEBOOK_BASE_URL}/login")
            
            # Wait for and fill email field
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "email"))
            )
            email_field.send_keys(self.config.FACEBOOK_EMAIL)
            log.debug("Email field filled")
            
            # Fill password field
            password_field = self.driver.find_element(By.ID, "pass")
            password_field.send_keys(self.config.FACEBOOK_PASSWORD)
            log.debug("Password field filled")
            
            # Click login button
            login_button = self.driver.find_element(By.NAME, "login")
            login_button.click()
            log.info("Login button clicked, waiting for page load...")
            
            # Wait for successful login
            WebDriverWait(self.driver, 15).until(
                lambda driver: driver.current_url != f"{self.FACEBOOK_BASE_URL}/login"
            )
            
            # Extract cookies
            self.cookies = {cookie['name']: cookie['value'] 
                          for cookie in self.driver.get_cookies()}
            
            log.success(f"Successfully logged in. Extracted {len(self.cookies)} cookies")
            return True
        
        except TimeoutException as e:
            log.error(f"Login timeout: {e}")
            return False
        except Exception as e:
            log.error(f"Login failed: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()
    
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
            
            # Fetch posts using requests + BeautifulSoup
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
        Scrape posts using requests library (more reliable than Selenium)
        
        Args:
            max_posts: Maximum posts to scrape
            
        Returns:
            List of Post objects
        """
        posts = []
        url = f"{self.FACEBOOK_BASE_URL}/{self.page_id}/posts"
        
        try:
            headers = self.headers.copy()
            
            # Fetch page
            log.info(f"Fetching posts from: {url}")
            response = requests.get(
                url,
                headers=headers,
                cookies=self.cookies,
                timeout=self.config.TIMEOUT_SECONDS
            )
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all post containers
            post_elements = soup.find_all('div', {'data-ft': True})
            
            for post_elem in post_elements[:max_posts]:
                try:
                    post = self._parse_post_element(post_elem)
                    if post:
                        posts.append(post)
                        self.posts.append(post)
                        log.debug(f"Parsed post: {post.post_id}")
                except Exception as e:
                    log.warning(f"Failed to parse post element: {e}")
                    continue
                
                # Add delay to avoid detection
                self.add_delay_between_requests()
            
            return posts
        
        except requests.exceptions.RequestException as e:
            log.error(f"Request failed: {e}")
            raise FacebookException(f"Failed to fetch posts: {e}")
    
    def _parse_post_element(self, element) -> Optional[Post]:
        """
        Parse a post element from Facebook
        
        Args:
            element: BeautifulSoup element containing post
            
        Returns:
            Post object or None
        """
        try:
            # Extract post ID
            post_id_str = element.get('data-ft', '{}')
            post_data = json.loads(post_id_str)
            post_id = post_data.get('mf_story_key', 'unknown')
            
            # Extract content
            content_elem = element.find('p')
            content = clean_text(content_elem.get_text()) if content_elem else "No content"
            
            # Extract timestamp
            time_elem = element.find('a', {'data-utime': True})
            timestamp = datetime.fromtimestamp(int(time_elem['data-utime'])) if time_elem else datetime.now()
            
            # Extract images
            images = []
            img_elements = element.find_all('img', {'style': True})
            for img in img_elements:
                src = img.get('src')
                if src and 'http' in src:
                    images.append(src)
            
            # Extract engagement metrics
            likes = self._extract_metric(element, 'Like')
            comments = self._extract_metric(element, 'Comment')
            shares = self._extract_metric(element, 'Share')
            
            # Extract external links
            external_links = []
            link_elements = element.find_all('a', href=True)
            for link in link_elements:
                href = link['href']
                if href and href.startswith('http'):
                    external_links.append(href)
            
            # Create Post object
            post = Post(
                platform='facebook',
                post_id=post_id,
                author=self.page_id,
                content=content,
                timestamp=timestamp,
                images=images,
                external_links=external_links,
                likes=likes,
                comments=comments,
                shares=shares,
                url=f"{self.FACEBOOK_BASE_URL}/{self.page_id}/posts/{post_id}"
            )
            
            return post
        
        except Exception as e:
            log.warning(f"Error parsing post element: {e}")
            return None
    
    def _extract_metric(self, element, metric_name: str) -> int:
        """Extract engagement metric (likes, comments, shares)"""
        try:
            metric_elem = element.find('span', string=lambda x: metric_name in x if x else False)
            if metric_elem:
                text = metric_elem.get_text()
                # Extract number from text like "1.2K likes"
                number_str = text.split()[0].replace('K', '000').replace('M', '000000')
                return int(float(number_str))
        except:
            pass
        return 0
    
    def get_post_details(self, post_id: str) -> Optional[Post]:
        """
        Get detailed information about a specific post
        
        Args:
            post_id: Post ID
            
        Returns:
            Post object or None
        """
        # Find post in existing posts
        for post in self.posts:
            if post.post_id == post_id:
                return post
        
        log.warning(f"Post {post_id} not found in scraped posts")
        return None
    
    def export_cookies_to_json(self, filepath: str) -> None:
        """
        Export cookies to JSON file for reuse
        
        Args:
            filepath: Path to save cookies JSON
        """
        try:
            with open(filepath, 'w') as f:
                json.dump(self.cookies, f, indent=2)
            log.success(f"Cookies exported to {filepath}")
        except Exception as e:
            log.error(f"Failed to export cookies: {e}")
