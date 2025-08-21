# Langkah 1: Mulai dari "dapur" yang sudah ada Python-nya
FROM python:3.11-slim

# Langkah 2: Buat folder kerja di dalam "kotak bekal"
WORKDIR /app

# Langkah 3: Salin daftar lauk-pauk terlebih dahulu
COPY requirements.txt .

# Langkah 4: Masak/Instal semua lauk-pauk tersebut
RUN pip install --no-cache-dir -r requirements.txt

# Langkah 5: Salin semua kode aplikasi Anda ke dalam "kotak bekal"
COPY . .

# Langkah 6: Tentukan perintah default saat "kotak bekal" dijalankan
# Ini akan menjalankan menu interaktif Anda
CMD ["python", "scrape_db.py"]