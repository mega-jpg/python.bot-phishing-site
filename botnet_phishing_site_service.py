# This file was renamed from botnet_scrape_sjc_service.py
import os
import re
import time
import threading
import asyncio
from typing import Dict

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

            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.chrome.service import Service as ChromeService
            from webdriver_manager.chrome import ChromeDriverManager
            from parsel import Selector
            import shutil
            from http.server import BaseHTTPRequestHandler, HTTPServer

            # Setup Chrome options
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            # options.add_argument('--disable-gpu')  # Deprecated in modern Chrome

            chromedriver_path = shutil.which('chromedriver')
            if chromedriver_path:
                print(f"Using system chromedriver: {chromedriver_path}")
                service = ChromeService(executable_path=chromedriver_path)
            else:
                service = ChromeService(ChromeDriverManager().install())

            chromium_path = shutil.which('chromium')
            if chromium_path:
                options.binary_location = chromium_path
                print(f"Using system chromium: {chromium_path}")

            driver = webdriver.Chrome(service=service, options=options)
            try:
                if not url:
                    url = "https://google.com.vn/"
                # Ensure URL has protocol
                if url and not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                print(f"📡 Navigating to {url}")
                driver.get(url)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'body'))
                )
                scraped_html = driver.page_source
                selector = Selector(text=scraped_html)
                title = selector.css('title::text').get() or 'Unknown'

                # Serve scraped HTML on port 5001
                class ScrapedContentHandler(BaseHTTPRequestHandler):
                    def do_GET(self):
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html; charset=utf-8')
                        self.end_headers()
                        self.wfile.write(scraped_html.encode('utf-8'))

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
            finally:
                driver.quit()
                print("🧹 Chrome driver closed")
        except Exception as e:
            error_msg = f"❌ SJC scraping failed: {str(e)}"
            print(error_msg)
            return {
                'success': False,
                'error': str(e),
                'timestamp': time.time()
            }