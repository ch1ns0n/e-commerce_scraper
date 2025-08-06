import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# URL Target
target_url = 'https://www.tokopedia.com/search?st=product&q=pc%20gaming'

# --- Opsi Chrome untuk menghindari deteksi bot ---
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36')

print("🚀 Membuka browser dengan konfigurasi baru...")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get(target_url)

print("⏳ Menunggu halaman memuat...")
time.sleep(5)

# --- LOGIKA PAGINASI BARU ---
# Tentukan berapa banyak halaman yang ingin di-scrape
jumlah_halaman_scrape = 10 
all_html = ""

for page in range(1, jumlah_halaman_scrape + 1):
    print(f"\n📄 Scraping Halaman ke-{page}...")
    
    # Lakukan sedikit scroll untuk memastikan semua elemen termuat
    for i in range(5): # Cukup 2x scroll per halaman
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5)

    # Kumpulkan HTML dari halaman saat ini
    html_content = driver.page_source
    all_html += html_content
    print(f"   -> HTML dari halaman {page} berhasil dikumpulkan.")

    # Cari dan klik tombol 'Laman berikutnya'
    try:
        # Menggunakan aria-label adalah selector yang lebih stabil
        next_button = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Laman berikutnya']")
        if next_button.is_enabled():
            next_button.click()
            print("   -> Mengklik tombol 'Laman berikutnya'. Menunggu halaman baru...")
            time.sleep(4) # Beri waktu untuk halaman baru memuat
        else:
            print("   -> Tombol 'Laman berikutnya' tidak aktif. Mungkin ini halaman terakhir.")
            break
    except Exception as e:
        print(f"🏁 Tidak dapat menemukan tombol 'Laman berikutnya'. Proses scraping selesai. Error: {e}")
        break

# Tutup browser setelah selesai
driver.quit()

# Simpan semua HTML yang terkumpul menjadi satu file
print("\n💾 Menyimpan semua HTML yang terkumpul...")
soup = BeautifulSoup(all_html, 'html.parser')
with open("tokped_pc_gaming.html", "w", encoding="utf-8") as f:
    f.write(soup.prettify())

print("✅ HTML dari beberapa halaman berhasil disimpan. Cek file tokped_pc_gaming.html")