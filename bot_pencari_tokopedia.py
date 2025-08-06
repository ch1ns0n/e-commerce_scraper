import pandas as pd
import time
import random
import sqlite3
import re
import requests
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)

# --- Database Setup ---
DB_FILE = "tokopedia_products.db"

def setup_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            "Nama Produk" TEXT,
            "Harga" INTEGER,
            "Toko" TEXT,
            "Lokasi" TEXT,
            "Rating" REAL,
            "Terjual" INTEGER,
            UNIQUE("Nama Produk", "Toko")
        )
    ''')
    conn.commit()
    return conn

# --- Anti-Bot Config ---
def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

# --- Scraping Logic ---
def scroll_to_load(driver, max_scrolls=10):
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(max_scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(1.5, 3))
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def parse_terjual(text):
    if not isinstance(text, str) or 'terjual' not in text.lower():
        return 0
    try:
        text = text.lower().replace('terjual', '').replace('+', '').strip()
        multiplier = 1000 if 'rb' in text else 1
        text = text.replace('rb', '').replace(',', '.').strip()
        numbers = re.findall(r'[\d.]+', text)
        return int(float(numbers[0]) * multiplier) if numbers else 0
    except:
        return 0

def extract_products_from_api(driver):
    """Intercept API responses while scrolling"""
    api_urls = []
    logs = driver.get_log('performance')
    for log in logs:
        message = json.loads(log['message'])['message']
        if 'Network.requestWillBeSent' in message['method']:
            url = message['params']['request'].get('url', '')
            if 'ace.tokopedia.com/search/product' in url:
                api_urls.append(url)
    
    products = []
    for url in set(api_urls[-3:]):  # Get last 3 unique API calls
        try:
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            data = response.json()
            for item in data.get('data', {}).get('products', []):
                products.append({
                    "Nama Produk": item.get("name", "N/A"),
                    "Harga": item.get("price", 0),
                    "Toko": item.get("shop", {}).get("name", "N/A"),
                    "Lokasi": item.get("shop", {}).get("location", "N/A"),
                    "Rating": item.get("rating", 0),
                    "Terjual": item.get("sold", 0)
                })
        except:
            continue
    return products

def scrape_tokopedia(keyword):
    driver = get_driver()
    url = f"https://www.tokopedia.com/search?q={keyword.replace(' ', '%20')}"
    driver.get(url)
    products = []

    try:
        # Wait for initial load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='divSRPContentProducts']"))
        
        # Method 1: Try API interception
        print("🛠 Attempting API interception...")
        api_products = extract_products_from_api(driver)
        products.extend(api_products)
        
        # Method 2: Fallback to scrolling
        if len(products) < 50:
            print("🔍 Falling back to scrolling...")
            scroll_to_load(driver)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            items = soup.select("div[data-testid='master-product-card']")
            for item in items[:100]:  # Limit to avoid duplicates
                try:
                    products.append({
                        "Nama Produk": item.select_one("div.prd_link-product-name").text.strip(),
                        "Harga": int(re.sub(r'\D', '', item.select_one("div.prd_link-product-price").text)),
                        "Toko": item.select_one("span.prd_link-shop-name").text.strip(),
                        "Lokasi": item.select_one("span.prd_link-shop-loc").text.strip(),
                        "Rating": float(item.select_one("span.prd_rating-average-text").text) if item.select_one("span.prd_rating-average-text") else 0,
                        "Terjual": parse_terjual(item.select_one("span.prd_label-integrity").text) if item.select_one("span.prd_label-integrity") else 0
                    })
                except:
                    continue
        )
        
        # Deduplicate
        df = pd.DataFrame(products).drop_duplicates(subset=["Nama Produk", "Toko"])
        return df

    except TimeoutException:
        print("❌ Timeout: CAPTCHA or slow loading detected.")
        return pd.DataFrame()
    finally:
        driver.quit()

# --- Main Execution ---
def main():
    conn = setup_database()
    keyword = input("Enter product keyword: ").strip()
    
    print(f"\n🔥 Scraping '{keyword}' with anti-bot measures...")
    df = scrape_tokopedia(keyword)
    
    if not df.empty:
        df.to_sql('products', conn, if_exists='append', index=False)
        print(f"✅ Saved {len(df)} products to database!")
        print(df.head())
    else:
        print("❌ No products found. Possible CAPTCHA or IP block.")

if __name__ == "__main__":
    main()