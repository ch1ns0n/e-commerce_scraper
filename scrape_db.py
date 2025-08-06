# --- Bagian 1: Import semua library yang dibutuhkan ---
import pandas as pd
import time
import random
import os
import re
import joblib
import warnings
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
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

warnings.simplefilter(action='ignore', category=FutureWarning)


def connect_to_mongodb():
    """Membuat koneksi ke database MongoDB Atlas menggunakan environment variable."""
    # DIUBAH: Ambil URI dari environment variable 'MONGO_URI'
    uri = os.environ.get("MONGO_URI")
    
    if not uri:
        print("❌ Gagal menemukan MONGO_URI. Pastikan secret sudah diatur di GitHub Actions.")
        # Anda bisa menambahkan URI lokal di sini untuk testing di komputer Anda
        uri = "mongodb+srv://samuelchinson:test123@cluster0.bxaivdh.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0" 
        return None
    
    client = MongoClient(uri, server_api=ServerApi('1'))
    try:
        client.admin.command('ping')
        print("✅ Berhasil terhubung ke MongoDB!")
        db = client['tokopedia_db']
        # Kembalikan client dan db
        return db, client
    except Exception as e:
        print(f"❌ Gagal terhubung ke MongoDB: {e}")
        return None, None

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

def parse_terjual(text: str) -> int:
    """
    Mengurai teks 'terjual' menjadi integer yang akurat.
    Contoh: 'Terjual 50+' -> 50, 'Terjual 1,5 rb' -> 1500, 'Terjual 2' -> 2
    """
    if not isinstance(text, str) or 'terjual' not in text.lower():
        return 0
    
    try:
        # 1. Bersihkan teks awal dan siapkan multiplier
        text_cleaned = text.lower().replace('terjual', '').replace('+', '').strip()
        multiplier = 1
        
        # 2. Cek apakah ada 'rb' (ribu)
        if 'rb' in text_cleaned:
            multiplier = 1000
            text_cleaned = text_cleaned.replace('rb', '').strip()
        
        # 3. Ganti koma desimal dengan titik dan ekstrak angka
        numeric_part_str = text_cleaned.replace(',', '.')
        
        # Ekstrak hanya angka dan titik desimal menggunakan regex
        found_numbers = re.findall(r'[\d.]+', numeric_part_str)
        if not found_numbers:
            return 0
            
        value = float(found_numbers[0])
        
        # 4. Hitung nilai akhir
        final_value = int(value * multiplier)
        
        return final_value
    except (ValueError, TypeError, IndexError):
        # Jika terjadi error saat konversi, kembalikan 0
        return 0

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
            terjual_tag = produk.find("span", class_="u6SfjDD2WiBlNW7zHmzRhQ==")
            
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
                "Terjual" : jumlah_terjual
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

def scrape_and_save(db):
    """
    Mengatur proses scraping dan menyimpan data ke MongoDB dengan logika upsert.
    """
    if db is None:
        print("Koneksi database tidak tersedia. Proses dibatalkan.")
        return
        
    keyword = input("\n> Masukkan kata kunci produk untuk di-scrape: ")
    if not keyword:
        print("❌ Kata kunci tidak boleh kosong.")
        return

    hasil_df = scrape_tokopedia_realtime(keyword)

    if hasil_df.empty:
        print("❌ Tidak ada produk yang ditemukan untuk di-scrape.")
        return

    # Pilih koleksi (mirip tabel) di dalam database Anda
    collection = db['products']
    
    inserted_count = 0
    updated_count = 0
    print("🔄 Memproses dan menyimpan data ke MongoDB...")
    
    try:
        # BARU: Muat model dan scaler yang sudah ada
        scaler = joblib.load('scaler.pkl')
        model = joblib.load('kmeans_model.pkl')
        print("Model clustering berhasil dimuat.")
    except FileNotFoundError:
        print("⚠️ File model tidak ditemukan. Harap jalankan run_clustering.py terlebih dahulu.")
        return

    # Loop setiap produk hasil scrape
    for index, row in hasil_df.iterrows():
        # Ubah baris DataFrame menjadi dictionary
        product_data = row.to_dict()
        
        # Tentukan filter untuk mencari dokumen yang cocok
        query_filter = {
            "Nama Produk": product_data["Nama Produk"],
            "Toko": product_data["Toko"]
        }
        
        # Buat data yang akan di-update atau di-insert
        update_data = {"$set": product_data}
        
        # Jalankan perintah upsert (update or insert)
        result = collection.update_one(query_filter, update_data, upsert=True)

        if result.upserted_id is not None:
            inserted_count += 1
        elif result.matched_count > 0:
            updated_count += 1
        else:
            # JIKA TIDAK ADA (PRODUK BARU):
            # 1. Siapkan fitur untuk prediksi
            fitur_produk = pd.DataFrame([row[['Harga', 'Rating', 'Terjual']]])
            
            # 2. Lakukan scaling pada fitur
            fitur_scaled = scaler.transform(fitur_produk)
            
            # 3. Prediksi clusternya
            cluster_prediksi = model.predict(fitur_scaled)[0]
            
            # 4. Tambahkan hasil prediksi ke data produk
            product_data = row.to_dict()
            product_data['Cluster'] = int(cluster_prediksi + 1) # Tambah 1 agar jadi 1-5
            
            # 5. Lakukan INSERT dokumen baru yang sudah lengkap
            collection.insert_one(product_data)
            inserted_count += 1

        # Tambahkan hasil prediksi ke data sebelum disimpan
        row['Cluster'] = int(cluster_prediksi + 1) # Tambah 1 agar jadi 1-5

        # Lakukan INSERT dengan data yang sudah ada clusternya
        collection.insert_one(row.to_dict())
        inserted_count += 1
            
    print(f"\n✅ Proses selesai!")
    print(f"   -> Produk baru ditambahkan: {inserted_count}")
    print(f"   -> Produk yang sudah ada diperbarui: {updated_count}")

