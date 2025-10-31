import pandas as pd
import numpy as np
import yaml
import random
from faker import Faker
from tqdm import tqdm
from pathlib import Path
from datetime import datetime, timedelta, date

# Inisialisasi Faker untuk data Indonesia
fake = Faker('id_ID')

def load_config(config_path='config.yaml'):
    """Memuat file konfigurasi YAML."""
    print(f"Memuat konfigurasi dari {config_path}...")
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    print("Konfigurasi berhasil dimuat.")
    return config

def create_output_directory(dir_name):
    """Membuat direktori output jika belum ada."""
    Path(dir_name).mkdir(parents=True, exist_ok=True)

def get_seasonal_date(start_date, end_date):
    """
    Menghasilkan tanggal dengan pola musiman.
    Bulan Juni-Juli (liburan) dan November-Desember (akhir tahun) akan lebih sibing.
   
    """
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    total_days = (end - start).days
    random_day = random.randint(0, total_days)
    date = start + timedelta(days=random_day)
    
    # Bobot untuk musiman (1-12)
    # Bobot lebih tinggi untuk Juni(6), Juli(7), Nov(11), Des(12)
    month_weights = [1.0, 1.0, 1.0, 1.0, 1.5, 2.0, 1.5, 1.0, 1.0, 1.0, 1.5, 2.5]
    
    # Pilih bulan berdasarkan bobot
    chosen_month = random.choices(range(1, 13), weights=month_weights, k=1)[0]
    
    # Ganti bulan dari tanggal yang di-generate
    try:
        date = date.replace(month=chosen_month)
    except ValueError:
        # Menangani kasus seperti 31 Februari
        date = date.replace(month=chosen_month, day=1)
        
    return date

def generate_master_data(config):
    """Menghasilkan data master (Categories, Suppliers, Warehouses, Products)."""
    
    vols = config['volumes']
    settings = config['settings']
    
    # 1. Categories
    print("Generating Categories...")
    categories = []
    for i in tqdm(range(vols['categories']), desc="Categories"):
        categories.append({
            'category_id': i + 1,
            'name': fake.unique.bs(),
            'description': fake.text(max_nb_chars=100)
        })
    df_categories = pd.DataFrame(categories)
    
    # 2. Suppliers
    print("Generating Suppliers...")
    suppliers = []
    for i in tqdm(range(vols['suppliers']), desc="Suppliers"):
        suppliers.append({
            'supplier_id': i + 1,
            'name': fake.company(),
            'contact_person': fake.name(),
            'email': fake.unique.email(),
            'phone': fake.phone_number(),
            'address': fake.address()
        })
    df_suppliers = pd.DataFrame(suppliers)
    
    # 3. Warehouses
    print("Generating Warehouses...")
    warehouses = []
    for i in tqdm(range(vols['warehouses']), desc="Warehouses"):
        warehouses.append({
            'warehouse_id': i + 1,
            'name': f"Gudang {fake.city()}",
            'location_code': fake.unique.postcode(),
            'address': fake.address()
        })
    df_warehouses = pd.DataFrame(warehouses)
    
    # 4. Products
    print("Generating Products...")
    products = []
    category_ids = df_categories['category_id'].tolist()
    supplier_ids = df_suppliers['supplier_id'].tolist()
    
    for i in tqdm(range(vols['products']), desc="Products"):
        products.append({
            'product_id': i + 1,
            'sku': fake.unique.ean(length=13),
            'name': fake.bs(), # Perbaikan dari error Faker
            'description': fake.text(max_nb_chars=150),
            'category_id': random.choice(category_ids),
            'supplier_id': random.choice(supplier_ids)
        })
    df_products = pd.DataFrame(products)
    
    # Menerapkan Aturan 80/20 (Pareto)
    num_hot_products = int(vols['products'] * settings['pareto_split'])
    hot_product_ids = df_products['product_id'].sample(n=num_hot_products).tolist()
    
    print(f"Master data generated. {len(hot_product_ids)} products ditandai sebagai 'hot products'.")
    
    return {
        'categories': df_categories,
        'suppliers': df_suppliers,
        'warehouses': df_warehouses,
        'products': df_products
    }, hot_product_ids

