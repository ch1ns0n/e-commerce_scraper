import streamlit as st
import pandas as pd
import joblib
import numpy as np

# --- 1. FUNGSI UNTUK MEMUAT ASET MODEL ---
@st.cache_resource
def load_prediction_assets():
    """Memuat model prediksi dan preprocessor yang sudah dilatih."""
    try:
        model = joblib.load('price_model.pkl')
        preprocessor = joblib.load('preprocessor.pkl')
        return model, preprocessor
    except FileNotFoundError:
        return None, None

# --- 2. MUAT MODEL & PREPROCESSOR ---
model, preprocessor = load_prediction_assets()

# --- TAMPILAN HALAMAN APLIKASI ---
st.set_page_config(page_title="Prediksi Harga PC", layout="centered")
st.title("🤖 Asisten Prediksi Harga PC Gaming")
st.write("Masukkan spesifikasi komponen PC untuk mendapatkan estimasi harga pasar yang wajar berdasarkan model Machine Learning.")

# Tampilkan pesan error jika model tidak ditemukan
if model is None or preprocessor is None:
    st.error(
        "File model 'price_model.pkl' atau 'preprocessor.pkl' tidak ditemukan. "
        "Pastikan Anda sudah menjalankan notebook pelatihan dan menempatkan file-file tersebut di folder yang benar."
    )
else:
    # --- 3. BUAT FORM INPUT DARI PENGGUNA ---
    with st.form("prediction_form"):
        st.subheader("Masukkan Spesifikasi PC Anda")

        # --- PERBAIKAN AttributeError DI SINI ---
        # Mengakses langkah 'onehot' di dalam pipeline untuk mendapatkan kategori
        ohe = preprocessor.named_transformers_['cat'].named_steps['onehot']
        cpu_options = list(ohe.categories_[0])
        gpu_options = list(ohe.categories_[1])
        storage_options = list(ohe.categories_[2])
        
        col1, col2 = st.columns(2)
        with col1:
            cpu_model = st.selectbox("Pilih Model CPU:", options=cpu_options)
            ram_size = st.number_input("Ukuran RAM (GB):", min_value=4, max_value=128, value=16, step=4)
            rating = st.slider("Target Rating Produk Anda:", 1.0, 5.0, 4.8, 0.1)
        
        with col2:
            gpu_model = st.selectbox("Pilih Model GPU:", options=gpu_options)
            storage = st.selectbox("Pilih Storage:", options=storage_options)
            terjual = st.number_input("Estimasi Penjualan per Bulan:", min_value=0, max_value=1000, value=10)
        
        # --- PERBAIKAN Missing Submit Button DI SINI ---
        submitted = st.form_submit_button("Prediksi Harga")

        # --- 4. PROSES PREDIKSI SETELAH TOMBOL DITEKAN ---
        if submitted:
            # Buat DataFrame dari input pengguna
            input_data = pd.DataFrame({
                'CPU_Model': [cpu_model],
                'GPU_Model': [gpu_model],
                'Storage': [storage],
                'RAM_Size': [ram_size],
                'Rating': [rating],
                'Terjual': [terjual]
            })

            # Lakukan transformasi pada data input menggunakan preprocessor
            input_processed = preprocessor.transform(input_data)
            
            # Lakukan prediksi menggunakan model
            predicted_price = model.predict(input_processed)
            
            # Ambil nilai prediksi pertama
            price = int(predicted_price[0])

            # Tentukan rentang harga wajar berdasarkan RMSE (sekitar 7.5 juta)
            price_error_margin = 7500000 
            lower_bound = int(price - price_error_margin)
            upper_bound = int(price + price_error_margin)

            # --- 5. TAMPILKAN HASIL PREDIKSI ---
            st.success("Analisis selesai!")
            st.header(f"Estimasi Harga Pasar: Rp {price:,}")
            
            st.info(
                f"Berdasarkan model, rentang harga kompetitif untuk spesifikasi ini adalah antara **Rp {lower_bound:,}** dan **Rp {upper_bound:,}**."
            )
            st.write("Rekomendasi ini dibuat berdasarkan perbandingan dengan ribuan produk serupa di pasar.")