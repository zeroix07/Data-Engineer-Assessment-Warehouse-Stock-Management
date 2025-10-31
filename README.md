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
git clone https://github.com/zeroix07/Data-Engineer-Assessment-Warehouse-Stock-Management.git
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
---

## 💡 Tantangan & Solusi

Selama pengerjaan proyek, beberapa tantangan teknis spesifik muncul:

1.  **Konflik Data vs. Skema (Task 2)**
    * **Tantangan:** Persyaratan untuk meng-inject 5% data berkualitas buruk (seperti `product_id = NULL`) bertentangan langsung dengan *constraint* `NOT NULL` pada skema database (Task 1).
    * **Solusi:** Jenis *Data Quality issue* diubah dari `missing_id` menjadi `bad_reference_id`. Alih-alih `NULL`, skrip meng-inject `reference_id` yang tidak valid (misal `9999999`). Ini tetap menjadi DQ issue yang valid untuk dideteksi oleh ETL (Task 4) tanpa menyebabkan kegagalan saat proses *load* data.

2.  **Render PDF yang Rusak (Task 4)**
    * **Tantangan:** Laporan PDF awal yang di-generate oleh `WeasyPrint` rusak total: *layout* 2 kolom gagal, *chart* tidak muncul, dan tabel di-render sebagai teks mentah.
    * **Solusi:**
        1.  **Layout:** *Template* HTML dirombak total, membuang CSS `grid` yang tidak kompatibel dan beralih ke *layout* **satu kolom** yang sederhana dan 100% *PDF-friendly*.
        2.  **Charts:** Jalur (path) ke file gambar diubah dari absolut (`/Users/pac/...`) menjadi **relatif** (`charts/chart.png`), yang memungkinkan `WeasyPrint` menemukannya.
        3.  **Tabel:** *Template* Jinja2 dipastikan menggunakan *filter* `|safe` pada variabel tabel (`{{ peak_dow | safe }}`) agar HTML-nya di-render dengan benar.

3.  **Error Timezone (Task 4)**
    * **Tantangan:** Pipeline ETL gagal saat mencoba mengurangi *timestamp* *timezone-aware* (dari PostgreSQL `TIMESTAMPTZ`) dengan *timestamp* *timezone-naive* (dari `pd.to_datetime('now')`).
    * **Solusi:** Menstandardisasi *timestamp* di Python agar *aware* dengan UTC menggunakan `pd.to_datetime('now', utc=True)`.

---

## 🧠 Pertimbangan Performa

1.  **Indeks Database:** Tabel `stock_movements` adalah tabel terbesar. Indeks telah ditambahkan pada *foreign key* (`product_id`, `warehouse_id`) dan `movement_date` untuk mempercepat *join* dan *filter* pada pipeline ETL.
2.  **Bulk Load Data:** Untuk mengimpor 1.8 juta baris data (Task 2), skrip generator membungkus semua *statement* `INSERT` dalam satu transaksi (`BEGIN`/`COMMIT`). Skrip ini juga menonaktifkan *trigger* sementara (`SET session_replication_role = 'replica'`) untuk mempercepat proses *load* secara drastis.
3.  **Incremental Load ETL:** Pipeline ETL (Task 4) mendukung mode `--load_type incremental`, yang hanya akan memproses data dari `stock_movements` yang lebih baru dari `last_run_timestamp`. Ini jauh lebih efisien daripada melakukan *full load* setiap hari.
4.  **Format Analitik:** Hasil ETL disimpan dalam format **Parquet**. Ini adalah format *columnar* terkompresi yang jauh lebih cepat untuk kueri analitik daripada CSV atau Excel.

---

## 🔮 Peningkatan di Masa Depan

Meskipun fungsional, proyek ini dapat dikembangkan lebih lanjut:

1.  **Orkestrasi Pipeline:** Menggunakan **Apache Airflow** atau **Dagster** untuk menjadwalkan dan meng-orkestrasi pipeline (Task 2 -> Task 3 -> Task 4) secara otomatis, lengkap dengan *retries* dan *alerting*.
2.  **Pemisahan OLTP & OLAP:** Memisahkan database transaksional (PostgreSQL) dari *data warehouse* analitik. Pipeline ETL seharusnya memuat data ke *warehouse* khusus seperti **ClickHouse**, **BigQuery**, atau **Snowflake** untuk performa kueri analitik yang lebih cepat.
3.  **Dashboarding Interaktif:** Mengganti laporan PDF/HTML statis dengan *dashboard* interaktif menggunakan **Metabase**, **Superset**, atau **Tableau** yang terhubung langsung ke tabel analitik.
4.  **Transformasi berbasis SQL:** Memindahkan logika transformasi Python/Pandas ke **dbt (data build tool)**. Ini akan membuat transformasi (seperti ABC Analysis) lebih mudah diuji, didokumentasikan, dan dipelihara langsung di dalam *warehouse*.

---

## 👨‍💻 Kontributor
| Nama | Peran |
|------|--------|
| Fadhel Muhammad Apriansyah | Analytics & AI Engineer |

---