def generate_orders(config, master_data, hot_product_ids):
    """Menghasilkan Purchase Orders (PO) dan Sales Orders (SO) beserta detailnya."""
    
    vols = config['volumes']
    settings = config['settings']
    
    product_ids = master_data['products']['product_id'].tolist()
    supplier_ids = master_data['suppliers']['supplier_id'].tolist()
    warehouse_ids = master_data['warehouses']['warehouse_id'].tolist()
    
    # 1. Purchase Orders (PO)
    print("Generating Purchase Orders...")
    purchase_orders = []
    po_details = []
    po_detail_id_counter = 1
    
    for i in tqdm(range(vols['purchase_orders']), desc="Purchase Orders"):
        po_id = i + 1
        purchase_orders.append({
            'po_id': po_id,
            'supplier_id': random.choice(supplier_ids),
            'warehouse_id': random.choice(warehouse_ids),
            'order_date': get_seasonal_date(settings['start_date'], settings['end_date']).date(),
            'status': random.choices(['PENDING', 'PROCESSING', 'SHIPPED', 'COMPLETED', 'CANCELLED'], weights=[0.1, 0.1, 0.1, 0.6, 0.1], k=1)[0]
        })
        
        # Perbaikan PO (Unique constraint)
        num_details = np.random.poisson(vols['po_details_avg_per_po'] - 1) + 1
        num_details = min(num_details, len(product_ids))
        
        chosen_product_ids = random.sample(product_ids, k=num_details)
        
        for product_id in chosen_product_ids:
            po_details.append({
                'po_detail_id': po_detail_id_counter,
                'po_id': po_id,
                'product_id': product_id,
                'quantity': random.randint(50, 500),
                'unit_price': round(random.uniform(5000, 500000), 2)
            })
            po_detail_id_counter += 1
            
    df_po = pd.DataFrame(purchase_orders)
    df_po_details = pd.DataFrame(po_details)
    print(f"Generated {len(df_po)} POs and {len(df_po_details)} PO Details.")

    # 2. Sales Orders (SO)
    print("Generating Sales Orders...")
    sales_orders = []
    so_details = []
    so_detail_id_counter = 1
    
    other_product_ids = list(set(product_ids) - set(hot_product_ids))
    
    for i in tqdm(range(vols['sales_orders']), desc="Sales Orders"):
        so_id = i + 1
        sales_orders.append({
            'so_id': so_id,
            'customer_name': fake.name(),
            'order_date': get_seasonal_date(settings['start_date'], settings['end_date']).date(),
            'status': random.choices(['PENDING', 'PROCESSING', 'SHIPPED', 'COMPLETED', 'CANCELLED'], weights=[0.1, 0.1, 0.1, 0.6, 0.1], k=1)[0],
            'shipping_address': fake.address()
        })
        
        # Perbaikan SO (Unique constraint)
        num_details = np.random.poisson(vols['so_details_avg_per_so'] - 1) + 1
        max_combinations = len(product_ids) * len(warehouse_ids)
        num_details = min(num_details, max_combinations)
        
        used_combos = set()
        
        for _ in range(num_details):
            tries = 0
            while tries < 10:
                if random.random() < settings['pareto_volume']:
                    product_id = random.choice(hot_product_ids)
                else:
                    product_id = random.choice(other_product_ids)
                
                warehouse_id = random.choice(warehouse_ids)
                
                if (product_id, warehouse_id) not in used_combos:
                    used_combos.add((product_id, warehouse_id))
                    so_details.append({
                        'so_detail_id': so_detail_id_counter,
                        'so_id': so_id,
                        'product_id': product_id,
                        'warehouse_id': warehouse_id,
                        'quantity': random.randint(1, 10),
                        'unit_price': round(random.uniform(10000, 1000000), 2)
                    })
                    so_detail_id_counter += 1
                    break
                
                tries += 1
            
    df_so = pd.DataFrame(sales_orders)
    df_so_details = pd.DataFrame(so_details)
    print(f"Generated {len(df_so)} SOs and {len(df_so_details)} SO Details (applying 80/20 rule).")
    
    return {
        'purchase_orders': df_po,
        'purchase_order_details': df_po_details,
        'sales_orders': df_so,
        'sales_order_details': df_so_details
    }

