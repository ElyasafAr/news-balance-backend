#!/usr/bin/env python3
# -*- coding: utf-8
"""
Live news scraper that fetches fresh news from Rotter.net in real-time.
Updated to work with PostgreSQL database instead of SQLite.
"""

import json
from datetime import datetime, timedelta
import re
import requests
from bs4 import BeautifulSoup
import time
import psycopg2
import hashlib
import os
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

class LiveRotterScraper:
    def __init__(self):
        self.base_url = "https://rotter.net"
        self.forum_url = "https://rotter.net/forum/listforum.php"
        self.database_url = os.getenv('DATABASE_URL')
        # Multiple User-Agents for rotation
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://rotter.net/',
            'Origin': 'https://rotter.net',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }
        
        # Initialize database
        self.init_database()
    
    def get_random_headers(self):
        """Get headers with random User-Agent"""
        import random
        headers = self.headers.copy()
        headers['User-Agent'] = random.choice(self.user_agents)
        return headers
    
    def get_db_connection(self):
        """Get PostgreSQL database connection"""
        try:
            conn = psycopg2.connect(self.database_url)
            return conn
        except Exception as e:
            print("Error connecting to database: " + str(e))
            return None
    
    def init_database(self):
        """Initialize the PostgreSQL database and create tables if they don't exist."""
        try:
            conn = self.get_db_connection()
            if not conn:
                return
            
            cursor = conn.cursor()
            
            # Create news_items table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS news_items (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL UNIQUE,
                    scraped_at TEXT,
                    row_text TEXT,
                    actual_datetime TEXT NOT NULL,
                    content TEXT,
                    clean_content TEXT,
                    content_length INTEGER,
                    date_time TEXT,
                    hash_id TEXT UNIQUE,
                    isProcessed INTEGER DEFAULT 0,
                    process_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create a hash table for quick lookup
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS news_hashes (
                    hash_id TEXT PRIMARY KEY,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            print("Database initialized successfully")
        except Exception as e:
            print("Error initializing database: " + str(e))
    
    def generate_article_hash(self, title, url):
        """Generate a unique hash for an article based on title and URL"""
        content = (title + url).encode('utf-8')
        return hashlib.md5(content).hexdigest()
    
    def is_article_exists(self, hash_id):
        """Check if an article already exists in the database"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return False
            
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM news_items WHERE hash_id = %s", (hash_id,))
            count = cursor.fetchone()[0]
            conn.close()
            return count > 0
        except Exception as e:
            print("Error checking article existence: " + str(e))
            return False
    
    def show_database_summary(self):
        """Show a summary of what's already in the database before scraping"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return 0
            
            cursor = conn.cursor()
            
            # Get recent articles count
            cursor.execute("""
                SELECT COUNT(*) FROM news_items 
                WHERE created_at >= NOW() - INTERVAL '1 day'
            """)
            recent_count = cursor.fetchone()[0]
            
            # Get total count
            cursor.execute("SELECT COUNT(*) FROM news_items")
            total_count = cursor.fetchone()[0]
            
            # Get latest article timestamp
            cursor.execute("""
                SELECT created_at FROM news_items 
                ORDER BY created_at DESC LIMIT 1
            """)
            latest_result = cursor.fetchone()
            latest_timestamp = latest_result[0] if latest_result else "None"
            
            conn.close()
            
            print("Database Summary:")
            print("   Total articles stored: " + str(total_count))
            print("   Articles from last 24 hours: " + str(recent_count))
            print("   Latest article added: " + str(latest_timestamp))
            
            if recent_count > 0:
                print("   Will skip existing articles for faster processing")
            
            return recent_count
            
        except Exception as e:
            print("Error getting database summary: " + str(e))
            return 0
    
    def save_article_to_db(self, article_data):
        """Save an article to the database"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return False
            
            cursor = conn.cursor()
            
            # Generate hash for this article
            hash_id = self.generate_article_hash(article_data['title'], article_data['url'])
            
            # Check if article already exists
            if self.is_article_exists(hash_id):
                print("    Article already exists in database (skipping)")
                conn.close()
                return False
            
            # Insert new article
            cursor.execute('''
                INSERT INTO news_items (
                    title, url, scraped_at, row_text, actual_datetime, 
                    content, clean_content, content_length, date_time, hash_id,
                    isprocessed, process_data
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                article_data['title'],
                article_data['url'],
                article_data['scraped_at'],
                article_data.get('row_text', ''),
                article_data.get('actual_datetime', ''),
                article_data.get('content', ''),
                article_data.get('clean_content', ''),
                article_data.get('content_length', 0),
                article_data.get('date_time', ''),
                hash_id,
                0,  # isProcessed defaults to False (0)
                ''   # process_data starts empty
            ))
            
            conn.commit()
            conn.close()
            print("    Article saved to database with hash: " + hash_id[:8] + "...")
            return True
            
        except Exception as e:
            print("    Error saving article to database: " + str(e))
            return False
    
    def get_database_stats(self):
        """Get statistics from the database"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return {'total': 0, 'last_24h': 0, 'last_hour': 0}
            
            cursor = conn.cursor()
            
            # Get total count
            cursor.execute("SELECT COUNT(*) FROM news_items")
            total_count = cursor.fetchone()[0]
            
            # Get count from last 24 hours
            cursor.execute("""
                SELECT COUNT(*) FROM news_items 
                WHERE created_at >= NOW() - INTERVAL '1 day'
            """)
            last_24h_count = cursor.fetchone()[0]
            
            # Get count from last hour
            cursor.execute("""
                SELECT COUNT(*) FROM news_items 
                WHERE created_at >= NOW() - INTERVAL '1 hour'
            """)
            last_hour_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total': total_count,
                'last_24h': last_24h_count,
                'last_hour': last_hour_count
            }
            
        except Exception as e:
            print("Error getting database stats: " + str(e))
            return {'total': 0, 'last_24h': 0, 'last_hour': 0}
    
    def check_article_exists_in_db(self, title, url):
        """Quick check if article already exists in database (faster than full hash check)"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return False
            
            cursor = conn.cursor()
            
            # Check by URL first (most reliable)
            cursor.execute("SELECT COUNT(*) FROM news_items WHERE url = %s", (url,))
            url_count = cursor.fetchone()[0]
            
            if url_count > 0:
                conn.close()
                return True
            
            # Also check by title similarity (for cases where URL might be slightly different)
            cursor.execute("SELECT COUNT(*) FROM news_items WHERE title = %s", (title,))
            title_count = cursor.fetchone()[0]
            
            conn.close()
            return title_count > 0
            
        except Exception as e:
            print("Error checking article existence: " + str(e))
            return False
    
    def get_live_forum_page(self):
        """Get the live forum page and extract recent news from last 5 hours"""
        print("Fetching live forum page from Rotter.net...")
        
        # Try different URLs if main one fails
        urls_to_try = [
            self.forum_url,
            "https://rotter.net/forum/",
            "https://rotter.net/",
            "https://rotter.net/forum/listforum.php?f=1"
        ]
        
        # Retry mechanism
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"Attempt {attempt + 1}/{max_retries}...")
                
                # Add delay between attempts
                if attempt > 0:
                    time.sleep(5)
                
                # Use random headers and add session for cookie persistence
                session = requests.Session()
                headers = self.get_random_headers()
                
                # Add random delay to mimic human behavior
                time.sleep(random.uniform(1, 3))
                
                # Try different URLs
                url_to_try = urls_to_try[attempt % len(urls_to_try)]
                print(f"Trying URL: {url_to_try}")
                
                response = session.get(url_to_try, headers=headers, timeout=15)
                response.raise_for_status()
                response.encoding = 'windows-1255'
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                recent_news_items = []
                processed_count = 0
                
                # Find all table rows
                rows = soup.find_all('tr')
                print("Found " + str(len(rows)) + " table rows")
                
                for row in rows:
                    # Look for links in each row
                    links = row.find_all('a', href=True)
                    
                    for link in links:
                        href = link.get('href', '')
                        title = link.get_text(strip=True)
                        
                        # Filter for news-like content
                        if (title and len(title) > 15 and 
                            not title.startswith('לחץ כאן') and
                            not title.startswith('אל לובי') and
                            ('dcboard.cgi' in href or 'forum' in href)):
                            
                            processed_count += 1
                            
                            # Get the entire row text to check for date/time
                            row_text = row.get_text()
                            
                            # Extract actual date and time from the row
                            extracted_datetime = self.extract_actual_datetime_from_row(row)
                            
                            if extracted_datetime:
                                print("  Found date/time: " + str(extracted_datetime))
                                
                                # Check if this is within last 24 hours (focused filtering)
                                if self.is_within_24_hours(extracted_datetime):
                                    # Make URL absolute
                                    if href.startswith('http'):
                                        url = href
                                    else:
                                        url = self.base_url + href
                                    
                                    recent_news_items.append({
                                        'title': title,
                                        'url': url,
                                        'scraped_at': datetime.now().isoformat(),
                                        'row_text': row_text[:200],
                                        'actual_datetime': extracted_datetime
                                    })
                                    print("  Added recent news: " + title[:60] + "...")
                                else:
                                    print("  Skipped (too old): " + title[:60] + "... - Date: " + str(extracted_datetime))
                            else:
                                print("  No date/time found for: " + title[:60] + "...")
                
                print("Processed " + str(processed_count) + " articles, found " + str(len(recent_news_items)) + " recent ones")
                print("Live scraping complete: Found " + str(len(recent_news_items)) + " recent news items from last 24 hours")
                return recent_news_items
                
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    print("All attempts failed, returning empty list")
                    return []
                else:
                    print("Retrying in 5 seconds...")
                    continue
    
    def extract_actual_datetime_from_row(self, row):
        """Extract the actual date and time from the table row - simplified and more reliable"""
        try:
            # Get all text from the row to analyze
            row_text = row.get_text(strip=True)
            
            # Look for the most common pattern: DD.MM.YY HH:MM
            date_time_pattern = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{2})\s+(\d{1,2}):(\d{2})', row_text)
            if date_time_pattern:
                day, month, year, hour, minute = date_time_pattern.groups()
                year = '20' + str(year)
                try:
                    dt = datetime(int(year), int(month), int(day), int(hour), int(minute))
                    print("    Found datetime: " + day + "." + month + "." + year + " " + hour + ":" + minute)
                    return dt
                except ValueError as e:
                    print("    Invalid datetime: " + str(e))
            
            # Look for separate date and time patterns
            date_pattern = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{2})', row_text)
            time_pattern = re.search(r'(\d{1,2}):(\d{2})', row_text)
            
            if date_pattern and time_pattern:
                day, month, year = date_pattern.groups()
                hour, minute = time_pattern.groups()
                year = '20' + str(year)
                try:
                    dt = datetime(int(year), int(month), int(day), int(hour), int(minute))
                    print("    Found separate date/time: " + day + "." + month + "." + year + " " + hour + ":" + minute)
                    return dt
                except ValueError as e:
                    print("    Invalid datetime: " + str(e))
            
            # If only date found, use current time
            elif date_pattern:
                day, month, year = date_pattern.groups()
                year = '20' + str(year)
                now = datetime.now()
                try:
                    dt = datetime(int(year), int(month), int(day), now.hour, now.minute)
                    print("    Found date only: " + day + "." + month + "." + year + " (using current time)")
                    return dt
                except ValueError as e:
                    print("    Invalid date: " + str(e))
            
            # If only time found, use today's date
            elif time_pattern:
                hour, minute = time_pattern.groups()
                today = datetime.now()
                try:
                    dt = datetime(today.year, today.month, today.day, int(hour), int(minute))
                    print("    Found time only: " + hour + ":" + minute + " (using today)")
                    return dt
                except ValueError as e:
                    print("    Invalid time: " + str(e))
            
            print("    No datetime found in row")
            return None
            
        except Exception as e:
            print("Error extracting datetime: " + str(e))
            return None
    
    def is_within_24_hours(self, article_datetime):
        """Check if the article datetime is within the last 24 hours"""
        if not article_datetime:
            return False
        
        now = datetime.now()
        time_diff = now - article_datetime
        
        # Accept articles from the last 24 hours (86400 seconds)
        return time_diff.total_seconds() <= 86400
    
    def get_live_article_content(self, url):
        """Get live content from article page - improved to focus on actual news"""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            response.encoding = 'windows-1255'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # First, try to extract the actual datetime from the article page
            article_datetime = self.extract_datetime_from_article_page(soup)
            
            # Look for the main content area - prioritize news content
            content_selectors = [
                'div.content',
                'div#content', 
                'td.content',
                'div.post',
                'div.message',
                'td[valign="top"]',
                'div.main-content',
                'div.article-content',
                'td.article',
                'div.forum-content',
                'table[width="100%"]'
            ]
            
            content = ""
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    # Remove scripts, styles, and navigation
                    for script in content_elem(["script", "style", "iframe", "nav", "header", "footer"]):
                        script.decompose()
                    
                    temp_content = content_elem.get_text(separator='\n', strip=True)
                    
                    # Look for the main article content (before responses/comments)
                    lines = temp_content.split('\n')
                    main_article_lines = []
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Stop when we hit response indicators
                        if any(indicator in line for indicator in [
                            'תגובה עם ציטוט', 'האשכול', 'מחבר', 'תאריך כתיבה',
                            'ציטוט:', 'תגובה:', 'משתמש:', 'הודעה:', 'פורום:',
                            'בחר פורום', 'בית המדרש', 'סקופים', 'אשכול מספר'
                        ]):
                            break
                        
                        # Only include substantial content lines
                        if len(line) > 20 and not self.is_forum_navigation(line):
                            main_article_lines.append(line)
                    
                    content = '\n'.join(main_article_lines)
                    if content and len(content) > 200:  # Require more substantial content
                        print("    Found news content with selector: " + selector)
                        break
            
            # If no content found with selectors, try to get the entire page text
            if not content or len(content) < 200:
                # Get all text from the page and filter intelligently
                all_text = soup.get_text(separator='\n', strip=True)
                lines = all_text.split('\n')
                
                # Look for content after the title
                content_started = False
                main_content_lines = []
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Skip navigation and header elements
                    if self.is_forum_navigation(line):
                        continue
                    
                    # Start collecting content after we find a substantial line
                    if len(line) > 30 and not content_started:
                        content_started = True
                    
                    if content_started:
                        # Stop when we hit response indicators
                        if any(indicator in line for indicator in [
                            'תגובה עם ציטוט', 'האשכול', 'מחבר', 'תאריך כתיבה'
                        ]):
                            break
                        
                        # Only include substantial content
                        if len(line) > 20 and not self.is_forum_navigation(line):
                            main_content_lines.append(line)
                
                content = '\n'.join(main_content_lines)
                if content and len(content) > 200:
                    print("    Found content using fallback method")
            
            # Return both content and the extracted datetime
            return content, article_datetime
            
        except Exception as e:
            print("Error getting content from " + url + ": " + str(e))
            return None, None
    
    def is_forum_navigation(self, line):
        """Check if a line is forum navigation (should be skipped)"""
        navigation_keywords = [
            'בית המדרש', 'הרגע קניתי', 'בני ה-20', 'סקופים', 'אשכול מספר',
            'בחר פורום', 'נושא #', 'חבר מתאריך', 'הודעות', 'מדרגים',
            'נקודות', 'ראה משוב', 'מנהל', 'סגן המנהל', 'מפקח',
            'עיתונאי', 'צל"ש', 'כותרות', 'שעה', 'הכותב', 'אל לובי',
            'החופשה הבאה', 'לוח שנה עברי', 'Downloads', 'שיתוף',
            'מוזיקה', 'סרטים', 'צילום', 'מוטוריקה', 'לובי', 'חופשה',
            'Booking.com', 'Kiwi', 'Skyscanner', 'TripAdvisor',
            'גירסת הדפסה', 'קבוצות דיון', 'אל לובי הפורומים',
            'החופשה הבאה שלך מתחילה כאן', '--------',
            'ביקורת תקשורת', 'עיתונות זרה', 'הפורום האקסקלוסיבי',
            'ביטקוין ומטבעות קריפטו', 'כושר ופיתוח גוף'
        ]
        
        return any(keyword in line for keyword in navigation_keywords)
    
    def extract_datetime_from_article_page(self, soup):
        """Extract the actual datetime from the article page itself"""
        try:
            # Look for datetime patterns in the article page
            # Common patterns: DD.MM.YY HH:MM or similar
            
            # Get all text from the page
            page_text = soup.get_text()
            
            # Look for date and time patterns
            date_time_pattern = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{2})\s+(\d{1,2}):(\d{2})', page_text)
            if date_time_pattern:
                day, month, year, hour, minute = date_time_pattern.groups()
                year = '20' + str(year)
                try:
                    dt = datetime(int(year), int(month), int(day), int(hour), int(minute))
                    print("    Found datetime in article page: " + day + "." + month + "." + year + " " + hour + ":" + minute)
                    return dt
                except ValueError as e:
                    print("    Invalid datetime from article page: " + str(e))
            
            # Look for just date pattern
            date_pattern = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{2})', page_text)
            if date_pattern:
                day, month, year = date_pattern.groups()
                year = '20' + str(year)
                try:
                    dt = datetime(int(year), int(month), int(day), 0, 0)
                    print("    Found date only in article page: " + day + "." + month + "." + year)
                    return dt
                except ValueError as e:
                    print("    Invalid date from article page: " + str(e))
            
            # Look for time pattern
            time_pattern = re.search(r'(\d{1,2}):(\d{2})', page_text)
            if time_pattern:
                hour, minute = time_pattern.groups()
                today = datetime.now()
                try:
                    dt = datetime(today.year, today.month, today.day, int(hour), int(minute))
                    print("    Found time only in article page: " + hour + ":" + minute + " (using today)")
                    return dt
                except ValueError as e:
                    print("    Invalid time from article page: " + str(e))
            
            print("    No datetime found in article page")
            return None
            
        except Exception as e:
            print("    Error extracting datetime from article page: " + str(e))
            return None
    
    def clean_article_content(self, content):
        """Clean the article content to remove forum navigation and keep only the news"""
        if not content:
            return 'אין תוכן זמין'
        
        # Remove all forum navigation elements completely
        clean_content = content
        
        # Remove forum navigation patterns - more aggressive cleaning
        forum_patterns = [
            r'בית המדרש[\s\S]*?סקופים[\s\S]*?אשכול מספר[\s\S]*?\d+[\s\S]*?[^א-ת]*?[א-ת]+[^א-ת]*?\d{2}:\d{2}[\s\S]*?\d{2}\.\d{2}\.\d{2}',
            r'בחר פורום[\s\S]*?סקופים',
            r'נושא #\d+',
            r'ערכתי לאחרונה.*?בברכה.*?',
            r'חבר מתאריך.*?הודעות.*?מדרגים.*?נקודות.*?ראה משוב',
            r'יום.*?כ.*?באב.*?תשפ.*?',
            r'מנהל[\s\S]*?צל"ש',
            r'ביקורת תקשורת[\s\S]*?(?=\n|$)',
            r'עיתונות זרה[\s\S]*?(?=\n|$)',
            r'הפורום האקסקלוסיבי[\s\S]*?(?=\n|$)',
            r'ביטקוין ומטבעות קריפטו[\s\S]*?(?=\n|$)',
            r'כושר ופיתוח גוף[\s\S]*?(?=\n|$)',
            r'https?://[^\s]+',  # Remove URLs
            r'\n{3,}',  # Remove excessive newlines
        ]
        
        for pattern in forum_patterns:
            clean_content = re.sub(pattern, '', clean_content)
        
        # Split into lines and filter out forum-related lines
        lines = clean_content.split('\n')
        meaningful_lines = []
        
        for line in lines:
            trimmed_line = line.strip()
            # Skip lines that are clearly forum navigation
            if (len(trimmed_line) < 10 or 
                any(keyword in trimmed_line for keyword in [
                    'בית המדרש', 'הרגע קניתי', 'בני ה-20', 'סקופים', 'אשכול מספר',
                    'בחר פורום', 'נושא #', 'חבר מתאריך', 'הודעות', 'מדרגים',
                    'נקודות', 'ראה משוב', 'מנהל', 'סגן המנהל', 'מפקח',
                    'עיתונאי', 'צל"ש', 'כותרות', 'שעה', 'הכותב', 'אל לובי',
                    'החופשה הבאה', 'לוח שנה עברי', 'Downloads', 'שיתוף',
                    'מוזיקה', 'סרטים', 'צילום', 'מוטוריקה', 'לובי', 'חופשה',
                    'Booking.com', 'Kiwi', 'Skyscanner', 'TripAdvisor',
                    'גירסת הדפסה', 'קבוצות דיון', 'אל לובי הפורומים',
                    'החופשה הבאה שלך מתחילה כאן', '--------',
                    'ביקורת תקשורת', 'עיתונות זרה', 'הפורום האקסקלוסיבי',
                    'ביטקוין ומטבעות קריפטו', 'כושר ופיתוח גוף'
                ])):
                continue
            
            # Skip lines that are just dates, times, or single words
            if (re.match(r'^\d{2}:\d{2}$', trimmed_line) or  # Time like "09:39"
                re.match(r'^\d{2}\.\d{2}\.\d{2}$', trimmed_line) or  # Date like "22.08.25"
                re.match(r'^[א-ת]+$', trimmed_line) or  # Single Hebrew word
                re.match(r'^[,\'\"]+$', trimmed_line)):  # Just punctuation
                continue
            
            meaningful_lines.append(line)
        
        # Join the meaningful lines
        clean_content = '\n'.join(meaningful_lines).strip()
        
        # Final cleanup
        clean_content = re.sub(r'^\s*[-=]+\s*$', '', clean_content, flags=re.MULTILINE)
        clean_content = re.sub(r'^\s*[א-ת]+\s*$', '', clean_content, flags=re.MULTILINE)
        clean_content = re.sub(r'\n{3,}', '\n\n', clean_content)
        
        # Take more content - increase to 1000 characters for better display
        if len(clean_content) > 1000:
            clean_content = clean_content[:1000] + '...'
        
        return clean_content or 'תוכן זמין בקישור המקורי'
    
    def scrape_live_news(self):
        """Main function - scrapes live news from Rotter.net"""
        print("Starting LIVE Rotter.net news scraper...")
        print("Fetching fresh news from the real website in real-time...")
        print("=" * 60)
        
        # Step 1: Get live forum page and extract recent titles/links (already filtered)
        recent_news_items = self.get_live_forum_page()
        
        if not recent_news_items:
            print("No recent news items found in live scraping")
            return []
        
        print("\nFound " + str(len(recent_news_items)) + " recent news items from live website!")
        print("=" * 60)
        
        # Step 2: Get full content for the filtered items
        print("\nGetting full content for " + str(len(recent_news_items)) + " recent items...")
        print("=" * 60)
        
        events_with_content = []
        
        # Counters for tracking
        skipped_count = 0
        processed_count = 0
        
        for i, item in enumerate(recent_news_items, 1):
            print("\nProcessing " + str(i) + "/" + str(len(recent_news_items)) + ": " + item['title'][:50] + "...")
            
            # Check if article already exists in database
            if self.check_article_exists_in_db(item['title'], item['url']):
                print("  Article already exists in database (skipping): " + item['title'][:50])
                skipped_count += 1
                continue

            content, article_datetime = self.get_live_article_content(item['url'])
            
            if content:
                # Clean the content
                cleaned_content = self.clean_article_content(content)
                item['content'] = content
                item['clean_content'] = cleaned_content
                item['content_length'] = len(cleaned_content)
                
                # Preserve the original extracted datetime and create a formatted version
                if article_datetime:
                    # Use the datetime from the article page (more accurate)
                    original_datetime = article_datetime
                    # Create a formatted string for display
                    item['date_time'] = original_datetime.strftime('%Y-%m-%d %H:%M:%S')
                    # Convert to string for JSON serialization
                    item['actual_datetime'] = original_datetime.isoformat()
                    print("  Content extracted and cleaned - Length: " + str(len(cleaned_content)) + " characters")
                    print("  Date/Time from ARTICLE PAGE: " + item['date_time'])
                elif 'actual_datetime' in item and item['actual_datetime']:
                    # Fall back to the datetime from the main page
                    original_datetime = item['actual_datetime']
                    # Create a formatted string for display
                    item['date_time'] = original_datetime.strftime('%Y-%m-%d %H:%M:%S')
                    # Convert to string for JSON serialization
                    item['actual_datetime'] = original_datetime.isoformat()
                    print("  Content extracted and cleaned - Length: " + str(len(cleaned_content)) + " characters")
                    print("  Date/Time from MAIN PAGE: " + item['date_time'])
                else:
                    item['date_time'] = 'Unknown'
                    item['actual_datetime'] = 'Unknown'
                    print("  Content extracted and cleaned - Length: " + str(len(cleaned_content)) + " characters")
                    print("  No datetime found for this article")
                
                # Save to database
                self.save_article_to_db(item)
                events_with_content.append(item)
                processed_count += 1
            else:
                print("  No content found")
                skipped_count += 1
            
            # Be respectful with delays
            time.sleep(0.3)  # Reduced delay for faster processing
        
        print("\nLive scraping complete!")
        print("Processing Summary:")
        print("   New articles processed: " + str(processed_count))
        print("   Articles skipped (already exist): " + str(skipped_count))
        print("   Total recent events from last 24 hours: " + str(len(events_with_content)))
        
        # Sort articles by datetime (newest to oldest)
        print("\nSorting articles by datetime (newest to oldest)...")
        events_with_content.sort(key=lambda x: x.get('actual_datetime', ''), reverse=True)
        
        # Print sorted order for verification
        print("Articles sorted by datetime:")
        for i, event in enumerate(events_with_content[:5], 1):  # Show first 5
            dt_str = event.get('date_time', 'Unknown')
            print("  " + str(i) + ". " + dt_str + " - " + event['title'][:50] + "...")
        if len(events_with_content) > 5:
            print("  ... and " + str(len(events_with_content) - 5) + " more articles")
        
        return events_with_content
    
    def save_to_json(self, events, filename='recent_news_only.json'):
        """Save events to JSON file"""
        try:
            # Convert any remaining datetime objects to strings
            def convert_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return obj
            
            # Clean the events data for JSON serialization
            clean_events = []
            for event in events:
                clean_event = {}
                for key, value in event.items():
                    clean_event[key] = convert_datetime(value)
                clean_events.append(clean_event)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(clean_events, f, ensure_ascii=False, indent=2)
            print("Saved " + str(len(clean_events)) + " events to " + filename)
        except Exception as e:
            print("Error saving to JSON: " + str(e))

def main():
    scraper = LiveRotterScraper()
    
    # Show database summary before scraping
    scraper.show_database_summary()
    
    # Scrape live news from the real website
    events = scraper.scrape_live_news()
    
    if events:
        print("\nLive scraping results - " + str(len(events)) + " recent events (sorted by datetime, newest first):")
        for i, event in enumerate(events, 1):
            print("\n" + str(i) + ". " + event['title'])
            print("   URL: " + event['url'])
            print("   Date/Time: " + event.get('date_time', 'Unknown'))
            print("   Clean content length: " + str(event.get('content_length', 0)) + " characters")
            print("   Content preview: " + event.get('clean_content', '')[:100] + "...")
        
        # Get database statistics
        stats = scraper.get_database_stats()
        print("\nDatabase Statistics:")
        print("   Total articles: " + str(stats['total']))
        print("   Last 24 hours: " + str(stats['last_24h']))
        print("   Last hour: " + str(stats['last_hour']))
        
        # Save to JSON
        scraper.save_to_json(events)
        print("\nAll " + str(len(events)) + " live recent news events have been saved to recent_news_only.json")
        print("Articles are also stored in PostgreSQL database")
        
        # Show final summary
        print("\nFinal Summary:")
        print("   Scraping completed successfully!")
        print("   New articles added to database: " + str(len(events)))
        print("   Total articles in database: " + str(stats['total']))
        print("   Next run will be faster (will skip existing articles)")
        print("   Articles filtered from last 24 hours")
        
    else:
        print("No live recent events were found from the website.")
        print("This could mean:")
        print("   - All recent articles are already in the database")
        print("   - No new articles were published in the last 24 hours")
        print("   - There was an issue with the scraping process")

if __name__ == "__main__":
    main()
