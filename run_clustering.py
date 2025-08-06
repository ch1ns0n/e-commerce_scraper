import pandas as pd
import joblib
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

def connect_to_mongodb():
    """Membuat koneksi ke database MongoDB Atlas menggunakan environment variable."""
    # DIUBAH: Ambil URI dari environment variable 'MONGO_URI'
    uri = os.environ.get("MONGO_URI")
    
    if not uri:
        print("❌ Gagal menemukan MONGO_URI. Pastikan secret sudah diatur di GitHub Actions.")
        # Anda bisa menambahkan URI lokal di sini untuk testing di komputer Anda
        uri = "mongodb+srv://samuelchinson:test123@cluster0.bxaivdh.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0" 
        return None
    
    client = MongoClient(uri, server_api=ServerApi('1'))
    try:
        client.admin.command('ping')
        print("✅ Berhasil terhubung ke MongoDB!")
        db = client['tokopedia_db']
        # Kembalikan client dan db
        return db, client
    except Exception as e:
        print(f"❌ Gagal terhubung ke MongoDB: {e}")
        return None, None

def main():
    db = connect_to_mongodb()
    if db is None:
        return

    collection = db['products']
    print("Memuat data dari MongoDB...")
    df = pd.DataFrame(list(collection.find({})))

    if df.empty:
        print("Tidak ada data di database untuk di-cluster.")
        return

    features = ['Harga', 'Rating', 'Terjual']
    df_clean = df.dropna(subset=features).copy()
    df_clean = df_clean[(df_clean['Harga'] > 100000) & (df_clean['Terjual'] > 0)]

    if len(df_clean) < 10:
        print("Tidak cukup data untuk clustering.")
        return

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df_clean[features])

    K_OPTIMAL = 5
    print(f"Menjalankan K-Means dengan k={K_OPTIMAL}...")
    kmeans = KMeans(n_clusters=K_OPTIMAL, random_state=42, n_init='auto')
    
    # Menjalankan clustering dan mendapatkan label (hasilnya 0, 1, 2, 3, 4)
    cluster_labels = kmeans.fit_predict(X_scaled)
    
    joblib.dump(scaler, 'scaler.pkl')
    joblib.dump(kmeans, 'kmeans_model.pkl')
    print("✅ Scaler dan Model K-Means telah disimpan ke file.")
    
    # --- DIUBAH: Tambahkan 1 ke setiap label agar menjadi 1, 2, 3, 4, 5 ---
    df_clean['Cluster'] = cluster_labels + 1
    # --------------------------------------------------------------------

    print("Menyimpan label cluster (1-5) ke MongoDB...")
    update_count = 0
    for index, row in df_clean.iterrows():
        collection.update_one(
            {'_id': row['_id']},
            {'$set': {'Cluster': int(row['Cluster'])}}
        )
        update_count += 1
    
    print(f"✅ Selesai! {update_count} produk telah diberi label cluster.")

if __name__ == "__main__":
    main()