"""
Facebook page scraper implementation using Playwright
Handles authentication and post scraping from Facebook pages with JavaScript rendering
"""

import asyncio
from typing import List, Optional
from datetime import datetime
import json
import re
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, Page

from .base_scraper import BaseScraper, Post
from .logger import log
from .exceptions import FacebookException, AuthenticationException
from .config import Config
from .utils import clean_text, extract_page_id


class FacebookScraper(BaseScraper):
    """
    Facebook page scraper using Playwright for JavaScript rendering
    Supports cookie-based authentication
    """
    
    FACEBOOK_BASE_URL = "https://www.facebook.com"
    
    def __init__(self, config: Config = None):
        """Initialize Facebook scraper"""
        super().__init__(config)
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.cookies = {}
        self.page_id = None
        
    async def _init_browser(self):
        """Initialize Playwright browser"""
        try:
            log.info("Initializing Playwright browser...")
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=self.config.HEADLESS,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
            )
            log.success("✅ Browser initialized")
        except Exception as e:
            log.error(f"Failed to initialize browser: {e}")
            raise FacebookException(f"Browser initialization failed: {e}")
    
    async def _create_page(self):
        """Create a new browser page with cookies"""
        try:
            if not self.browser:
                await self._init_browser()
            
            self.page = await self.browser.new_page()
            
            # Add cookies
            if self.cookies:
                await self.page.context.add_cookies([
                    {
                        'name': name,
                        'value': value,
                        'domain': '.facebook.com',
                        'path': '/',
                    }
                    for name, value in self.cookies.items()
                ])
                log.info(f"Added {len(self.cookies)} cookies to page")
            
            # Set user agent
            await self.page.set_extra_http_headers({
                'User-Agent': self.headers['User-Agent'],
            })
            
            log.success("✅ Page created with cookies")
        except Exception as e:
            log.error(f"Failed to create page: {e}")
            raise FacebookException(f"Page creation failed: {e}")
    
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
            log.info(f"🔐 Loaded {len(self.cookies)} cookies")
            log.success("✅ Cookie-based authentication successful!")
            return True
        
        except Exception as e:
            log.error(f"Facebook authentication failed: {e}")
            return False
    
    def scrape_posts(self, page_identifier: str, max_posts: int = None) -> List[Post]:
        """
        Scrape posts from a Facebook page (async wrapper)
        
        Args:
            page_identifier: Page URL, ID, or name
            max_posts: Maximum number of posts to scrape
            
        Returns:
            List of Post objects
        """
        if not max_posts:
            max_posts = self.config.MAX_POSTS
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self._async_scrape_posts(page_identifier, max_posts)
        )
    
    async def _async_scrape_posts(self, page_identifier: str, max_posts: int) -> List[Post]:
        """Async method to scrape posts from a Facebook page"""
        try:
            log.info(f"Starting to scrape Facebook page: {page_identifier}")
            
            self.page_id = extract_page_id(page_identifier)
            if not self.page_id:
                raise FacebookException(f"Could not extract page ID from: {page_identifier}")
            
            log.info(f"Extracted page ID: {self.page_id}")
            
            # Create browser page
            await self._create_page()
            
            # Scrape posts
            posts = await self._scrape_posts_with_playwright(max_posts)
            
            # Sort chronologically (oldest first)
            self.sort_posts_chronological(reverse=False)
            
            log.success(f"Successfully scraped {len(posts)} posts")
            return self.posts
        
        except Exception as e:
            log.error(f"Failed to scrape Facebook page: {e}")
            raise FacebookException(f"Scraping failed: {e}")
        finally:
            await self._cleanup()
    
    async def _scrape_posts_with_playwright(self, max_posts: int) -> List[Post]:
        """Scrape posts using Playwright with JavaScript rendering"""
        posts = []
        
        try:
            page_url = f"{self.FACEBOOK_BASE_URL}/{self.page_id}"
            log.info(f"Navigating to: {page_url}")
            
            # Navigate to page
            await self.page.goto(page_url, wait_until='networkidle', timeout=60000)
            log.success("✅ Page loaded")
            
            # Wait for posts to load
            try:
                await self.page.wait_for_selector('[role="article"]', timeout=10000)
                log.info("Posts container found")
            except:
                log.warning("Posts container not immediately found, continuing anyway")
            
            # Scroll to load more posts
            log.info("Scrolling to load more posts...")
            for scroll_count in range(min(8, max(1, max_posts // 10))):
                await self.page.evaluate('window.scrollBy(0, window.innerHeight)')
                await self.page.wait_for_timeout(2000)
                log.debug(f"Scroll #{scroll_count + 1}")
            
            # Get page content
            content = await self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find all post containers
            post_elements = soup.find_all('div', {'data-ft': True})
            log.info(f"Found {len(post_elements)} potential post elements")
            
            if not post_elements:
                post_elements = soup.find_all('[role="article"]')
                log.info(f"Trying article selector: found {len(post_elements)}")
            
            # Parse posts
            for post_elem in post_elements[:max_posts]:
                try:
                    post = self._parse_post_element(post_elem)
                    if post and post.content.strip():
                        posts.append(post)
                        self.posts.append(post)
                        log.debug(f"✅ Parsed post: {post.post_id}")
                except Exception as e:
                    log.debug(f"Failed to parse post: {e}")
                    continue
            
            if not posts:
                log.warning("⚠️ No posts found. Page might be private or structure changed.")
            
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
            content_elem = element.find('p')
            content = clean_text(content_elem.get_text()) if content_elem else ""
            
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
            img_elements = element.find_all('img')
            for img in img_elements:
                src = img.get('src')
                if src and ('http' in src):
                    images.append(src)
            
            # Extract engagement metrics
            likes = self._extract_metric(element, 'like')
            comments = self._extract_metric(element, 'comment')
            shares = self._extract_metric(element, 'share')
            
            # Extract external links
            external_links = []
            link_elements = element.find_all('a', href=True)
            for link in link_elements:
                href = link.get('href', '')
                if href and href.startswith('http') and 'facebook.com' not in href:
                    external_links.append(href)
            
            # Create Post object
            post = Post(
                platform='facebook',
                post_id=str(post_id),
                author=self.page_id,
                content=content,
                timestamp=timestamp,
                images=images[:3],
                external_links=external_links[:5],
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
            element_text = element.get_text().lower()
            if metric_type in element_text:
                pattern = rf'(\d+(?:[.,]\d+)?)\s*([KMB]?)\s*{metric_type}'
                match = re.search(pattern, element_text)
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
    
    async def _cleanup(self):
        """Cleanup browser resources"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            log.info("Browser cleaned up")
        except Exception as e:
            log.warning(f"Error during cleanup: {e}")
