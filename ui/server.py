#!/usr/bin/env python3
"""
Simple HTTP server to serve the AARO UI files.
Run this to serve the UI on http://localhost:3000
"""

import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        super().end_headers()

def serve_ui(port=3000):
    """Serve the AARO UI on the specified port."""
    
    # Change to the UI directory
    ui_dir = Path(__file__).parent
    os.chdir(ui_dir)
    
    # Create server
    handler = CORSHTTPRequestHandler
    httpd = socketserver.TCPServer(("", port), handler)
    
    print(f"🚀 AARO UI Server starting...")
    print(f"📱 UI available at: http://localhost:{port}")
    print(f"🤖 Make sure AARO API is running at: http://localhost:8000")
    print(f"📖 API docs available at: http://localhost:8000/docs")
    print(f"\n🎯 Opening browser...")
    
    # Open browser
    try:
        webbrowser.open(f'http://localhost:{port}')
    except:
        pass
    
    print(f"\n⚡ Server running. Press Ctrl+C to stop.")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print(f"\n🛑 Server stopped.")
        httpd.shutdown()

if __name__ == "__main__":
    serve_ui()