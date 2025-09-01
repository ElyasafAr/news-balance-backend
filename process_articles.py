#!/usr/bin/env python3
# -*- coding: utf-8
"""
Article Processing Script - 4-Stage Approach
Reads unprocessed articles from the database and processes them using a 4-stage pipeline:
1. Relevance Check
2. Research
3. Technical Analysis
4. Journalistic Writing
"""

import sqlite3
import os
import json
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import anthropic
from dotenv import load_dotenv

# Load environment variables from .env.local file
load_dotenv('.env.local')

class ArticleProcessor:
    def __init__(self, db_path: str = "rotter_news.db"):
        """Initialize the article processor with database path"""
        self.db_path = db_path
        self.anthropic_client = None
        self.init_anthropic()
        
        # Stage 1: Relevance check prompt
        self.relevance_prompt = """
אתה עיתונאי ישראלי מנוסה. קרא את הכתבה הבאה וענה בקצרה:

1. האם זה נושא פוליטי או חברתי שנוי במחלוקת בישראל?
2. אם כן - מה סוג המחלוקת?
3. אם לא - מה קטגוריית הכתבה?

שים לב: משלים כמו "כדור השלג" או "משחקי כוח" הם בדרך כלל פוליטיים, לא ספורט.

ענה בקצרה - עד 50 מילים.

כותרת: {title}
תוכן: {content}
"""
        
        # Stage 2: Research with verification
        self.research_prompt = """
חשוב מאוד: בצע חיפוש מעמיק באינטרנט על הנושא הזה עכשיו!

חפש בעברית:
1. "{main_topic}"
2. "{main_topic} + מחלוקת"
3. "{main_topic} + עמדות שונות"

חובה למצוא:
- לפחות 3 מקורות שונים
- דעות מנוגדות מהתקשורת הישראלית
- הצהרות רשמיות אם יש

אם לא מוצא מידע נוסף - כתוב במפורש "לא מצאתי מידע נוסף"

נושא: {main_topic}
מידע ראשוני: {article_summary}
"""
        
        # Stage 3: Analysis
        self.analysis_prompt = """
כתוב ניתוח מאוזן תוך שילוב המחקר:

כתוב כתבה עיתונאית זורמת וקריאה שתכלול את כל המידע החשוב מהמחקר, אבל בלי כותרות משנה או חלוקה לסעיפים. הכתבה צריכה להיות טקסט רציף וזורם שכולל:

- פתיח שמציג את המחלוקת
- עובדות מוסכמות
- הצגת כל הצדדים
- מה שחסר מהדיווח
- הקשר רחב
- סיכום מאוזן

חשוב: אל תכתוב כותרות כמו "כותרת אובייקטיבית", "פתיח", "עובדות מוסכמות" וכו'. כתוב טקסט רציף וזורם.

טקסט מקורי: {original_text}
ממצאי מחקר: {research_findings}
"""
        
        # Stage 4: Journalistic writing
        self.journalistic_prompt = """
הפך את הניתוח הטכני הזה לכתבה עיתונאית זורמת וקריאה:

- שפה עיתונאית נעימה
- מעברים חלקים
- ללא ביטויים טכניים
- מעניינת לקורא הממוצע
- טקסט רציף וזורם בלי כותרות משנה או חלוקה לסעיפים

חשוב: אל תכתוב כותרות כמו "כותרת אובייקטיבית", "פתיח", "עובדות מוסכמות", "הצגת כל הצדדים", "מה שחסר מהדיווח", "הקשר רחב", "סיכום מאוזן". כתוב טקסט רציף וזורם.

ניתוח טכני: {technical_analysis}
"""

    def init_anthropic(self):
        """Initialize Anthropic client with API key from environment"""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            print("❌ Error: ANTHROPIC_API_KEY not found in .env.local file")
            return False
        
        try:
            self.anthropic_client = anthropic.Anthropic(api_key=api_key)
            print("✅ Anthropic client initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Error initializing Anthropic client: {e}")
            return False

    def test_internet_access(self):
        """Test if the model has internet access"""
        test_prompt = "חפש באינטרנט מה קרה היום בחדשות ישראל"
        
        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=200,
                messages=[{"role": "user", "content": test_prompt}]
            )
            
            result = response.content[0].text
            if "לא יכול לגשת" in result or "אין לי גישה" in result:
                print("❌ Model has no internet access!")
                return False
            
            print("✅ Model appears to have internet access")
            return True
        except:
            return False

    def verify_research_quality(self, research_result: str) -> bool:
        """Verify research was actually performed"""
        quality_indicators = [
            "מקורות שנמצאו", "לפי דיווח", "על פי", "מתוך כתבה",
            "הצהרה של", "לדברי", "בעיתון", "באתר"
        ]
        
        has_sources = any(indicator in research_result for indicator in quality_indicators)
        is_too_short = len(research_result) < 150
        is_generic = "לא מצאתי" in research_result
        
        return has_sources and not is_too_short and not is_generic

    def check_article_relevance(self, article_content: str, article_title: str) -> Tuple[bool, str]:
        """Check if article is relevant"""
        try:
            prompt = self.relevance_prompt.format(
                title=article_title,
                content=article_content[:2000]
            )
            
            response = self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=200,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            
            relevance_text = response.content[0].text
            
            # Check if the AI explicitly said it's not relevant
            non_relevant_keywords = ["ספורט", "בידור", "עסקים", "שגרתי", "כלכלי"]
            is_relevant = not any(keyword in relevance_text for keyword in non_relevant_keywords)
            
            return is_relevant, relevance_text
            
        except Exception as e:
            print(f"❌ Error in relevance check: {e}")
            return True, "Error in checking relevance"

    def research_topic(self, main_topic: str, article_summary: str) -> str:
        """Research with quality verification"""
        try:
            prompt = self.research_prompt.format(
                main_topic=main_topic,
                article_summary=article_summary
            )
            
            response = self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1500,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            research_result = response.content[0].text
            
            # Verify quality
            if not self.verify_research_quality(research_result):
                print("⚠️ Research quality low - trying again...")
                retry_prompt = f"בצע חיפוש מעמיק יותר על: {main_topic}. חובה למצוא מקורות אמיתיים!"
                retry_response = self.anthropic_client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=1500,
                    messages=[{"role": "user", "content": retry_prompt}]
                )
                research_result = retry_response.content[0].text
            
            return research_result
            
        except Exception as e:
            print(f"❌ Error in research stage: {e}")
            return "Research failed"

    def create_technical_analysis(self, original_text: str, research_findings: str) -> str:
        """Stage 3: Create technical analysis using the analysis prompt"""
        try:
            prompt = self.analysis_prompt.format(
                original_text=original_text[:2000],
                research_findings=research_findings
            )
            
            response = self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=2000,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            print(f"❌ Error in technical analysis: {e}")
            return f"Technical analysis failed: {e}"

    def create_journalistic_article(self, technical_analysis: str) -> str:
        """Stage 4: Convert technical analysis to readable article using the journalistic prompt"""
        try:
            prompt = self.journalistic_prompt.format(
                technical_analysis=technical_analysis
            )
            
            response = self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=2000,
                temperature=0.4,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            print(f"❌ Error in journalistic writing: {e}")
            return f"Journalistic writing failed: {e}"

    def analyze_article_with_anthropic(self, article_content: str, article_title: str) -> Optional[Dict]:
        """Main analysis pipeline using 4-stage approach"""
        print(f"🚀 Starting 4-stage analysis for: {article_title[:50]}...")
        
        # Stage 1: Check relevance
        print("📋 Stage 1: Checking relevance...")
        is_relevant, relevance_reason = self.check_article_relevance(article_content, article_title)
        
        if not is_relevant:
            print(f"🚫 Article not relevant: {relevance_reason}")
            return {
                'analysis': {
                    'relevant': False,
                    'reason': relevance_reason,
                    'category': 'non-political'
                },
                'model_used': "claude-3-haiku-20240307",
                'processed_at': datetime.now().isoformat(),
                'is_relevant': False
            }
        
        print(f"✅ Article is relevant: {relevance_reason}")
        
        # Stage 2: Research
        print("🔍 Stage 2: Researching topic...")
        main_topic = article_title  # Simple topic extraction
        article_summary = article_content[:500]  # First 500 chars as summary
        research_findings = self.research_topic(main_topic, article_summary)
        
        print(f"📚 Research completed, findings length: {len(research_findings)} characters")
        
        # Add delay between stages
        time.sleep(1)
        
        # Stage 3: Technical Analysis
        print("✍️ Stage 3: Technical analysis...")
        technical_analysis = self.create_technical_analysis(article_content, research_findings)
        time.sleep(1)
        
        # Stage 4: Journalistic Writing
        print("📝 Stage 4: Final article...")
        final_article = self.create_journalistic_article(technical_analysis)
        
        # Combine results
        final_result = {
            'technical_analysis': technical_analysis,
            'journalistic_article': final_article,
            'research_notes': research_findings,
            'model_used': "claude-3-haiku-20240307",
            'processed_at': datetime.now().isoformat(),
            'is_relevant': True
        }
        
        print("🎉 4-stage analysis completed successfully")
        print("\n" + "="*80)
        print("📝 FINAL ARTICLE:")
        print("="*80)
        print(final_article)
        print("="*80)
        print()
        
        return final_result

    def get_unprocessed_articles(self) -> List[Dict]:
        """Get all articles where isProcessed = 0"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, title, url, clean_content, created_at 
                FROM news_items 
                WHERE isProcessed = 0 
                ORDER BY created_at ASC
            """)
            
            articles = []
            for row in cursor.fetchall():
                articles.append({
                    'id': row[0],
                    'title': row[1],
                    'url': row[2],
                    'clean_content': row[3],
                    'created_at': row[4]
                })
            
            conn.close()
            print(f"📰 Found {len(articles)} unprocessed articles")
            return articles
            
        except Exception as e:
            print(f"❌ Error getting unprocessed articles: {e}")
            return []

    def update_article_as_processed(self, article_id: int, analysis_data: Dict):
        """Mark article as processed and save analysis data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Determine the isProcessed value based on relevance
            if analysis_data.get('is_relevant', True):
                is_processed_value = 1  # Relevant article - fully processed
                print(f"✅ Article {article_id} marked as RELEVANT (isProcessed = 1)")
            else:
                is_processed_value = 2  # Non-relevant article - marked as such
                print(f"🚫 Article {article_id} marked as NOT RELEVANT (isProcessed = 2)")
            
            # Update the article with the new 4-stage result structure
            cursor.execute("""
                UPDATE news_items 
                SET isProcessed = ?, 
                    process_data = ? 
                WHERE id = ?
            """, (is_processed_value, json.dumps(analysis_data), article_id))
            
            conn.commit()
            conn.close()
            
            print(f"✅ Article {article_id} updated successfully with 4-stage analysis")
            
        except Exception as e:
            print(f"❌ Error updating article {article_id}: {e}")

    def process_articles(self, limit: Optional[int] = None):
        """Main function to process unprocessed articles automatically"""
        print("🚀 Starting automatic article processing with 4-stage pipeline...")
        print("=" * 60)
        
        # Get unprocessed articles
        articles = self.get_unprocessed_articles()
        
        if not articles:
            print("✨ No unprocessed articles found!")
            return
        
        # Apply limit if specified
        if limit:
            articles = articles[:limit]
            print(f"📝 Processing limited to {limit} articles")
        else:
            print(f"📝 Processing ALL {len(articles)} unprocessed articles automatically")
        
        processed_count = 0
        relevant_count = 0
        non_relevant_count = 0
        error_count = 0
        
        for i, article in enumerate(articles, 1):
            print(f"\n📰 Processing article {i}/{len(articles)}: {article['title'][:60]}...")
            print(f"   ID: {article['id']}")
            print(f"   URL: {article['url']}")
            print(f"   Content length: {len(article['clean_content'])} characters")
            
            # Analyze the article using 4-stage pipeline
            analysis_result = self.analyze_article_with_anthropic(
                article['clean_content'], 
                article['title']
            )
            
            if analysis_result:
                # Update the article as processed
                self.update_article_as_processed(article['id'], analysis_result)
                processed_count += 1
                
                # Count relevant vs non-relevant
                if analysis_result.get('is_relevant', True):
                    relevant_count += 1
                    print(f"   ✅ Marked as RELEVANT")
                else:
                    non_relevant_count += 1
                    print(f"   🚫 Marked as NOT RELEVANT")
            else:
                error_count += 1
                print(f"   ❌ Failed to process")
            
            # Add delay to avoid rate limiting
            if i < len(articles):
                print("   ⏳ Waiting 2 seconds before next article...")
                time.sleep(2)
        
        print("\n" + "=" * 60)
        print(f"🎉 Processing complete!")
        print(f"   ✅ Successfully processed: {processed_count}")
        print(f"   🔍 Relevant articles: {relevant_count}")
        print(f"   🚫 Non-relevant articles: {non_relevant_count}")
        print(f"   ❌ Errors: {error_count}")
        print(f"   📊 Total articles: {len(articles)}")

    def show_processing_stats(self):
        """Show statistics about processed vs unprocessed articles"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get counts for all statuses
            cursor.execute("SELECT COUNT(*) FROM news_items WHERE isProcessed = 0")
            unprocessed_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM news_items WHERE isProcessed = 1")
            processed_relevant_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM news_items WHERE isProcessed = 2")
            processed_non_relevant_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM news_items")
            total_count = cursor.fetchone()[0]
            
            conn.close()
            
            print(f"\n📊 Processing Statistics:")
            print(f"   Total articles: {total_count}")
            print(f"   🔍 Relevant & processed: {processed_relevant_count}")
            print(f"   🚫 Non-relevant & marked: {processed_non_relevant_count}")
            print(f"   ⏳ Unprocessed: {unprocessed_count}")
            
            total_processed = processed_relevant_count + processed_non_relevant_count
            if total_count > 0:
                progress = (total_processed/total_count*100)
                print(f"   📈 Progress: {progress:.1f}% ({total_processed}/{total_count})")
            
        except Exception as e:
            print(f"❌ Error getting processing stats: {e}")

def main():
    """Main function - runs silently and processes all articles automatically"""
    print("Article Processor for News Balance Analyzer (4-Stage Pipeline)")
    print("Running in SILENT MODE - Processing ALL articles automatically")
    print("=" * 70)
    
    # Initialize processor
    processor = ArticleProcessor()
    
    if not processor.anthropic_client:
        print("❌ Cannot proceed without Anthropic client")
        return
    
    # Test internet access first
    if not processor.test_internet_access():
        print("⚠️ Warning: Limited internet access detected")
    
    # Show current stats before processing
    processor.show_processing_stats()
    
    # Start automatic processing of ALL remaining articles
    print("\n🚀 Starting automatic processing of ALL remaining articles...")
    print("⏳ This will run silently without user interaction")
    print("=" * 70)
    
    try:
        # Process ALL remaining articles
        processor.process_articles()
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Processing interrupted by user")
        return
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        return
    
    # Show final stats after processing
    print("\n" + "=" * 70)
    print("🎉 AUTOMATIC PROCESSING COMPLETE!")
    print("=" * 70)
    processor.show_processing_stats()

if __name__ == "__main__":
    main()
