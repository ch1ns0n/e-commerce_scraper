import streamlit as st
from utils import connect_to_mongodb, scrape_and_save, jalankan_clustering, hapus_data_dibawah_harga

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
                if db is not None:
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

# --- Bagian Hapus Data ---
st.markdown("---")
st.header("3. Bersihkan Data Tidak Logis")
st.write("Gunakan fitur ini untuk menghapus produk yang harganya tidak masuk akal (misalnya di bawah batas tertentu) dari database secara permanen.")

# Gunakan form untuk mengelompokkan input dan tombol
with st.form("cleaning_form"):
    harga_minimum_input = st.number_input(
        "Hapus semua produk dengan harga di bawah (Rp):",
        min_value=0,
        max_value=150000000,
        value=1500000,
        step=100000
    )
    
    # Checkbox konfirmasi untuk keamanan
    konfirmasi = st.checkbox("⚠️ Saya mengerti bahwa tindakan ini tidak dapat diurungkan.")
    
    submitted = st.form_submit_button("Hapus Permanen Data")

    if submitted:
        if konfirmasi:
            with st.spinner(f"Mencari dan menghapus produk di bawah Rp {harga_minimum_input:,}..."):
                db, client = connect_to_mongodb()
                if db is not None:
                    # Panggil fungsi dari utils
                    ditemukan, dihapus = hapus_data_dibawah_harga(db, harga_minimum_input)
                    
                    if ditemukan > 0:
                        st.success(f"✅ Selesai! Ditemukan {ditemukan} produk dan berhasil menghapus {dihapus} produk.")
                    else:
                        st.info("✅ Tidak ada produk yang cocok dengan kriteria untuk dihapus.")
                    
                    if client:
                        client.close()
                else:
                    st.error("Gagal terhubung ke database.")
        else:
            st.error("Harap centang kotak konfirmasi untuk melanjutkan proses penghapusan.")