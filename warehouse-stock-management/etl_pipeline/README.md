# ETL Pipeline untuk Analytics (Task 4)

Direktori ini berisi pipeline ETL Python modular untuk memproses data warehouse dan menghasilkan analitik.

## Fitur

* [cite_start]**Modular**: Logika dipisahkan ke dalam folder `extract`, `transform`, dan `load`[cite: 179].
* [cite_start]**Configurable**: Koneksi database, parameter ETL, dan output diatur melalui `config/config.yaml`[cite: 180].
* [cite_start]**Logging**: Logging terperinci diimplementasikan di seluruh pipeline [cite: 181] dan dikonfigurasi melalui `config/logging.conf`.
* [cite_start]**Data Quality**: Memiliki langkah untuk menangani dan memfilter data berkualitas buruk (DQ) yang di-generate di Task 2[cite: 147].
* [cite_start]**Incremental Load**: Mendukung *full load* dan *incremental load* (berdasarkan `movement_date`) melalui argumen CLI[cite: 146].
* [cite_start]**Analytics**: Menghitung metrik inventori (dead stock) [cite: 153][cite_start], pergerakan (peak times) [cite: 157][cite_start], dan finansial (ABC analysis)[cite: 175].
* **Outputs**:
    * [cite_start]Menyimpan laporan analitik mendalam ke format **Parquet** (atau CSV/Excel).
    * [cite_start]Membuat tabel summary di database (`analytics_daily_summary`).
    * [cite_start]Menghasilkan laporan ringkasan **HTML** dan **PDF** otomatis (termasuk visualisasi).
* [cite_start]**Testing**: Termasuk unit test untuk logika transformasi utama menggunakan `pytest`[cite: 190].
* [cite_start]**Scheduling Ready**: `main.py` dapat dijalankan dari *scheduler* seperti Airflow atau cron[cite: 191].

## Cara Menjalankan

1.  **Instal Dependencies:**
    ```bash
    # (Pastikan Anda berada di direktori etl_pipeline/)
    pip install -r requirements.txt
    
    # (Opsional, untuk Laporan PDF)
    # Anda harus menginstal wkhtmltopdf secara manual
    # (misal: 'brew install wkhtmltopdf' di macOS)
    ```

2.  **Konfigurasi Database:**
    * Pastikan detail koneksi di `config/config.yaml` sudah sesuai dengan database PostgreSQL Anda di Docker.

3.  **Menjalankan Unit Tests (Opsional):**
    ```bash
    # (Dari direktori root proyek 'warehouse-stock-management')
    pytest
    ```

4.  **Menjalankan Pipeline:**

    * **Full Load:** (Menjalankan pipeline pada semua data)
        ```bash
        # (Pastikan CWD Anda ada di 'etl_pipeline/')
        python main.py --load_type full
        ```

    * **Incremental Load:** (Hanya memproses data baru)
        ```bash
        # Edit 'last_run_timestamp' di config.yaml
        python main.py --load_type incremental
        ```

5.  **Cek Hasil:**
    * Lihat file-file (Parquet/CSV/HTML/PDF) di direktori `etl_pipeline/analytics_output/`.
    * Cek tabel `analytics_daily_summary` di database Anda.