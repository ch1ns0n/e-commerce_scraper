import streamlit as st
import pandas as pd
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import joblib

# --- Fungsi Pemuatan Data & Model (WAJIB ADA di setiap halaman) ---
@st.cache_data
def load_data():
    uri = "mongodb+srv://samuelchinson:test123@cluster0.bxaivdh.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    client = MongoClient(uri, server_api=ServerApi('1'))
    db = client['tokopedia_db']
    collection = db['products']
    df = pd.DataFrame(list(collection.find({})))
    if '_id' in df.columns: df = df.drop(columns=['_id'])
    if 'Cluster' in df.columns: df['Cluster'] = df['Cluster'].fillna(-1).astype(int)
    return df

@st.cache_resource
def load_models():
    try:
        scaler = joblib.load('scaler.pkl')
        model = joblib.load('kmeans_model.pkl')
        return scaler, model
    except FileNotFoundError:
        return None, None

df = load_data()
scaler, model = load_models()

# --- Tampilan Halaman Simulasi ---
st.title("🚀 Asisten Peluncuran Produk")
st.write("Masukkan spesifikasi komponen PC yang Anda rencanakan untuk dijual untuk mendapatkan analisis pasar.")

if scaler is None or model is None:
    st.error("Model tidak ditemukan! Harap jalankan `run_clustering.py` terlebih dahulu untuk membuat file `scaler.pkl` dan `kmeans_model.pkl`.")
else:
    with st.form("simulasi_form"):
        st.subheader("Masukkan Spesifikasi Produk Baru Anda")
        rating_target = st.slider("Target Rating Produk Anda:", 1.0, 5.0, 4.8, 0.1)
        st.markdown("Pilih komponen utama untuk estimasi harga:")
        col1, col2 = st.columns(2)
        with col1:
            pilihan_cpu = st.selectbox("Prosesor (CPU):", ('i3', 'i5', 'i7', 'i9', 'Ryzen 3', 'Ryzen 5', 'Ryzen 7', 'Ryzen 9'))
        with col2:
            pilihan_gpu = st.selectbox("Kartu Grafis (GPU):", ('RTX 3050', 'RTX 3060', 'RTX 3070', 'RTX 3080', 'RTX 3090', 'RTX 4050', 'RTX 4060', 'RTX 4070', 'RTX 4080', 'RTX 4090', 'RX 6500', 'RX 6700 XT', 'RX 6800 XT', 'RX 6900 XT'))

        submitted = st.form_submit_button("Jalankan Simulasi")

        if submitted:
            df_spek_serupa = df[
                (df['Nama Produk'].str.contains(pilihan_cpu, case=False, na=False)) & 
                (df['Nama Produk'].str.contains(pilihan_gpu, case=False, na=False))
            ]
            
            if df_spek_serupa.empty:
                st.warning("Tidak ditemukan produk dengan kombinasi spek serupa. Menggunakan rata-rata harga keseluruhan sebagai estimasi.")
                harga_awal = int(df['Harga'].mean())
            else:
                harga_awal = int(df_spek_serupa['Harga'].mean())
            
            input_data = pd.DataFrame({
                'Harga': [harga_awal],
                'Rating': [rating_target],
                'Terjual': [1] # Menggunakan nama kolom yang benar
            })

            input_scaled = scaler.transform(input_data)
            prediksi_cluster = model.predict(input_scaled)[0] + 1
            
            st.success(f"Analisis Selesai! Estimasi harga awal untuk spek ini adalah **Rp {harga_awal:,}**.")
            st.header(f"Prediksi Segmen Pasar: Cluster {prediksi_cluster}")

            df_kompetitor = df[df['Cluster'] == prediksi_cluster]

            if not df_kompetitor.empty:
                harga_avg = int(df_kompetitor['Harga'].mean())
                harga_min_comp = int(df_kompetitor['Harga'].min())
                harga_max_comp = int(df_kompetitor['Harga'].max())
                
                st.subheader(f"📈 Benchmarking Harga (Berdasarkan {len(df_kompetitor)} Kompetitor di Cluster {prediksi_cluster})")
                st.info(f"Untuk bersaing di segmen ini, kompetitor menjual produk di rentang **Rp {harga_min_comp:,}** hingga **Rp {harga_max_comp:,}**.")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Rata-rata Harga Kompetitor", f"Rp {harga_avg:,}")
                c2.metric("Harga Terendah", f"Rp {harga_min_comp:,}")
                c3.metric("Harga Tertinggi", f"Rp {harga_max_comp:,}")

                st.subheader("🏆 Kompetitor Utama di Segmen Ini")
                st.dataframe(df_kompetitor['Toko'].value_counts().nlargest(5))
            else:
                st.info("Tidak ditemukan kompetitor langsung di segmen ini. Ini bisa menjadi peluang!")