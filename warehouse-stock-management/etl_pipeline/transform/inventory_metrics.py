import pandas as pd
import logging

log = logging.getLogger(__name__)

def calculate_inventory_metrics(data_frames, dead_stock_days=180):
    """
    Menghitung metrik inventori kunci[cite: 149].
    """
    log.info("Menghitung metrik inventori...")
    
    df_movements = data_frames['stock_movements']
    df_stock = data_frames['stock']
    df_so_details = data_frames['sales_order_details']

    # Pastikan tipe data tanggal
    df_movements['movement_date'] = pd.to_datetime(df_movements['movement_date'])
    
    # 1. Dead Stock Identification [cite: 153]
    # (Stok tidak bergerak > 180 hari)
    log.info(f"  -> Mengidentifikasi dead stock (tidak bergerak > {dead_stock_days} hari)...")
    
    # Cari tanggal pergerakan terakhir per (produk, gudang)
    last_movement_date = df_movements.groupby(['product_id', 'warehouse_id'])['movement_date'].max().reset_index()
    
    # Gabung dengan stok saat ini
    df_dead_stock = pd.merge(df_stock, last_movement_date, on=['product_id', 'warehouse_id'], how='left')
    
    # Hitung hari sejak pergerakan terakhir
    today = pd.to_datetime('now', utc=True)
    df_dead_stock['days_since_last_movement'] = (today - df_dead_stock['movement_date']).dt.days
    
    # Isi NaN (tidak pernah bergerak) dengan angka besar
    df_dead_stock['days_since_last_movement'] = df_dead_stock['days_since_last_movement'].fillna(9999)

    # Identifikasi dead stock
    df_dead_stock['is_dead_stock'] = (
        (df_dead_stock['days_since_last_movement'] > dead_stock_days) &
        (df_dead_stock['quantity_on_hand'] > 0)
    )
    
    # 2. Stock Turnover Ratio [cite: 150]
    # Rumus: (Total COGS) / (Rata-rata Inventori)
    # Kita sederhanakan: (Total Kuantitas Terjual) / (Rata-rata Kuantitas Stok)
    
    log.info("  -> Menghitung stock turnover ratio...")
    
    total_qty_sold = df_so_details['quantity'].sum()
    avg_inventory_qty = df_stock['quantity_on_hand'].mean()
    
    if avg_inventory_qty > 0:
        stock_turnover_ratio = total_qty_sold / avg_inventory_qty
    else:
        stock_turnover_ratio = 0

    # 3. Days of Inventory on Hand (DOH) [cite: 151]
    # Rumus: (Rata-rata Inventori / COGS) * 365
    # Kita sederhanakan: (Rata-rata Kuantitas Stok / Total Kuantitas Terjual) * (jumlah hari dalam data)
    
    log.info("  -> Menghitung days of inventory on hand...")
    
    num_days_in_data = (df_movements['movement_date'].max() - df_movements['movement_date'].min()).days
    if num_days_in_data == 0: num_days_in_data = 1 # hindari pembagian nol
    
    if total_qty_sold > 0:
        doh = (avg_inventory_qty / total_qty_sold) * num_days_in_data
    else:
        doh = 0
        
    summary_metrics = {
        'total_dead_stock_items': int(df_dead_stock['is_dead_stock'].sum()),
        'total_dead_stock_value': 0, # Kita hitung ini di financial_metrics
        'stock_turnover_ratio': round(stock_turnover_ratio, 2),
        'days_of_inventory_on_hand': round(doh, 2)
    }
    
    # Simpan hasil kalkulasi untuk Laporan
    data_frames['dead_stock_report'] = df_dead_stock[df_dead_stock['is_dead_stock'] == True]
    data_frames['inventory_summary'] = summary_metrics
    
    log.info(f"Metrik inventori selesai: {summary_metrics}")
    
    return data_frames