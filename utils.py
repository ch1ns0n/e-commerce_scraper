import pandas as pd
import time
import random
import re
import joblib
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
import mlflow

# --- KONEKSI DATABASE ---
def connect_to_mongodb():
    """Membuat koneksi ke database MongoDB Atlas."""
    uri = "mongodb+srv://samuelchinson:test123@cluster0.bxaivdh.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    client = MongoClient(uri, server_api=ServerApi('1'))
    try:
        client.admin.command('ping')
        print("✅ Berhasil terhubung ke MongoDB!")
        db = client['tokopedia_db']
        return db, client
    except Exception as e:
        print(f"Gagal terhubung ke MongoDB: {e}")
        return None, None

# --- FUNGSI PEMUATAN DATA UNTUK STREAMLIT ---
# Fungsi ini tidak perlu diubah, sudah bagus.
def load_data_for_dashboard():
    """Menghubungkan ke MongoDB dan memuat data produk untuk ditampilkan."""
    db, client = connect_to_mongodb()
    if db is None:
        return pd.DataFrame()
    collection = db['products']
    df = pd.DataFrame(list(collection.find({})))
    if client:
        client.close()
    if '_id' in df.columns:
        df = df.drop(columns=['_id'])
    if 'Cluster' in df.columns:
        df['Cluster'] = df['Cluster'].fillna(-1).astype(int)
    return df

# --- FUNGSI-FUNGSI PEMBANTU SCRAPING MURNI (TANPA STREAMLIT) ---
def menggunakan_pagination(driver) -> bool:
    try:
        driver.find_element(By.CSS_SELECTOR, "ul[data-testid='pagination-list']")
        return True
    except:
        return False

def scroll_to_load_products(driver, max_scrolls=20, pause_time=2):
    print("🌀 Deteksi: Halaman menggunakan infinite scroll. Melakukan auto-scroll...")
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
        print(f"Gagal klik tombol next: {e}")
        return False

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
            harga_numerik = int(re.sub(r'[Rp.]', '', harga_tag.get_text(strip=True))) if harga_tag else 0
            rating_numerik = float(rating_tag.get_text(strip=True)) if rating_tag else 0.0
            terjual_text = terjual_tag.get_text(strip=True) if terjual_tag else "0"
            jumlah_terjual = parse_terjual(terjual_text)
            produk_ditemukan.append({
                "Nama Produk": nama_tag.get_text(strip=True) if nama_tag else "N/A", "Harga": harga_numerik,
                "Toko": lokasi_toko_spans[0].get_text(strip=True) if len(lokasi_toko_spans) > 0 else "N/A",
                "Lokasi": lokasi_toko_spans[1].get_text(strip=True) if len(lokasi_toko_spans) > 1 else "N/A",
                "Rating": rating_numerik, "Terjual" : jumlah_terjual
            })
        except Exception:
            continue

# --- FUNGSI UTAMA SCRAPING (TANPA STREAMLIT) ---
def scrape_tokopedia_realtime(keyword: str) -> pd.DataFrame:
    print(f"\n⚙️  Mencari produk untuk kata kunci: '{keyword}'...")
    url_target = f"https://www.tokopedia.com/search?st=product&q={keyword.replace(' ', '%20')}"
    options = webdriver.ChromeOptions()
    options.add_argument('--headless') # <-- Tambahkan ini agar browser tidak muncul saat scraping
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
            page_count = 1
            while True:
                print(f"   -> Mengambil data dari halaman {page_count}...")
                ambil_data_dari_halaman(driver, produk_ditemukan)
                page_count += 1
                if not klik_tombol_next_page(driver):
                    break
        else:
            print("🌀 Deteksi: Halaman menggunakan infinite scroll.")
            scroll_to_load_products(driver)
            ambil_data_dari_halaman(driver, produk_ditemukan)
    except TimeoutException:
        print("   -> Gagal menemukan kontainer produk setelah menunggu.")
    finally:
        if 'driver' in locals() and driver:
            driver.quit()
    return pd.DataFrame(produk_ditemukan)

# --- FUNGSI LOGIKA PENYIMPANAN DATA (TANPA STREAMLIT) ---
def scrape_and_save(keyword: str, db):
    """
    Mengatur scraping dan menyimpan data, lalu MENGEMBALIKAN hasil.
    """
    if db is None:
        print("Koneksi database tidak tersedia.")
        return 0, 0
    if not keyword:
        print("Kata kunci tidak boleh kosong.")
        return 0, 0

    try:
        scaler = joblib.load('scaler.pkl')
        model = joblib.load('kmeans_model.pkl')
        print("INFO: Model clustering berhasil dimuat.")
    except FileNotFoundError:
        print("⚠️ Peringatan: File model tidak ditemukan. Produk baru tidak akan diklasifikasikan.")
        scaler, model = None, None

    hasil_df = scrape_tokopedia_realtime(keyword)

    if hasil_df.empty:
        print("Tidak ada produk yang ditemukan untuk di-scrape.")
        return 0, 0

    collection = db['products']
    inserted_count = 0
    updated_count = 0
    print("🔄 Memproses dan menyimpan data ke MongoDB...")

    for index, row in hasil_df.iterrows():
        product_data = row.to_dict()
        query_filter = {"Nama Produk": product_data.get("Nama Produk"), "Toko": product_data.get("Toko")}
        existing_product = collection.find_one(query_filter)
        if existing_product:
            collection.update_one(query_filter, {"$set": product_data})
            updated_count += 1
        else:
            if model and scaler:
                try:
                    fitur_produk = pd.DataFrame([row[['Harga', 'Rating', 'Terjual']]])
                    fitur_scaled = scaler.transform(fitur_produk)
                    cluster_prediksi = model.predict(fitur_scaled)[0]
                    product_data['Cluster'] = int(cluster_prediksi + 1)
                except Exception:
                    product_data['Cluster'] = -1
            else:
                product_data['Cluster'] = -1
            collection.insert_one(product_data)
            inserted_count += 1
            
    print(f"\n✅ Proses selesai!")
    print(f"   -> Produk baru: {inserted_count}, Produk diperbarui: {updated_count}")
    return inserted_count, updated_count # <-- DIUBAH: Mengembalikan nilai


# --- FUNGSI PENGHAPUSAN DATA (TANPA STREAMLIT) ---
def hapus_data_dibawah_harga(db, harga_minimum: int):
    """Menemukan dan menghapus produk di bawah harga minimum dari MongoDB."""
    if db is None:
        print("Koneksi database tidak tersedia.")
        return 0, 0 # Mengembalikan 0 jika tidak ada koneksi
        
    collection = db['products']
    query_filter = {"Harga": {"$lt": harga_minimum}}
    
    try:
        # Hitung dulu berapa banyak dokumen yang cocok
        count = collection.count_documents(query_filter)
        
        if count == 0:
            return 0, 0 # Tidak ada yang perlu dihapus
        
        # Lakukan penghapusan
        result = collection.delete_many(query_filter)
        deleted_count = result.deleted_count
        
        print(f"✅ Sukses! {deleted_count} produk telah dihapus dari database.")
        return count, deleted_count
        
    except Exception as e:
        print(f"Terjadi error tak terduga saat membersihkan data: {e}")
        return 0, 0