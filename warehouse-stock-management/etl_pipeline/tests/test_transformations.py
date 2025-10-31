import pandas as pd
import pytest
from datetime import datetime, timedelta
from etl_pipeline.transform.inventory_metrics import calculate_inventory_metrics
from etl_pipeline.transform.financial_metrics import calculate_financial_metrics

@pytest.fixture
def sample_data():
    """Menyiapkan data dummy untuk testing."""
    today = pd.to_datetime('now')
    
    # Data stok saat ini
    df_stock = pd.DataFrame({
        'product_id': [1, 2, 3],
        'warehouse_id': [1, 1, 1],
        'quantity_on_hand': [10, 5, 0] # Produk 3 stoknya 0
    })
    
    # Data pergerakan
    df_movements = pd.DataFrame({
        'product_id': [1, 2],
        'warehouse_id': [1, 1],
        # Produk 1 bergerak 10 hari lalu (BUKAN dead stock)
        'movement_date': [today - timedelta(days=10), 
        # Produk 2 bergerak 200 hari lalu (DEAD STOCK)
                          today - timedelta(days=200)]
    })
    
    # Data penjualan
    df_so_details = pd.DataFrame({
        'product_id': [1, 1, 2, 3],
        'quantity': [5, 5, 2, 10],
        'unit_price': [100, 100, 500, 50],
        'revenue': [500, 500, 1000, 500]
    })
    
    return {
        "stock": df_stock,
        "stock_movements": df_movements,
        "sales_order_details": df_so_details
    }

def test_dead_stock_identification(sample_data):
    """
    Test untuk memastikan identifikasi dead stock (Task 4.2)[cite: 153].
    """
    DEAD_STOCK_DAYS = 180
    
    # Jalankan fungsi
    result_data = calculate_inventory_metrics(sample_data, dead_stock_days=DEAD_STOCK_DAYS)
    
    # Ambil laporan dead stock
    dead_stock_report = result_data['dead_stock_report']
    
    # Validasi: Hanya produk 2 yang seharusnya dead stock
    assert len(dead_stock_report) == 1
    assert dead_stock_report.iloc[0]['product_id'] == 2
    assert dead_stock_report.iloc[0]['is_dead_stock'] == True
    
    # Validasi: Produk 1 tidak dead stock
    assert 1 not in dead_stock_report['product_id'].values
    
    # Validasi: Produk 3 tidak dead stock (karena stok 0)
    assert 3 not in dead_stock_report['product_id'].values

def test_abc_analysis(sample_data):
    """
    Test untuk logika ABC Analysis (Task 4.2)[cite: 175].
    """
    abc_config = {'A_percent': 0.8, 'B_percent': 0.15, 'C_percent': 0.05}
    
    # Data Revenue:
    # Prod 1: 1000
    # Prod 2: 1000
    # Prod 3: 500
    # Total: 2500
    
    # Prod 1: 1000 / 2500 = 40% (Class A)
    # Prod 2: 1000 / 2500 = 40% (Total 80%) (Class A)
    # Prod 3: 500 / 2500 = 20% (Total 100%) (Class B)
    
    result_data = calculate_financial_metrics(sample_data, abc_config)
    abc_report = result_data['abc_analysis']
    
    class_A = abc_report[abc_report['abc_class'] == 'A']['product_id'].tolist()
    class_B = abc_report[abc_report['abc_class'] == 'B']['product_id'].tolist()
    
    assert 1 in class_A
    assert 2 in class_A
    assert 3 in class_B