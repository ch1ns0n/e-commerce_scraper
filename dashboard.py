import streamlit as st
import pandas as pd
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import plotly.express as px
import joblib
import numpy as np

# --- Konfigurasi Halaman Web ---
st.set_page_config(page_title="Dashboard Intelijen Pasar", layout="wide")

# --- Koneksi dan Pemuatan Data & Model ---
@st.cache_data
def load_data():
    """Menghubungkan ke MongoDB dan memuat data produk."""
    uri = "mongodb+srv://samuelchinson:test123@cluster0.bxaivdh.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    client = MongoClient(uri, server_api=ServerApi('1'))
    db = client['tokopedia_db']
    collection = db['products']
    df = pd.DataFrame(list(collection.find({})))
    if '_id' in df.columns:
        df = df.drop(columns=['_id'])
    if 'Cluster' in df.columns:
        df['Cluster'] = df['Cluster'].fillna(-1).astype(int)
    # Ganti nama kolom agar konsisten
    if 'Terjual' in df.columns:
        df.rename(columns={'Terjual': 'Terjual'}, inplace=True)
    return df

@st.cache_resource
def load_models():
    """Memuat model scaler dan k-means dari file."""
    try:
        scaler = joblib.load('scaler.pkl')
        model = joblib.load('kmeans_model.pkl')
        return scaler, model
    except FileNotFoundError:
        return None, None

df = load_data()
scaler, model = load_models()

# --- Navigasi Sidebar ---
st.sidebar.title("Navigasi")
page = st.sidebar.radio("Pilih Halaman:", ["📈 Dashboard Analisis", "🎮 Simulasi Produk Baru"])

# ==============================================================================
# --- HALAMAN 1: DASHBOARD ANALISIS ---
# ==============================================================================
if page == "📈 Dashboard Analisis":
    st.title("📊 Dashboard Analisis Pasar PC Gaming di Tokopedia")
    st.write("Dashboard ini memvisualisasikan data produk hasil scraping untuk analisis kompetitor.")
    
    st.sidebar.header("Filter & Pencarian")
    search_query = st.sidebar.text_input("Cari Nama Produk atau Toko:")
    
    all_lokasi = sorted(df["Lokasi"].unique())
    select_all_option = "(Pilih Semua)"
    options = [select_all_option] + all_lokasi
    
    lokasi_selection = st.sidebar.multiselect("Pilih Lokasi Toko:", options=options, default=select_all_option)

    if select_all_option in lokasi_selection or not lokasi_selection:
        final_lokasi_filter = all_lokasi
    else:
        final_lokasi_filter = lokasi_selection
        
    harga_min, harga_max = st.sidebar.slider(
        "Rentang Harga (Rp):",
        min_value=int(df["Harga"].min()), max_value=int(df["Harga"].max()),
        value=(int(df["Harga"].min()), int(df["Harga"].max()))
    )

    df_selection = df[df["Lokasi"].isin(final_lokasi_filter) & df["Harga"].between(harga_min, harga_max)].copy()

    if search_query:
        words = [word for word in search_query.strip().split() if word]
        for word in words:
            word_mask = (df_selection['Nama Produk'].str.contains(word, case=False, na=False) | df_selection['Toko'].str.contains(word, case=False, na=False))
            df_selection = df_selection[word_mask]

    # Menggunakan nama kolom yang benar: "Terjual"
    df_display = df_selection.sort_values(by=["Terjual", "Rating"], ascending=[False, False])
    
    total_produk = len(df_display)
    harga_rata2 = int(df_display["Harga"].mean()) if total_produk > 0 else 0
    terjual_rata2 = int(df_display["Terjual"].mean()) if total_produk > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Produk Ditemukan", f"{total_produk}")
    col2.metric("Rata-rata Harga", f"Rp {harga_rata2:,}")
    col3.metric("Rata-rata Penjualan", f"{int(terjual_rata2)}")
    st.markdown("---")

    if total_produk > 0:
        st.header("Visualisasi Analisis Pasar")

        # 1. Definisikan kedua grafik terlebih dahulu
        fig_scatter = px.scatter(
            df_display[df_display.get('Cluster', pd.Series([-1])).ne(-1)],
            x="Terjual",
            y="Harga",
            color="Cluster",
            color_continuous_scale=px.colors.sequential.Viridis,
            hover_name="Nama Produk",
            title="Peta Segmen Pasar (Harga vs. Penjualan)"
        )
        fig_scatter.update_layout(plot_bgcolor="rgba(0,0,0,0)")

        df_top_toko = df_display['Toko'].value_counts().nlargest(10)
        fig_bar = px.bar(
            df_top_toko,
            orientation='h',
            title="Papan Peringkat Toko (Top 10)",
            labels={'value': 'Jumlah Produk', 'index': 'Toko'}
        )
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})

        # 2. Buat layout 2 kolom dan tampilkan grafiknya
        left_column, right_column = st.columns(2)
        left_column.plotly_chart(fig_scatter, use_container_width=True)
        right_column.plotly_chart(fig_bar, use_container_width=True)

        st.subheader("Data Produk (Diurutkan berdasarkan Penjualan & Rating)")
        st.dataframe(df_display)
    else:
        st.warning("Tidak ada data yang cocok dengan filter yang Anda pilih.")

