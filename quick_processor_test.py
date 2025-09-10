#!/usr/bin/env python3
# -*- coding: utf-8
"""
Quick processor test for Railway
"""

import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

def main():
    print("=" * 60)
    print("QUICK PROCESSOR TEST FOR RAILWAY")
    print("=" * 60)
    
    try:
        print("1. Testing imports...")
        from process_articles_postgres import ArticleProcessor
        print("   ✅ Imports successful")
        
        print("2. Testing processor initialization...")
        processor = ArticleProcessor()
        print("   ✅ Processor initialized")
        
        print("3. Testing database connection...")
        articles = processor.get_unprocessed_articles()
        print(f"   ✅ Found {len(articles)} unprocessed articles")
        
        if articles:
            print("4. Testing single article processing...")
            print(f"   Processing: {articles[0]['title'][:50]}...")
            
            # Process just one article
            result = processor.analyze_article_with_anthropic(
                articles[0]['clean_content'], 
                articles[0]['title']
            )
            
            if result:
                print("   ✅ Article processed successfully!")
                print(f"   Relevant: {result.get('is_relevant', 'Unknown')}")
            else:
                print("   ❌ Article processing failed")
        else:
            print("4. No articles to process")
        
        print("=" * 60)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
