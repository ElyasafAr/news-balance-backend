#!/usr/bin/env python3
"""
Live news scraper that fetches fresh news from Rotter.net in real-time.
This now scrapes live from the website instead of just filtering existing data.
"""

import json
from datetime import datetime, timedelta
import re
import requests
from bs4 import BeautifulSoup
import time
import sqlite3
import hashlib

class LiveRotterScraper:
    def __init__(self):
        self.base_url = "https://rotter.net"
        self.forum_url = "https://rotter.net/forum/listforum.php"
        self.db_path = "rotter_news.db"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        
        # Initialize database
        self.init_database()
    
    def init_database(self):
        """Initialize the SQLite database and create tables if they don't exist."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create news_items table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS news_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL UNIQUE,
                    scraped_at TEXT NOT NULL,
                    row_text TEXT,
                    actual_datetime TEXT NOT NULL,
                    content TEXT,
                    clean_content TEXT,
                    content_length INTEGER,
                    date_time TEXT,
                    hash_id TEXT UNIQUE,
                    isProcessed BOOLEAN DEFAULT 0,
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
            print(f"Database initialized at {self.db_path}")
        except Exception as e:
            print(f"Error initializing database: {e}")
    
    def generate_article_hash(self, title, url):
        """Generate a unique hash for an article based on title and URL"""
        content = f"{title}{url}".encode('utf-8')
        return hashlib.md5(content).hexdigest()
    
    def is_article_exists(self, hash_id):
        """Check if an article already exists in the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM news_items WHERE hash_id = ?", (hash_id,))
            count = cursor.fetchone()[0]
            conn.close()
            return count > 0
        except Exception as e:
            print(f"Error checking article existence: {e}")
            return False
    
    def show_database_summary(self):
        """Show a summary of what's already in the database before scraping"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get recent articles count
            cursor.execute("""
                SELECT COUNT(*) FROM news_items 
                WHERE datetime(created_at) >= datetime('now', '-1 day')
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
            
            print(f"🗄️  Database Summary:")
            print(f"   Total articles stored: {total_count}")
            print(f"   Articles from last 24 hours: {recent_count}")
            print(f"   Latest article added: {latest_timestamp}")
            
            if recent_count > 0:
                print(f"   Will skip existing articles for faster processing")
            
            return recent_count
            
        except Exception as e:
            print(f"Error getting database summary: {e}")
            return 0
    
    def save_article_to_db(self, article_data):
        """Save an article to the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Generate hash for this article
            hash_id = self.generate_article_hash(article_data['title'], article_data['url'])
            
            # Check if article already exists
            if self.is_article_exists(hash_id):
                print(f"    ⚠️  Article already exists in database (skipping)")
                conn.close()
                return False
            
            # Insert new article
            cursor.execute('''
                INSERT INTO news_items (
                    title, url, scraped_at, row_text, actual_datetime, 
                    content, clean_content, content_length, date_time, hash_id,
                    isProcessed, process_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            print(f"    Article saved to database with hash: {hash_id[:8]}...")
            return True
            
        except Exception as e:
            print(f"    Error saving article to database: {e}")
            return False
    
    def get_database_stats(self):
        """Get statistics from the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get total count
            cursor.execute("SELECT COUNT(*) FROM news_items")
            total_count = cursor.fetchone()[0]
            
            # Get count from last 24 hours
            cursor.execute("""
                SELECT COUNT(*) FROM news_items 
                WHERE datetime(created_at) >= datetime('now', '-1 day')
            """)
            last_24h_count = cursor.fetchone()[0]
            
            # Get count from last hour
            cursor.execute("""
                SELECT COUNT(*) FROM news_items 
                WHERE datetime(created_at) >= datetime('now', '-1 hour')
            """)
            last_hour_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total': total_count,
                'last_24h': last_24h_count,
                'last_hour': last_hour_count
            }
            
        except Exception as e:
            print(f"Error getting database stats: {e}")
            return {'total': 0, 'last_24h': 0, 'last_hour': 0}
    
    def export_recent_articles_from_db(self, hours=5, limit=100):
        """Export recent articles from database to JSON format"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get recent articles from the last N hours
            cursor.execute("""
                SELECT id, title, url, actual_datetime, clean_content, content_length, date_time, created_at
                FROM news_items 
                WHERE datetime(actual_datetime) >= datetime('now', '-{} hours')
                ORDER BY actual_datetime DESC
                LIMIT ?
            """.format(hours, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            articles = []
            for row in rows:
                articles.append({
                    'id': row[0],
                    'title': row[1],
                    'url': row[2],
                    'actual_datetime': row[3],
                    'clean_content': row[4],
                    'content_length': row[5],
                    'date_time': row[6],
                    'created_at': row[7]
                })
            
            print(f"📤 Exported {len(articles)} articles from database (last {hours} hours)")
            return articles
            
        except Exception as e:
            print(f"Error exporting articles from database: {e}")
            return []
    
    def check_article_exists_in_db(self, title, url):
        """Quick check if article already exists in database (faster than full hash check)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check by URL first (most reliable)
            cursor.execute("SELECT COUNT(*) FROM news_items WHERE url = ?", (url,))
            url_count = cursor.fetchone()[0]
            
            if url_count > 0:
                conn.close()
                return True
            
            # Also check by title similarity (for cases where URL might be slightly different)
            cursor.execute("SELECT COUNT(*) FROM news_items WHERE title = ?", (title,))
            title_count = cursor.fetchone()[0]
            
            conn.close()
            return title_count > 0
            
        except Exception as e:
            print(f"Error checking article existence: {e}")
            return False
    
    def get_live_forum_page(self):
        """Get the live forum page and extract recent news from last 5 hours"""
        print("Fetching live forum page from Rotter.net...")
        
        try:
            response = requests.get(self.forum_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            response.encoding = 'windows-1255'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            recent_news_items = []
            processed_count = 0
            
            # Find all table rows
            rows = soup.find_all('tr')
            print(f"Found {len(rows)} table rows")
            
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
                            print(f"  Found date/time: {extracted_datetime}")
                            
                            # Check if this is within last 5 hours (focused filtering)
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
                                print(f"  ✓ Added recent news: {title[:60]}...")
                            else:
                                print(f"  ✗ Skipped (too old): {title[:60]}... - Date: {extracted_datetime}")
                        else:
                            print(f"  ⚠️  No date/time found for: {title[:60]}...")
                
                # Break outer loop if we reached the limit
                # if len(recent_news_items) >= 50:
                #     break
            
            print(f"📊 Processed {processed_count} articles, found {len(recent_news_items)} recent ones")
            print(f"Live scraping complete: Found {len(recent_news_items)} recent news items from last 24 hours")
            return recent_news_items
            
        except Exception as e:
            print(f"Error in live scraping: {e}")
            return []
    
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
                    print(f"    Found datetime: {day}.{month}.{year} {hour}:{minute}")
                    return dt
                except ValueError as e:
                    print(f"    ❌ Invalid datetime: {e}")
            
            # Look for separate date and time patterns
            date_pattern = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{2})', row_text)
            time_pattern = re.search(r'(\d{1,2}):(\d{2})', row_text)
            
            if date_pattern and time_pattern:
                day, month, year = date_pattern.groups()
                hour, minute = time_pattern.groups()
                year = '20' + str(year)
                try:
                    dt = datetime(int(year), int(month), int(day), int(hour), int(minute))
                    print(f"    ✅ Found separate date/time: {day}.{month}.{year} {hour}:{minute}")
                    return dt
                except ValueError as e:
                    print(f"    ❌ Invalid datetime: {e}")
            
            # If only date found, use current time
            elif date_pattern:
                day, month, year = date_pattern.groups()
                year = '20' + str(year)
                now = datetime.now()
                try:
                    dt = datetime(int(year), int(month), int(day), now.hour, now.minute)
                    print(f"    ✅ Found date only: {day}.{month}.{year} (using current time)")
                    return dt
                except ValueError as e:
                    print(f"    ❌ Invalid date: {e}")
            
            # If only time found, use today's date
            elif time_pattern:
                hour, minute = time_pattern.groups()
                today = datetime.now()
                try:
                    dt = datetime(today.year, today.month, today.day, int(hour), int(minute))
                    print(f"    ✅ Found time only: {hour}:{minute} (using today)")
                    return dt
                except ValueError as e:
                    print(f"    ❌ Invalid time: {e}")
            
            print(f"    ❌ No datetime found in row")
            return None
            
        except Exception as e:
            print(f"Error extracting datetime: {e}")
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
                        print(f"    ✓ Found news content with selector: {selector}")
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
                    print(f"    ✓ Found content using fallback method")
            
            # Return both content and the extracted datetime
            return content, article_datetime
            
        except Exception as e:
            print(f"Error getting content from {url}: {e}")
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
                    print(f"    📅 Found datetime in article page: {day}.{month}.{year} {hour}:{minute}")
                    return dt
                except ValueError as e:
                    print(f"    ❌ Invalid datetime from article page: {e}")
            
            # Look for just date pattern
            date_pattern = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{2})', page_text)
            if date_pattern:
                day, month, year = date_pattern.groups()
                year = '20' + str(year)
                try:
                    dt = datetime(int(year), int(month), int(day), 0, 0)
                    print(f"    📅 Found date only in article page: {day}.{month}.{year}")
                    return dt
                except ValueError as e:
                    print(f"    ❌ Invalid date from article page: {e}")
            
            # Look for time pattern
            time_pattern = re.search(r'(\d{1,2}):(\d{2})', page_text)
            if time_pattern:
                hour, minute = time_pattern.groups()
                today = datetime.now()
                try:
                    dt = datetime(today.year, today.month, today.day, int(hour), int(minute))
                    print(f"    📅 Found time only in article page: {hour}:{minute} (using today)")
                    return dt
                except ValueError as e:
                    print(f"    ❌ Invalid time from article page: {e}")
            
            print(f"    ⚠️  No datetime found in article page")
            return None
            
        except Exception as e:
            print(f"    ❌ Error extracting datetime from article page: {e}")
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
        
        print(f"\n📰 Found {len(recent_news_items)} recent news items from live website!")
        print("=" * 60)
        
        # Step 2: Get full content for the filtered items
        print(f"\n📰 Getting full content for {len(recent_news_items)} recent items...")
        print("=" * 60)
        
        events_with_content = []
        
        # Counters for tracking
        skipped_count = 0
        processed_count = 0
        
        for i, item in enumerate(recent_news_items, 1):
            print(f"\nProcessing {i}/{len(recent_news_items)}: {item['title'][:50]}...")
            
            # Check if article already exists in database
            if self.check_article_exists_in_db(item['title'], item['url']):
                print(f"  ⚠️  Article already exists in database (skipping): {item['title'][:50]}")
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
                    print(f"  ✓ Content extracted and cleaned - Length: {len(cleaned_content)} characters")
                    print(f"  📅 Date/Time from ARTICLE PAGE: {item['date_time']}")
                elif 'actual_datetime' in item and item['actual_datetime']:
                    # Fall back to the datetime from the main page
                    original_datetime = item['actual_datetime']
                    # Create a formatted string for display
                    item['date_time'] = original_datetime.strftime('%Y-%m-%d %H:%M:%S')
                    # Convert to string for JSON serialization
                    item['actual_datetime'] = original_datetime.isoformat()
                    print(f"  ✓ Content extracted and cleaned - Length: {len(cleaned_content)} characters")
                    print(f"  📅 Date/Time from MAIN PAGE: {item['date_time']}")
                else:
                    item['date_time'] = 'Unknown'
                    item['actual_datetime'] = 'Unknown'
                    print(f"  ✓ Content extracted and cleaned - Length: {len(cleaned_content)} characters")
                    print(f"  ⚠️  No datetime found for this article")
                
                # Save to database
                self.save_article_to_db(item)
                events_with_content.append(item)
                processed_count += 1
            else:
                print(f"  ✗ No content found")
                skipped_count += 1
            
            # Be respectful with delays
            time.sleep(0.3)  # Reduced delay for faster processing
        
        print(f"\n🎉 Live scraping complete!")
        print(f"📊 Processing Summary:")
        print(f"   ✓ New articles processed: {processed_count}")
        print(f"   ⚠️  Articles skipped (already exist): {skipped_count}")
        print(f"   📰 Total recent events from last 5 hours: {len(events_with_content)}")
        
        # Sort articles by datetime (newest to oldest)
        print(f"\n🔄 Sorting articles by datetime (newest to oldest)...")
        events_with_content.sort(key=lambda x: x.get('actual_datetime', ''), reverse=True)
        
        # Print sorted order for verification
        print(f"📅 Articles sorted by datetime:")
        for i, event in enumerate(events_with_content[:5], 1):  # Show first 5
            dt_str = event.get('date_time', 'Unknown')
            print(f"  {i}. {dt_str} - {event['title'][:50]}...")
        if len(events_with_content) > 5:
            print(f"  ... and {len(events_with_content) - 5} more articles")
        
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
            print(f"💾 Saved {len(clean_events)} events to {filename}")
        except Exception as e:
            print(f"Error saving to JSON: {e}")

