#!/usr/bin/env python3
# -*- coding: utf-8
"""
Dashboard Script for News Balance Backend
Provides real-time statistics and monitoring
"""

import psycopg2
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from logging_system import get_logger

# Load environment variables
load_dotenv('.env.local')

class Dashboard:
    def __init__(self):
        self.logger = get_logger("Dashboard")
        self.database_url = os.getenv('DATABASE_URL')
    
    def get_db_connection(self):
        """Get database connection"""
        try:
            return psycopg2.connect(self.database_url)
        except Exception as e:
            print("Database connection failed: " + str(e))
            return None
    
    def get_article_stats(self) -> Dict:
        """Get article processing statistics"""
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
                    MAX(created_at) as last_article
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
            
            # Processing rate
            cursor.execute("""
                SELECT 
                    COUNT(*) as processed_today
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
                    'last_article': overall[4]
                },
                'last_24h': {
                    'total': last_24h[0],
                    'unprocessed': last_24h[1],
                    'relevant': last_24h[2],
                    'non_relevant': last_24h[3]
                },
                'processed_today': processed_today[0]
            }
            
        except Exception as e:
            self.logger.error("Error getting article stats: " + str(e))
            return {}
    
    def get_system_logs(self, hours: int = 24) -> Dict:
        """Get system logs summary"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return {}
            
            cursor = conn.cursor()
            
            # Log counts by level
            cursor.execute("""
                SELECT 
                    level,
                    COUNT(*) as count
                FROM system_logs
                WHERE timestamp >= NOW() - INTERVAL '%s hours'
                GROUP BY level
                ORDER BY count DESC
            """, (hours,))
            log_levels = dict(cursor.fetchall())
            
            # Recent errors
            cursor.execute("""
                SELECT 
                    timestamp,
                    component,
                    message
                FROM system_logs
                WHERE level = 'ERROR'
                AND timestamp >= NOW() - INTERVAL '%s hours'
                ORDER BY timestamp DESC
                LIMIT 10
            """, (hours,))
            recent_errors = [
                {'timestamp': row[0], 'component': row[1], 'message': row[2]}
                for row in cursor.fetchall()
            ]
            
            # Component activity
            cursor.execute("""
                SELECT 
                    component,
                    COUNT(*) as activity_count
                FROM system_logs
                WHERE timestamp >= NOW() - INTERVAL '%s hours'
                GROUP BY component
                ORDER BY activity_count DESC
            """, (hours,))
            component_activity = dict(cursor.fetchall())
            
            conn.close()
            
            return {
                'log_levels': log_levels,
                'recent_errors': recent_errors,
                'component_activity': component_activity
            }
            
        except Exception as e:
            self.logger.error("Error getting system logs: " + str(e))
            return {}
    
    def get_performance_metrics(self, hours: int = 24) -> Dict:
        """Get performance metrics"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return {}
            
            cursor = conn.cursor()
            
            # Average processing time
            cursor.execute("""
                SELECT 
                    AVG(metric_value) as avg_processing_time
                FROM performance_metrics
                WHERE metric_name = 'processing_time_seconds'
                AND timestamp >= NOW() - INTERVAL '%s hours'
            """, (hours,))
            avg_processing = cursor.fetchone()
            
            # API response times
            cursor.execute("""
                SELECT 
                    component,
                    metric_name,
                    AVG(metric_value) as avg_value,
                    MAX(metric_value) as max_value
                FROM performance_metrics
                WHERE metric_name LIKE '%_response_time'
                AND timestamp >= NOW() - INTERVAL '%s hours'
                GROUP BY component, metric_name
            """, (hours,))
            api_times = [
                {
                    'component': row[0],
                    'metric': row[1],
                    'avg': float(row[2]) if row[2] else 0,
                    'max': float(row[3]) if row[3] else 0
                }
                for row in cursor.fetchall()
            ]
            
            conn.close()
            
            return {
                'avg_processing_time': float(avg_processing[0]) if avg_processing[0] else 0,
                'api_response_times': api_times
            }
            
        except Exception as e:
            self.logger.error("Error getting performance metrics: " + str(e))
            return {}
    
    def generate_dashboard_data(self) -> Dict:
        """Generate complete dashboard data"""
        self.logger.info("Generating dashboard data")
        
        data = {
            'timestamp': datetime.now().isoformat(),
            'articles': self.get_article_stats(),
            'logs': self.get_system_logs(),
            'performance': self.get_performance_metrics()
        }
        
        return data
    
    def print_dashboard(self, data: Dict):
        """Print formatted dashboard"""
        print("\n" + "="*80)
        print("📊 NEWS BALANCE BACKEND - DASHBOARD")
        print("="*80)
        print(f"🕐 Last Updated: {data['timestamp']}")
        print()
        
        # Article Statistics
        articles = data['articles']
        if articles:
            print("📰 ARTICLE STATISTICS")
            print("-" * 40)
            overall = articles['overall']
            last_24h = articles['last_24h']
            
            print(f"📊 Total Articles: {overall['total']}")
            print(f"⏳ Unprocessed: {overall['unprocessed']}")
            print(f"✅ Relevant: {overall['relevant']}")
            print(f"❌ Non-relevant: {overall['non_relevant']}")
            print(f"📅 Last Article: {overall['last_article']}")
            print()
            
            print("📈 LAST 24 HOURS")
            print("-" * 40)
            print(f"📊 New Articles: {last_24h['total']}")
            print(f"⏳ Unprocessed: {last_24h['unprocessed']}")
            print(f"✅ Processed (Relevant): {last_24h['relevant']}")
            print(f"❌ Processed (Non-relevant): {last_24h['non_relevant']}")
            print(f"🔄 Processed Today: {articles['processed_today']}")
            print()
        
        # System Logs
        logs = data['logs']
        if logs:
            print("📝 SYSTEM LOGS (24h)")
            print("-" * 40)
            for level, count in logs['log_levels'].items():
                emoji = "🔴" if level == "ERROR" else "🟡" if level == "WARNING" else "🔵" if level == "INFO" else "⚪"
                print(f"{emoji} {level}: {count}")
            print()
            
            if logs['recent_errors']:
                print("🚨 RECENT ERRORS")
                print("-" * 40)
                for error in logs['recent_errors'][:5]:
                    print(f"⏰ {error['timestamp']} | {error['component']}: {error['message'][:60]}...")
                print()
        
        # Performance Metrics
        performance = data['performance']
        if performance:
            print("⚡ PERFORMANCE METRICS")
            print("-" * 40)
            print(f"⏱️ Avg Processing Time: {performance['avg_processing_time']:.2f}s")
            
            if performance['api_response_times']:
                print("🌐 API Response Times:")
                for api in performance['api_response_times']:
                    print(f"   {api['component']} ({api['metric']}): {api['avg']:.2f}s avg, {api['max']:.2f}s max")
            print()
        
        print("="*80)
    
    def save_dashboard_data(self, data: Dict, filename: str = "dashboard_data.json"):
        """Save dashboard data to file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            self.logger.info(f"Dashboard data saved to {filename}")
        except Exception as e:
            self.logger.error(f"Error saving dashboard data: {e}")

def main():
    """Main function"""
    print("📊 Generating Dashboard...")
    
    dashboard = Dashboard()
    data = dashboard.generate_dashboard_data()
    dashboard.print_dashboard(data)
    dashboard.save_dashboard_data(data)
    
    print("\n💾 Dashboard data saved to dashboard_data.json")

if __name__ == "__main__":
    main()