def generate_stock_movements(config, master_data, orders_data, hot_product_ids):
    """
    Menghasilkan data stock_movements.
    Ini adalah inti logika, memastikan data realistis.
    """
    
    print("Generating Stock Movements...")
    vols = config['volumes']
    settings = config['settings']
    
    product_ids = master_data['products']['product_id'].tolist()
    warehouse_ids = master_data['warehouses']['warehouse_id'].tolist()
    po_ids = orders_data['purchase_orders']['po_id'].tolist()
    so_ids = orders_data['sales_orders']['so_id'].tolist()
    other_product_ids = list(set(product_ids) - set(hot_product_ids))
    
    movements = []
    
    # Perbaikan 'movement_id' (Unique constraint)
    movement_id_counter = 1 
    
    for i in tqdm(range(vols['stock_movements']), desc="Stock Movements"):
        if random.random() < settings['pareto_volume']:
            product_id = random.choice(hot_product_ids)
        else:
            product_id = random.choice(other_product_ids)
            
        movement_type = random.choices(
            ['IN', 'OUT', 'TRANSFER', 'ADJUSTMENT', 'RETURN'], 
            weights=[0.35, 0.45, 0.1, 0.05, 0.05], 
            k=1
        )[0]
        
        reference_type = None
        reference_id = None
        quantity = 0
        
        if movement_type == 'IN':
            quantity = random.randint(50, 500)
            reference_type = 'PURCHASE_ORDER'
            reference_id = random.choice(po_ids)
        elif movement_type == 'OUT':
            quantity = -random.randint(1, 10) 
            reference_type = 'SALES_ORDER'
            reference_id = random.choice(so_ids)
        elif movement_type == 'TRANSFER':
            quantity = -random.randint(1, 50) 
            reference_type = 'STOCK_TRANSFER'
            reference_id = movement_id_counter 
            
            movements.append({
                'movement_id': movement_id_counter, 
                'product_id': product_id,
                'warehouse_id': random.choice(warehouse_ids),
                'movement_type': 'TRANSFER',
                'quantity': quantity,
                'reference_type': reference_type,
                'reference_id': reference_id,
                'movement_date': get_seasonal_date(settings['start_date'], settings['end_date']),
                'notes': 'Transfer Out'
            })
            movement_id_counter += 1 
            
            from_warehouse_id = movements[-1]['warehouse_id']
            to_warehouse_id = random.choice([w for w in warehouse_ids if w != from_warehouse_id])
            
            movements.append({
                'movement_id': movement_id_counter, 
                'product_id': product_id,
                'warehouse_id': to_warehouse_id,
                'movement_type': 'TRANSFER',
                'quantity': -quantity, 
                'reference_type': reference_type,
                'reference_id': reference_id,
                'movement_date': movements[-1]['movement_date'] + timedelta(minutes=30),
                'notes': 'Transfer In'
            })
            movement_id_counter += 1 
            
            continue 
            
        elif movement_type == 'ADJUSTMENT':
            quantity = random.randint(-5, 5)
            if quantity == 0: quantity = 1
            reference_type = 'MANUAL_ADJUSTMENT'
            reference_id = None
        elif movement_type == 'RETURN':
            quantity = random.randint(1, 3)
            reference_type = 'SALES_ORDER'
            reference_id = random.choice(so_ids)

        movements.append({
            'movement_id': movement_id_counter,
            'product_id': product_id,
            'warehouse_id': random.choice(warehouse_ids),
            'movement_type': movement_type,
            'quantity': quantity,
            'reference_type': reference_type,
            'reference_id': reference_id,
            'movement_date': get_seasonal_date(settings['start_date'], settings['end_date']),
            'notes': fake.text(max_nb_chars=50)
        })
        movement_id_counter += 1 

    df_movements = pd.DataFrame(movements)
    
    # --- PERBAIKAN LOGIKA 'DATA QUALITY ISSUE' DIMULAI DI SINI ---
    print(f"Injecting {settings['dq_issue_percent']*100}% data quality issues...")
    n_issues = int(len(df_movements) * settings['dq_issue_percent'])
    issue_indices = df_movements.sample(n=n_issues).index
    
    # Ganti 'missing_id' dengan 'bad_reference_id'
    dq_issue_types = ['bad_reference_id', 'invalid_qty', 'future_date']
    
    for idx in tqdm(issue_indices, desc="Injecting DQ Issues"):
        issue_type = random.choice(dq_issue_types)
        
        if issue_type == 'bad_reference_id':
            # Ganti 'missing_id' (yang melanggar NOT NULL)
            # dengan ID referensi yang tidak valid (tidak melanggar constraint)
            df_movements.loc[idx, 'reference_id'] = 9999999
            
        elif issue_type == 'invalid_qty':
            if df_movements.loc[idx, 'movement_type'] in ['IN', 'RETURN']:
                df_movements.loc[idx, 'quantity'] = -abs(df_movements.loc[idx, 'quantity'])
        elif issue_type == 'future_date':
            df_movements.loc[idx, 'movement_date'] = datetime.now() + timedelta(days=random.randint(30, 365))
    # --- PERBAIKAN LOGIKA 'DATA QUALITY ISSUE' BERAKHIR DI SINI ---
            
    print(f"Generated {len(df_movements)} stock movements (with DQ issues).")
    return df_movements

