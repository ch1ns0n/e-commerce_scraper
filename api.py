import joblib
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel

# --- 1. Inisialisasi Aplikasi FastAPI ---
app = FastAPI(
    title="API Prediksi Cluster Produk",
    description="API ini menerima fitur produk dan mengembalikan prediksi segmen pasarnya.",
    version="1.0"
)

# --- 2. Muat Model dan Scaler saat Startup ---
# Model hanya dimuat sekali saat API pertama kali dijalankan
try:
    scaler = joblib.load('scaler.pkl')
    model = joblib.load('kmeans_model.pkl')
    print("Model dan scaler berhasil dimuat.")
except FileNotFoundError:
    scaler, model = None, None
    print("PERINGATAN: File model tidak ditemukan!")

# --- 3. Definisikan Struktur Data Input ---
# Pydantic akan otomatis memvalidasi data yang masuk
class ProductFeatures(BaseModel):
    Harga: int
    Rating: float
    Terjual: int # Gunakan underscore agar valid sebagai nama variabel

# --- 4. Buat "Endpoint" untuk Prediksi ---
@app.post("/predict_cluster")
def predict_cluster(features: ProductFeatures):
    """
    Menerima data produk dan mengembalikan prediksi clusternya.
    """
    if not model or not scaler:
        return {"error": "Model tidak tersedia. Harap latih model terlebih dahulu."}

    # Ubah input menjadi DataFrame yang bisa dibaca oleh scaler
    input_df = pd.DataFrame([{
        "Harga": features.Harga,
        "Rating": features.Rating,
        "Terjual": features.Terjual
    }])

    # Lakukan scaling dan prediksi
    input_scaled = scaler.transform(input_df)
    prediksi = model.predict(input_scaled)[0]
    cluster_hasil = int(prediksi + 1) # Ubah jadi 1-4

    # Kembalikan hasil dalam format JSON
    return {
        "input_features": features.dict(),
        "predicted_cluster": cluster_hasil
    }

# Endpoint sederhana untuk cek status
@app.get("/")
def read_root():
    return {"status": "API Prediksi Cluster sedang berjalan."}