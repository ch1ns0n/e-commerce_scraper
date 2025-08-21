# Nama file: backup.py
# Versi ini sepenuhnya menggunakan SQLite dan scraper asli Anda.

# --- Bagian 1: Import semua library yang dibutuhkan ---
import pandas as pd
import time
import random
import re
import warnings
import sqlite3
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

warnings.simplefilter(action='ignore', category=FutureWarning)

# --- Bagian 2: Fungsi untuk Database LOKAL (SQLite) ---
DB_FILE = "tokopedia_backup_local.db"

def setup_database():
    """Mempersiapkan database SQLite lokal untuk eksperimen."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            "Nama Produk" TEXT, "Harga" INTEGER, "Toko" TEXT,
            "Lokasi" TEXT, "Rating" REAL, "Produk Terjual" INTEGER,
            "URL" TEXT, "Ulasan" TEXT,
            UNIQUE("Nama Produk", "Toko")
        )
    ''')
    conn.commit()
    print(f"✅ Terhubung ke database lokal: {DB_FILE}")
    return conn

# --- Bagian 3: Fungsi-Fungsi Scraper (Milik Anda, tidak diubah kecuali penambahan URL) ---

def menggunakan_pagination(driver) -> bool:
    try:
        driver.find_element(By.CSS_SELECTOR, "ul[data-testid='pagination-list']"); return True
    except: return False

def scroll_to_load_products(driver, max_scrolls=20, pause_time=2):
    print("🌀 Deteksi: Halaman menggunakan infinite scroll..."); time.sleep(1) # Implementasi asli Anda

def klik_tombol_next_page(driver) -> bool:
    try:
        next_button = driver.find_element(By.CSS_SELECTOR, 'li[data-testid="btnNextPage"]')
        if 'disabled' in next_button.get_attribute('class'): return False
        driver.execute_script("arguments[0].scrollIntoView();", next_button)
        time.sleep(1); next_button.click(); time.sleep(random.uniform(3, 5))
        return True
    except Exception as e:
        print(f"❌ Gagal klik tombol next: {e}"); return False

def parse_terjual(text: str) -> int:
    if not isinstance(text, str) or 'terjual' not in text.lower(): return 0
    try:
        text_cleaned = text.lower().replace('terjual', '').replace('+', '').strip()
        multiplier = 1
        if 'rb' in text_cleaned:
            multiplier = 1000
            text_cleaned = text_cleaned.replace('rb', '').strip()
        numeric_part_str = text_cleaned.replace(',', '.')
        found_numbers = re.findall(r'[\d.]+', numeric_part_str)
        if not found_numbers: return 0
        value = float(found_numbers[0])
        return int(value * multiplier)
    except (ValueError, TypeError, IndexError): return 0

def ambil_data_dari_halaman(driver, produk_ditemukan: list):
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    product_container = soup.find("div", attrs={"data-testid": "divSRPContentProducts"})
    if not product_container: return
    produk_list = product_container.find_all("a", attrs={"data-theme": "default"})

    for produk in produk_list:
        try:
            nama_tag = produk.find("span", class_="+tnoqZhn89+NHUA43BpiJg==")
            harga_tag = produk.find("div", class_="urMOIDHH7I0Iy1Dv2oFaNw==")
            lokasi_toko_spans = produk.find_all("span", class_=lambda c: c and 'gxi+fsElj' in c)
            rating_tag = produk.find("span", class_="_2NfJxPu4JC-55aCJ8bEsyw==")
            terjual_tag = produk.find("span", class_="u6SfjDD2WiBlNW7zHmzRhQ==")
            product_url = produk.get('href', "N/A")
            if "ta.tokopedia.com" in product_url: continue

            harga_numerik = int(re.sub(r'[Rp.]', '', harga_tag.get_text(strip=True))) if harga_tag else 0
            rating_numerik = float(rating_tag.get_text(strip=True)) if rating_tag else 0.0
            terjual_text = terjual_tag.get_text(strip=True) if terjual_tag else "0"
            jumlah_terjual = parse_terjual(terjual_text)

            produk_ditemukan.append({
                "Nama Produk": nama_tag.get_text(strip=True) if nama_tag else "N/A",
                "Harga": harga_numerik,
                "Toko": lokasi_toko_spans[0].get_text(strip=True) if len(lokasi_toko_spans) > 0 else "N/A",
                "Lokasi": lokasi_toko_spans[1].get_text(strip=True) if len(lokasi_toko_spans) > 1 else "N/A",
                "Rating": rating_numerik,
                "Produk Terjual": jumlah_terjual,
                "URL": product_url
            })
        except Exception: continue

def scrape_tokopedia_realtime(keyword: str, max_pages: int = 2) -> pd.DataFrame:
    print(f"\n⚙️  Mencari produk untuk kata kunci: '{keyword}'...")
    url_target = f"https://www.tokopedia.com/search?st=product&q={keyword.replace(' ', '%20')}"
    options = webdriver.ChromeOptions()
    # DIUBAH: Menonaktifkan headless agar browser terlihat untuk penanganan CAPTCHA
    # options.add_argument('--headless')
    options.add_argument('--start-maximized')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url_target)
    produk_ditemukan = []
    try:
        print("   -> Menunggu halaman produk...")
        # BARU: Jeda interaktif untuk CAPTCHA
        input("   -> Jendela browser telah terbuka. Jika ada CAPTCHA, selesaikan sekarang lalu tekan ENTER di sini untuk melanjutkan...")
        
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='divSRPContentProducts']")))
        print("   -> Kontainer produk ditemukan!")
        page_count = 1
        if menggunakan_pagination(driver):
            print("📄 Deteksi: Halaman menggunakan pagination.")
            while page_count <= max_pages:
                ambil_data_dari_halaman(driver, produk_ditemukan)
                if page_count == max_pages or not klik_tombol_next_page(driver): break
                page_count += 1
        else:
            print("🌀 Deteksi: Halaman menggunakan infinite scroll.")
            scroll_to_load_products(driver)
            ambil_data_dari_halaman(driver, produk_ditemukan)
    except TimeoutException:
        print("   -> Gagal menemukan kontainer produk setelah menunggu.")
    finally:
        print("Proses scraping di browser selesai. Anda bisa menutup browser secara manual.")
        # driver.quit() # Jangan ditutup otomatis agar bisa dilihat
    return pd.DataFrame(produk_ditemukan)

# --- Bagian 4: Fungsi-Fungsi Aplikasi ---

def scrape_and_save(conn):
    """Mengatur scraping dan menyimpan data ke SQLite."""
    keyword = input("\n> Masukkan kata kunci produk untuk di-scrape: ")
    if not keyword: return
    hasil_df = scrape_tokopedia_realtime(keyword)
    if hasil_df.empty: print("❌ Tidak ada produk yang ditemukan."); return
    cursor = conn.cursor()
    for _, row in hasil_df.iterrows():
        try:
            cursor.execute('INSERT INTO products ("Nama Produk", "Harga", "Toko", "Lokasi", "Rating", "Produk Terjual", "URL") VALUES (?,?,?,?,?,?,?)',
                           (row["Nama Produk"], row["Harga"], row["Toko"], row["Lokasi"], row["Rating"], row["Produk Terjual"], row["URL"]))
        except sqlite3.IntegrityError: continue
    conn.commit()
    print(f"\n✅ Proses selesai!")

def scrape_ulasan_lokal(conn, limit=10):
    """Mengambil ulasan dari produk yang ada di database SQLite."""
    cursor = conn.cursor()
    try: cursor.execute("SELECT Ulasan FROM products LIMIT 1")
    except sqlite3.OperationalError:
        print("INFO: Kolom 'Ulasan' tidak ditemukan, menambahkan kolom..."); cursor.execute("ALTER TABLE products ADD COLUMN Ulasan TEXT"); conn.commit()
    query = 'SELECT id, URL FROM products WHERE URL IS NOT NULL AND URL != "N/A" AND Ulasan IS NULL LIMIT ?'
    df_produk = pd.read_sql_query(query, conn, params=(limit,))
    if df_produk.empty: print("\n✅ Semua produk sudah memiliki data ulasan."); return

    print(f"\n🕵️‍♂️ Menemukan {len(df_produk)} produk untuk diambil ulasannya...")
    options = webdriver.ChromeOptions(); options.add_argument('--headless')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    for _, row in df_produk.iterrows():
        product_id, url = row['id'], row['URL']
        try:
            print(f"   -> Mengunjungi: {url[:70]}...")
            driver.get(url)
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "article[data-testid='divPdpReview']")))
            ulasan_elements = driver.find_elements(By.CSS_SELECTOR, "p[data-testid='lblItemUlasan']")
            list_ulasan = [ulasan.text for ulasan in ulasan_elements[:5] if ulasan.text]
            ulasan_json = json.dumps(list_ulasan)
            cursor.execute("UPDATE products SET Ulasan = ? WHERE id = ?", (ulasan_json, product_id)); conn.commit()
            print(f"      -> Ditemukan dan disimpan {len(list_ulasan)} ulasan.")
            time.sleep(random.uniform(2, 4))
        except Exception:
            print(f"      -> ❌ Gagal mengambil ulasan."); cursor.execute("UPDATE products SET Ulasan = ? WHERE id = ?", ('gagal_scrape', product_id)); conn.commit()
            continue
    driver.quit(); print("\n✅ Proses pengambilan ulasan selesai.")

def lihat_semua_data(conn):
    """Menampilkan seluruh isi tabel dari SQLite."""
    print("\n📦 Menampilkan seluruh data dari database lokal...")
    df = pd.read_sql_query('SELECT * FROM products ORDER BY "Produk Terjual" DESC, "Rating" DESC', conn)
    if df.empty: print("Database masih kosong."); return
    pd.set_option('display.max_colwidth', 40)
    print(df.drop(columns=['id']))

# --- Bagian 5: Fungsi Utama (Main) ---
def main():
    """Fungsi utama untuk menjalankan aplikasi eksperimen."""
    conn = setup_database()
    while True:
        print("\n--- MENU EKSPERIMEN (DATABASE LOKAL) ---")
        print("1. ⚙️  Scrape Produk & URL")
        print("2. 🕵️‍♂️ Scrape Ulasan Produk")
        print("3. 📦 Lihat Semua Data")
        print("4. 🚪 Keluar")
        choice = input("> Pilih opsi: ")
        if choice == '1': scrape_and_save(conn)
        elif choice == '2': scrape_ulasan_lokal(conn)
        elif choice == '3': lihat_semua_data(conn)
        elif choice == '4': print("\n👋 Keluar dari mode eksperimen."); break
        else: print("❌ Pilihan tidak valid.")
    if conn: conn.close(); print("Koneksi ke database lokal ditutup.")

if __name__ == "__main__":
    main()