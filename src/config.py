"""
Configuration management for TheScraper
"""

import os
from dotenv import load_dotenv
from pathlib import Path
from typing import Optional
import json

# Load environment variables
load_dotenv()


class Config:
    """Configuration class for TheScraper"""
    
    # Facebook Configuration
    FACEBOOK_EMAIL: Optional[str] = os.getenv("FACEBOOK_EMAIL")
    FACEBOOK_PASSWORD: Optional[str] = os.getenv("FACEBOOK_PASSWORD")
    FACEBOOK_COOKIES: Optional[dict] = None
    
    # Twitter/X Configuration
    TWITTER_BEARER_TOKEN: Optional[str] = os.getenv("TWITTER_BEARER_TOKEN")
    TWITTER_API_KEY: Optional[str] = os.getenv("TWITTER_API_KEY")
    TWITTER_API_SECRET: Optional[str] = os.getenv("TWITTER_API_SECRET")
    
    # URLs to scrape
    TARGET_PAGE_URL: Optional[str] = os.getenv("TARGET_PAGE_URL")
    TARGET_HANDLE: Optional[str] = os.getenv("TARGET_HANDLE")
    
    # Output Configuration
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "./output")
    OUTPUT_FORMAT: str = os.getenv("OUTPUT_FORMAT", "markdown")
    
    # Scraping Configuration
    MAX_POSTS: int = int(os.getenv("MAX_POSTS", "100"))
    TIMEOUT_SECONDS: int = int(os.getenv("TIMEOUT_SECONDS", "30"))
    RETRY_ATTEMPTS: int = int(os.getenv("RETRY_ATTEMPTS", "3"))
    RATE_LIMIT_DELAY: float = float(os.getenv("RATE_LIMIT_DELAY", "2"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Browser Configuration
    HEADLESS: bool = os.getenv("HEADLESS", "True").lower() == "true"
    USER_AGENTS: list = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    ]

    
    @classmethod
    def load_facebook_cookies(cls, cookies_json_path: Optional[str] = None):
        """Load Facebook cookies from JSON file or environment variable"""
        try:
            cookies_str = os.getenv("FACEBOOK_COOKIES_JSON", "").strip()
            
            if cookies_json_path and Path(cookies_json_path).exists():
                with open(cookies_json_path, 'r') as f:
                    cls.FACEBOOK_COOKIES = json.load(f)
                    print(f"✅ Loaded cookies from file: {cookies_json_path}")
            elif cookies_str:
                log.info(f"Found FACEBOOK_COOKIES_JSON in environment")
                cls.FACEBOOK_COOKIES = json.loads(cookies_str)
                log.success(f"✅ Loaded cookies with keys: {list(cls.FACEBOOK_COOKIES.keys())}")
            else:
                log.warning("❌ No Facebook cookies found in environment or file")
        except json.JSONDecodeError as e:
            log.error(f"❌ Invalid JSON in FACEBOOK_COOKIES_JSON: {e}")
            log.info("Make sure your JSON is valid. Example: {\"c_user\":\"123\",\"xs\":\"abc\"}")
        except Exception as e:
            log.error(f"❌ Error loading cookies: {e}")
            
    # @classmethod
    # def load_facebook_cookies(cls, cookies_json_path: Optional[str] = None):
    #     """Load Facebook cookies from JSON file or environment variable"""
    #     cookies_str = os.getenv("FACEBOOK_COOKIES_JSON")
        
    #     if cookies_json_path and Path(cookies_json_path).exists():
    #         with open(cookies_json_path, 'r') as f:
    #             cls.FACEBOOK_COOKIES = json.load(f)
    #     elif cookies_str:
    #         cls.FACEBOOK_COOKIES = json.loads(cookies_str)
    
    @classmethod
    def create_output_dir(cls):
        """Create output directory if it doesn't exist"""
        Path(cls.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        Path("logs").mkdir(parents=True, exist_ok=True)


# Initialize configuration
Config.create_output_dir()