def calculate_current_stock(config, df_movements, master_data):
    """
    Menghitung snapshot 'stock' saat ini berdasarkan histori 'stock_movements'.
    Ini memastikan data logis.
    """
    print("Calculating current 'stock' table from movements...")
    
    # 'product_id' tidak akan pernah NULL lagi, jadi dropna() tidak diperlukan
    # tapi kita biarkan untuk keamanan
    valid_movements = df_movements.dropna(subset=['product_id'])
    
    stock = valid_movements.groupby(['product_id', 'warehouse_id'])['quantity'].sum().reset_index()
    stock = stock.rename(columns={'quantity': 'quantity_on_hand'})
    
    stock = stock[stock['quantity_on_hand'] != 0]
    
    stock['reorder_point'] = stock.apply(lambda _: random.randint(10, 50), axis=1)
    stock['safety_stock'] = stock.apply(lambda row: random.randint(5, int(row['reorder_point'])), axis=1)
    
    stock.loc[stock['quantity_on_hand'] <= stock['reorder_point'], 'quantity_on_hand'] = stock['reorder_point'] + random.randint(-5, 5)
    
    stock['product_id'] = stock['product_id'].astype(int)
    
    all_combinations = pd.MultiIndex.from_product([
        master_data['products']['product_id'],
        master_data['warehouses']['warehouse_id']
    ], names=['product_id', 'warehouse_id']).to_frame(index=False)
    
    df_stock_final = pd.merge(all_combinations, stock, on=['product_id', 'warehouse_id'], how='left')
    
    df_stock_final['quantity_on_hand'] = df_stock_final['quantity_on_hand'].fillna(0)
    df_stock_final['reorder_point'] = df_stock_final['reorder_point'].fillna(10)
    df_stock_final['safety_stock'] = df_stock_final['safety_stock'].fillna(5)
    
    int_cols = ['quantity_on_hand', 'reorder_point', 'safety_stock']
    df_stock_final[int_cols] = df_stock_final[int_cols].astype(int)

    print(f"Generated {len(df_stock_final)} current stock records.")
    
    return df_stock_final

def df_to_sql_insert(df, table_name, file_handle, chunk_size=5000):
    """Menulis DataFrame sebagai statement INSERT SQL multi-baris ke file handle."""
    
    # Perbaikan 'nan'
    df = df.astype(object)
    df = df.where(pd.notna(df), None)
    
    columns = ', '.join([f'"{col}"' for col in df.columns])
    
    print(f"    -> Writing {len(df)} rows to SQL for table {table_name}...")
    
    for i in tqdm(range(0, len(df), chunk_size), desc=f"Writing {table_name}", leave=False):
        chunk = df.iloc[i:i + chunk_size]
        
        values_list = []
        for _, row in chunk.iterrows():
            row_values = []
            for val in row:
                if val is None:
                    row_values.append("NULL")
                elif isinstance(val, (int, float)):
                    row_values.append(str(val))
                elif isinstance(val, (date, datetime, pd.Timestamp)):
                    row_values.append(f"'{val.isoformat()}'")
                else:
                    clean_val = str(val).replace("'", "''").replace("\\", "\\\\")
                    row_values.append(f"'{clean_val}'")
            values_list.append(f"({', '.join(row_values)})")
        
        if not values_list:
            continue
            
        values_string = ',\n'.join(values_list)
        insert_statement = f"INSERT INTO {table_name} ({columns})\nVALUES\n{values_string};\n\n"
        file_handle.write(insert_statement)

