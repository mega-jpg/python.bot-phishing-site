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

    # Removed start_sjc_cronjob_thread logic from main program. Method is retained for manual use if needed.

    async def scrape_sjc(self) -> Dict:
        """Crawl SJC gold price from webgia.com and return status via backend logs"""
        try:
            print(f"[SJC] scrape_sjc called. (thread: {threading.current_thread().name})")
            print("🔄 Starting SJC price scraping from webgia.com...")

            # Use Selenium for JavaScript-rendered content
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from webdriver_manager.chrome import ChromeDriverManager
            from parsel import Selector

            # Setup Chrome options
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-gpu')

            print("🌐 Initializing Chrome WebDriver...")
            from selenium.webdriver.chrome.service import Service as ChromeService
            import shutil
            
            # Use system chromedriver in Replit environment
            chromedriver_path = shutil.which('chromedriver')
            if chromedriver_path:
                print(f"Using system chromedriver: {chromedriver_path}")
                service = ChromeService(executable_path=chromedriver_path)
            else:
                # Fallback to ChromeDriverManager if not in Replit
                from webdriver_manager.chrome import ChromeDriverManager
                service = ChromeService(ChromeDriverManager().install())
            
            # Use system chromium binary
            chromium_path = shutil.which('chromium')
            if chromium_path:
                options.binary_location = chromium_path
                print(f"Using system chromium: {chromium_path}")
            
            driver = webdriver.Chrome(service=service, options=options)

            try:
                url = "https://webgia.com/gia-vang/sjc/"
                print(f"📡 Navigating to {url}")
                driver.get(url)

                # Wait for page to load
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'body'))
                )

                # Task todo list

            
                return {'success': True,}

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