#!/usr/bin/env python3
# -*- coding: utf-8
"""
News Balance Backend Monitor
Simple Python script to read and display all data from PostgreSQL database
"""

import psycopg2
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

class NewsMonitor:
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
    
    def get_db_connection(self):
        """Get database connection"""
        try:
            return psycopg2.connect(self.database_url)
        except Exception as e:
            print("❌ Database connection failed: " + str(e))
            return None
    
    def get_articles(self, limit=10, status=None):
        """Get articles with optional filtering"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return []
            
            cursor = conn.cursor()
            
            if status is not None:
                cursor.execute("""
                    SELECT id, title, url, isprocessed, created_at, actual_datetime
                    FROM news_items 
                    WHERE isprocessed = %s
                    ORDER BY created_at DESC 
                    LIMIT %s
                """, (status, limit))
            else:
                cursor.execute("""
                    SELECT id, title, url, isprocessed, created_at, actual_datetime
                    FROM news_items 
                    ORDER BY created_at DESC 
                    LIMIT %s
                """, (limit,))
            
            articles = []
            for row in cursor.fetchall():
                status_text = {0: "⏳ Unprocessed", 1: "✅ Relevant", 2: "❌ Non-relevant"}.get(row[3], "❓ Unknown")
                articles.append({
                    'id': row[0],
                    'title': row[1],
                    'url': row[2],
                    'status': status_text,
                    'created_at': row[4],
                    'actual_datetime': row[5]
                })
            
            conn.close()
            return articles
            
        except Exception as e:
            print("❌ Error getting articles: " + str(e))
            return []
    
    def get_article_details(self, article_id):
        """Get full article details including processed content"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return None
            
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, title, url, content, clean_content, isprocessed, 
                       process_data, created_at, actual_datetime
                FROM news_items 
                WHERE id = %s
            """, (article_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            process_data = json.loads(row[6]) if row[6] else None
            
            article = {
                'id': row[0],
                'title': row[1],
                'url': row[2],
                'content': row[3],
                'clean_content': row[4],
                'isprocessed': row[5],
                'process_data': process_data,
                'created_at': row[7],
                'actual_datetime': row[8]
            }
            
            conn.close()
            return article
            
        except Exception as e:
            print("❌ Error getting article details: " + str(e))
            return None
    
    def get_statistics(self):
        """Get comprehensive statistics"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return {}
            
            cursor = conn.cursor()
            
            # Overall stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN isprocessed = 0 THEN 1 END) as unprocessed,
                    COUNT(CASE WHEN isprocessed = 1 THEN 1 END) as relevant,
                    COUNT(CASE WHEN isprocessed = 2 THEN 1 END) as non_relevant,
                    MAX(created_at) as last_article,
                    MIN(created_at) as first_article
                FROM news_items
            """)
            overall = cursor.fetchone()
            
            # Last 24 hours
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_24h,
                    COUNT(CASE WHEN isprocessed = 0 THEN 1 END) as unprocessed_24h,
                    COUNT(CASE WHEN isprocessed = 1 THEN 1 END) as relevant_24h,
                    COUNT(CASE WHEN isprocessed = 2 THEN 1 END) as non_relevant_24h
                FROM news_items
                WHERE created_at >= NOW() - INTERVAL '24 hours'
            """)
            last_24h = cursor.fetchone()
            
            # Last 7 days
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_7d,
                    COUNT(CASE WHEN isprocessed = 1 THEN 1 END) as relevant_7d
                FROM news_items
                WHERE created_at >= NOW() - INTERVAL '7 days'
            """)
            last_7d = cursor.fetchone()
            
            # Processing rate today
            cursor.execute("""
                SELECT COUNT(*) as processed_today
                FROM news_items
                WHERE isprocessed > 0 
                AND created_at >= CURRENT_DATE
            """)
            processed_today = cursor.fetchone()
            
            conn.close()
            
            return {
                'overall': {
                    'total': overall[0],
                    'unprocessed': overall[1],
                    'relevant': overall[2],
                    'non_relevant': overall[3],
                    'last_article': overall[4],
                    'first_article': overall[5]
                },
                'last_24h': {
                    'total': last_24h[0],
                    'unprocessed': last_24h[1],
                    'relevant': last_24h[2],
                    'non_relevant': last_24h[3]
                },
                'last_7d': {
                    'total': last_7d[0],
                    'relevant': last_7d[1]
                },
                'processed_today': processed_today[0]
            }
            
        except Exception as e:
            print("❌ Error getting statistics: " + str(e))
            return {}
    
    def get_system_logs(self, limit=50, level=None):
        """Get system logs"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return []
            
            cursor = conn.cursor()
            
            if level:
                cursor.execute("""
                    SELECT timestamp, level, component, message, details
                    FROM system_logs 
                    WHERE level = %s
                    ORDER BY timestamp DESC 
                    LIMIT %s
                """, (level, limit))
            else:
                cursor.execute("""
                    SELECT timestamp, level, component, message, details
                    FROM system_logs 
                    ORDER BY timestamp DESC 
                    LIMIT %s
                """, (limit,))
            
            logs = []
            for row in cursor.fetchall():
                details = json.loads(row[4]) if row[4] else None
                logs.append({
                    'timestamp': row[0],
                    'level': row[1],
                    'component': row[2],
                    'message': row[3],
                    'details': details
                })
            
            conn.close()
            return logs
            
        except Exception as e:
            print("❌ Error getting logs: " + str(e))
            return []
    
    def get_performance_metrics(self, hours=24):
        """Get performance metrics"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return {}
            
            cursor = conn.cursor()
            
            # Check if performance_metrics table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'performance_metrics'
                )
            """)
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                return {'message': 'Performance metrics table not found'}
            
            # Get recent metrics
            cursor.execute("""
                SELECT 
                    component,
                    metric_name,
                    AVG(metric_value) as avg_value,
                    MAX(metric_value) as max_value,
                    MIN(metric_value) as min_value,
                    COUNT(*) as count
                FROM performance_metrics 
                WHERE timestamp >= NOW() - INTERVAL '%s hours'
                GROUP BY component, metric_name
                ORDER BY component, metric_name
            """, (hours,))
            
            metrics = {}
            for row in cursor.fetchall():
                component = row[0]
                metric_name = row[1]
                
                if component not in metrics:
                    metrics[component] = {}
                
                metrics[component][metric_name] = {
                    'avg': float(row[2]) if row[2] else 0,
                    'max': float(row[3]) if row[3] else 0,
                    'min': float(row[4]) if row[4] else 0,
                    'count': row[5]
                }
            
            conn.close()
            return metrics
            
        except Exception as e:
            print("❌ Error getting performance metrics: " + str(e))
            return {}
    
    def print_dashboard(self):
        """Print formatted dashboard"""
        print("\n" + "="*80)
        print("📊 NEWS BALANCE BACKEND - MONITOR DASHBOARD")
        print("="*80)
        print(f"🕐 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Statistics
        stats = self.get_statistics()
        if stats:
            print("📰 ARTICLE STATISTICS")
            print("-" * 50)
            overall = stats['overall']
            last_24h = stats['last_24h']
            
            print(f"📊 Total Articles: {overall['total']}")
            print(f"⏳ Unprocessed: {overall['unprocessed']}")
            print(f"✅ Relevant: {overall['relevant']}")
            print(f"❌ Non-relevant: {overall['non_relevant']}")
            print(f"📅 Last Article: {overall['last_article']}")
            print(f"🔄 Processed Today: {stats['processed_today']}")
            print()
            
            print("📈 LAST 24 HOURS")
            print("-" * 50)
            print(f"📊 New Articles: {last_24h['total']}")
            print(f"⏳ Unprocessed: {last_24h['unprocessed']}")
            print(f"✅ Processed (Relevant): {last_24h['relevant']}")
            print(f"❌ Processed (Non-relevant): {last_24h['non_relevant']}")
            print()
        
        # Recent Articles
        print("📰 RECENT ARTICLES")
        print("-" * 50)
        articles = self.get_articles(limit=5)
        for article in articles:
            print(f"{article['status']} | {article['title'][:60]}...")
            print(f"   📅 {article['created_at']} | 🔗 {article['url']}")
            print()
        
        # Recent Logs
        print("📝 RECENT SYSTEM LOGS")
        print("-" * 50)
        logs = self.get_system_logs(limit=10)
        for log in logs:
            emoji = "🔴" if log['level'] == "ERROR" else "🟡" if log['level'] == "WARNING" else "🔵"
            print(f"{emoji} {log['timestamp']} | {log['component']}: {log['message'][:50]}...")
        
        print("\n" + "="*80)
    
    def export_to_json(self, filename="monitor_data.json"):
        """Export all data to JSON file"""
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'statistics': self.get_statistics(),
                'recent_articles': self.get_articles(limit=20),
                'recent_logs': self.get_system_logs(limit=100),
                'performance_metrics': self.get_performance_metrics()
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            
            print(f"✅ Data exported to {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Error exporting data: {e}")
            return False

def main():
    """Main function with menu"""
    monitor = NewsMonitor()
    
    while True:
        print("\n" + "="*50)
        print("📊 NEWS BALANCE MONITOR")
        print("="*50)
        print("1. 📊 Show Dashboard")
        print("2. 📰 Show Recent Articles")
        print("3. 📝 Show System Logs")
        print("4. 🔍 Show Article Details")
        print("5. 📈 Show Statistics")
        print("6. 💾 Export to JSON")
        print("7. ❌ Exit")
        print("-" * 50)
        
        choice = input("Choose option (1-7): ").strip()
        
        if choice == "1":
            monitor.print_dashboard()
        elif choice == "2":
            articles = monitor.get_articles(limit=10)
            print("\n📰 RECENT ARTICLES:")
            for article in articles:
                print(f"{article['status']} | {article['title']}")
                print(f"   📅 {article['created_at']} | 🔗 {article['url']}")
                print()
        elif choice == "3":
            logs = monitor.get_system_logs(limit=20)
            print("\n📝 SYSTEM LOGS:")
            for log in logs:
                emoji = "🔴" if log['level'] == "ERROR" else "🟡" if log['level'] == "WARNING" else "🔵"
                print(f"{emoji} {log['timestamp']} | {log['component']}: {log['message']}")
        elif choice == "4":
            article_id = input("Enter article ID: ").strip()
            if article_id.isdigit():
                article = monitor.get_article_details(int(article_id))
                if article:
                    print(f"\n📰 ARTICLE #{article['id']}")
                    print(f"Title: {article['title']}")
                    print(f"URL: {article['url']}")
                    print(f"Status: {article['isprocessed']}")
                    print(f"Created: {article['created_at']}")
                    if article['process_data']:
                        print(f"Processed: {article['process_data'].get('processed_at', 'N/A')}")
                else:
                    print("❌ Article not found")
            else:
                print("❌ Invalid article ID")
        elif choice == "5":
            stats = monitor.get_statistics()
            print("\n📈 STATISTICS:")
            print(json.dumps(stats, indent=2, default=str))
        elif choice == "6":
            monitor.export_to_json()
        elif choice == "7":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main()