def main():
    scraper = LiveRotterScraper()
    
    # Show database summary before scraping
    scraper.show_database_summary()
    
    # Scrape live news from the real website
    events = scraper.scrape_live_news()
    
    if events:
        print(f"\n📊 Live scraping results - {len(events)} recent events (sorted by datetime, newest first):")
        for i, event in enumerate(events, 1):
            print(f"\n{i}. {event['title']}")
            print(f"   URL: {event['url']}")
            print(f"   Date/Time: {event.get('date_time', 'Unknown')}")
            print(f"   Clean content length: {event.get('content_length', 0)} characters")
            print(f"   Content preview: {event.get('clean_content', '')[:100]}...")
        
        # Get database statistics
        stats = scraper.get_database_stats()
        print(f"\n🗄️  Database Statistics:")
        print(f"   Total articles: {stats['total']}")
        print(f"   Last 24 hours: {stats['last_24h']}")
        print(f"   Last hour: {stats['last_hour']}")
        
        # Export recent articles from database
        scraper.export_recent_articles_from_db(hours=24, limit=100)

        # Save ALL articles from last 24 hours
        print(f"\n📝 Saving ALL {len(events)} articles from the last 24 hours")
        
        # Save to JSON
        scraper.save_to_json(events)
        print(f"\n✅ All {len(events)} live recent news events have been saved to recent_news_only.json")
        print(f"🌐 You can now view these in your web interface at http://localhost:8080/news_scroller.html")
        print(f"💾 Articles are also stored in SQLite database: {scraper.db_path}")
        
        # Show final summary
        print(f"\n🎯 Final Summary:")
        print(f"   🚀 Scraping completed successfully!")
        print(f"   📰 New articles added to database: {len(events)}")
        print(f"   💾 Total articles in database: {stats['total']}")
        print(f"   ⚡ Next run will be faster (will skip existing articles)")
        print(f"   📅 Articles filtered from last 24 hours")
        
    else:
        print("❌ No live recent events were found from the website.")
        print("💡 This could mean:")
        print("   - All recent articles are already in the database")
        print("   - No new articles were published in the last 5 hours")
        print("   - There was an issue with the scraping process")

if __name__ == "__main__":
    main()
