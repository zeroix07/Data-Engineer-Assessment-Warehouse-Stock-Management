import pandas as pd
import yaml
import logging
from sqlalchemy import create_engine

log = logging.getLogger(__name__)

class DataExtractor:
    def __init__(self, db_config):
        """
        Inisialisasi koneksi engine SQLAlchemy.
        """
        try:
            conn_str = f"{db_config['type']}://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['db_name']}"
            self.engine = create_engine(conn_str)
            log.info("Koneksi database berhasil dibuat.")
        except Exception as e:
            log.error(f"Gagal membuat koneksi database: {e}")
            raise
    
    def extract_full(self):
        """
        Mengekstrak semua data relevan untuk full load.
        """
        log.info("Memulai EKTRAKSI data (FULL LOAD)...")
        try:
            with self.engine.connect() as conn:
                tables = {
                    "products": pd.read_sql("SELECT * FROM products", conn),
                    "categories": pd.read_sql("SELECT * FROM categories", conn),
                    "warehouses": pd.read_sql("SELECT * FROM warehouses", conn),
                    "stock": pd.read_sql("SELECT * FROM stock", conn),
                    "stock_movements": pd.read_sql("SELECT * FROM stock_movements", conn),
                    "sales_order_details": pd.read_sql("SELECT * FROM sales_order_details", conn),
                    "purchase_order_details": pd.read_sql("SELECT * FROM purchase_order_details", conn) # <--- TAMBAHKAN BARIS INI
                }
            log.info(f"Ekstraksi FULL LOAD selesai. {len(tables['stock_movements'])} baris movements diambil.")
            return tables
        except Exception as e:
            log.error(f"Error saat full extraction: {e}")
            return None

    def extract_incremental(self, last_run_timestamp):
        """
        Mengekstrak data baru berdasarkan timestamp[cite: 146].
        """
        log.info(f"Memulai EKSTRAKSI data (INCREMENTAL) > {last_run_timestamp}...")
        try:
            with self.engine.connect() as conn:
                # Hanya mengambil movements & stock yang baru
                query = f"""
                SELECT * FROM stock_movements 
                WHERE movement_date > '{last_run_timestamp}'
                """
                tables = {
                    "stock_movements": pd.read_sql(query, conn),
                    "stock": pd.read_sql("SELECT * FROM stock", conn), # Stok selalu diambil full
                    
                    # Data master biasanya diambil full atau pakai CDC
                    "products": pd.read_sql("SELECT * FROM products", conn),
                    "categories": pd.read_sql("SELECT * FROM categories", conn),
                    "warehouses": pd.read_sql("SELECT * FROM warehouses", conn),
                    "sales_order_details": pd.read_sql("SELECT * FROM sales_order_details", conn),
                    "purchase_order_details": pd.read_sql("SELECT * FROM purchase_order_details", conn)
                }
            log.info(f"Ekstraksi INCREMENTAL selesai. {len(tables['stock_movements'])} baris movements baru diambil.")
            return tables
        except Exception as e:
            log.error(f"Error saat incremental extraction: {e}")
            return None

    def handle_data_quality_issues(self, data_frames):
        """
        Menangani isu kualitas data yang kita buat di Task 2[cite: 147].
        """
        log.info("Memulai penanganan data quality issues...")
        
        # 1. Isu: 'bad_reference_id' (reference_id = 9999999)
        # Kita akan tandai ini sebagai 'invalid_reference'
        df_movements = data_frames['stock_movements']
        df_movements['dq_issue'] = 'valid'
        df_movements.loc[df_movements['reference_id'] == 9999999, 'dq_issue'] = 'invalid_reference'
        
        # 2. Isu: 'invalid_qty' (Qty IN negatif)
        df_movements.loc[
            (df_movements['movement_type'].isin(['IN', 'RETURN'])) & (df_movements['quantity'] < 0), 
            'dq_issue'
        ] = 'invalid_quantity'
        
        # 3. Isu: 'future_date' (Tanggal di masa depan)
        df_movements.loc[
            df_movements['movement_date'] > pd.to_datetime('now', utc=True), 
            'dq_issue'
        ] = 'future_date'

        # Filter baris yang bermasalah (kita tidak proses)
        valid_movements = df_movements[df_movements['dq_issue'] == 'valid'].copy()
        invalid_movements_count = len(df_movements) - len(valid_movements)
        
        log.warning(f"Total {invalid_movements_count} baris data movements difilter karena isu kualitas data.")
        
        # Kembalikan data yang sudah bersih
        data_frames['stock_movements'] = valid_movements
        return data_frames