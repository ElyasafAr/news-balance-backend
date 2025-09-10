#!/usr/bin/env python3
# -*- coding: utf-8
"""
Simple test script to check if the processor can run
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

def test_environment():
    """Test if all required environment variables are set"""
    print("Testing environment variables...")
    
    required_vars = ['DATABASE_URL', 'ANTHROPIC_API_KEY', 'groc_API_key']
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {'*' * 10}...{value[-4:]}")
        else:
            print(f"❌ {var}: NOT SET")
    
    return all(os.getenv(var) for var in required_vars)

def test_processor():
    """Test if processor can initialize"""
    print("\nTesting processor initialization...")
    
    try:
        from process_articles_postgres import ArticleProcessor
        processor = ArticleProcessor()
        print("✅ Processor initialized successfully")
        
        # Test database connection
        articles = processor.get_unprocessed_articles()
        print(f"✅ Database connection: {len(articles)} unprocessed articles")
        
        return True
    except Exception as e:
        print(f"❌ Processor initialization failed: {e}")
        return False

def main():
    """Main test function"""
    print("=" * 50)
    print("PROCESSOR DIAGNOSTIC TEST")
    print("=" * 50)
    
    env_ok = test_environment()
    processor_ok = test_processor()
    
    print("\n" + "=" * 50)
    if env_ok and processor_ok:
        print("✅ ALL TESTS PASSED - Processor should work")
    else:
        print("❌ SOME TESTS FAILED - Check the issues above")
    print("=" * 50)

if __name__ == "__main__":
    main()
