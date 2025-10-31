import pandas as pd
import logging
import numpy as np

log = logging.getLogger(__name__)

def calculate_financial_metrics(data_frames, abc_config):
    """
    Menghitung metrik finansial[cite: 168].
    """
    log.info("Menghitung metrik finansial...")
    
    df_so_details = data_frames['sales_order_details']
    df_stock = data_frames['stock']
    df_products = data_frames['products']
    
    # 1. ABC Analysis (Pareto) [cite: 175]
    # Berdasarkan volume penjualan (revenue)
    log.info("  -> Menghitung ABC Analysis...")
    
    # Hitung revenue per produk
    df_so_details['revenue'] = df_so_details['quantity'] * df_so_details['unit_price']
    product_revenue = df_so_details.groupby('product_id')['revenue'].sum().sort_values(ascending=False).reset_index()
    
    # Hitung cumulative percentage
    product_revenue['total_revenue'] = product_revenue['revenue'].sum()
    product_revenue['revenue_cumsum'] = product_revenue['revenue'].cumsum()
    product_revenue['revenue_percent'] = (product_revenue['revenue_cumsum'] / product_revenue['total_revenue'])
    
    # Terapkan klasifikasi ABC
    def abc_classifier(percent):
        if percent <= abc_config['A_percent']:
            return 'A'
        elif percent <= (abc_config['A_percent'] + abc_config['B_percent']):
            return 'B'
        else:
            return 'C'
            
    product_revenue['abc_class'] = product_revenue['revenue_percent'].apply(abc_classifier)
    
    abc_summary = product_revenue.groupby('abc_class')['product_id'].count().to_dict()
    log.info(f"  -> ABC Analysis selesai: {abc_summary}")
    
    # 2. Inventory Value Over Time [cite: 169]
    # Ini memerlukan pemanggilan fungsi DB `calculate_stock_value`
    # Untuk kesederhanaan, kita hitung nilai stok SAAT INI
    # (Kita asumsikan data `purchase_order_details` ada di `data_frames`)
    # ... (Logika ini bisa sangat kompleks, kita akan hitung nilai stok saat ini)
    # Untuk Task 4, lebih baik kita hitung ulang di Python
    
    log.info("  -> Menghitung nilai inventori saat ini...")
    
    # Asumsikan kita perlu mengambil data PO
    if 'purchase_order_details' not in data_frames:
        log.warning("Data PO tidak ada, nilai inventori tidak dapat dihitung akurat.")
        product_avg_cost = pd.DataFrame(columns=['product_id', 'avg_cost'])
    else:
        df_po_details = data_frames['purchase_order_details']
        # Hitung biaya rata-rata per produk
        product_avg_cost = df_po_details.groupby('product_id').apply(
            lambda x: np.average(x['unit_price'], weights=x['quantity'])
        ).reset_index(name='avg_cost')

    # Gabung biaya rata-rata dengan stok saat ini
    df_stock_value = pd.merge(df_stock, product_avg_cost, on='product_id', how='left')
    df_stock_value['avg_cost'] = df_stock_value['avg_cost'].fillna(0).infer_objects(copy=False) # Asumsi biaya 0 jika tidak pernah dibeli
    df_stock_value['stock_value'] = df_stock_value['quantity_on_hand'] * df_stock_value['avg_cost']
    
    total_inventory_value = df_stock_value['stock_value'].sum()
    log.info(f"  -> Total nilai inventori saat ini: {total_inventory_value:,.2f}")

    # Simpan hasil kalkulasi
    data_frames['abc_analysis'] = product_revenue
    data_frames['stock_value_report'] = df_stock_value
    data_frames['financial_summary'] = {
        'total_inventory_value': total_inventory_value,
        'abc_summary': abc_summary
    }
    
    # Hitung nilai dead stock (dari inventory_metrics)
    if 'dead_stock_report' in data_frames:
        df_dead_stock_value = pd.merge(
            data_frames['dead_stock_report'], 
            df_stock_value[['product_id', 'warehouse_id', 'stock_value']],
            on=['product_id', 'warehouse_id']
        )
        total_dead_stock_value = df_dead_stock_value['stock_value'].sum()
        data_frames['inventory_summary']['total_dead_stock_value'] = total_dead_stock_value
        log.info(f"  -> Total nilai dead stock: {total_dead_stock_value:,.2f}")

    return data_frames