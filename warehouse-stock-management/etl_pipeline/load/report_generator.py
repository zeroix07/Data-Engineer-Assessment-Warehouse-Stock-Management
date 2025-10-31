import logging
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Tambahkan root proyek ke sys.path
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# PERUBAHAN: Impor fungsi dari model.py
from model import generate_narrative_analysis

# Impor untuk WeasyPrint
try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    log = logging.getLogger(__name__) 
    log.warning("WeasyPrint tidak ditemukan. Laporan PDF tidak akan dibuat. Instal dengan `pip install WeasyPrint`.")

# Konfigurasi logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)


class ReportGenerator:
    def __init__(self, output_dir="reports", report_filename="warehouse_report"):
        self.output_dir = Path(output_dir)
        self.report_filename = report_filename
        self.template_dir = Path(__file__).parent
        plt.style.use('ggplot') 
        
        # Daftarkan filter kustom ke Jinja
        self.env = Environment(loader=FileSystemLoader(self.template_dir))
        self.env.filters['format_rupiah'] = self.format_rupiah
        self.env.filters['format_number'] = self.format_number
        
        self.charts_dir = self.output_dir / "charts"
        self.charts_dir.mkdir(parents=True, exist_ok=True)
        log.info(f"Direktori charts disiapkan di: {self.charts_dir}")

    # --- Fungsi Helper Formatting ---
    def format_rupiah(self, value):
        """Format angka sebagai Rupiah, misal: 1.234.567,89"""
        try:
            s = f"{float(value):,.2f}"
            s_swap = s.replace(",", "X").replace(".", ",").replace("X", ".")
            return s_swap
        except (ValueError, TypeError, AttributeError):
            return str(value)

    def format_number(self, value, precision=1):
        """Format angka biasa, misal: 3.590,8"""
        try:
            s = f"{float(value):,.{precision}f}"
            s_swap = s.replace(",", "X").replace(".", ",").replace("X", ".")
            return s_swap
        except (ValueError, TypeError, AttributeError):
            return str(value)

    # --- Menggunakan Jalur Relatif untuk Charts ---
    def create_charts(self, data_frames):
        """Membuat visualisasi data (4 charts) dan menyimpannya sebagai gambar."""
        log.info("Membuat visualisasi (charts)...")
        chart_paths = {}
        
        try:
            # 1. Chart: Monthly Movements
            if 'monthly_trends' in data_frames:
                df = data_frames['monthly_trends']
                plt.figure(figsize=(10, 6))
                plt.plot(df['movement_date'], df['monthly_movements'], marker='o', linestyle='-')
                plt.title('Monthly Sales Movements')
                plt.xlabel('Date')
                plt.ylabel('Total Movements')
                plt.grid(True, linestyle='--', alpha=0.6)
                plt.xticks(rotation=45)
                plt.tight_layout()
                path = self.charts_dir / "monthly_movements.png"
                plt.savefig(path, bbox_inches='tight')
                plt.close()
                chart_paths['monthly_movements'] = "charts/monthly_movements.png" 

            # 2. Chart: ABC Analysis
            if 'abc_analysis' in data_frames:
                df = data_frames['abc_analysis'].groupby('abc_class')['product_id'].count()
                plt.figure(figsize=(7, 7))
                df.plot(kind='pie', autopct='%1.1f%%', startangle=90, wedgeprops=dict(width=0.4), labels=df.index)
                plt.title('ABC Analysis (by Product Count)')
                plt.ylabel('')
                path = self.charts_dir / "abc_analysis_pie.png"
                plt.savefig(path, bbox_inches='tight')
                plt.close()
                chart_paths['abc_analysis_pie'] = "charts/abc_analysis_pie.png"
            
            # 3. Chart: Warehouse Activity
            if 'warehouse_io_summary' in data_frames:
                df_wh = data_frames['warehouse_io_summary']
                df_wh_plot = df_wh[['IN', 'OUT', 'TRANSFER', 'ADJUSTMENT', 'RETURN']]
                
                plt.figure(figsize=(12, 7))
                df_wh_plot.plot(kind='bar', stacked=True, figsize=(12, 7), ax=plt.gca())
                plt.title('Warehouse Activity (Total Movements)')
                plt.xlabel('Warehouse ID')
                plt.ylabel('Number of Movements')
                plt.xticks(rotation=0)
                plt.legend(title='Movement Type')
                plt.tight_layout()
                path = self.charts_dir / "warehouse_activity.png"
                plt.savefig(path, bbox_inches='tight')
                plt.close('all') 
                chart_paths['warehouse_activity'] = "charts/warehouse_activity.png"

            # 4. Chart: Top 10 Valuable Products
            if 'stock_value_report' in data_frames:
                df_val = data_frames['stock_value_report']
                df_top10 = df_val.nlargest(10, 'stock_value').sort_values('stock_value', ascending=True)
                df_top10['product_id_str'] = df_top10['product_id'].astype(str)
                
                plt.figure(figsize=(10, 8))
                plt.barh(df_top10['product_id_str'], df_top10['stock_value'], color='skyblue')
                plt.title('Top 10 Most Valuable Products (by Current Stock Value)')
                plt.xlabel('Total Stock Value (Rp)')
                plt.ylabel('Product ID')
                plt.gca().xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'Rp {x/1e9:,.1f} M'))
                plt.grid(True, linestyle='--', axis='x', alpha=0.6)
                plt.tight_layout()
                path = self.charts_dir / "top_10_value_products.png"
                plt.savefig(path, bbox_inches='tight')
                plt.close()
                chart_paths['top_10_value_products'] = "charts/top_10_value_products.png"
            
            log.info(f"Berhasil membuat {len(chart_paths)} charts.")
            return chart_paths
            
        except Exception as e:
            log.error(f"Gagal membuat chart: {e}")
            return chart_paths

    def generate_report(self, data_frames):
        """Menggabungkan data dan charts ke dalam template HTML."""
        log.info("Membuat laporan HTML...")
        
        self.create_template_if_not_exists()
        chart_paths = self.create_charts(data_frames)
        
        # --- PERUBAHAN: Memanggil fungsi dari model.py untuk生成 narasi ---
        log.info("Membuat narasi analitik menggunakan AI...")
        inv_summary = data_frames.get('inventory_summary', {})
        fin_summary = data_frames.get('financial_summary', {})
        total_items = data_frames.get('stock_value_report', pd.DataFrame()).shape[0]
        
        summary_narrative = generate_narrative_analysis(
            inventory_summary=inv_summary,
            financial_summary=fin_summary,
            total_items=total_items
        )
        # --- AKHIR PERUBAHAN ---

        template_data = {
            'run_date': pd.to_datetime('now').strftime('%Y-%m-%d %H:%M:%S'),
            'inventory_summary': inv_summary,
            'financial_summary': fin_summary,
            'summary_narrative': summary_narrative, 
            'peak_dow': data_frames.get('peak_day_of_week', pd.DataFrame()).to_html(index=False, classes='table table-sm'),
            'peak_month': data_frames.get('peak_month', pd.DataFrame()).to_html(index=False, classes='table table-sm'),
            'transfer_patterns': data_frames.get('transfer_patterns', pd.DataFrame()).head(10).to_html(index=False, classes='table table-sm'),
            'charts': chart_paths
        }
        
        try:
            template = self.env.get_template('report_template.html')
            html_content = template.render(template_data)
            
            html_path = self.output_dir / f"{self.report_filename}.html"
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            log.info(f"Laporan HTML berhasil disimpan di: {html_path}")
            
            if WEASYPRINT_AVAILABLE:
                try:
                    pdf_path = self.output_dir / f"{self.report_filename}.pdf"
                    base_url = self.output_dir.resolve().as_uri() + "/"
                    
                    HTML(string=html_content, base_url=base_url).write_pdf(pdf_path)
                    log.info(f"Laporan PDF (via WeasyPrint) berhasil disimpan di: {pdf_path}")
                    
                except Exception as e:
                    log.error(f"Gagal membuat PDF dengan WeasyPrint: {e}")
            else:
                log.warning("WeasyPrint tidak tersedia. Melewatkan pembuatan PDF.")
            
        except Exception as e:
            log.error(f"Gagal me-render laporan HTML: {e}")

    def create_template_if_not_exists(self):
        """Helper untuk membuat file template HTML baru yang dinamis untuk A4."""
        template_path = self.template_dir / "report_template.html"
        
        if template_path.exists():
            log.warning("Menghapus template HTML lama untuk regenerasi...")
            template_path.unlink()
        
        log.info("Membuat template HTML baru yang dinamis untuk A4...")
        
        html_template = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <title>Warehouse Analytics Report</title>
    <style>
        /* --- Gaya Umum --- */
        body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #e0e0e0; margin: 0; padding: 20px; color: #333; }
        .a4-page { width: 210mm; min-height: 297mm; padding: 20mm; margin: 20px auto; background-color: #ffffff; box-shadow: 0 0 10px rgba(0, 0, 0, 0.2); box-sizing: border-box; }
        h1, h2, h3 { color: #2c3e50; }
        h1 { text-align: center; margin-bottom: 15px; }
        h2 { text-align: center; margin-top: 30px; margin-bottom: 20px; border-bottom: 2px solid #3498db; padding-bottom: 10px; page-break-after: avoid; }
        .card { border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px; margin-bottom: 20px; page-break-inside: avoid; background-color: #fdfdfd; }
        .card h3 { margin-top: 0; color: #3498db; border-bottom: 1px solid #eee; padding-bottom: 8px; margin-bottom: 12px; text-align: center; }
        .table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.9em; }
        .table th, .table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #ddd; }
        .table th { background-color: #34495e; color: #ffffff; font-weight: 600; text-transform: uppercase; font-size: 0.8em; }
        .table tr:nth-child(even) { background-color: #f9f9f9; }
        .table tr:hover { background-color: #f1f1f1; }
        .table td:not(:first-child), .table th:not(:first-child) { text-align: right; }
        img { max-width: 100%; height: auto; display: block; margin: 10px auto; }
        ul { list-style-type: none; padding-left: 0; }
        li { margin-bottom: 8px; font-size: 1.1em; display: flex; justify-content: space-between;}
        li b { color: #34495e; }
        p { font-size: 1.0em; line-height: 1.6; text-align: justify; }
        @media print {
            body { background-color: #ffffff; padding: 0; }
            @page { size: A4; margin: 20mm; }
            .a4-page { width: 100%; min-height: 100vh; margin: 0; padding: 0; box-shadow: none; background: none; }
            img { max-width: 100% !important; page-break-inside: avoid; }
            .table tr:hover { background-color: transparent; }
        }
    </style>
</head>
<body>
    <div class="a4-page">
        <h1>Warehouse Analytics Report</h1>
        <p style="text-align: center; font-size: 0.9em; color: #777;">Laporan ini dibuat pada: {{ run_date }}</p>
        <h2>Executive Summary</h2>
        <div class="card">
            <h3>Inventory Summary</h3>
            <ul>
                <li><span>Total Nilai Inventori:</span> <span><b>Rp {{ financial_summary.total_inventory_value | format_rupiah }}</b></span></li>
                <li><span>Rasio Stock Turnover:</span> <span><b>{{ inventory_summary.stock_turnover_ratio | format_number(1) }}</b></span></li>
                <li><span>Hari Stok (DOH):</span> <span><b>{{ inventory_summary.days_of_inventory_on_hand | format_number(1) }} hari</b></span></li>
                <li><span>Item Dead Stock:</span> <span><b>{{ inventory_summary.total_dead_stock_items | format_number(0) }} SKU</b></span></li>
                <li><span>Nilai Dead Stock:</span> <span><b>Rp {{ inventory_summary.total_dead_stock_value | format_rupiah }}</b></span></li>
            </ul>
        </div>
        <div class="card">
            <h3>Analisis Naratif</h3>
            <p>{{ summary_narrative|safe }}</p>
        </div>
        <h2>Movement Analytics</h2>
        <div class="card"><h3>ABC Analysis (by Product Count)</h3><img src="{{ charts.abc_analysis_pie }}" alt="ABC Analysis Chart" style="max-width: 60%;"></div>
        <div class="card"><h3>Monthly Sales Movements</h3><img src="{{ charts.monthly_movements }}" alt="Monthly Movements Chart"></div>
        <div class="card"><h3>Peak Day of Week (Avg Movements)</h3>{{ peak_dow|safe }}</div>
        <div class="card"><h3>Peak Month (Avg Movements)</h3>{{ peak_month|safe }}</div>
        <h2>Warehouse & Financial Performance</h2>
        <div class="card"><h3>Aktivitas Gudang (IN/OUT/TRANSFER)</h3><img src="{{ charts.warehouse_activity }}" alt="Warehouse Activity Chart"></div>
        <div class="card"><h3>Top 10 Produk Bernilai (Berdasarkan Nilai Stok)</h3><img src="{{ charts.top_10_value_products }}" alt="Top 10 Value Products Chart"></div>
        <div class="card"><h3>Top 10 Transfer Patterns</h3>{{ transfer_patterns|safe }}</div>
    </div>
</body>
</html>
        """
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(html_template)


# --- Blok untuk menjalankan contoh ---
if __name__ == "__main__":
    log.info("Memulai proses pembuatan laporan contoh...")
    
    # Membuat data contoh (dummy data)
    dates = pd.to_datetime(pd.date_range(end='2023-12-31', periods=12, freq='M'))
    monthly_trends_df = pd.DataFrame({'movement_date': dates, 'monthly_movements': np.random.randint(5000, 15000, size=12)})
    abc_data = {'product_id': range(100), 'abc_class': np.random.choice(['A', 'B', 'C'], 100, p=[0.2, 0.3, 0.5])}
    abc_analysis_df = pd.DataFrame(abc_data)
    warehouse_data = {'warehouse_id': ['WH-A', 'WH-B', 'WH-C'], 'IN': np.random.randint(100, 500, size=3), 'OUT': np.random.randint(100, 500, size=3), 'TRANSFER': np.random.randint(50, 200, size=3), 'ADJUSTMENT': np.random.randint(10, 50, size=3), 'RETURN': np.random.randint(10, 50, size=3)}
    warehouse_io_df = pd.DataFrame(warehouse_data)
    stock_value_data = {'product_id': range(50), 'stock_value': np.random.randint(1_000_000, 50_000_000, size=50)}
    stock_value_df = pd.DataFrame(stock_value_data)
    peak_dow_df = pd.DataFrame({'day_of_week': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'], 'avg_movements': np.random.randint(800, 1200, size=5)})
    peak_month_df = pd.DataFrame({'month': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'], 'avg_movements': np.random.randint(9000, 11000, size=6)})
    transfer_patterns_df = pd.DataFrame({'from_warehouse': np.random.choice(['WH-A', 'WH-B', 'WH-C'], 15), 'to_warehouse': np.random.choice(['WH-A', 'WH-B', 'WH-C'], 15), 'total_transfers': np.random.randint(20, 150, size=15)}).drop_duplicates(subset=['from_warehouse', 'to_warehouse']).head(10)
    inventory_summary_dict = {'stock_turnover_ratio': 2.5, 'days_of_inventory_on_hand': 146.0, 'total_dead_stock_items': 450, 'total_dead_stock_value': 2_500_000_000}
    financial_summary_dict = {'total_inventory_value': 5_100_000_000}

    report_data = {
        'monthly_trends': monthly_trends_df, 'abc_analysis': abc_analysis_df, 'warehouse_io_summary': warehouse_io_df,
        'stock_value_report': stock_value_df, 'peak_day_of_week': peak_dow_df, 'peak_month': peak_month_df,
        'transfer_patterns': transfer_patterns_df, 'inventory_summary': inventory_summary_dict, 'financial_summary': financial_summary_dict
    }

    generator = ReportGenerator()
    generator.generate_report(report_data)
    
    log.info("Proses selesai. Laporan HTML dan PDF telah dibuat di folder 'reports'.")