"""
Markdown file generator for scraped posts
Converts post data to well-formatted Markdown files
"""

from typing import List, Optional
from datetime import datetime
from pathlib import Path
from .base_scraper import Post
from .logger import log
from .utils import sanitize_filename, format_timestamp


class MarkdownGenerator:
    """Generate Markdown files from scraped posts"""
    
    def __init__(self, output_dir: str = "./output"):
        """
        Initialize Markdown generator
        
        Args:
            output_dir: Directory to save Markdown files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        log.info(f"Initialized MarkdownGenerator with output dir: {output_dir}")
    
    def generate_markdown(
        self,
        posts: List[Post],
        filename: Optional[str] = None,
        include_metadata: bool = True,
        include_comments: bool = True
    ) -> str:
        """
        Generate Markdown content from posts
        
        Args:
            posts: List of Post objects (should be chronologically sorted)
            filename: Optional custom filename
            include_metadata: Include post metadata (likes, comments, shares)
            include_comments: Include comment sections
            
        Returns:
            Markdown content as string
        """
        log.info(f"Generating Markdown for {len(posts)} posts")
        
        # Generate filename
        if not filename:
            platform = posts[0].platform if posts else "posts"
            author = posts[0].author if posts else "unknown"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{platform}_{sanitize_filename(author)}_{timestamp}.md"
        
        # Start building markdown
        markdown = self._build_header(posts)
        markdown += self._build_table_of_contents(posts)
        markdown += "\n\n---\n\n"
        
        # Add each post
        for idx, post in enumerate(posts, 1):
            markdown += self._build_post_section(
                post,
                idx,
                include_metadata,
                include_comments
            )
            markdown += "\n\n---\n\n"
        
        # Add footer
        markdown += self._build_footer(posts, filename)
        
        return markdown, filename
    
    def save_markdown(
        self,
        posts: List[Post],
        filename: Optional[str] = None,
        include_metadata: bool = True,
        include_comments: bool = True
    ) -> Path:
        """
        Save Markdown file
        
        Args:
            posts: List of Post objects
            filename: Optional custom filename
            include_metadata: Include post metadata
            include_comments: Include comment sections
            
        Returns:
            Path to saved file
        """
        markdown, filename = self.generate_markdown(
            posts,
            filename,
            include_metadata,
            include_comments
        )
        
        filepath = self.output_dir / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown)
            
            log.success(f"Markdown file saved: {filepath}")
            return filepath
        
        except Exception as e:
            log.error(f"Failed to save Markdown file: {e}")
            raise
    
    def _build_header(self, posts: List[Post]) -> str:
        """Build Markdown header"""
        if not posts:
            return "# Posts\n"
        
        post = posts[0]
        platform_name = post.platform.capitalize()
        author = post.author
        total_posts = len(posts)
        
        first_date = posts[0].timestamp.strftime("%Y-%m-%d")
        last_date = posts[-1].timestamp.strftime("%Y-%m-%d")
        
        header = f"""# {platform_name} Posts - {author}

**Platform:** {platform_name}  
**Author:** {author}  
**Total Posts:** {total_posts}  
**Date Range:** {first_date} to {last_date}  
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## Overview

This document contains all posts from **{author}** on **{platform_name}**, organized chronologically from oldest to newest.

**Summary Statistics:**
- Total Posts: {total_posts}
- Total Likes: {sum(p.likes for p in posts):,}
- Total Comments: {sum(p.comments for p in posts):,}
- Total Shares: {sum(p.shares for p in posts):,}

