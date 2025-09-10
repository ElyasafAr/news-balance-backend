#!/usr/bin/env python3
# -*- coding: utf-8
"""
Backend Runner for News Balance Analyzer
Runs both Python scripts in an infinite loop:
1. filter_recent_postgres.py - Scrapes live news from Rotter.net
2. process_articles_postgres.py - Processes articles using AI analysis

This script runs continuously as a backend service.
Updated to work with PostgreSQL database
"""

import subprocess
import time
import logging
import signal
import sys
import os
from datetime import datetime
import psycopg2
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

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
        self.database_url = os.getenv('DATABASE_URL')
        self.scraper_running = False  # Flag to prevent parallel execution
        self.processor_running = False  # Flag to prevent parallel execution
        
        # Setup signal handlers for graceful shutdown
        try:
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
        except Exception as e:
            logger.warning("Could not set up signal handlers: " + str(e))
        
        logger.info("Backend Runner initialized")
        logger.info("Scraper interval: " + str(self.scraper_interval) + " seconds")
        logger.info("Processor interval: " + str(self.processor_interval) + " seconds")
    
    def get_db_connection(self):
        """Get PostgreSQL database connection"""
        try:
            conn = psycopg2.connect(self.database_url)
            return conn
        except Exception as e:
            logger.error("Error connecting to database: " + str(e))
            return None
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info("Received signal " + str(signum) + ", shutting down gracefully...")
        self.running = False
    
    def run_script(self, script_name: str, description: str) -> bool:
        """Run a Python script and return success status"""
        try:
            logger.info("Running " + description + "...")
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
                timeout=300  # 5 minutes timeout
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            if result.returncode == 0:
                logger.info("SUCCESS: " + description + " completed successfully in " + str(duration)[:4] + " seconds")
                if result.stdout:
                    logger.info("Output: " + result.stdout[-500:] + "...")  # Last 500 chars
                return True
            else:
                logger.error("FAILED: " + description + " failed with return code " + str(result.returncode))
                if result.stderr:
                    logger.error("Error: " + result.stderr)
                if result.stdout:
                    logger.error("Output: " + result.stdout[-500:] + "...")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("TIMEOUT: " + description + " timed out after 30 minutes")
            return False
        except Exception as e:
            logger.error("ERROR: Error running " + description + ": " + str(e))
            return False
    
    def get_database_stats(self) -> dict:
        """Get current database statistics"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return {}
            
            cursor = conn.cursor()
            
            # Get counts for all statuses
            cursor.execute("SELECT COUNT(*) FROM news_items WHERE isprocessed = 0")
            unprocessed_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM news_items WHERE isprocessed = 1")
            processed_relevant_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM news_items WHERE isprocessed = 2")
            processed_non_relevant_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM news_items")
            total_count = cursor.fetchone()[0]
            
            # Get recent activity
            cursor.execute("""
                SELECT COUNT(*) FROM news_items 
                WHERE created_at >= NOW() - INTERVAL '1 hour'
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
            logger.error("Error getting database stats: " + str(e))
            return {}
    
    def should_run_scraper(self) -> bool:
        """Check if it's time to run the scraper"""
        return time.time() - self.last_scraper_run >= self.scraper_interval
    
    def should_run_processor(self) -> bool:
        """Check if it's time to run the processor"""
        return time.time() - self.last_processor_run >= self.processor_interval
    
    def run_scraper(self):
        """Run the news scraper"""
        if self.scraper_running:
            logger.warning("Scraper is already running, skipping...")
            return
        
        self.scraper_running = True
        try:
            if self.run_script('filter_recent_postgres.py', 'News Scraper'):
                self.last_scraper_run = time.time()
                logger.info("Scraper completed, updating timestamp")
            else:
                logger.error("Scraper failed, will retry on next cycle")
        finally:
            self.scraper_running = False
    
    def run_processor(self):
        """Run the article processor"""
        if self.processor_running:
            logger.warning("Processor is already running, skipping...")
            return
        
        self.processor_running = True
        try:
            if self.run_script('process_articles_postgres.py', 'Article Processor'):
                self.last_processor_run = time.time()
                logger.info("Processor completed, updating timestamp")
            else:
                logger.error("Processor failed, will retry on next cycle")
        finally:
            self.processor_running = False
    
    def log_status(self):
        """Log current status and statistics"""
        logger.info("Status Update:")
        logger.info("=" * 50)
        
        # Try to get database stats
        try:
            stats = self.get_database_stats()
            if stats:
                logger.info("Database Statistics:")
                logger.info("   Total articles: " + str(stats.get('total', 0)))
                logger.info("   Unprocessed: " + str(stats.get('unprocessed', 0)))
                logger.info("   Processed (relevant): " + str(stats.get('processed_relevant', 0)))
                logger.info("   Processed (non-relevant): " + str(stats.get('processed_non_relevant', 0)))
                logger.info("   Last hour activity: " + str(stats.get('last_hour', 0)))
            else:
                logger.warning("Could not get database stats - database might not be accessible")
        except Exception as e:
            logger.error("Error getting database stats: " + str(e))
        
        # Calculate next run times
        next_scraper = self.last_scraper_run + self.scraper_interval - time.time()
        next_processor = self.last_processor_run + self.processor_interval - time.time()
        
        logger.info("Next runs:")
        logger.info("   Scraper: in " + str(next_scraper)[:4] + " seconds")
        logger.info("   Processor: in " + str(next_processor)[:4] + " seconds")
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
                
                logger.info("\nCycle " + str(cycle_count) + " - " + current_time)
                logger.info("=" * 60)
                
                # Run processes synchronously - one after another
                # First: Run scraper if needed
                if self.should_run_scraper() and not self.scraper_running:
                    logger.info("Time to run scraper...")
                    self.run_scraper()
                    logger.info("Scraper completed, waiting 10 seconds before processor...")
                    time.sleep(10)  # Wait 10 seconds between processes
                else:
                    if self.scraper_running:
                        logger.info("Scraper already running, skipping...")
                    else:
                        logger.info("Scraper not due yet")
                
                # Second: Run processor if needed (after scraper is done)
                if self.should_run_processor() and not self.processor_running:
                    logger.info("Time to run processor...")
                    self.run_processor()
                    logger.info("Processor completed")
                else:
                    if self.processor_running:
                        logger.info("Processor already running, skipping...")
                    else:
                        logger.info("Processor not due yet")
                
                # Log current status
                self.log_status()
                
                # Wait before next cycle (5 minutes = 300 seconds)
                logger.info("Sleeping for 300 seconds (5 minutes) before next cycle...")
                time.sleep(300)
                
            except KeyboardInterrupt:
                logger.info("Interrupted by user")
                self.running = False
                break
            except Exception as e:
                logger.error("Unexpected error in main loop: " + str(e))
                logger.info("Waiting 300 seconds (5 minutes) before retrying...")
                time.sleep(300)
        
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
    required_files = ['filter_recent_postgres.py', 'process_articles_postgres.py']
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print("ERROR: Missing required files: " + str(missing_files))
        print("Please ensure all required scripts are in the current directory")
        return
    
    # Check if .env.local exists for API keys
    if not os.path.exists('.env.local'):
        print("WARNING: .env.local file not found. Make sure you have ANTHROPIC_API_KEY configured.")
    
    print("\nStarting backend service...")
    print("Press Ctrl+C to stop")
    
    runner = BackendRunner()
    runner.run()

if __name__ == "__main__":
    main()