def save_data(data_frames, output_dir, file_format="csv"):
    """Menyimpan DataFrame ke file (CSV atau SQL Inserts)."""
    
    print(f"Saving data to '{output_dir}' as {file_format}...")
    
    if file_format == 'csv':
        for name, df in data_frames.items():
            path = Path(output_dir) / f"{name}.csv"
            print(f"  -> Saving {name}.csv ({len(df)} rows)")
            df.to_csv(path, index=False)
    
    elif file_format == 'sql':
        table_order = [
            'categories', 
            'suppliers', 
            'warehouses', 
            'products',
            'purchase_orders', 
            'purchase_order_details',
            'sales_orders', 
            'sales_order_details',
            'stock', 
            'stock_movements'
        ]
        
        sql_file_path = Path(output_dir) / "all_data.sql"
        with open(sql_file_path, 'w', encoding='utf-8') as f:
            f.write("-- Data Ekspor untuk Warehouse Stock Management\n")
            f.write("-- Dijalankan di dalam satu transaksi\n")
            f.write("BEGIN;\n\n") 
            f.write("SET session_replication_role = 'replica';\n\n")
            
            for table_name in table_order:
                if table_name in data_frames:
                    df = data_frames[table_name]
                    if not df.empty:
                        print(f"  -> Preparing SQL for {table_name}...")
                        df_to_sql_insert(df, table_name, f)
                    else:
                        print(f"  -> Skipping empty table {table_name}")
            
            f.write("\nSET session_replication_role = 'origin';\n")
            
            # --- PERBAIKAN: Setel ulang sequence generator ---
            # Setelah semua data di-load, kita perlu update sequence
            # agar 'SERIAL' PKeys tidak bertabrakan dengan data yang di-load
            f.write("\n-- Menyesuaikan sequence generator setelah data load --\n")
            f.write("SELECT setval('categories_category_id_seq', (SELECT MAX(category_id) FROM categories));\n")
            f.write("SELECT setval('suppliers_supplier_id_seq', (SELECT MAX(supplier_id) FROM suppliers));\n")
            f.write("SELECT setval('warehouses_warehouse_id_seq', (SELECT MAX(warehouse_id) FROM warehouses));\n")
            f.write("SELECT setval('products_product_id_seq', (SELECT MAX(product_id) FROM products));\n")
            f.write("SELECT setval('purchase_orders_po_id_seq', (SELECT MAX(po_id) FROM purchase_orders));\n")
            f.write("SELECT setval('purchase_order_details_po_detail_id_seq', (SELECT MAX(po_detail_id) FROM purchase_order_details));\n")
            f.write("SELECT setval('sales_orders_so_id_seq', (SELECT MAX(so_id) FROM sales_orders));\n")
            f.write("SELECT setval('sales_order_details_so_detail_id_seq', (SELECT MAX(so_detail_id) FROM sales_order_details));\n")
            f.write("SELECT setval('stock_movements_movement_id_seq', (SELECT MAX(movement_id) FROM stock_movements));\n")
            
            f.write("\nCOMMIT;\n") 
            
        print(f"\nAll SQL data written to {sql_file_path}")

    else:
        print(f"Format output '{file_format}' tidak didukung. Gunakan 'csv' or 'sql'.")

def validation_summary(data_frames):
    """Mencetak ringkasan validasi data."""
    print("\n--- Validation Summary ---")
    total_rows = 0
    for name, df in data_frames.items():
        print(f"\nTable: {name}")
        print(f"  Rows: {len(df)}")
        print(f"  Columns: {list(df.columns)}")
        if 'movement_date' in df.columns:
            try:
                min_date = df['movement_date'].min()
                max_date = df['movement_date'].max()
                print(f"  Date Range: {min_date} to {max_date}")
            except TypeError:
                print("  Date Range: (Mengandung data non-date akibat DQ issues)")
        if 'quantity' in df.columns:
            print(f"  Total Quantity: {df['quantity'].sum()}")
        total_rows += len(df)
    print("\n--------------------------")
    print(f"Total rows generated (all tables): {total_rows}")

def main():
    """Fungsi utama untuk menjalankan generator data."""
    
    config = load_config('config.yaml')
    output_dir = config['output']['directory']
    
    create_output_directory(output_dir)
    
    master_data, hot_product_ids = generate_master_data(config)
    
    orders_data = generate_orders(config, master_data, hot_product_ids)
    
    df_movements = generate_stock_movements(config, master_data, orders_data, hot_product_ids)
    
    df_stock = calculate_current_stock(config, df_movements, master_data)
    
    all_data = {
        **master_data,
        **orders_data,
        'stock_movements': df_movements,
        'stock': df_stock
    }
    
    save_data(all_data, output_dir, config['output']['format'])
    
    validation_summary(all_data)
    
    print("\nData generation complete!")
    print(f"Output files are saved in '{output_dir}' directory.")

if __name__ == "__main__":
    main()