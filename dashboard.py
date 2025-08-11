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

    df_display = df_selection.sort_values(by=["Terjual", "Rating"], ascending=[False, False])
    
    # BARU: Menggunakan kontainer agar metrik lebih rapi
    with st.container(border=True):
        total_produk = len(df_display)
        harga_rata2 = int(df_display["Harga"].mean()) if total_produk > 0 else 0
        terjual_rata2 = int(df_display["Terjual"].mean()) if total_produk > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Produk Ditemukan", f"{total_produk}")
        col2.metric("Rata-rata Harga", f"Rp {harga_rata2:,}")
        col3.metric("Rata-rata Penjualan", f"{int(terjual_rata2)}")

    if total_produk > 0:
        # BARU: Menggunakan st.tabs untuk merapikan konten
        tab1, tab2, tab3, tab4 = st.tabs(["📈 Visualisasi Utama", "🕵️‍♂️ Intip Kompetitor", "💎 Kalkulator Peluang", "📋 Data Mentah"])

        with tab1:
            st.header("Visualisasi Analisis Pasar")
            fig_scatter = px.scatter(
                df_display[df_display.get('Cluster', pd.Series([-1])).ne(-1)],
                x="Terjual", y="Harga", color="Cluster", hover_name="Nama Produk",
                title="Peta Segmen Pasar (Harga vs. Penjualan)"
            )
            df_top_toko = df_display['Toko'].value_counts().nlargest(10)
            fig_bar = px.bar(
                df_top_toko, orientation='h', title="Papan Peringkat Toko (Top 10)",
                labels={'value': 'Jumlah Produk', 'index': 'Toko'}
            )
            fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
            left_column, right_column = st.columns(2)
            left_column.plotly_chart(fig_scatter, use_container_width=True)
            right_column.plotly_chart(fig_bar, use_container_width=True)

        with tab2:
            st.header("🕵️‍♂️ Intip Kompetitor")
            list_toko_filtered = df_display['Toko'].unique()
            toko_terpilih = st.selectbox("Pilih Toko untuk dianalisis:", options=list_toko_filtered)
            if toko_terpilih:
                df_toko = df_display[df_display['Toko'] == toko_terpilih]
                st.subheader(f"Profil Toko: {toko_terpilih}")
                total_produk_toko = len(df_toko)
                harga_rata2_toko = int(df_toko["Harga"].mean()) if total_produk_toko > 0 else 0
                terjual_rata2_toko = int(df_toko["Terjual"].mean()) if total_produk_toko > 0 else 0
                c1, c2, c3 = st.columns(3)
                c1.metric("Jumlah Listing", f"{total_produk_toko}")
                c2.metric("Rata-rata Harga", f"Rp {harga_rata2_toko:,}")
                c3.metric("Rata-rata Penjualan", f"{int(terjual_rata2_toko)}")
                st.write("**Produk Terlaris dari Toko Ini:**")
                st.dataframe(df_toko[['Nama Produk', 'Harga', 'Rating', 'Terjual']].sort_values(by="Terjual", ascending=False).head(5))

        with tab3:
            st.header("💎 Kalkulator Peluang (Produk Paling 'Worth It')")
            df_score = df_display[(df_display['Harga'] > 0) & (df_display['Terjual'] > 0) & (df_display['Rating'] > 0)].copy()
            if not df_score.empty:
                scaler_norm = MinMaxScaler()
                df_score[['Harga_norm', 'Rating_norm', 'Terjual_norm']] = scaler_norm.fit_transform(df_score[['Harga', 'Rating', 'Terjual']])
                df_score['Skor Peluang'] = ((1 - df_score['Harga_norm']) + df_score['Rating_norm'] + df_score['Terjual_norm'])
                st.write("Top 10 produk dengan 'value' terbaik:")
                df_top_value = df_score.sort_values(by="Skor Peluang", ascending=False).head(10)
                st.dataframe(df_top_value[['Nama Produk', 'Harga', 'Rating', 'Terjual', 'Toko']])
            else:
                st.write("Tidak cukup data untuk menghitung skor peluang.")
        
        with tab4:
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