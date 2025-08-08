import streamlit as st
import pandas as pd
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from sklearn.preprocessing import MinMaxScaler
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
    # DIUBAH: Mengganti nama kolom 'Terjual' menjadi 'Terjual' agar konsisten
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

    # DIUBAH: Menggunakan nama kolom yang benar "Terjual"
    df_display = df_selection.sort_values(by=["Terjual", "Rating"], ascending=[False, False])
    
    total_produk = len(df_display)
    harga_rata2 = int(df_display["Harga"].mean()) if total_produk > 0 else 0
    terjual_rata2 = int(df_display["Terjual"].mean()) if total_produk > 0 else 0 # DIUBAH

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Produk Ditemukan", f"{total_produk}")
    col2.metric("Rata-rata Harga", f"Rp {harga_rata2:,}")
    col3.metric("Rata-rata Penjualan", f"{int(terjual_rata2)}")
    st.markdown("---")

    if total_produk > 0:
        st.header("Visualisasi Analisis Pasar")

        fig_scatter = px.scatter(
            df_display[df_display.get('Cluster', pd.Series([-1])).ne(-1)],
            x="Terjual", # DIUBAH
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

        left_column, right_column = st.columns(2)
        left_column.plotly_chart(fig_scatter, use_container_width=True)
        right_column.plotly_chart(fig_bar, use_container_width=True)

        st.subheader("Data Produk (Diurutkan berdasarkan Penjualan & Rating)")
        st.dataframe(df_display)
        
        # --- FITUR INTIP KOMPETITOR ---
        st.markdown("---")
        st.header("🕵️‍♂️ Intip Kompetitor")

        # --- FITUR KALKULATOR PELUANG ---
        st.markdown("---")
        st.header("💎 Kalkulator Peluang (Produk Paling 'Worth It')")

        # 1. Siapkan data untuk scoring dari data yang sudah difilter
        df_score = df_display[(df_display['Harga'] > 0) & (df_display['Terjual'] > 0) & (df_display['Rating'] > 0)].copy()

        if not df_score.empty:
            # 2. Normalisasi data (ubah skala 0-1)
            scaler = MinMaxScaler()
            df_score[['Harga_norm', 'Rating_norm', 'Terjual_norm']] = scaler.fit_transform(
                df_score[['Harga', 'Rating', 'Terjual']]
            )

            # 3. Buat Skor Peluang
            # Kita ingin harga rendah (1 - Harga_norm), dan rating/penjualan tinggi
            df_score['Skor Peluang'] = ( (1 - df_score['Harga_norm']) + df_score['Rating_norm'] + df_score['Terjual_norm'] )
    
            # 4. Tampilkan 10 produk dengan skor tertinggi
            st.write("Top 10 produk dengan 'value' terbaik berdasarkan harga, rating, dan penjualan:")
            df_top_value = df_score.sort_values(by="Skor Peluang", ascending=False).head(10)
            st.dataframe(df_top_value[['Nama Produk', 'Harga', 'Rating', 'Terjual', 'Toko']])
        else:
            st.write("Tidak cukup data (produk dengan harga, rating, dan penjualan > 0) untuk menghitung skor peluang.")

        # 1. Buat dropdown untuk memilih toko
        # Filter dulu toko yang ada di hasil seleksi saat ini
        list_toko_filtered = df_display['Toko'].unique()
        toko_terpilih = st.selectbox("Pilih Toko untuk dianalisis:", options=list_toko_filtered)

        if toko_terpilih:
            # 2. Filter data untuk toko yang dipilih saja
            df_toko = df_display[df_display['Toko'] == toko_terpilih]
    
            st.subheader(f"Profil Toko: {toko_terpilih}")
    
            # 3. Tampilkan metrik utama toko tersebut
            total_produk_toko = len(df_toko)
            harga_rata2_toko = int(df_toko["Harga"].mean()) if total_produk_toko > 0 else 0
            terjual_rata2_toko = int(df_toko["Terjual"].mean()) if total_produk_toko > 0 else 0

            col1, col2, col3 = st.columns(3)
            col1.metric("Jumlah Listing Produk", f"{total_produk_toko}")
            col2.metric("Rata-rata Harga Jual", f"Rp {harga_rata2_toko:,}")
            col3.metric("Rata-rata Penjualan per Produk", f"{int(terjual_rata2_toko)}")
    
            # 4. Tampilkan produk terlaris dari toko tersebut
            st.write("**Produk Terlaris dari Toko Ini:**")
            st.dataframe(
                df_toko[['Nama Produk', 'Harga', 'Rating', 'Terjual']].sort_values(
                    by="Terjual", ascending=False
                    ).head(5)
                )
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
            
            rating_target = st.slider("Target Rating Produk Anda:", 1.0, 5.0, 4.8, 0.1)
            
            st.markdown("Pilih komponen utama untuk estimasi harga:")
            col1, col2 = st.columns(2)
            with col1:
                # DIUBAH: Menghapus spasi ekstra dari opsi
                pilihan_cpu = st.selectbox("Prosesor (CPU):", ('i3', 'i5', 'i7', 'i9', 'Ryzen 3', 'Ryzen 5', 'Ryzen 7', 'Ryzen 9'))
            with col2:
                pilihan_gpu = st.selectbox("Kartu Grafis (GPU):", ('RTX 3050', 'RTX 3060', 'RTX 3070', 'RTX 3080', 'RTX 3090', 'RTX 4050', 'RTX 4060', 'RTX 4070', 'RTX 4080', 'RTX 4090', 'RX 6500', 'RX 6700 XT', 'RX 6800 XT', 'RX 6900 XT'))

            submitted = st.form_submit_button("Jalankan Simulasi")

            if submitted:
                df_spek_serupa = df[
                    (df['Nama Produk'].str.contains(pilihan_cpu.replace('Intel ', '').replace('AMD ', ''), case=False)) & 
                    (df['Nama Produk'].str.contains(pilihan_gpu, case=False))
                ]
                
                if df_spek_serupa.empty:
                    st.warning("Tidak ditemukan produk dengan kombinasi spek serupa. Menggunakan rata-rata harga keseluruhan sebagai estimasi.")
                    harga_awal = int(df['Harga'].mean())
                else:
                    harga_awal = int(df_spek_serupa['Harga'].mean())
                
                input_data = pd.DataFrame({
                    'Harga': [harga_awal],
                    'Rating': [rating_target],
                    'Terjual': [1] # DIUBAH
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