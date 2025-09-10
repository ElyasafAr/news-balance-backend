#!/usr/bin/env python3
# -*- coding: utf-8
"""
Advanced Logging System for News Balance Backend
Stores logs in PostgreSQL database for monitoring and debugging
"""

import psycopg2
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

class DatabaseLogger:
    def __init__(self, database_url: str = None):
        """Initialize database logger"""
        self.database_url = database_url or os.getenv('DATABASE_URL')
        self.init_logs_table()
        
    def get_db_connection(self):
        """Get database connection"""
        try:
            return psycopg2.connect(self.database_url)
        except Exception as e:
            print("Database connection failed: " + str(e))
            return None
    
    def init_logs_table(self):
        """Create logs table if it doesn't exist"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return False
                
            cursor = conn.cursor()
            
            # Create logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_logs (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    level VARCHAR(20) NOT NULL,
                    component VARCHAR(50) NOT NULL,
                    message TEXT NOT NULL,
                    details JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create performance metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metric_name VARCHAR(100) NOT NULL,
                    metric_value DECIMAL(10,2) NOT NULL,
                    component VARCHAR(50) NOT NULL,
                    details JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            conn.close()
            print("Logging tables initialized successfully")
            return True
            
        except Exception as e:
            print("Error initializing logging tables: " + str(e))
            return False
    
    def log(self, level: str, component: str, message: str, details: Dict = None):
        """Log a message to database"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return False
                
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO system_logs (level, component, message, details)
                VALUES (%s, %s, %s, %s)
            """, (level, component, message, json.dumps(details) if details else None))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print("Error logging to database: " + str(e))
            return False
    
    def log_performance(self, metric_name: str, metric_value: float, component: str, details: Dict = None):
        """Log performance metrics"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return False
                
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO performance_metrics (metric_name, metric_value, component, details)
                VALUES (%s, %s, %s, %s)
            """, (metric_name, metric_value, component, json.dumps(details) if details else None))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print("Error logging performance metrics: " + str(e))
            return False
    
    def get_recent_logs(self, limit: int = 100, level: str = None) -> List[Dict]:
        """Get recent logs"""
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
                logs.append({
                    'timestamp': row[0],
                    'level': row[1],
                    'component': row[2],
                    'message': row[3],
                    'details': json.loads(row[4]) if row[4] else None
                })
            
            conn.close()
            return logs
            
        except Exception as e:
            print("Error getting logs: " + str(e))
            return []
    
    def get_performance_summary(self, hours: int = 24) -> Dict:
        """Get performance summary for last N hours"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return {}
                
            cursor = conn.cursor()
            
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
            
            summary = {}
            for row in cursor.fetchall():
                component = row[0]
                metric_name = row[1]
                
                if component not in summary:
                    summary[component] = {}
                
                summary[component][metric_name] = {
                    'avg': float(row[2]),
                    'max': float(row[3]),
                    'min': float(row[4]),
                    'count': row[5]
                }
            
            conn.close()
            return summary
            
        except Exception as e:
            print("Error getting performance summary: " + str(e))
            return {}

class EnhancedLogger:
    """Enhanced logger that combines file and database logging"""
    
    def __init__(self, name: str, database_url: str = None):
        self.name = name
        self.db_logger = DatabaseLogger(database_url)
        
        # Setup file logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('backend_runner.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(name)
    
    def info(self, message: str, details: Dict = None):
        """Log info message"""
        self.logger.info(message)
        self.db_logger.log('INFO', self.name, message, details)
    
    def error(self, message: str, details: Dict = None):
        """Log error message"""
        self.logger.error(message)
        self.db_logger.log('ERROR', self.name, message, details)
    
    def warning(self, message: str, details: Dict = None):
        """Log warning message"""
        self.logger.warning(message)
        self.db_logger.log('WARNING', self.name, message, details)
    
    def debug(self, message: str, details: Dict = None):
        """Log debug message"""
        self.logger.debug(message)
        self.db_logger.log('DEBUG', self.name, message, details)
    
    def performance(self, metric_name: str, value: float, details: Dict = None):
        """Log performance metric"""
        self.db_logger.log_performance(metric_name, value, self.name, details)

def get_logger(name: str) -> EnhancedLogger:
    """Get enhanced logger instance"""
    return EnhancedLogger(name)
