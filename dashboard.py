import streamlit as st
import pandas as pd
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import plotly.express as px

# --- Konfigurasi Halaman Web ---
st.set_page_config(page_title="Dashboard Intelijen Pasar", layout="wide")
st.title("📊 Dashboard Analisis Pasar PC Gaming di Tokopedia")
st.write("Dashboard ini memvisualisasikan data produk hasil scraping untuk analisis kompetitor.")

# --- Koneksi dan Pemuatan Data ---
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

df = load_data()

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

# --- DIUBAH: LOGIKA PENCARIAN YANG LEBIH CANGGIH ---
if search_query:
    # 1. Pecah kata kunci menjadi beberapa kata
    words = [word for word in search_query.strip().split() if word]
    
    # 2. Loop setiap kata dan filter DataFrame secara bertahap
    for word in words:
        # Buat filter untuk satu kata (cari di Nama Produk ATAU Toko)
        word_mask = (
            df_selection['Nama Produk'].str.contains(word, case=False, na=False) |
            df_selection['Toko'].str.contains(word, case=False, na=False)
        )
        # Terapkan filter (semua kata harus ada - logika AND)
        df_selection = df_selection[word_mask]
# --- AKHIR DARI PERUBAHAN ---

df_display = df_selection.sort_values(by=["Terjual", "Rating"], ascending=[False, False])

# --- Tampilan Utama ---
total_produk = len(df_display)
harga_rata2 = int(df_display["Harga"].mean()) if total_produk > 0 else 0
terjual_rata2 = int(df_display["Terjual"].mean()) if total_produk > 0 else 0

col1, col2, col3 = st.columns(3)
col1.metric("Total Produk Ditemukan", f"{total_produk}")
col2.metric("Rata-rata Harga", f"Rp {harga_rata2:,}")
col3.metric("Rata-rata Penjualan", f"{int(terjual_rata2)}")

st.markdown("---")

# --- Visualisasi Data ---
if total_produk > 0:
    st.header("Visualisasi Analisis Pasar")

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

    left_column, right_column = st.columns(2)
    left_column.plotly_chart(fig_scatter, use_container_width=True)
    right_column.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("Data Produk (Diurutkan berdasarkan Penjualan & Rating)")
    st.dataframe(df_display)
else:
    st.warning("Tidak ada data yang cocok dengan filter yang Anda pilih.")