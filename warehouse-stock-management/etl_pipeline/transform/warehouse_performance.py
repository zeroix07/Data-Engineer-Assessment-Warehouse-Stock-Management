import pandas as pd
import logging

log = logging.getLogger(__name__)

def calculate_warehouse_performance(data_frames):
    """
    Menghitung metrik kinerja gudang[cite: 160].
    """
    log.info("Menghitung kinerja gudang...")
    
    df_movements = data_frames['stock_movements']
    
    # 1. Transfer Patterns Between Warehouses [cite: 166]
    log.info("  -> Menganalisis pola transfer...")
    
    df_transfers = df_movements[df_movements['movement_type'] == 'TRANSFER'].copy()
    
    # Pisahkan IN dan OUT
    transfers_out = df_transfers[df_transfers['quantity'] < 0][['reference_id', 'warehouse_id', 'product_id', 'quantity']]
    transfers_out.rename(columns={'warehouse_id': 'from_warehouse_id', 'quantity': 'qty_out'}, inplace=True)
    
    transfers_in = df_transfers[df_transfers['quantity'] > 0][['reference_id', 'warehouse_id', 'product_id', 'quantity']]
    transfers_in.rename(columns={'warehouse_id': 'to_warehouse_id', 'quantity': 'qty_in'}, inplace=True)
    
    # Gabungkan berdasarkan reference_id
    # Kita asumsikan reference_id unik per transfer
    df_transfer_pairs = pd.merge(transfers_out, transfers_in, on=['reference_id', 'product_id'])
    
    # Agregat pola transfer
    transfer_patterns = df_transfer_pairs.groupby(['from_warehouse_id', 'to_warehouse_id']) \
                                          .agg(total_transfers=('reference_id', 'nunique'),
                                               total_qty=('qty_in', 'sum')) \
                                          .sort_values(by='total_transfers', ascending=False) \
                                          .reset_index()
                                          
    log.info("  -> Analisis pola transfer selesai.")

    # 2. In/Out Efficiency [cite: 164]
    # Kita definisikan sebagai total pergerakan IN vs OUT per gudang
    warehouse_io = df_movements.groupby(['warehouse_id', 'movement_type'])['quantity'].count().unstack(fill_value=0)
    
    
    # Simpan hasil kalkulasi
    data_frames['transfer_patterns'] = transfer_patterns
    data_frames['warehouse_io_summary'] = warehouse_io
    
    return data_frames