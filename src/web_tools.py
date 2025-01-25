import requests
from bs4 import BeautifulSoup
import json
import os
from dotenv import load_dotenv
import traceback
from googlesearch import search
from datetime import datetime
import pytz
import re

load_dotenv()

class WebTools:
    def __init__(self):
        self.debug = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.sa_timezone = pytz.timezone('Africa/Johannesburg')

    def debug_print(self, *args, **kwargs):
        if self.debug:
            print(*args, **kwargs)

    def get_search_urls(self, query: str, num_results: int = 3) -> list:
        """Get URLs from Google search"""
        try:
            self.debug_print(f"\n[DEBUG] Performing Google search for: '{query}'")
            urls = list(search(query, num_results=num_results))
            self.debug_print(f"\n[DEBUG] Found {len(urls)} URLs:")
            for i, url in enumerate(urls, 1):
                self.debug_print(f"URL {i}: {url}")
            return urls
        except Exception as e:
            self.debug_print(f"\n[DEBUG] Error in Google search: {str(e)}")
            self.debug_print(traceback.format_exc())
            return []

    def clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        # Remove extra whitespace
        text = ' '.join(text.split())
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s.,!?-]', '', text)
        return text.strip()

    def extract_article_content(self, soup: BeautifulSoup) -> str:
        """Extract main article content from HTML"""
        content = []
        
        # Try to find main content area
        main_content = (
            soup.find('article') or 
            soup.find('main') or 
            soup.find(class_=re.compile(r'article|content|post|story|text|body', re.I))
        )
        
        if main_content:
            soup = main_content
            
        # Get all text paragraphs
        for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            text = self.clean_text(p.get_text())
            if len(text) > 20:  # Only keep substantial paragraphs
                content.append(text)
                
        return '\n\n'.join(content)

    def fetch_url_content(self, url: str, index: int) -> dict:
        """Fetch and parse content from a URL"""
        try:
            self.debug_print(f"\n[DEBUG] Fetching content from: {url}")
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get the title
            title = soup.title.string if soup.title else url
            
            # Get the full article content
            content = self.extract_article_content(soup)
            
            if content:
                self.debug_print(f"[DEBUG] Result {index} processed successfully")
                self.debug_print(f"[DEBUG] Content length: {len(content)} characters")
                return {
                    "title": title,
                    "url": url,
                    "content": content
                }
            return None
            
        except Exception as e:
            self.debug_print(f"\n[DEBUG] Error processing URL {url}: {str(e)}")
            return None

    def search_web(self, query: str, num_results: int = 3) -> str:
        """Search the web for information"""
        try:
            # First get the URLs from Google
            urls = self.get_search_urls(query, num_results)
            if not urls:
                return "No search results found."
            
            # Then fetch content from each URL
            results = []
            for i, url in enumerate(urls, 1):
                result = self.fetch_url_content(url, i)
                if result:
                    results.append(
                        f"Source {i}:\n"
                        f"Title: {result['title']}\n"
                        f"URL: {result['url']}\n"
                        f"Content:\n{result['content']}\n"
                    )
            
            combined_results = "\n---\n".join(results) if results else "No useful content found in search results."
            self.debug_print(f"\n[DEBUG] Total processed results: {len(results)}")
            return combined_results
            
        except Exception as e:
            error_msg = f"Error searching web: {str(e)}"
            self.debug_print(f"\n[DEBUG] {error_msg}")
            self.debug_print("\n[DEBUG] Full error:")
            self.debug_print(traceback.format_exc())
            return error_msg

    def get_sa_time(self) -> str:
        """Get current date and time in South Africa"""
        try:
            self.debug_print("\n[DEBUG] Getting South African time")
            
            # Get current time in SA timezone
            sa_time = datetime.now(self.sa_timezone)
            
            # Format the time string
            formatted_time = sa_time.strftime("%A, %d %B %Y, %H:%M:%S %Z")
            
            self.debug_print(f"[DEBUG] Current SA time: {formatted_time}")
            return f"Current time in South Africa: {formatted_time}"
            
        except Exception as e:
            error_msg = f"Error getting SA time: {str(e)}"
            self.debug_print(f"\n[DEBUG] {error_msg}")
            self.debug_print(traceback.format_exc())
            return error_msg