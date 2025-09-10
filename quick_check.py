#!/usr/bin/env python3
# -*- coding: utf-8
"""
Quick Check Script - Fast status check for News Balance Backend
"""

import psycopg2
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

def quick_check():
    """Quick status check"""
    print("🔍 QUICK STATUS CHECK")
    print("=" * 40)
    
    # Database connection
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()
        
        # Basic stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN isprocessed = 0 THEN 1 END) as unprocessed,
                COUNT(CASE WHEN isprocessed = 1 THEN 1 END) as relevant,
                COUNT(CASE WHEN isprocessed = 2 THEN 1 END) as non_relevant,
                MAX(created_at) as last_article
            FROM news_items
        """)
        stats = cursor.fetchone()
        
        print(f"✅ Database: Connected")
        print(f"📊 Total Articles: {stats[0]}")
        print(f"⏳ Unprocessed: {stats[1]}")
        print(f"✅ Relevant: {stats[2]}")
        print(f"❌ Non-relevant: {stats[3]}")
        print(f"📅 Last Article: {stats[4]}")
        
        # Check recent activity
        cursor.execute("""
            SELECT COUNT(*) as recent_articles
            FROM news_items 
            WHERE created_at >= NOW() - INTERVAL '1 hour'
        """)
        recent = cursor.fetchone()
        print(f"🕐 Articles (1h): {recent[0]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database Error: {e}")
        return False
    
    # Check if system is running
    print(f"\n🕐 Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("✅ Quick check completed!")
    return True

if __name__ == "__main__":
    quick_check()