def clean_data_for_analytics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Membersihkan DataFrame mentah untuk analisis. 
    Mengubah Teks (Rp, dll) menjadi Angka dan menangani nilai yang hilang.
    """
    print("🧼 Membersihkan data untuk analisis...")
    df_clean = df.copy()

    # 1. Membersihkan Harga dan mengubahnya menjadi numerik
    #    Mengganti kolom 'Harga' secara langsung, bukan membuat kolom baru.
    df_clean['Harga'] = pd.to_numeric(
        df_clean['Harga'].astype(str).str.replace(r'[Rp.]', '', regex=True), 
        errors='coerce'
    ).fillna(0).astype(int)

    # 2. Membersihkan Rating dan mengubahnya menjadi numerik
    #    Mengganti kolom 'Rating' secara langsung dan mengisi N/A dengan 0.
    df_clean['Rating'] = pd.to_numeric(
        df_clean['Rating'], 
        errors='coerce'
    ).fillna(0.0)

    # 3. Filter data yang tidak logis (harga 0) dan lokasi N/A
    df_clean = df_clean[df_clean['Harga'] > 0]
    df_clean = df_clean[df_clean['Lokasi'] != 'N/A']
    df_clean.dropna(subset=['Lokasi'], inplace=True)
    
    return df_clean

def visualize_diagnostics(raw_df: pd.DataFrame):
    """
    Menampilkan menu interaktif untuk memilih jenis visualisasi diagnostik.
    """
    # Langkah 1: Selalu bersihkan data terlebih dahulu
    df = clean_data_for_analytics(raw_df)

    if df.empty or len(df) < 2:
        print("❌ Tidak cukup data untuk analisis diagnostik (minimal 2 produk valid).")
        return

    # Langkah 2: Buat loop untuk menu interaktif
    while True:
        print("\n--- 📊 Menu Visualisasi Diagnostik ---")
        print("1. Distribusi Harga di Berbagai Kota (Box Plot)")
        print("2. Sebaran Harga Keseluruhan (Histogram)")
        print("3. Hubungan Harga vs. Rating (Scatter Plot)")
        print("4. Jumlah Produk per Lokasi (Bar Chart)")
        print("0. Kembali ke Menu Utama")

        choice = input("> Pilih visualisasi yang ingin ditampilkan (0-4): ")

        if choice == '1':
            # Menjawab: "Apakah lokasi toko mempengaruhi sebaran harga produk?"
            print("Membuat plot: Distribusi Harga per Lokasi...")
            plt.figure(figsize=(12, 8))
            top_lokasi = df['Lokasi'].value_counts().nlargest(10).index
            sns.boxplot(data=df[df['Lokasi'].isin(top_lokasi)], x='Harga', y='Lokasi', palette='coolwarm')
            plt.title('Distribusi Harga di Top 10 Lokasi', fontsize=16)
            plt.xlabel("Harga (Rp)", fontsize=12)
            plt.ylabel("Lokasi", fontsize=12)
            plt.ticklabel_format(style='plain', axis='x')
            plt.tight_layout()
            plt.show()

        elif choice == '2':
            # Menjawab: "Berapa rentang harga yang paling umum untuk produk ini?"
            print("Membuat plot: Sebaran Harga Keseluruhan...")
            plt.figure(figsize=(10, 6))
            sns.histplot(data=df, x='Harga', kde=True, bins=25, color='dodgerblue')
            plt.title('Sebaran Harga Keseluruhan', fontsize=16)
            plt.xlabel("Harga (Rp)", fontsize=12)
            plt.ylabel("Jumlah Produk", fontsize=12)
            plt.ticklabel_format(style='plain', axis='x')
            plt.tight_layout()
            plt.show()

        elif choice == '3':
            # Menjawab: "Apakah produk yang lebih mahal cenderung punya rating lebih baik?"
            df_rated = df[df['Rating'] > 0]
            if df_rated.empty:
                print("\n⚠️ Tidak ada produk dengan rating > 0 untuk dianalisis.")
                continue
            
            print("Membuat plot: Hubungan Harga vs. Rating...")
            plt.figure(figsize=(10, 6))
            sns.scatterplot(data=df_rated, x='Rating', y='Harga', alpha=0.6, color='seagreen')
            plt.title('Hubungan Harga vs. Rating', fontsize=16)
            plt.xlabel("Rating", fontsize=12)
            plt.ylabel("Harga (Rp)", fontsize=12)
            plt.grid(True, linestyle='--', alpha=0.6)
            plt.ticklabel_format(style='plain', axis='y')
            plt.tight_layout()
            plt.show()

        elif choice == '4':
            # Menjawab: "Kota mana yang memiliki listing produk paling banyak?"
            print("Membuat plot: Jumlah Produk per Lokasi...")
            plt.figure(figsize=(12, 8))
            df['Lokasi'].value_counts().nlargest(15).plot(kind='barh', color='mediumorchid')
            plt.title('Jumlah Listing Produk per Lokasi (Top 15)', fontsize=16)
            plt.xlabel("Jumlah Produk", fontsize=12)
            plt.ylabel("Lokasi", fontsize=12)
            plt.gca().invert_yaxis() # Urutkan dari terbesar ke terkecil
            plt.tight_layout()
            plt.show()

        elif choice == '0':
            print("✅ Kembali ke menu utama.")
            break

        else:
            print("❌ Pilihan tidak valid. Silakan masukkan angka dari 0 hingga 4.")

def search_and_display(db):
    """Mencari produk di MongoDB dan menampilkannya dengan penanganan input yang lebih baik."""
    if db is None: return
    collection = db['products']
    
    search_term = input("\n> Masukkan kata kunci untuk dicari di database: ")
    if not search_term:
        print("❌ Kata kunci tidak boleh kosong.")
        return
        
    # --- PERBAIKAN DIMULAI DI SINI ---
    
    # 1. Bersihkan input dari spasi di awal/akhir dan pastikan tidak ada kata kosong
    words = [word for word in search_term.strip().split() if word]
    
    # 2. Jika setelah dibersihkan tidak ada kata yang tersisa, batalkan pencarian
    if not words:
        print("❌ Kata kunci tidak valid.")
        return

    # --- AKHIR DARI PERBAIKAN ---

    # Query builder sekarang menggunakan 'words' yang sudah bersih
    query_filter = {
        "$and": [
            {
                "$or": [
                    {"Nama Produk": {"$regex": word, "$options": "i"}},
                    {"Toko": {"$regex": word, "$options": "i"}}
                ]
            } for word in words
        ]
    }
    
    results_cursor = collection.find(query_filter).sort([("Terjual", -1), ("Rating", -1)])
    
    results_list = list(results_cursor)
    if not results_list:
        print("❌ Tidak ada produk yang cocok dengan kata kunci di database.")
        return
        
    results_df = pd.DataFrame(results_list)
    
    urutan_kolom = ["Nama Produk", "Harga", "Rating", "Terjual", "Toko", "Lokasi"]
    # Menambahkan pengecekan kolom sebelum mengurutkan
    kolom_tersedia = [kol for kol in urutan_kolom if kol in results_df.columns]
    results_df = results_df.drop(columns=['_id'])[kolom_tersedia]
    
    print(f"\n✅ Ditemukan {len(results_df)} produk dari database (diurutkan berdasarkan penjualan & rating):")
    pd.set_option('display.max_colwidth', 30)
    print(results_df)
    
    # Opsi untuk ekspor dan visualisasi
    export_choice = input("\n📄 Ekspor hasil ini ke file CSV? (y/n): ").lower()
    if export_choice == 'y':
        filename = f"pencarian_{search_term.replace(' ', '_')}_{int(time.time())}.csv"
        results_df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"✅ Hasil disimpan ke file: {filename}")
        
    viz_choice = input("📊 Buat visualisasi diagnostik dari hasil ini? (y/n): ").lower()
    if viz_choice == 'y':
        # Pastikan Anda sudah memiliki fungsi visualize_diagnostics dari jawaban sebelumnya
        visualize_diagnostics(results_df) 
    else:
        print("❌ Tidak ada produk yang cocok dengan kata kunci di database.")

def lihat_semua_data(db):
    """Mengambil dan menampilkan seluruh isi koleksi products dari MongoDB."""
    if db is None: return
    collection = db['products']
    
    print("\n📦 Menampilkan seluruh data dari database...")
    try:
        results_cursor = collection.find({}).sort([
            ("Terjual", -1), 
            ("Rating", -1)
        ])
        # Mengambil semua dokumen dari koleksi
        results_list = list(results_cursor)
        
        if not results_list:
            print("Database masih kosong. Lakukan scraping terlebih dahulu.")
            return
        
        df = pd.DataFrame(results_list)
        
        urutan_kolom = ["Nama Produk", "Harga", "Toko", "Lokasi", "Rating", "Terjual"]
        df = df.drop(columns=['_id'])[urutan_kolom]
        
        pd.set_option('display.max_colwidth', 30)
        print(df)
        print(f"\nTotal: {len(df)} produk ditemukan di database.")

    except Exception as e:
        print(f"Terjadi error saat mengambil data: {e}")
        
def ekspor_semua_ke_csv(db):
    """Mengekspor seluruh koleksi 'products' ke dalam satu file CSV."""
    if db is None: return
    collection = db['products']

    print("\n💾 Mengekspor seluruh data ke file CSV...")
    try:
        df = pd.DataFrame(list(collection.find({})))
        
        if df.empty:
            print("Database masih kosong. Tidak ada data untuk diekspor.")
            return
            
        nama_file = f"tokopedia_dataset_{int(time.time())}.csv"
        # Menyimpan DataFrame ke file CSV tanpa kolom '_id'
        df.drop(columns=['_id']).to_csv(nama_file, index=False, encoding='utf-8-sig')
        
        print(f"✅ Sukses! {len(df)} produk telah diekspor ke file: {nama_file}")

    except Exception as e:
        print(f"❌ Terjadi error saat mengekspor data: {e}")

def hapus_data_tidak_logis(db):
    """Menghapus produk dari MongoDB yang harganya di bawah ambang batas."""
    if db is None: return
    collection = db['products']
    harga_minimum = 1500000

    try:
        # Query MongoDB untuk harga "lebih kecil dari" ($lt)
        query_filter = {"Harga": {"$lt": harga_minimum}}
        
        count = collection.count_documents(query_filter)

        if count == 0:
            print("\n✅ Tidak ada produk dengan harga di bawah Rp1.500.000 untuk dihapus.")
            return

        konfirmasi = input(f"\n⚠️ Ditemukan {count} produk dengan harga di bawah Rp{harga_minimum:,}. Anda yakin ingin menghapusnya? (y/n): ").lower()

        if konfirmasi == 'y':
            result = collection.delete_many(query_filter)
            print(f"✅ Sukses! {result.deleted_count} produk telah dihapus dari database.")
        else:
            print("ℹ️ Proses penghapusan dibatalkan.")

    except Exception as e:
        print(f"Terjadi error tak terduga: {e}")

# --- Bagian 5: Fungsi Utama (Main) dengan Menu ---

def main():
    """Fungsi utama untuk menjalankan aplikasi dengan menu interaktif."""
    # Ganti koneksi SQLite dengan MongoDB
    db, client = connect_to_mongodb()
    
    if db is None:
        print("Keluar dari program karena tidak ada koneksi database.")
        return

    print("=========================================")
    print("🤖 Selamat Datang di Bot Tokopedia (MongoDB Edition)")
    print("=========================================")

    while True:
        print("\n--- MENU UTAMA ---")
        print("1. ⚙️  Scrape data produk baru dari Tokopedia")
        print("2. 🔍 Cari produk di database lokal")
        print("3. 📦 Lihat semua data di database") # Pilihan baru
        print("4. 🗑️ Hapus data di bawah 1,5 juta") # Pilihan baru
        print("5. 💾 Ekspor semua data ke CSV") # Pilihan baru
        print("6. 🚪 Keluar")

        choice = input("> Pilih opsi: ")

        if choice == '1':
            scrape_and_save(db)
        elif choice == '2':
            search_and_display(db)
        elif choice == '3': # Pilihan baru
            lihat_semua_data(db)
        elif choice == '4': # Pilihan baru
            hapus_data_tidak_logis(db)
        elif choice == '5': # Pilihan baru
            ekspor_semua_ke_csv(db)
        elif choice == '6': # Nomor urut disesuaikan
            print("\n👋 Terima kasih! Sampai jumpa!")
            break
        else:
            print("❌ Pilihan tidak valid, silakan coba lagi.")
    
    if client:
        client.close()

if __name__ == "__main__":
    main()