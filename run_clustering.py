import pandas as pd
import joblib
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

def connect_to_mongodb():
    """Membuat koneksi ke database MongoDB Atlas."""
    uri = "mongodb+srv://samuelchinson:test123@cluster0.bxaivdh.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    client = MongoClient(uri, server_api=ServerApi('1'))
    try:
        client.admin.command('ping')
        print("✅ Berhasil terhubung ke MongoDB!")
        db = client['tokopedia_db']
        return db, client
    except Exception as e:
        print(f"❌ Gagal terhubung ke MongoDB: {e}")
        return None, None

def main():
    """Fungsi utama untuk melatih model dan memperbarui cluster di database."""
    db, client = connect_to_mongodb()
    
    if db is None:
        return

    collection = db['products']
    print("Memuat data dari MongoDB...")
    df = pd.DataFrame(list(collection.find({})))
    
    if df.empty:
        print("Tidak ada data di database untuk di-cluster.")
        if client: client.close()
        return

    features = ['Harga', 'Rating', 'Terjual']
    df_clean = df.dropna(subset=features).copy()
    df_clean = df_clean[(df_clean['Harga'] > 100000) & (df_clean['Terjual'] > 0)]

    if len(df_clean) < 10:
        print("Tidak cukup data untuk clustering.")
        if client: client.close()
        return

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df_clean[features])

    K_OPTIMAL = 5 # Menggunakan k=4 yang lebih stabil
    print(f"Menjalankan K-Means dengan k={K_OPTIMAL}...")
    kmeans = KMeans(n_clusters=K_OPTIMAL, random_state=42, n_init='auto')
    
    cluster_labels = kmeans.fit_predict(X_scaled)
    
    # Simpan model dan scaler ke file
    joblib.dump(scaler, 'scaler.pkl')
    joblib.dump(kmeans, 'kmeans_model.pkl')
    print("✅ Scaler dan Model K-Means telah disimpan ke file.")
    
    # Tambahkan 1 ke setiap label agar menjadi 1, 2, 3, 4
    df_clean['Cluster'] = cluster_labels + 1
    
    print("Menyimpan label cluster (1-5) ke MongoDB...")
    update_count = 0
    for index, row in df_clean.iterrows():
        collection.update_one(
            {'_id': row['_id']},
            {'$set': {'Cluster': int(row['Cluster'])}}
        )
        update_count += 1
    
    print(f"✅ Selesai! {update_count} produk telah diberi label cluster.")
    
    if client:
        client.close()

if __name__ == "__main__":
    main()