import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --- PENGATURAN ---
KATA_KUNCI = "pc gaming"
JUMLAH_HALAMAN = 10  # Tentukan berapa halaman yang ingin Anda scrape
NAMA_FILE_CSV = "hasil_scrape_gaming_pc.csv"

# --- Fungsi Parsing (Sama seperti sebelumnya, tidak perlu diubah) ---
def parse_produk_dari_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    produk_ditemukan = []
    product_container = soup.find("div", attrs={"data-testid": "divSRPContentProducts"})
    if not product_container:
        return []
    produk_list = product_container.find_all("div", attrs={"data-testid": "master-product-card"})
    for produk in produk_list:
        try:
            nama_tag = produk.find("div", attrs={"data-testid": "spnSRPProdName"})
            harga_tag = produk.find("div", attrs={"data-testid": "spnSRPProdPrice"})
            toko_tag = produk.find("span", attrs={"data-testid": "spnSRPProdTabShopName"})
            # Mengambil rating, perlu penanganan khusus karena tidak selalu ada
            rating_div = produk.find("div", class_="css-153qjw7")
            rating = rating_div.find("span", class_="css-t70v7i").text if rating_div else "N/A"

            produk_ditemukan.append({
                "Nama Produk": nama_tag.text.strip() if nama_tag else "N/A",
                "Harga": harga_tag.text.strip() if harga_tag else "N/A",
                "Toko": toko_tag.text.strip() if toko_tag else "N/A",
                "Rating": rating
            })
        except Exception:
            continue
    return produk_ditemukan

# --- SKRIP UTAMA ---
if __name__ == "__main__":
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('log-level=3')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    semua_produk = []
    print(f"Memulai proses scraping untuk kata kunci: '{KATA_KUNCI}'")

    for page in range(1, JUMLAH_HALAMAN + 1):
        # Membuat URL dinamis dengan nomor halaman
        url_target = f"https://www.tokopedia.com/search?st=product&q={KATA_KUNCI.replace(' ', '%20')}&page={page}"
        
        print(f"📄 Mengambil data dari Halaman ke-{page}...")
        driver.get(url_target)

        try:
            # Tunggu hingga kontainer produk utama muncul
            wait = WebDriverWait(driver, 15)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='divSRPContentProducts']")))
            
            # Scroll ke bawah untuk memastikan semua elemen ter-load
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            # Parsing HTML halaman saat ini
            produk_di_halaman_ini = parse_produk_dari_html(driver.page_source)
            if not produk_di_halaman_ini:
                print("   -> Tidak ada produk ditemukan di halaman ini, mungkin halaman terakhir. Berhenti.")
                break
            
            semua_produk.extend(produk_di_halaman_ini)
            print(f"   -> Ditemukan {len(produk_di_halaman_ini)} produk. Total sejauh ini: {len(semua_produk)}")

        except TimeoutException:
            print("   -> Gagal memuat halaman atau halaman kosong. Berhenti.")
            break
            
    driver.quit()

    # Simpan semua hasil ke dalam satu file CSV
    if semua_produk:
        df_hasil = pd.DataFrame(semua_produk)
        df_hasil.to_csv(NAMA_FILE_CSV, index=False)
        print(f"\n✅ Proses selesai. {len(df_hasil)} produk berhasil disimpan di file '{NAMA_FILE_CSV}'")
    else:
        print("\n❌ Tidak ada produk yang berhasil di-scrape.")