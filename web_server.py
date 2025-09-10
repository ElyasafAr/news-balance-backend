#!/usr/bin/env python3
# -*- coding: utf-8
"""
Simple HTTP server for Railway deployment
This keeps the container alive and provides health check endpoint
"""

import os
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            health_data = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'service': 'news-balance-backend',
                'uptime': time.time() - self.server.start_time
            }
            
            self.wfile.write(json.dumps(health_data).encode())
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>News Balance Backend</title>
                <meta charset="utf-8">
            </head>
            <body>
                <h1>News Balance Backend</h1>
                <p>Backend service is running...</p>
                <p>Health check: <a href="/health">/health</a></p>
                <p>Time: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
            </body>
            </html>
            """
            
            self.wfile.write(html.encode())
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass

def start_web_server():
    """Start the HTTP server in a separate thread"""
    port = int(os.environ.get('PORT', 8000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    server.start_time = time.time()
    
    print(f"Starting web server on port {port}...")
    server.serve_forever()

def main():
    """Main function - start web server and backend runner"""
    print("Starting News Balance Backend with HTTP server...")
    
    # Start web server in background thread
    web_thread = threading.Thread(target=start_web_server, daemon=True)
    web_thread.start()
    
    # Import and run the backend runner
    try:
        from backend_runner_postgres import BackendRunner
        runner = BackendRunner()
        runner.run()
    except KeyboardInterrupt:
        print("Shutting down...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
