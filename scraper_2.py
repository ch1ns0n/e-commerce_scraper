import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Setup opsi untuk browser (opsional, bisa dijalankan headless)
options = Options()
# options.add_argument("--headless")  # jalankan tanpa membuka window browser

driver = webdriver.Chrome(options=options)
url = 'https://www.tokopedia.com/search?st=product&q=%27pc%20gaming&srp_component_id=02.01.00.00&srp_page_id=&srp_page_title=&navsource='
driver.get(url)

try:
    # Tunggu hingga elemen produk muncul
    WebDriverWait(driver, 20).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.css-1asz3by'))
    )

    # Ambil semua elemen produk
    produk_elements = driver.find_elements(By.CSS_SELECTOR, 'div.css-1asz3by')

    for produk in produk_elements:
        try:
            nama = produk.find_element(By.CSS_SELECTOR, 'div.css-92gq3h').text
            print(nama)
        except:
            continue

finally:
    driver.quit()