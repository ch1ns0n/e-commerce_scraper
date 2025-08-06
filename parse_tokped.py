from bs4 import BeautifulSoup
import csv
import os

# Nama file input dan output
html_file = "tokped_pc_gaming.html"
csv_file = "tokped_products_4.csv"

# Pastikan file HTML ada
if not os.path.exists(html_file):
    print(f"❌ Error: File '{html_file}' tidak ditemukan. Jalankan 'scraping.py' terlebih dahulu.")
else:
    # Buka file HTML
    with open(html_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    # Cari container utama yang berisi semua produk
    # Menggunakan data-testid lebih stabil daripada class CSS yang sering berubah
    product_container = soup.find("div", attrs={"data-testid": "divSRPContentProducts"})

    produk_list = []
    if product_container:
        # Cari semua kartu produk di dalam container
        # Atribut data-theme='default' adalah penanda yang baik untuk kartu produk
        produk_list = product_container.find_all("a", attrs={"data-theme": "default"})

    print(f"🔍 Ditemukan {len(produk_list)} produk di dalam file HTML.")

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(['Nama Produk', 'Harga', 'Toko', 'Lokasi', 'Rating', 'Terjual'])

        successful_parses = 0
        for idx, produk in enumerate(produk_list, start=1):
            try:
                # Karena class CSS sangat dinamis, kita harus menggunakan nama yang aneh ini
                # Ini spesifik untuk file HTML yang Anda berikan
                nama_tag = produk.find("span", class_="+tnoqZhn89+NHUA43BpiJg==")
                harga_tag = produk.find("div", class_="urMOIDHH7I0Iy1Dv2oFaNw==")
                
                # Toko dan lokasi berada dalam spans dengan class yang mirip
                lokasi_toko_spans = produk.find_all("span", class_=lambda c: c and 'gxi+fsElj' in c)
                
                rating_tag = produk.find("span", class_="_2NfJxPu4JC-55aCJ8bEsyw==")
                terjual_tag = produk.find("span", class_="u6SfjDD2WiBlNW7zHmzRhQ==")

                # Ekstrak teks, berikan 'N/A' jika tag tidak ditemukan
                nama = nama_tag.get_text(strip=True) if nama_tag else "N/A"
                harga = harga_tag.get_text(strip=True) if harga_tag else "N/A"
                
                toko = lokasi_toko_spans[0].get_text(strip=True) if len(lokasi_toko_spans) > 0 else "N/A"
                lokasi = lokasi_toko_spans[1].get_text(strip=True) if len(lokasi_toko_spans) > 1 else "N/A"
                
                rating = rating_tag.get_text(strip=True) if rating_tag else "N/A"
                terjual = terjual_tag.get_text(strip=True) if terjual_tag else "N/A"
                
                # Hanya tulis baris jika nama produk berhasil ditemukan
                if nama != "N/A":
                    writer.writerow([nama, harga, toko, lokasi, rating, terjual])
                    successful_parses += 1
            except Exception as e:
                print(f"⚠️ Gagal parsing produk ke-{idx}: {e}")

    print(f"✅ Selesai. Sebanyak {successful_parses} produk berhasil disimpan di {csv_file}")