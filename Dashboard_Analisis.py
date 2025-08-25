import streamlit as st
import pandas as pd
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from sklearn.preprocessing import MinMaxScaler
from utils import load_data_for_dashboard
import plotly.express as px

# --- Konfigurasi Halaman Web ---
st.set_page_config(page_title="Dashboard Analisis", layout="wide")

df = load_data_for_dashboard()

# --- Tampilan Halaman ---
st.title("📊 Dashboard Analisis Pasar PC Gaming di Tokopedia")
st.write("Dashboard ini memvisualisasikan data produk hasil scraping untuk analisis kompetitor.")

# --- Sidebar untuk Filter ---
st.sidebar.header("Filter & Pencarian")
search_query = st.sidebar.text_input("Cari Nama Produk atau Toko:")

all_lokasi = sorted(df["Lokasi"].unique())
select_all_option = "(Pilih Semua)"
options = [select_all_option] + all_lokasi

lokasi_selection = st.sidebar.multiselect(
    "Pilih Lokasi Toko:",
    options=options,
    default=select_all_option
)

if select_all_option in lokasi_selection or not lokasi_selection:
    final_lokasi_filter = all_lokasi
else:
    final_lokasi_filter = lokasi_selection
    
harga_min, harga_max = st.sidebar.slider(
    "Rentang Harga (Rp):",
    min_value=int(df["Harga"].min()),
    max_value=int(df["Harga"].max()),
    value=(int(df["Harga"].min()), int(df["Harga"].max()))
)

# Terapkan filter awal
df_selection = df[
    df["Lokasi"].isin(final_lokasi_filter) &
    df["Harga"].between(harga_min, harga_max)
].copy()

# Terapkan filter pencarian
if search_query:
    words = [word for word in search_query.strip().split() if word]
    for word in words:
        word_mask = (df_selection['Nama Produk'].str.contains(word, case=False, na=False) |
                     df_selection['Toko'].str.contains(word, case=False, na=False))
        df_selection = df_selection[word_mask]

# DIUBAH: Menggunakan nama kolom yang benar "Terjual"
df_display = df_selection.sort_values(by=["Terjual", "Rating"], ascending=[False, False])

# --- Tampilan Utama ---
with st.container(border=True):
    total_produk = len(df_display)
    harga_rata2 = int(df_display["Harga"].mean()) if total_produk > 0 else 0
    # DIUBAH: Menggunakan nama kolom yang benar "Terjual"
    terjual_rata2 = int(df_display["Terjual"].mean()) if total_produk > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Produk Ditemukan", f"{total_produk}")
    col2.metric("Rata-rata Harga", f"Rp {harga_rata2:,}")
    col3.metric("Rata-rata Penjualan", f"{int(terjual_rata2)}")

if total_produk > 0:
    # DIUBAH: Struktur Tab yang lebih rapi
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Peta & Peringkat", "🔬 Analisis Segmen", "🕵️‍♂️ Intip Kompetitor", "💎 Kalkulator Peluang", "📋 Data Mentah"])

    with tab1:
        st.header("Visualisasi Utama Pasar")
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
        st.header("Analisis Mendalam per Segmen Pasar")
        st.subheader("Perbandingan Distribusi Harga per Segmen")
        fig_box = px.box(
            df_display[df_display['Cluster'] > 0], x="Cluster", y="Harga", color="Cluster",
            points="all", notched=True, title="Distribusi Harga di Setiap Cluster"
        )
        st.plotly_chart(fig_box, use_container_width=True)
        
        st.subheader("Struktur Pasar Berdasarkan Total Penjualan Toko")
        df_treemap = df_display[df_display['Cluster'] > 0].groupby(['Cluster', 'Toko'])['Terjual'].sum().reset_index()
        if not df_treemap.empty:
            fig_treemap = px.treemap(
                df_treemap, path=[px.Constant("Semua Pasar"), 'Cluster', 'Toko'],
                values='Terjual', title="Peta Pangsa Pasar per Segmen"
            )
            st.plotly_chart(fig_treemap, use_container_width=True)

    with tab3:
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

    with tab4:
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
    
    with tab5:
        st.subheader("Data Produk (Diurutkan berdasarkan Penjualan & Rating)")
        st.dataframe(df_display)
else:
    st.warning("Tidak ada data yang cocok dengan filter yang Anda pilih.")