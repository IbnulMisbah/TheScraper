import json
import time
from facebook_scraper import get_posts

def create_markdown(posts, filename="math_posts.md"):
    # পোস্টগুলোকে পুরোনো থেকে নতুন ক্রমানুসারে সাজানোর জন্য লিস্টটি রিভার্স করা হলো (Past posts up)
    posts.reverse()
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("# 🧮 Mathematics Page Posts\n\n")
        f.write("---\n\n")
        
        for post in posts:
            date = post.get('time', 'Unknown Date')
            text = post.get('text', 'No text available')
            image = post.get('image', None)
            post_url = post.get('post_url', '#')
            likes = post.get('likes', 0)
            shares = post.get('shares', 0)
            comments_count = post.get('comments', 0)
            
            f.write(f"### 📅 Date: {date}\n\n")
            f.write(f"{text}\n\n")
            
            if image:
                f.write(f"![Image]({image})\n\n")
            
            f.write(f"**🔗 [Original Post Link]({post_url})**\n\n")
            f.write(f"👍 Likes: {likes} | 🔁 Shares: {shares} | 💬 Comments: {comments_count}\n\n")
            
            # কমেন্ট স্ক্র্যাপ করা থাকলে তা যুক্ত করা
            if 'comments_full' in post and post['comments_full']:
                f.write("**Top Comments:**\n")
                for comment in post['comments_full'][:5]: # প্রথম ৫টি কমেন্ট
                    f.write(f"> *{comment.get('commenter_name', 'User')}*: {comment.get('comment_text', '')}\n\n")
                    
            f.write("---\n\n")
            
def scrape_and_build_md(page_name):
    print(f"Scraping started for: {page_name}")
    posts_data = []
    
    try:
        # কুকিজ ছাড়া পাবলিক পেজ স্ক্র্যাপ করার চেষ্টা
        # ব্রাউজারের মতো আচরণ করতে রিকোয়েস্টের মাঝে delay দেওয়া উচিত
        for post in get_posts(page_name, pages=5, options={"comments": True}):
            posts_data.append(post)
            print(f"Scraped post from {post.get('time')}")
            time.sleep(3) # ব্লক এড়ানোর জন্য ছোট একটি বিরতি
            
    except Exception as e:
        print(f"Error during scraping: {e}")
        print("Note: If blocked, you need to provide a cookies.txt file or use proxies.")
        
    if posts_data:
        create_markdown(posts_data)
        print("Markdown file successfully created!")

if __name__ == "__main__":
    # আপনার কাঙ্ক্ষিত পেজের আইডি বা ইউজারনেম এখানে দিন
    TARGET_PAGE = "maths.explain.page" 
    scrape_and_build_md(TARGET_PAGE)
