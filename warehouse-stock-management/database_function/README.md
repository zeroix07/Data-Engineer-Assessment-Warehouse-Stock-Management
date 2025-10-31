# Database Functions & Stored Procedures (Task 3)

Direktori ini berisi logika bisnis inti (fungsi, prosedur, dan trigger) untuk data warehouse.

## Daftar File

* `functions.sql`: Berisi semua fungsi utama untuk manipulasi dan kalkulasi data (Task 3.1 - 3.4).
* `triggers.sql`: Berisi fungsi trigger untuk audit trail (Task 3.5) dan trigger bonus untuk `updated_at`.
* `test_cases.sql`: Skrip SQL untuk menguji fungsionalitas semua file di atas.

## Cara Instalasi

File-file ini harus dijalankan di database PostgreSQL Anda **setelah** Task 1 (schema) dan Task 2 (data load) selesai.

1.  **Instal Fungsi:**
    ```bash
    # (Pastikan container 'my_pg' berjalan)
    docker cp database_functions/functions.sql my_pg:/functions.sql
    docker exec -u postgres my_pg psql -f /functions.sql
    ```
    Output: `CREATE FUNCTION`, `CREATE FUNCTION`, ...

2.  **Instal Triggers:**
    ```bash
    docker cp database_functions/triggers.sql my_pg:/triggers.sql
    docker exec -u postgres my_pg psql -f /triggers.sql
    ```
    Output: `CREATE TABLE`, `CREATE FUNCTION`, `CREATE TRIGGER`, ...

## Cara Menjalankan Tes

Setelah fungsi dan trigger diinstal, Anda dapat menjalankan skrip `test_cases.sql`. Skrip ini dirancang untuk dijalankan di dalam satu transaksi dan akan otomatis me-ROLLBACK semua perubahan, sehingga tidak akan mengotori data Anda.

```bash
docker cp database_functions/test_cases.sql my_pg:/test_cases.sql
docker exec -u postgres my_pg psql -f /test_cases.sql