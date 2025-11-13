# This file was renamed from botnet_scrape_sjc_service.py
import os
import re
import time
import threading
import asyncio
import mimetypes
from typing import Dict
import subprocess
import tempfile
from bs4 import BeautifulSoup

# --- Telegram Notify ---
def send_telegram_notify(message: str):
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        print('[Telegram Notify] Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID')
        return
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    payload = {'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'}
    try:
        import requests
        resp = requests.post(url, data=payload, timeout=10)
        if resp.status_code == 200:
            print('[Telegram Notify] Sent successfully')
        else:
            print(f'[Telegram Notify] Failed: {resp.text}')
    except Exception as e:
        print(f'[Telegram Notify] Error: {e}')


class SJCScrapeService:
    """
    Service for scraping SJC gold prices and managing cronjob thread
    """

    def __init__(self):
        # Biến lưu giá SJC trước đó để so sánh
        self._last_special_mua = None
        self._last_special_ban = None
        # Server instance để quản lý
        self.current_server = None

    # Removed start_sjc_cronjob_thread logic from main program. Method is retained for manual use if needed.

    async def scrape_sjc(self, url: str = None) -> Dict:
        """Scrape HTML from a given URL and serve it on port 5001. Returns title, url, and frontend_url."""
        try:
            print(f"[SJC] scrape_sjc called. (thread: {threading.current_thread().name})")
            print(f"🔄 Starting SJC price scraping from {url or 'default'}...")

            # Shutdown any existing server immediately
            if self.current_server:
                print("[Frontend] Shutting down existing server...")
                self.current_server.shutdown()
                self.current_server = None

            from http.server import BaseHTTPRequestHandler, HTTPServer

            if not url:
                url = "https://google.com.vn/"
            # Ensure URL has protocol
            if url and not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            print(f"📡 Scraping {url} with SingleFile CLI")

            # Create single-file directory if not exists
            os.makedirs("single-file", exist_ok=True)
            temp_filename = os.path.join("single-file", "scraped_page.html")

            # Remove existing file if it exists to ensure clean overwrite
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

            # Run single-file CLI
            single_file_path = os.path.join(os.environ.get('APPDATA', ''), 'npm', 'single-file.cmd')
            try:
                result = subprocess.run([
                    single_file_path, url, temp_filename,
                    '--dump-content=false'
                ], capture_output=True, text=True, timeout=120)
            except subprocess.TimeoutExpired:
                raise Exception(f"SingleFile CLI timed out after 120 seconds for URL: {url}")

            if result.returncode != 0:
                raise Exception(f"SingleFile CLI failed: {result.stderr or 'Unknown error'}")

            # Read the saved HTML
            with open(temp_filename, 'r', encoding='utf-8') as f:
                scraped_html = f.read()

            # Note: Keeping the file in single-file directory for persistence

            # Extract title and process HTML for better display
            soup = BeautifulSoup(scraped_html, 'html.parser')
            title = soup.title.string if soup.title else 'Unknown'

            # Remove restrictive CSP meta tags that block content
            for meta in soup.find_all('meta', attrs={'http-equiv': 'content-security-policy'}):
                print(f"[Frontend] Removing CSP meta tag: {meta.get('content', '')[:100]}...")
                meta.decompose()

            # Add base tag to handle relative URLs
            base_tag = soup.find('base')
            if not base_tag:
                head = soup.find('head')
                if head:
                    new_base = soup.new_tag('base', href=url)
                    head.insert(0, new_base)
                    print(f"[Frontend] Added base tag with href={url}")

            # Optional: Add our own permissive CSP
            head = soup.find('head')
            if head:
                new_meta = soup.new_tag('meta')
                new_meta.attrs['http-equiv'] = 'Content-Security-Policy'
                new_meta.attrs['content'] = "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:;"
                head.append(new_meta)
                print("[Frontend] Added permissive CSP meta tag")

            # Save the processed HTML back
            processed_html = str(soup)
            with open(temp_filename, 'w', encoding='utf-8') as f:
                f.write(processed_html)
            print(f"[Frontend] Processed HTML saved ({len(processed_html)} bytes)")

            # Serve scraped HTML on port 5001
            class ScrapedContentHandler(BaseHTTPRequestHandler):
                def log_message(self, format, *args):
                    """Override để log requests"""
                    print(f"[Frontend Server] {format % args}")

                def do_GET(self):
                    """Handle GET requests - serve scraped HTML for any path"""
                    print(f"[Frontend Server] Handling GET {self.path}")
                    try:
                        # Check if file exists
                        if not os.path.exists(temp_filename):
                            error_msg = f"File not found: {temp_filename}"
                            print(f"[Frontend Server] ERROR: {error_msg}")
                            self.send_response(404)
                            self.send_header('Content-type', 'text/html; charset=utf-8')
                            self.end_headers()
                            self.wfile.write(f"<html><body><h1>404 Not Found</h1><p>{error_msg}</p></body></html>".encode('utf-8'))
                            return

                        # Read and serve the scraped HTML
                        with open(temp_filename, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        print(f"[Frontend Server] Successfully read {len(content)} bytes from {temp_filename}")
                        
                        # Send response with proper headers for better compatibility
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html; charset=utf-8')
                        self.send_header('Content-Length', str(len(content.encode('utf-8'))))
                        # CORS headers for cross-origin access
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
                        # Cache control for development
                        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                        self.send_header('Pragma', 'no-cache')
                        self.send_header('Expires', '0')
                        self.end_headers()
                        
                        self.wfile.write(content.encode('utf-8'))
                        print(f"[Frontend Server] Response sent successfully")
                        
                    except Exception as e:
                        error_msg = f"Error serving content: {str(e)}"
                        print(f"[Frontend Server] ERROR: {error_msg}")
                        self.send_response(500)
                        self.send_header('Content-type', 'text/html; charset=utf-8')
                        self.end_headers()
                        self.wfile.write(f"<html><body><h1>500 Internal Server Error</h1><p>{error_msg}</p></body></html>".encode('utf-8'))

                def do_OPTIONS(self):
                    """Handle OPTIONS for CORS"""
                    self.send_response(200)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', '*')
                    self.end_headers()

            def run_server():
                server_address = ('', 5001)
                try:
                    httpd = HTTPServer(server_address, ScrapedContentHandler)
                    self.current_server = httpd  # Store server instance
                    print(f"[Frontend] Server started successfully at http://localhost:5001")
                    print(f"[Frontend] Serving file: {temp_filename}")
                    print(f"[Frontend] File exists: {os.path.exists(temp_filename)}")
                    if os.path.exists(temp_filename):
                        print(f"[Frontend] File size: {os.path.getsize(temp_filename)} bytes")
                    httpd.serve_forever()
                except OSError as e:
                    if e.errno == 10048:  # Port already in use on Windows
                        print(f"[Frontend] ERROR: Port 5001 is already in use")
                    else:
                        print(f"[Frontend] ERROR: Failed to start server: {e}")
                except Exception as e:
                    print(f"[Frontend] ERROR: Server error: {e}")

            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()

            return {
                'success': True,
                'frontend_url': 'http://localhost:5001',
                'url': url,
                'title': title,
                'timestamp': time.time()
            }
        except Exception as e:
            error_msg = f"❌ SJC scraping failed: {str(e)}"
            print(error_msg)
            return {
                'success': False,
                'error': str(e),
                'timestamp': time.time()
            }