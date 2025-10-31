import yaml
import logging
import logging.config
import argparse
from pathlib import Path
import os

# Setup logging
try:
    logging.config.fileConfig('etl_pipeline/config/logging.conf')
except Exception as e:
    # Ini terjadi jika CWD bukan root proyek
    try:
        logging.config.fileConfig('config/logging.conf')
    except Exception as e_inner:
        print(f"Error: Tidak dapat memuat konfigurasi logging: {e_inner}")
        # Setup logging dasar jika file config gagal
        logging.basicConfig(level=logging.INFO, 
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

log = logging.getLogger(__name__)

# Impor modul-modul ETL
from extract.data_extractor import DataExtractor
from load.data_loader import DataLoader
from load.report_generator import ReportGenerator
import transform.inventory_metrics as inv
import transform.movement_analytics as mov
import transform.financial_metrics as fin
import transform.warehouse_performance as wh

def load_config(config_dir='config'):
    """Memuat file konfigurasi YAML."""
    try:
        config_path = Path(config_dir) / 'config.yaml'
        if not config_path.exists():
             # Coba path alternatif jika CWD ada di dalam 'etl_pipeline'
             config_path = Path('..') / config_dir / 'config.yaml'
             if not config_path.exists():
                 # Coba path CWD
                 config_path = Path('config.yaml')

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        log.info(f"Konfigurasi berhasil dimuat dari {config_path.resolve()}")
        return config
    except Exception as e:
        log.error(f"Gagal memuat config.yaml: {e}")
        raise

def run_pipeline(config, load_type='full'):
    """
    Menjalankan pipeline E-T-L[cite: 179].
    """
    log.info(f"--- MEMULAI PIPELINE ETL (Mode: {load_type.upper()}) ---")
    
    # 1. EXTRACT [cite: 144]
    try:
        extractor = DataExtractor(config['database'])
        if load_type == 'incremental':
            raw_data = extractor.extract_incremental(config['etl_settings']['last_run_timestamp'])
        else:
            raw_data = extractor.extract_full()
        
        # Penanganan Data Quality [cite: 147]
        clean_data = extractor.handle_data_quality_issues(raw_data)
        
        if clean_data['stock_movements'].empty:
            log.warning("Tidak ada data baru untuk diproses. Pipeline berhenti.")
            return
            
    except Exception as e:
        log.error(f"FATAL: Gagal pada tahap EXTRACT: {e}")
        return

    # 2. TRANSFORM [cite: 148]
    try:
        log.info("Memulai tahap TRANSFORM...")
        data = clean_data.copy()
        
        # Jalankan modul-modul transformasi secara sekuensial
        data = inv.calculate_inventory_metrics(data, config['etl_settings']['dead_stock_days'])
        data = mov.calculate_movement_analytics(data)
        data = fin.calculate_financial_metrics(data, config['etl_settings']['abc_analysis'])
        data = wh.calculate_warehouse_performance(data)
        
        log.info("Tahap TRANSFORM selesai.")
        
    except Exception as e:
        log.error(f"FATAL: Gagal pada tahap TRANSFORM: {e}")
        return

    # 3. LOAD [cite: 171]
    try:
        log.info("Memulai tahap LOAD...")
        loader = DataLoader(config['output'], config['database'])
        
        # Simpan ke file (Parquet/CSV)
        loader.save_to_file(data)
        
        # Simpan ke summary table
        loader.load_to_summary_table(data)
        
        # Buat Laporan
        report_gen = ReportGenerator(config['output']['analytics_dir'], 
                                     config['output']['report_filename'])
        report_gen.generate_report(data)
        
        log.info("Tahap LOAD selesai.")
        
    except Exception as e:
        log.error(f"FATAL: Gagal pada tahap LOAD: {e}")
        return

    log.info(f"--- PIPELINE ETL (Mode: {load_type.upper()}) SELESAI ---")

if __name__ == "__main__":
    # Ini membuat skrip siap untuk dijadwalkan (scheduling ready) [cite: 191]
    
    parser = argparse.ArgumentParser(description="Warehouse Stock ETL Pipeline.")
    parser.add_argument(
        '--load_type', 
        choices=['full', 'incremental'], 
        default='full',
        help="Jenis ETL load: 'full' atau 'incremental'."
    )
    
    args = parser.parse_args()
    
    # Pindah CWD ke root script agar path config benar
    os.chdir(Path(__file__).parent)
    
    config = load_config(config_dir='config')
    run_pipeline(config, args.load_type)