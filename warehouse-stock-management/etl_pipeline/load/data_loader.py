import pandas as pd
import logging
from pathlib import Path
from sqlalchemy import create_engine

log = logging.getLogger(__name__)

class DataLoader:
    def __init__(self, output_config, db_config=None):
        self.output_dir = Path(output_config['analytics_dir'])
        self.output_format = output_config['format']
        self.summary_table_name = output_config['summary_table_name']
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        log.info(f"Direktori output disiapkan di: {self.output_dir.resolve()}")
        
        self.engine = None
        if db_config:
            try:
                conn_str = f"{db_config['type']}://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['db_name']}"
                self.engine = create_engine(conn_str)
                log.info("Koneksi database untuk Loader berhasil dibuat.")
            except Exception as e:
                log.error(f"Gagal membuat koneksi database untuk Loader: {e}")
                
    def save_to_file(self, data_frames):
        """
        Menyimpan DataFrame analitik ke format file yang diminta (Parquet/CSV).
        """
        log.info(f"Menyimpan file analitik ke {self.output_format}...")
        
        # Kita hanya simpan data frame yang 'bersih' (bukan data mentah)
        analytics_reports = [
            'dead_stock_report', 'inventory_summary', 'daily_trends', 
            'weekly_trends', 'monthly_trends', 'peak_day_of_week', 
            'peak_month', 'abc_analysis', 'stock_value_report', 
            'financial_summary', 'transfer_patterns', 'warehouse_io_summary'
        ]
        
        for name, df in data_frames.items():
            if name not in analytics_reports:
                continue
            
            # Ubah summary dict ke DataFrame
            if isinstance(df, dict):
                df = pd.DataFrame([df])
            
            try:
                if self.output_format == 'parquet':
                    path = self.output_dir / f"{name}.parquet"
                    df.to_parquet(path, index=False)
                elif self.output_format == 'csv':
                    path = self.output_dir / f"{name}.csv"
                    df.to_csv(path, index=False)
                elif self.output_format == 'excel':
                    # Excel tidak ideal untuk data besar, tapi sebagai opsi
                    path = self.output_dir / f"{name}.xlsx"
                    df.to_excel(path, index=False, engine='openpyxl')
                
                log.info(f"  -> Berhasil menyimpan {path.name}")
                
            except Exception as e:
                log.error(f"Gagal menyimpan {name}: {e}")

    def load_to_summary_table(self, data_frames):
        """
        Menyimpan gabungan summary ke tabel database.
        """
        if not self.engine:
            log.warning("Engine database tidak dikonfigurasi. Melewatkan load ke summary table.")
            return

        try:
            log.info(f"Mempersiapkan data untuk summary table: {self.summary_table_name}")
            
            # Gabungkan summary metrics
            summary = {
                'run_timestamp': pd.to_datetime('now'),
                **data_frames.get('inventory_summary', {}),
                **data_frames.get('financial_summary', {})
            }
            
            # Hapus data non-skalar
            summary.pop('abc_summary', None)
            
            df_summary = pd.DataFrame([summary])

            # Load ke database (append)
            df_summary.to_sql(
                self.summary_table_name,
                self.engine,
                if_exists='append',
                index=False
            )
            log.info(f"Berhasil memuat data summary ke tabel {self.summary_table_name}.")
            
        except Exception as e:
            log.error(f"Gagal memuat summary table: {e}")