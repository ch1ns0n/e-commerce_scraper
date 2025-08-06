# Simpan sebagai bot_proxy_tokopedia.py

import pandas as pd
import time
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import warnings

# Impor fungsi dari file pertama
from proxy_extension import create_proxy_extension

warnings.simplefilter(action='ignore', category=FutureWarning)

# --- PENGATURAN PROXY (Ganti dengan informasi dari penyedia Anda) ---
PROXY_HOST = 'dc.oxylabs.io'
PROXY_PORT = 8000
PROXY_USER = 'user-samuel_sJEw7-country-US'
PROXY_PASS = '502030_Samue1'

# Fungsi parsing dan scroll tidak perlu diubah, bisa disalin dari skrip sebelumnya
def ambil_data_dari_halaman(driver, produk_ditemukan: list):
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    produk_list = soup.find_all("div", attrs={"data-testid": "master-product-card"})
    initial_count = len(produk_ditemukan)
    for produk in produk_list:
        try:
            nama_tag = produk.find("div", attrs={"data-testid": "spnSRPProdName"})
            harga_tag = produk.find("div", attrs={"data-testid": "spnSRPProdPrice"})
            toko_tag = produk.find("span", attrs={"data-testid": "spnSRPProdTabShopName"})
            
            if not nama_tag: continue
            nama_produk_unik = nama_tag.text.strip()
            if any(p['Nama Produk'] == nama_produk_unik for p in produk_ditemukan): continue

            produk_ditemukan.append({
                "Nama Produk": nama_produk_unik,
                "Harga": harga_tag.text.strip() if harga_tag else "N/A",
                "Toko": toko_tag.text.strip() if toko_tag else "N/A",
            })
        except Exception:
            continue
    newly_added = len(produk_ditemukan) - initial_count
    print(f"   -> Berhasil mem-parsing {newly_added} produk baru dari halaman ini.")

def scroll_to_load_products(driver, max_scrolls=10):
    print("   -> Melakukan auto-scroll perlahan...")
    last_count = 0
    for i in range(max_scrolls):
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(1.5)
        product_containers = driver.find_elements(By.CSS_SELECTOR, "div[data-testid='master-product-card']")
        current_count = len(product_containers)
        print(f"   -> Scroll ke-{i+1}: {last_count} → {current_count} produk")
        if current_count == last_count and last_count > 0: break
        last_count = current_count

def scrape_tokopedia_realtime(keyword: str) -> pd.DataFrame:
    print(f"\n⚙️  Mencari produk untuk '{keyword}' menggunakan proxy...")
    url_target = f"https://www.tokopedia.com/search?st=product&q={keyword.replace(' ', '%20')}"

    # Membuat file ekstensi proxy
    proxy_zip = create_proxy_extension(PROXY_HOST, PROXY_PORT, PROXY_USER, PROXY_PASS)
    
    options = uc.ChromeOptions()
    # Muat ekstensi proxy yang baru dibuat
    options.add_extension(proxy_zip)
    
    driver = uc.Chrome(options=options)
    
    produk_ditemukan = []
    try:
        driver.get(url_target)
        print("   -> Menunggu produk pertama muncul di halaman (via proxy)...")
        wait = WebDriverWait(driver, 25) # Waktu tunggu sedikit lebih lama karena proxy
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='master-product-card']")))
        print("   -> Produk pertama berhasil dimuat!")
        time.sleep(1)

        scroll_to_load_products(driver)
        ambil_data_dari_halaman(driver, produk_ditemukan)

    except TimeoutException:
        print("   -> Gagal menemukan produk setelah menunggu. Proxy mungkin lambat atau diblokir.")
    finally:
        if 'driver' in locals() and driver:
            driver.quit()
    
    return pd.DataFrame(produk_ditemukan)

if __name__ == "__main__":
    # ... (Bagian ini sama persis seperti skrip sebelumnya) ...
    print("==================================================")
    print("🤖 Bot Pencari Tokopedia dengan Residential Proxy")
    print("==================================================")
    while True:
        user_input = input("\n> Masukkan kata kunci ('keluar' untuk stop): ")
        if user_input.lower() in ['keluar', 'exit']:
            print("👋 Terima kasih!")
            break
        hasil_df = scrape_tokopedia_realtime(user_input)
        if not hasil_df.empty:
            print(f"\n✅ Ditemukan {len(hasil_df)} produk:")
            print(hasil_df)
        else:
            print("❌ Tidak ada produk yang ditemukan.")