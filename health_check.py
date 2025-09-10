#!/usr/bin/env python3
# -*- coding: utf-8
"""
Health Check Script for News Balance Backend
Checks all system components and provides status report
"""

import psycopg2
import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from logging_system import get_logger

# Load environment variables
load_dotenv('.env.local')

class HealthChecker:
    def __init__(self):
        self.logger = get_logger("HealthChecker")
        self.database_url = os.getenv('DATABASE_URL')
        self.anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        self.grok_key = os.getenv('groc_API_key')
        
    def check_database(self) -> Dict:
        """Check database connectivity and health"""
        try:
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor()
            
            # Check basic connectivity
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
            # Check table structure
            cursor.execute("""
                SELECT table_name, column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'news_items'
                ORDER BY ordinal_position
            """)
            columns = cursor.fetchall()
            
            # Check recent activity
            cursor.execute("""
                SELECT COUNT(*) as total_articles,
                       COUNT(CASE WHEN isprocessed = 0 THEN 1 END) as unprocessed,
                       COUNT(CASE WHEN isprocessed = 1 THEN 1 END) as processed_relevant,
                       COUNT(CASE WHEN isprocessed = 2 THEN 1 END) as processed_non_relevant
                FROM news_items
            """)
            stats = cursor.fetchone()
            
            # Check recent logs
            cursor.execute("""
                SELECT COUNT(*) as log_count
                FROM system_logs 
                WHERE timestamp >= NOW() - INTERVAL '1 hour'
            """)
            recent_logs = cursor.fetchone()
            
            conn.close()
            
            return {
                'status': 'healthy',
                'connection': 'ok',
                'tables': len(columns),
                'articles_total': stats[0],
                'articles_unprocessed': stats[1],
                'articles_relevant': stats[2],
                'articles_non_relevant': stats[3],
                'recent_logs': recent_logs[0]
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def check_anthropic_api(self) -> Dict:
        """Check Anthropic API connectivity"""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.anthropic_key)
            
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=10,
                messages=[{"role": "user", "content": "Test"}]
            )
            
            return {
                'status': 'healthy',
                'model': 'claude-3-haiku-20240307',
                'response_length': len(response.content[0].text)
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def check_grok_api(self) -> Dict:
        """Check Grok API connectivity"""
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=self.grok_key,
                base_url="https://api.x.ai/v1"
            )
            
            response = client.chat.completions.create(
                model="grok-3",
                max_tokens=10,
                messages=[{"role": "user", "content": "Test"}]
            )
            
            return {
                'status': 'healthy',
                'model': 'grok-3',
                'response_length': len(response.choices[0].message.content)
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def check_scraper(self) -> Dict:
        """Check if scraper can access Rotter.net"""
        try:
            response = requests.get("https://rotter.net/forum/scoops1/", timeout=10)
            
            return {
                'status': 'healthy' if response.status_code == 200 else 'error',
                'status_code': response.status_code,
                'response_size': len(response.content)
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def check_recent_activity(self) -> Dict:
        """Check recent system activity"""
        try:
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor()
            
            # Check last article processing
            cursor.execute("""
                SELECT MAX(created_at) as last_article,
                       COUNT(*) as articles_last_hour
                FROM news_items 
                WHERE created_at >= NOW() - INTERVAL '1 hour'
            """)
            article_activity = cursor.fetchone()
            
            # Check last processing activity
            cursor.execute("""
                SELECT MAX(timestamp) as last_processing,
                       COUNT(*) as processing_events_last_hour
                FROM system_logs 
                WHERE component IN ('Scraper', 'Processor') 
                AND timestamp >= NOW() - INTERVAL '1 hour'
            """)
            processing_activity = cursor.fetchone()
            
            conn.close()
            
            return {
                'last_article': article_activity[0],
                'articles_last_hour': article_activity[1],
                'last_processing': processing_activity[0],
                'processing_events_last_hour': processing_activity[1]
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def run_full_check(self) -> Dict:
        """Run complete health check"""
        self.logger.info("Starting full health check")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'database': self.check_database(),
            'anthropic_api': self.check_anthropic_api(),
            'grok_api': self.check_grok_api(),
            'scraper': self.check_scraper(),
            'recent_activity': self.check_recent_activity()
        }
        
        # Determine overall status
        all_healthy = all(
            result.get('status') == 'healthy' 
            for result in results.values() 
            if isinstance(result, dict) and 'status' in result
        )
        
        results['overall_status'] = 'healthy' if all_healthy else 'degraded'
        
        self.logger.info("Health check completed", {'overall_status': results['overall_status']})
        
        return results
    
    def print_status_report(self, results: Dict):
        """Print formatted status report"""
        print("\n" + "="*60)
        print("🏥 NEWS BALANCE BACKEND - HEALTH CHECK REPORT")
        print("="*60)
        print(f"📅 Timestamp: {results['timestamp']}")
        print(f"🎯 Overall Status: {results['overall_status'].upper()}")
        print()
        
        # Database Status
        db = results['database']
        if db['status'] == 'healthy':
            print("✅ DATABASE: Healthy")
            print(f"   📊 Total Articles: {db['articles_total']}")
            print(f"   ⏳ Unprocessed: {db['articles_unprocessed']}")
            print(f"   ✅ Processed (Relevant): {db['articles_relevant']}")
            print(f"   ❌ Processed (Non-relevant): {db['articles_non_relevant']}")
            print(f"   📝 Recent Logs (1h): {db['recent_logs']}")
        else:
            print("❌ DATABASE: Error")
            print(f"   🚨 {db['error']}")
        
        print()
        
        # API Status
        anthropic = results['anthropic_api']
        if anthropic['status'] == 'healthy':
            print("✅ ANTHROPIC API: Healthy")
            print(f"   🤖 Model: {anthropic['model']}")
        else:
            print("❌ ANTHROPIC API: Error")
            print(f"   🚨 {anthropic['error']}")
        
        grok = results['grok_api']
        if grok['status'] == 'healthy':
            print("✅ GROK API: Healthy")
            print(f"   🤖 Model: {grok['model']}")
        else:
            print("❌ GROK API: Error")
            print(f"   🚨 {grok['error']}")
        
        print()
        
        # Scraper Status
        scraper = results['scraper']
        if scraper['status'] == 'healthy':
            print("✅ SCRAPER: Healthy")
            print(f"   🌐 Status Code: {scraper['status_code']}")
        else:
            print("❌ SCRAPER: Error")
            print(f"   🚨 {scraper['error']}")
        
        print()
        
        # Recent Activity
        activity = results['recent_activity']
        if 'error' not in activity:
            print("📈 RECENT ACTIVITY:")
            print(f"   📰 Last Article: {activity['last_article']}")
            print(f"   📊 Articles (1h): {activity['articles_last_hour']}")
            print(f"   ⚙️ Last Processing: {activity['last_processing']}")
            print(f"   🔄 Processing Events (1h): {activity['processing_events_last_hour']}")
        else:
            print("❌ RECENT ACTIVITY: Error")
            print(f"   🚨 {activity['error']}")
        
        print("\n" + "="*60)

def main():
    """Main function"""
    print("🔍 Starting Health Check...")
    
    checker = HealthChecker()
    results = checker.run_full_check()
    checker.print_status_report(results)
    
    # Save results to file
    with open('health_check_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    
    print("\n💾 Results saved to health_check_results.json")
    
    # Return exit code based on status
    if results['overall_status'] == 'healthy':
        print("🎉 All systems operational!")
        return 0
    else:
        print("⚠️ Some systems need attention!")
        return 1

if __name__ == "__main__":
    exit(main())