# ==============================================================================
# --- HALAMAN 2: SIMULASI PRODUK BARU ---
# ==============================================================================
elif page == "🎮 Simulasi Produk Baru":
    st.title("🚀 Asisten Peluncuran Produk")
    st.write("Masukkan spesifikasi komponen PC yang Anda rencanakan untuk dijual untuk mendapatkan analisis pasar.")

    if scaler is None or model is None:
        st.error("Model tidak ditemukan! Harap jalankan `run_clustering.py` terlebih dahulu untuk membuat file `scaler.pkl` dan `kmeans_model.pkl`.")
    else:
        with st.form("simulasi_form"):
            st.subheader("Masukkan Spesifikasi Produk Baru Anda")
            
            # Input dari pengguna
            rating_target = st.slider("Target Rating Produk Anda:", 1.0, 5.0, 4.8, 0.1)
            
            # Estimasi harga berdasarkan komponen
            st.markdown("Pilih komponen utama untuk estimasi harga:")
            col1, col2 = st.columns(2)
            with col1:
                pilihan_cpu = st.selectbox("Prosesor (CPU):", ('Intel i3', 'Intel i5', 'Intel i7', 'Intel i9', 'AMD Ryzen 3', 'AMD Ryzen 5', 'AMD Ryzen 7', 'AMD Ryzen 9'))
            with col2:
                pilihan_gpu = st.selectbox("Kartu Grafis (GPU):", ('RTX 3050', 'RTX 3060', 'RTX 3070', 'RTX 3080', 'RTX 3090', 'RTX 4050', 'RTX 4060', 'RTX 4070', 'RTX 4080', 'RTX 4090', 'RTX 5060', 'RTX 5070','RTX 5080', 'RX 6500', 'RX 6700 XT', 'RX 6800 XT', 'RX 6900 XT', 'RX 9060'))

            submitted = st.form_submit_button("Jalankan Simulasi")

            if submitted:
                # 1. Estimasi harga awal berdasarkan produk serupa di database
                df_spek_serupa = df[
                    (df['Nama Produk'].str.contains(pilihan_cpu, case=False)) & 
                    (df['Nama Produk'].str.contains(pilihan_gpu, case=False))
                ]
                
                if df_spek_serupa.empty:
                    st.warning("Tidak ditemukan produk dengan kombinasi spek serupa. Menggunakan rata-rata harga keseluruhan sebagai estimasi.")
                    harga_awal = int(df['Harga'].mean())
                else:
                    harga_awal = int(df_spek_serupa['Harga'].mean())
                
                # 2. Siapkan data input untuk model clustering
                input_data = pd.DataFrame({
                    'Harga': [harga_awal],
                    'Rating': [rating_target],
                    'Terjual': [1] # Asumsi awal untuk produk baru
                })

                # 3. Lakukan scaling & Prediksi cluster
                input_scaled = scaler.transform(input_data)
                prediksi_cluster = model.predict(input_scaled)[0] + 1
                
                st.success(f"Analisis Selesai! Estimasi harga awal untuk spek ini adalah **Rp {harga_awal:,}**.")
                st.header(f"Prediksi Segmen Pasar: Cluster {prediksi_cluster}")

                # 4. Analisis kompetitor di cluster tersebut
                df_kompetitor = df[df['Cluster'] == prediksi_cluster]

                if not df_kompetitor.empty:
                    harga_avg = int(df_kompetitor['Harga'].mean())
                    harga_min_comp = int(df_kompetitor['Harga'].min())
                    harga_max_comp = int(df_kompetitor['Harga'].max())
                    
                    st.subheader(f"📈 Benchmarking Harga (Berdasarkan {len(df_kompetitor)} Kompetitor di Cluster {prediksi_cluster})")
                    st.info(f"Untuk bersaing di segmen ini, kompetitor menjual produk di rentang **Rp {harga_min_comp:,}** hingga **Rp {harga_max_comp:,}**.")
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Harga Rata-rata Kompetitor", f"Rp {harga_avg:,}")
                    c2.metric("Harga Terendah", f"Rp {harga_min_comp:,}")
                    c3.metric("Harga Tertinggi", f"Rp {harga_max_comp:,}")

                    st.subheader("🏆 Kompetitor Utama di Segmen Ini")
                    st.dataframe(df_kompetitor['Toko'].value_counts().nlargest(5))
                else:
                    st.info("Tidak ditemukan kompetitor langsung di segmen ini. Ini bisa menjadi peluang!")