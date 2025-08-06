# --- Bagian 1: Import semua library yang dibutuhkan ---
import pandas as pd
import time
import random
import sqlite3
import re
import matplotlib.pyplot as plt
import seaborn as sns
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)

# --- Bagian 2: Fungsi untuk Database dan Fitur Baru ---
DB_FILE = "tokopedia_products.db"

def setup_database():
    """Mempersiapkan database SQLite dan membuat tabel jika belum ada."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            "Nama Produk" TEXT,
            "Harga" TEXT,
            "Toko" TEXT,
            "Lokasi" TEXT,
            "Rating" TEXT,
            UNIQUE("Nama Produk", "Toko")
        )
    ''')
    conn.commit()
    return conn

# --- Bagian 3: Fungsi-Fungsi Scraper (Struktur Asli Anda dengan Pembaruan Penting) ---

def menggunakan_pagination(driver) -> bool:
    try:
        driver.find_element(By.CSS_SELECTOR, "ul[data-testid='pagination-list']")
        return True
    except:
        return False

def scroll_to_load_products(driver, max_scrolls=20, pause_time=2):
    print("🌀 Deteksi: Halaman menggunakan infinite scroll. Melakukan auto-scroll perlahan...")

    last_count = 0
    scroll_step = 1000

    for i in range(max_scrolls):
        driver.execute_script(f"window.scrollBy(0, {scroll_step});")
        time.sleep(pause_time)

        product_containers = driver.find_elements(By.CSS_SELECTOR, "div[data-testid='master-product-card']")
        current_count = len(product_containers)

        print(f"📦 Scroll ke-{i+1}: {last_count} → {current_count} produk")

        if current_count == last_count:
            print("⚠️ Tidak ada produk baru setelah scroll. Menghentikan proses.")
            break

        last_count = current_count

def klik_tombol_next_page(driver) -> bool:
    try:
        next_button = driver.find_element(By.CSS_SELECTOR, 'li[data-testid="btnNextPage"]')
        if 'disabled' in next_button.get_attribute('class'):
            return False
        driver.execute_script("arguments[0].scrollIntoView();", next_button)
        time.sleep(1)
        next_button.click()
        time.sleep(random.uniform(3, 5))
        return True
    except Exception as e:
        print(f"❌ Gagal klik tombol next: {e}")
        return False

def ambil_data_dari_halaman(driver, produk_ditemukan: list):
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    product_container = soup.find("div", attrs={"data-testid": "divSRPContentProducts"})
    if not product_container:
        return

    produk_list = product_container.find_all("a", attrs={"data-theme": "default"})

    for produk in produk_list:
        try:
            nama_tag = produk.find("span", class_="+tnoqZhn89+NHUA43BpiJg==")
            harga_tag = produk.find("div", class_="urMOIDHH7I0Iy1Dv2oFaNw==")
            lokasi_toko_spans = produk.find_all("span", class_=lambda c: c and 'gxi+fsElj' in c)
            rating_tag = produk.find("span", class_="_2NfJxPu4JC-55aCJ8bEsyw==")

            produk_ditemukan.append({
                "Nama Produk": nama_tag.get_text(strip=True) if nama_tag else "N/A",
                "Harga": harga_tag.get_text(strip=True) if harga_tag else "N/A",
                "Toko": lokasi_toko_spans[0].get_text(strip=True) if len(lokasi_toko_spans) > 0 else "N/A",
                "Lokasi": lokasi_toko_spans[1].get_text(strip=True) if len(lokasi_toko_spans) > 1 else "N/A",
                "Rating": rating_tag.get_text(strip=True) if rating_tag else "N/A"
            })
        except Exception:
            continue

def scrape_tokopedia_realtime(keyword: str) -> pd.DataFrame:
    print(f"\n⚙️  Mencari produk untuk kata kunci: '{keyword}'...")
    url_target = f"https://www.tokopedia.com/search?st=product&q={keyword.replace(' ', '%20')}"

    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('log-level=3')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url_target)

    produk_ditemukan = []

    try:
        print("   -> Menunggu kontainer produk muncul di halaman...")
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='divSRPContentProducts']")))
        print("   -> Kontainer produk ditemukan!")

        if menggunakan_pagination(driver):
            print("📄 Deteksi: Halaman menggunakan pagination klasik.")
            while True:
                ambil_data_dari_halaman(driver, produk_ditemukan)
                if not klik_tombol_next_page(driver):
                    break
        else:
            print("🌀 Deteksi: Halaman menggunakan infinite scroll. Melakukan auto-scroll...")
            scroll_to_load_products(driver)
            ambil_data_dari_halaman(driver, produk_ditemukan)

    except TimeoutException:
        print("   -> Gagal menemukan kontainer produk setelah menunggu. Kemungkinan halaman CAPTCHA atau halaman kosong.")
    finally:
        if 'driver' in locals() and driver:
            driver.quit()

    return pd.DataFrame(produk_ditemukan)


# --- Bagian 4: Fungsi untuk menjalankan fitur-fitur baru ---

def scrape_and_save(conn):
    """Mengatur proses scraping dan penyimpanan ke database."""
    keyword = input("\n> Masukkan kata kunci produk untuk di-scrape: ")
    if not keyword:
        print("❌ Kata kunci tidak boleh kosong.")
        return

    hasil_df = scrape_tokopedia_realtime(keyword)

    if not hasil_df.empty:
        try:
            # 'append' akan menambahkan data baru dan mengabaikan duplikat berdasarkan UNIQUE constraint
            hasil_df.to_sql('products', conn, if_exists='append', index=False)
            print(f"✅ Sukses! {len(hasil_df)} produk baru ditemukan dan disimpan ke database.")
        except sqlite3.IntegrityError:
            print("ℹ️  Data baru ditambahkan. Beberapa produk yang sama persis diabaikan (sudah ada di database).")
    else:
        print("❌ Tidak ada produk yang ditemukan untuk di-scrape.")

def clean_data_for_viz(df: pd.DataFrame) -> pd.DataFrame:
    """Membersihkan DataFrame untuk keperluan visualisasi."""
    df_clean = df.copy()
    df_clean['HargaNumerik'] = df_clean['Harga'].str.replace(r'[Rp.]', '', regex=True)
    df_clean['HargaNumerik'] = pd.to_numeric(df_clean['HargaNumerik'], errors='coerce')
    df_clean['RatingNumerik'] = pd.to_numeric(df_clean['Rating'], errors='coerce')
    df_clean.dropna(subset=['HargaNumerik', 'Lokasi'], inplace=True)
    df_clean = df_clean[df_clean['Lokasi'] != 'N/A']
    return df_clean

def visualize_results(df: pd.DataFrame):
    """Membuat dan menampilkan visualisasi dari hasil pencarian."""
    if df.empty:
        print("❌ Tidak ada data untuk divisualisasikan.")
        return
        
    print("\n📊 Membersihkan data dan membuat visualisasi...")
    df_viz = clean_data_for_viz(df)

    if df_viz.empty:
        print("❌ Setelah dibersihkan, tidak ada data valid untuk visualisasi.")
        return

    plt.figure(figsize=(12, 7))
    avg_price_location = df_viz.groupby('Lokasi')['HargaNumerik'].mean().sort_values(ascending=False).head(10)
    sns.barplot(x=avg_price_location.values, y=avg_price_location.index, palette='viridis', orient='h')
    plt.title('Top 10 Rata-Rata Harga Produk Berdasarkan Lokasi Toko', fontsize=16)
    plt.xlabel('Rata-Rata Harga (Rp)', fontsize=12)
    plt.ylabel('Lokasi Toko', fontsize=12)
    plt.ticklabel_format(style='plain', axis='x')
    plt.tight_layout()

    print("✅ Visualisasi selesai. Menampilkan plot...")
    plt.show()

def search_and_display(conn):
    """Mencari di database, menampilkan hasil, dan menawarkan ekspor/visualisasi."""
    search_term = input("\n> Masukkan kata kunci untuk dicari di database: ")
    if not search_term:
        print("❌ Kata kunci tidak boleh kosong.")
        return
    
    query_parts = [f'"Nama Produk" LIKE ?' for word in search_term.split()]
    sql_query = f'SELECT * FROM products WHERE {" AND ".join(query_parts)}'
    params = [f'%{word}%' for word in search_term.split()]

    results_df = pd.read_sql_query(sql_query, conn, params=params)

    if not results_df.empty:
        print(f"\n✅ Ditemukan {len(results_df)} produk dari database:")
        print(results_df.drop('id', axis=1))

        export_choice = input("\n📄 Ekspor hasil ini ke file CSV? (y/n): ").lower()
        if export_choice == 'y':
            filename = f"pencarian_{search_term.replace(' ', '_')}_{int(time.time())}.csv"
            results_df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"✅ Hasil disimpan ke file: {filename}")
        
        viz_choice = input("📊 Buat visualisasi dari hasil ini? (y/n): ").lower()
        if viz_choice == 'y':
            visualize_results(results_df)
    else:
        print("❌ Tidak ada produk yang cocok dengan kata kunci di database.")

# --- Bagian 5: Fungsi Utama (Main) dengan Menu ---

def main():
    """Fungsi utama untuk menjalankan aplikasi dengan menu interaktif."""
    conn = setup_database()
    print("=========================================")
    print("🤖 Selamat Datang di Bot Tokopedia Lanjutan")
    print(f"💾 Database terhubung di: {DB_FILE}")
    print("=========================================")

    while True:
        print("\n--- MENU UTAMA ---")
        print("1. ⚙️  Scrape data produk baru dari Tokopedia")
        print("2. 🔍 Cari produk di database lokal")
        print("3. 🚪 Keluar")
        choice = input("> Pilih opsi (1/2/3): ")

        if choice == '1':
            scrape_and_save(conn)
        elif choice == '2':
            search_and_display(conn)
        elif choice == '3':
            print("\n👋 Terima kasih! Sampai jumpa!")
            break
        else:
            print("❌ Pilihan tidak valid, silakan coba lagi.")
    
    conn.close()

if __name__ == "__main__":
    main()