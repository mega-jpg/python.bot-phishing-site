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

            # Extract title
            soup = BeautifulSoup(scraped_html, 'html.parser')
            title = soup.title.string if soup.title else 'Unknown'

            # Serve scraped HTML on port 5001
            class ScrapedContentHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.end_headers()
                    # Read from file each time to render the scraped content
                    try:
                        with open(temp_filename, 'r', encoding='utf-8') as f:
                            content = f.read()
                        self.wfile.write(content.encode('utf-8'))
                    except Exception as e:
                        self.send_error(500, f"Error reading file: {str(e)}")

                def do_OPTIONS(self):
                    self.send_response(200)
                    self.end_headers()

            def run_server():
                server_address = ('', 5001)
                httpd = HTTPServer(server_address, ScrapedContentHandler)
                self.current_server = httpd  # Store server instance
                print("[Frontend] Serving scraped content at http://localhost:5001")
                try:
                    httpd.serve_forever()
                except Exception as e:
                    print(f"[Frontend] Server error: {e}")

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