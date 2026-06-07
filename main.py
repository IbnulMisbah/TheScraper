#!/usr/bin/env python3
"""
TheScraper - Main entry point
Advanced Social Media Scraper with Markdown export
"""

import sys
import argparse
from typing import Optional
from pathlib import Path

from src.config import Config
from src.logger import log
from src.facebook_scraper import FacebookScraper
from src.twitter_scraper import TwitterScraper
from src.markdown_generator import MarkdownGenerator
from src.exceptions import ScraperException
from src.utils import is_facebook_url, is_twitter_url


class TheScraper:
    """Main scraper orchestrator"""
    
    def __init__(self, config: Config = None):
        """Initialize TheScraper"""
        self.config = config or Config
        self.markdown_gen = MarkdownGenerator(self.config.OUTPUT_DIR)
    
    def scrape_and_export(
        self,
        url: str,
        output_file: Optional[str] = None,
        max_posts: Optional[int] = None
    ) -> Path:
        """
        Scrape social media page and export to Markdown
        
        Args:
            url: Social media page URL
            output_file: Optional custom output filename
            max_posts: Maximum posts to scrape
            
        Returns:
            Path to generated Markdown file
        """
        try:
            log.info("=" * 60)
            log.info("TheScraper - Social Media Scraper")
            log.info("=" * 60)
            
            scraper = None
            
            # Determine platform and create appropriate scraper
            if is_facebook_url(url):
                log.info(f"Detected Facebook URL: {url}")
                scraper = FacebookScraper(self.config)
                
            elif is_twitter_url(url):
                log.info(f"Detected Twitter/X URL: {url}")
                scraper = TwitterScraper(self.config)
            
            else:
                raise ScraperException(
                    f"Unsupported URL: {url}\n"
                    "Supported platforms: Facebook, Twitter/X"
                )
            
            # Authenticate
            log.info("Authenticating with platform...")
            if not scraper.authenticate():
                raise ScraperException("Authentication failed")
            
            # Scrape posts
            log.info(f"Scraping posts (max: {max_posts or self.config.MAX_POSTS})...")
            posts = scraper.scrape_posts(url, max_posts)
            
            if not posts:
                log.warning("No posts were scraped")
                return None
            
            log.success(f"Successfully scraped {len(posts)} posts")
            
            # Generate Markdown
            log.info("Generating Markdown file...")
            markdown_path = self.markdown_gen.save_markdown(
                posts,
                filename=output_file,
                include_metadata=True,
                include_comments=True
            )
            
            # Generate summary
            summary = self.markdown_gen.generate_summary_report(posts)
            log.info(f"\n{summary}")
            
            log.info("=" * 60)
            log.success(f"Scraping completed! Output: {markdown_path}")
            log.info("=" * 60)
            
            return markdown_path
        
        except ScraperException as e:
            log.error(f"Scraper error: {e}")
            sys.exit(1)
        except Exception as e:
            log.error(f"Unexpected error: {e}")
            sys.exit(1)
        finally:
            if scraper:
                scraper.close()


def main():
    """Main CLI entry point"""
    
    parser = argparse.ArgumentParser(
        description="TheScraper - Advanced Social Media Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py https://www.facebook.com/page_name
  python main.py https://twitter.com/username --max-posts 50
  python main.py https://x.com/username -o my_tweets.md
        """
    )
    
    parser.add_argument(
        "url",
        help="Social media page URL (Facebook or Twitter/X)"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output filename (default: auto-generated)"
    )
    
    parser.add_argument(
        "-m", "--max-posts",
        type=int,
        help="Maximum number of posts to scrape"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="Path to .env configuration file"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Update log level if verbose
    if args.verbose:
        from src.logger import setup_logger
        setup_logger("DEBUG")
    
    # Load custom config if provided
    if args.config and Path(args.config).exists():
        import dotenv
        dotenv.load_dotenv(args.config)
    
    # Run scraper
    scraper = TheScraper()
    scraper.scrape_and_export(
        url=args.url,
        output_file=args.output,
        max_posts=args.max_posts
    )


if __name__ == "__main__":
    main()
