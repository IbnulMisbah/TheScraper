"""
Twitter/X scraper implementation
Uses Twitter API v2 for reliable scraping
"""

import tweepy
from typing import List, Optional
from datetime import datetime, timedelta
from .base_scraper import BaseScraper, Post
from .logger import log
from .exceptions import TwitterException, AuthenticationException
from .config import Config
from .utils import extract_twitter_handle, clean_text


class TwitterScraper(BaseScraper):
    """
    Twitter/X scraper using official Twitter API v2
    Requires bearer token or API credentials
    """
    
    def __init__(self, config: Config = None):
        """Initialize Twitter scraper"""
        super().__init__(config)
        self.client = None
        self.user_id = None
        
    def authenticate(self) -> bool:
        """
        Authenticate with Twitter API v2
        
        Returns:
            True if authentication successful, False otherwise
        """
        log.info("Starting Twitter API authentication...")
        
        try:
            if self.config.TWITTER_BEARER_TOKEN:
                log.info("Using Bearer Token authentication")
                self.client = tweepy.Client(
                    bearer_token=self.config.TWITTER_BEARER_TOKEN,
                    wait_on_rate_limit=True
                )
            
            elif (self.config.TWITTER_API_KEY and 
                  self.config.TWITTER_API_SECRET and
                  self.config.TWITTER_ACCESS_TOKEN and
                  self.config.TWITTER_ACCESS_SECRET):
                log.info("Using OAuth 1.0a User Context authentication")
                self.client = tweepy.Client(
                    consumer_key=self.config.TWITTER_API_KEY,
                    consumer_secret=self.config.TWITTER_API_SECRET,
                    access_token=self.config.TWITTER_ACCESS_TOKEN,
                    access_token_secret=self.config.TWITTER_ACCESS_SECRET,
                    wait_on_rate_limit=True
                )
            
            else:
                raise AuthenticationException(
                    "No Twitter credentials provided. "
                    "Set TWITTER_BEARER_TOKEN or Twitter API credentials"
                )
            
            # Verify authentication
            user = self.client.get_me()
            log.success(f"Twitter authentication successful. User: @{user.data.username}")
            return True
        
        except Exception as e:
            log.error(f"Twitter authentication failed: {e}")
            return False
    
    def scrape_posts(self, page_identifier: str, max_posts: int = None) -> List[Post]:
        """
        Scrape posts from a Twitter account
        
        Args:
            page_identifier: Twitter handle or URL
            max_posts: Maximum number of posts to scrape
            
        Returns:
            List of Post objects
        """
        if not max_posts:
            max_posts = self.config.MAX_POSTS
        
        try:
            # Extract handle
            if page_identifier.startswith('http'):
                handle = extract_twitter_handle(page_identifier)
            else:
                handle = page_identifier.lstrip('@')
            
            log.info(f"Starting to scrape Twitter account: @{handle}")
            
            # Get user info
            user = self.client.get_user(username=handle)
            if not user.data:
                raise TwitterException(f"User @{handle} not found")
            
            user_id = user.data.id
            log.info(f"Found user {user.data.name} (ID: {user_id})")
            
            # Fetch tweets
            tweets = self.client.get_users_tweets(
                id=user_id,
                max_results=min(100, max_posts),
                tweet_fields=['created_at', 'public_metrics', 'author_id'],
                expansions=['author_id'],
                user_fields=['username']
            )
            
            if not tweets.data:
                log.warning(f"No tweets found for @{handle}")
                return []
            
            # Parse tweets
            for tweet in tweets.data:
                try:
                    post = self._parse_tweet(tweet, user.data.username)
                    self.posts.append(post)
                except Exception as e:
                    log.warning(f"Failed to parse tweet {tweet.id}: {e}")
                    continue
            
            # Sort chronologically (oldest first)
            self.sort_posts_chronological(reverse=False)
            
            log.success(f"Successfully scraped {len(self.posts)} tweets")
            return self.posts
        
        except Exception as e:
            log.error(f"Failed to scrape Twitter account: {e}")
            raise TwitterException(f"Scraping failed: {e}")
    
    def _parse_tweet(self, tweet, username: str) -> Post:
        """
        Parse a tweet into Post object
        
        Args:
            tweet: Tweepy Tweet object
            username: Username of tweet author
            
        Returns:
            Post object
        """
        try:
            # Extract metrics
            metrics = tweet.public_metrics
            
            # Extract URLs from text
            external_links = []
            if tweet.entities and 'urls' in tweet.entities:
                for url_obj in tweet.entities['urls']:
                    external_links.append(url_obj['expanded_url'])
            
            # Extract images/media
            images = []
            if tweet.entities and 'media' in tweet.entities:
                for media in tweet.entities['media']:
                    if media['type'] in ['photo', 'video']:
                        images.append(media.get('url', ''))
            
            post = Post(
                platform='twitter',
                post_id=str(tweet.id),
                author=username,
                content=clean_text(tweet.text),
                timestamp=tweet.created_at,
                images=images,
                external_links=external_links,
                likes=metrics['like_count'],
                comments=metrics['reply_count'],
                shares=metrics['retweet_count'],
                url=f"https://twitter.com/{username}/status/{tweet.id}"
            )
            
            return post
        
        except Exception as e:
            log.error(f"Error parsing tweet: {e}")
            raise
    
    def get_post_details(self, post_id: str) -> Optional[Post]:
        """
        Get detailed information about a specific tweet
        
        Args:
            post_id: Tweet ID
            
        Returns:
            Post object or None
        """
        # Find post in existing posts
        for post in self.posts:
            if post.post_id == post_id:
                return post
        
        log.warning(f"Tweet {post_id} not found in scraped posts")
        return None
