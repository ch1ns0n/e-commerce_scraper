import time
import csv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
# Import untuk WebDriverWait
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --- PENGATURAN ---
URL_TARGET = 'https://www.tokopedia.com/search?st=product&q=pc%20gaming%20streaming&srp_component_id=02.01.00.00&srp_page_id=&srp_page_title=&navsource='
JUMLAH_HALAMAN_SCRAPE = 10
NAMA_FILE_CSV = 'pc_gaming_streaming.csv'

# --- FUNGSI UNTUK PARSING (Tidak ada perubahan) ---
def parse_produk_dari_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    produk_ditemukan = []
    product_container = soup.find("div", attrs={"data-testid": "divSRPContentProducts"})
    if not product_container:
        return []
    produk_list = product_container.find_all("a", attrs={"data-theme": "default"})
    for produk in produk_list:
        try:
            nama_tag = produk.find("span", class_="+tnoqZhn89+NHUA43BpiJg==")
            harga_tag = produk.find("div", class_="urMOIDHH7I0Iy1Dv2oFaNw==")
            lokasi_toko_spans = produk.find_all("span", class_=lambda c: c and 'gxi+fsElj' in c)
            rating_tag = produk.find("span", class_="_2NfJxPu4JC-55aCJ8bEsyw==")
            terjual_tag = produk.find("span", class_="u6SfjDD2WiBlNW7zHmzRhQ==")
            nama = nama_tag.get_text(strip=True) if nama_tag else "N/A"
            harga = harga_tag.get_text(strip=True) if harga_tag else "N/A"
            toko = lokasi_toko_spans[0].get_text(strip=True) if len(lokasi_toko_spans) > 0 else "N/A"
            lokasi = lokasi_toko_spans[1].get_text(strip=True) if len(lokasi_toko_spans) > 1 else "N/A"
            rating = rating_tag.get_text(strip=True) if rating_tag else "N/A"
            terjual = terjual_tag.get_text(strip=True) if terjual_tag else "N/A"
            if nama != "N/A":
                produk_ditemukan.append([nama, harga, toko, lokasi, rating, terjual])
        except Exception:
            continue
    return produk_ditemukan

# --- SKRIP UTAMA ---
if __name__ == "__main__":
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(URL_TARGET)
    print("Browser terbuka, menunggu halaman awal memuat...")
    time.sleep(5)

    semua_produk = []
    for page in range(1, JUMLAH_HALAMAN_SCRAPE + 1):
        print(f"📄 Memproses Halaman ke-{page}...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        produk_di_halaman_ini = parse_produk_dari_html(driver.page_source)
        if not produk_di_halaman_ini and page > 1:
            print("   -> Tidak menemukan produk baru di halaman ini, mungkin halaman yang sama ter-load ulang. Menghentikan.")
            break
            
        semua_produk.extend(produk_di_halaman_ini)
        print(f"   -> Ditemukan {len(produk_di_halaman_ini)} produk. Total sejauh ini: {len(semua_produk)}")

        if page == JUMLAH_HALAMAN_SCRAPE:
            print("   -> Telah mencapai jumlah halaman maksimum yang diatur.")
            break

        # --- LOGIKA BARU UNTUK MENCARI & MENGKLIK TOMBOL ---
        try:
            print("   -> Mencari tombol 'Laman berikutnya'...")
            # Menunggu maksimal 10 detik hingga tombol bisa diklik
            wait = WebDriverWait(driver, 10)
            next_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='btnSRPNextPage']")))
            
            # Scroll ke tombol sebelum mengklik untuk memastikan tombol terlihat
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
            time.sleep(3) # Beri jeda sesaat setelah scroll

            next_button.click()
            print("   -> Berhasil mengklik 'Laman berikutnya'. Menunggu halaman baru...")
            time.sleep(4) # Tunggu halaman baru memuat
        except TimeoutException:
            print("🏁 Tombol 'Laman berikutnya' tidak ditemukan atau tidak bisa diklik setelah menunggu. Scraping selesai.")
            break
        except Exception as e:
            print(f"🏁 Terjadi error saat mencoba klik halaman berikutnya: {e}")
            break
            
    driver.quit()

    print(f"\n✅ Proses scraping selesai. Menulis {len(semua_produk)} produk ke file {NAMA_FILE_CSV}...")
    with open(NAMA_FILE_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(['Nama Produk', 'Harga', 'Toko', 'Lokasi', 'Rating', 'Terjual'])
        writer.writerows(semua_produk)
        
    print("✨ Selesai! ✨")