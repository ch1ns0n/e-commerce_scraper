import streamlit as st
from utils import connect_to_mongodb, scrape_and_save, jalankan_clustering # <-- Import fungsi dari utils

st.set_page_config(page_title="Kontrol Data", layout="centered")

st.title("⚙️ Kontrol Data: Scraping & Clustering")
st.write("Gunakan halaman ini untuk mengambil data produk terbaru dari Tokopedia atau untuk melatih ulang model segmentasi pasar (clustering).")

# --- Bagian Scraping ---
st.header("1. Ambil Data Produk Baru")
with st.form("scraping_form"):
    keyword = st.text_input("Masukkan kata kunci produk (contoh: pc gaming)", "laptop gaming")
    submitted = st.form_submit_button("🚀 Mulai Scraping")

    if submitted:
        if not keyword:
            st.error("Kata kunci tidak boleh kosong!")
        else:
            # Menggunakan st.status untuk menampilkan progres
            with st.spinner(f"Mencari produk untuk '{keyword}'... Ini mungkin memakan waktu beberapa menit."):
                st.info("Menghubungkan ke database...")
                db, client = connect_to_mongodb()
                if db:
                    st.info("Memulai proses scraping... Browser sedang berjalan di latar belakang (headless).")
                    
                    # Panggil fungsi dari utils.py
                    inserted, updated = scrape_and_save(keyword, db)
                    
                    st.success("✅ Proses Scraping Selesai!")
                    st.write(f"- **Produk baru ditambahkan:** {inserted}")
                    st.write(f"- **Produk yang ada diperbarui:** {updated}")
                    
                    if client:
                        client.close()
                        st.info("Koneksi ke database ditutup.")
                else:
                    st.error("Gagal terhubung ke database. Proses dibatalkan.")

# --- Bagian Clustering ---
st.header("2. Latih Ulang Model Segmentasi (Clustering)")
st.warning("Proses ini akan melatih ulang model K-Means berdasarkan data terbaru di database dan memperbarui label 'Cluster' untuk setiap produk.")

if st.button("🧠 Latih Ulang Model"):
    with st.spinner("Memproses clustering... Ini bisa memakan waktu jika data sangat banyak."):
        # Panggil fungsi clustering dari utils.py
        result_message = jalankan_clustering()
        st.success("✅ Proses Clustering Selesai!")
        st.info(result_message)