"""
        return header
    
    def _build_table_of_contents(self, posts: List[Post]) -> str:
        """Build table of contents"""
        toc = "## Table of Contents\n\n"
        
        # Group by date
        posts_by_date = {}
        for post in posts:
            date_key = post.timestamp.strftime("%Y-%m-%d")
            if date_key not in posts_by_date:
                posts_by_date[date_key] = []
            posts_by_date[date_key].append(post)
        
        # Build TOC
        for idx, (date, date_posts) in enumerate(sorted(posts_by_date.items()), 1):
            toc += f"- [{date}](#post-{idx}-{sanitize_filename(date)}) - {len(date_posts)} post(s)\n"
        
        return toc
    
    def _build_post_section(
        self,
        post: Post,
        post_number: int,
        include_metadata: bool = True,
        include_comments: bool = True
    ) -> str:
        """Build a single post section"""
        
        section = f"## Post #{post_number}\n\n"
        section += f"**Posted on:** {format_timestamp(post.timestamp)}\n\n"
        
        # Content
        section += "### Content\n\n"
        section += f"{post.content}\n\n"
        
        # Images
        if post.images:
            section += "### Media\n\n"
            for img_url in post.images:
                section += f"![Post Image]({img_url})\n\n"
        
        # Links in post
        if post.external_links:
            section += "### Links\n\n"
            for link in post.external_links:
                section += f"- [{link}]({link})\n"
            section += "\n"
        
        # Metadata
        if include_metadata:
            section += "### Engagement Metrics\n\n"
            section += f"| Metric | Count |\n"
            section += f"|--------|-------|\n"
            section += f"| ❤️ Likes | {post.likes:,} |\n"
            section += f"| 💬 Comments | {post.comments:,} |\n"
            section += f"| 🔄 Shares/Retweets | {post.shares:,} |\n"
            section += f"\n"
        
        # Post URL
        if post.url:
            section += f"**Post URL:** [{post.url}]({post.url})\n\n"
        
        # Comments
        if include_comments and post.comment_list:
            section += "### Top Comments\n\n"
            for comment in post.comment_list[:5]:  # Top 5 comments
                author = comment.get('author', 'Unknown')
                text = comment.get('text', '')
                section += f"**{author}:** {text}\n\n"
        
        return section
    
    def _build_footer(self, posts: List[Post], filename: str) -> str:
        """Build Markdown footer"""
        
        footer = f"""---

## Document Information

- **Total Posts:** {len(posts)}
- **File Name:** {filename}
- **Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

### Legend

- ❤️ **Likes:** Number of likes/reactions
- 💬 **Comments:** Number of comments
- 🔄 **Shares/Retweets:** Number of shares or retweets

### Notes

This document was automatically generated by TheScraper. Posts are listed from oldest (top) to newest (bottom).

For more information, visit: [TheScraper GitHub](https://github.com/IbnulMisbah/TheScraper)
"""
        return footer
    
    def generate_summary_report(self, posts: List[Post]) -> str:
        """
        Generate a summary report of posts
        
        Args:
            posts: List of Post objects
            
        Returns:
            Summary report as string
        """
        if not posts:
            return "No posts to summarize"
        
        # Group by date
        posts_by_date = {}
        for post in posts:
            date_key = post.timestamp.strftime("%Y-%m-%d")
            if date_key not in posts_by_date:
                posts_by_date[date_key] = []
            posts_by_date[date_key].append(post)
        
        # Calculate statistics
        total_likes = sum(p.likes for p in posts)
        total_comments = sum(p.comments for p in posts)
        total_shares = sum(p.shares for p in posts)
        avg_likes = total_likes / len(posts) if posts else 0
        avg_comments = total_comments / len(posts) if posts else 0
        
        # Find best post
        best_post = max(posts, key=lambda p: p.likes + p.comments + p.shares)
        
        report = f"""
# Summary Report

## Statistics
- Total Posts: {len(posts)}
- Total Likes: {total_likes:,}
- Total Comments: {total_comments:,}
- Total Shares: {total_shares:,}
- Average Likes per Post: {avg_likes:.2f}
- Average Comments per Post: {avg_comments:.2f}

## Best Performing Post
- Date: {format_timestamp(best_post.timestamp)}
- Likes: {best_post.likes:,}
- Comments: {best_post.comments:,}
- Shares: {best_post.shares:,}
- Content: {best_post.content[:100]}...

## Posts by Date
"""
        
        for date in sorted(posts_by_date.keys()):
            count = len(posts_by_date[date])
            report += f"- {date}: {count} post(s)\n"
        
        return report
