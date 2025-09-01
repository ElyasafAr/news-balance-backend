#!/usr/bin/env python3
# -*- coding: utf-8
"""
Backend Runner for News Balance Analyzer
Runs both Python scripts in an infinite loop:
1. filter_recent.py - Scrapes live news from Rotter.net
2. process_articles.py - Processes articles using AI analysis

This script runs continuously as a backend service.
"""

import subprocess
import time
import logging
import signal
import sys
import os
from datetime import datetime
import sqlite3
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backend_runner.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class BackendRunner:
    def __init__(self):
        self.running = True
        self.scraper_interval = 60  # 1 minute between scraping runs
        self.processor_interval = 60  # 1 minute between processing runs
        self.last_scraper_run = 0
        self.last_processor_run = 0
        self.db_path = "rotter_news.db"
        
        # Setup signal handlers for graceful shutdown
        try:
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
        except Exception as e:
            logger.warning(f"Could not set up signal handlers: {e}")
        
        logger.info("Backend Runner initialized")
        logger.info(f"Scraper interval: {self.scraper_interval} seconds")
        logger.info(f"Processor interval: {self.processor_interval} seconds")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def run_script(self, script_name: str, description: str) -> bool:
        """Run a Python script and return success status"""
        try:
            logger.info(f"Running {description}...")
            start_time = time.time()
            
            # Run the script with proper environment for Windows
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            # Run the script
            result = subprocess.run(
                [sys.executable, script_name],
                capture_output=True,
                text=True,
                encoding='utf-8',
                env=env,
                timeout=1800  # 30 minutes timeout
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            if result.returncode == 0:
                logger.info(f"SUCCESS: {description} completed successfully in {duration:.1f} seconds")
                if result.stdout:
                    logger.info(f"Output: {result.stdout[-500:]}...")  # Last 500 chars
                return True
            else:
                logger.error(f"FAILED: {description} failed with return code {result.returncode}")
                if result.stderr:
                    logger.error(f"Error: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"TIMEOUT: {description} timed out after 30 minutes")
            return False
        except Exception as e:
            logger.error(f"ERROR: Error running {description}: {e}")
            return False
    
    def get_database_stats(self) -> dict:
        """Get current database statistics"""
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
            
            # Get recent activity
            cursor.execute("""
                SELECT COUNT(*) FROM news_items 
                WHERE datetime(created_at) >= datetime('now', '-1 hour')
            """)
            last_hour_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total': total_count,
                'unprocessed': unprocessed_count,
                'processed_relevant': processed_relevant_count,
                'processed_non_relevant': processed_non_relevant_count,
                'last_hour': last_hour_count
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting database stats: {e}")
            return {}
    
    def should_run_scraper(self) -> bool:
        """Check if it's time to run the scraper"""
        return time.time() - self.last_scraper_run >= self.scraper_interval
    
    def should_run_processor(self) -> bool:
        """Check if it's time to run the processor"""
        return time.time() - self.last_processor_run >= self.processor_interval
    
    def run_scraper(self):
        """Run the news scraper"""
        if self.run_script('filter_recent.py', 'News Scraper'):
            self.last_scraper_run = time.time()
            logger.info("Scraper completed, updating timestamp")
        else:
            logger.error("Scraper failed, will retry on next cycle")
    
    def run_processor(self):
        """Run the article processor"""
        if self.run_script('process_articles.py', 'Article Processor'):
            self.last_processor_run = time.time()
            logger.info("Processor completed, updating timestamp")
        else:
            logger.error("Processor failed, will retry on next cycle")
    
    def log_status(self):
        """Log current status and statistics"""
        logger.info("📊 Status Update:")
        logger.info("=" * 50)
        
        # Try to get database stats
        try:
            stats = self.get_database_stats()
            if stats:
                logger.info(f"🗄️ Database Statistics:")
                logger.info(f"   📈 Total articles: {stats.get('total', 0)}")
                logger.info(f"   ⏳ Unprocessed: {stats.get('unprocessed', 0)}")
                logger.info(f"   ✅ Processed (relevant): {stats.get('processed_relevant', 0)}")
                logger.info(f"   ❌ Processed (non-relevant): {stats.get('processed_non_relevant', 0)}")
                logger.info(f"   🕐 Last hour activity: {stats.get('last_hour', 0)}")
            else:
                logger.warning("⚠️ Could not get database stats - database might not be accessible")
        except Exception as e:
            logger.error(f"💥 Error getting database stats: {e}")
        
        # Calculate next run times
        next_scraper = self.last_scraper_run + self.scraper_interval - time.time()
        next_processor = self.last_processor_run + self.processor_interval - time.time()
        
        logger.info(f"⏰ Next runs:")
        logger.info(f"   🕷️ Scraper: in {next_scraper:.0f} seconds")
        logger.info(f"   🧠 Processor: in {next_processor:.0f} seconds")
        logger.info("=" * 50)
    
    def run(self):
        """Main loop - run continuously"""
        logger.info("Starting Backend Runner main loop...")
        logger.info("Press Ctrl+C to stop gracefully")
        
        # Initialize timestamps
        self.last_scraper_run = time.time() - self.scraper_interval  # Run scraper immediately
        self.last_processor_run = time.time() - self.processor_interval  # Run processor immediately
        
        cycle_count = 0
        
        while self.running:
            try:
                cycle_count += 1
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                logger.info(f"\nCycle {cycle_count} - {current_time}")
                logger.info("=" * 60)
                
                # Check if we should run the scraper
                if self.should_run_scraper():
                    logger.info("Time to run scraper...")
                    self.run_scraper()
                else:
                    logger.info("Scraper not due yet")
                
                # Check if we should run the processor
                if self.should_run_processor():
                    logger.info("Time to run processor...")
                    self.run_processor()
                else:
                    logger.info("Processor not due yet")
                
                # Log current status
                self.log_status()
                
                # Wait before next cycle
                logger.info("Sleeping for 60 seconds before next cycle...")
                time.sleep(60)
                
            except KeyboardInterrupt:
                logger.info("Interrupted by user")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                logger.info("Waiting 60 seconds before retrying...")
                time.sleep(60)
        
        logger.info("Backend Runner stopped gracefully")

def main():
    """Main function"""
    print("News Balance Analyzer - Backend Runner")
    print("=" * 50)
    print("This service will run continuously and:")
    print("Scrape news every 1 minute")
    print("Process articles every 1 minute")
    print("Provide real-time status updates")
    print("=" * 50)
    
    # Check if required files exist
    required_files = ['filter_recent.py', 'process_articles.py']
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print(f"ERROR: Missing required files: {missing_files}")
        print("Please ensure all required scripts are in the current directory")
        return
    
    # Check if database exists
    if not os.path.exists('rotter_news.db'):
        print("WARNING: Database not found. The scraper will create it on first run.")
    
    # Check if .env.local exists for API keys
    if not os.path.exists('.env.local'):
        print("WARNING: .env.local file not found. Make sure you have ANTHROPIC_API_KEY configured.")
    
    print("\nStarting backend service...")
    print("Press Ctrl+C to stop")
    
    runner = BackendRunner()
    runner.run()

if __name__ == "__main__":
    main()
