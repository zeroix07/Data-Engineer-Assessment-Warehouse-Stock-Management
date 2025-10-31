# 🧠 Proyek Asesmen Data Engineer: Warehouse Stock Management

> Implementasi *end-to-end* sistem **Data Warehouse** untuk manajemen stok gudang — bagian dari asesmen Data Engineer PT Informatika Media Pratama.  
> Mencakup desain database, generasi data skala besar, *stored procedure* SQL, *pipeline* ETL modular berbasis Python, serta pembuatan laporan analitik otomatis.

---

## 🚀 Fitur Utama

### 🗃️ 1. Desain Database (Task 1)
Skema **PostgreSQL** yang dinormalisasi untuk melacak:
- Stok barang per gudang  
- Pesanan penjualan & pembelian (SO/PO)  
- Pergerakan antar gudang (*stock movement*)

### ⚙️ 2. Generator Data (Task 2)
- Skrip Python menghasilkan **>1.8 juta baris data realistis**  
- Menggunakan aturan 80/20, pola musiman, dan variasi stok  
- Output: file `INSERT` SQL siap impor ke PostgreSQL

### 🧩 3. Logika Database (Task 3)
- Fungsi dan *trigger* **PL/pgSQL** untuk menjaga integritas data  
- Contoh:
  - `record_stock_movement()`  
  - `transfer_stock()`

### 🪄 4. Pipeline ETL Modular (Task 4)
Pipeline Python modular yang:
- **Extract**: ambil data dari PostgreSQL  
- **Transform**: bersihkan data dan hitung metrik bisnis seperti:
  - *Dead Stock*
  - *ABC Analysis*
  - *Peak Times*
  - *Stock Value*
- **Load**: hasil disimpan ke **Parquet** & tabel ringkasan di database

### 📊 5. Pelaporan Otomatis
- Membuat laporan otomatis dalam format **PDF** dan **HTML**  
- Termasuk visualisasi (chart) dan tabel analitik  

### 💬 6. Analisis Naratif (Enhancement)
- Menggunakan **OpenAI API** (`model.py`) untuk menulis *executive summary* dinamis dari hasil analitik

---

## 🛠️ Tech Stack

| Komponen | Teknologi |
|-----------|------------|
| **Database** | PostgreSQL (via Docker) |
| **Backend & Data Gen** | Python 3.12 |
| **ETL & DB** | SQLAlchemy, psycopg2 |
| **Data Processing** | Pandas, NumPy |
| **Data Generation** | Faker, PyYAML |
| **Reporting** | Jinja2, WeasyPrint, Matplotlib |
| **AI Integration** | OpenAI API, python-dotenv |
| **Containerization** | Docker |

---

## ⚙️ Setup & Instalasi

> Pastikan Anda telah menginstal **Docker** dan **Python 3.10+**

### 1️⃣ Clone Repositori
```bash
git clone [URL_REPO_ANDA]
cd warehouse-stock-management
```

### 2️⃣ Jalankan Database (Docker)
```bash
# Jalankan container PostgreSQL
docker run --name my_pg -e POSTGRES_PASSWORD=mysecretpassword -p 5432:5432 -d postgres

# Impor skema database (Task 1)
docker cp database/schema.sql my_pg:/schema.sql
docker exec -u postgres my_pg psql -f /schema.sql
```

### 3️⃣ Siapkan Lingkungan Python
```bash
python3 -m venv .venv
source .venv/bin/activate

# Instal dependensi
pip install -r requirements.txt
```

### 4️⃣ Tambahkan API Key (OpenAI)
Buat file `.env` di dalam folder `etl_pipeline/`:
```bash
# etl_pipeline/.env
OPENAI_API_KEY="sk-..."
```

---

## 🧱 Cara Menjalankan Pipeline

Langkah-langkah eksekusi proyek secara berurutan:

---

### 🧬 1. Generate & Load Data (Task 2)
```bash
cd data_generator

# (Opsional) ubah format output di config.yaml
nano config.yaml  # pastikan 'format: "sql"'

# Jalankan generator
python3 generate_data.py

# Impor hasil ke PostgreSQL
docker cp output/all_data.sql my_pg:/all_data.sql
docker exec -u postgres my_pg psql -f /all_data.sql

cd ..
```

---

### ⚙️ 2. Instal Fungsi & Trigger (Task 3)
```bash
# Fungsi PL/pgSQL
docker cp database_functions/functions.sql my_pg:/functions.sql
docker exec -u postgres my_pg psql -f /functions.sql

# Trigger PL/pgSQL
docker cp database_functions/triggers.sql my_pg:/triggers.sql
docker exec -u postgres my_pg psql -f /triggers.sql
```

---

### 🧠 3. Jalankan Pipeline ETL (Task 4)
```bash
cd etl_pipeline
python3 main.py
cd ..
```

---

## 📈 Output & Hasil

- 📂 **`/etl_pipeline/output/`**
  - `summary_stock.parquet`
  - `analytics_summary.pdf`
  - `analytics_summary.html`
- 🧾 **Laporan Otomatis**
  - Grafik dan tabel analisis stok
  - Narasi eksekutif berbasis AI

---

## 👨‍💻 Kontributor
| Nama | Peran |
|------|--------|
| Fadhel Muhammad Apriansyah | Analytics & AI Engineer |

---
