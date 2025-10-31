-- Skrip DDL untuk Sistem Manajemen Stok Gudang
-- Dialek: PostgreSQL

-- Hapus tabel jika sudah ada (untuk idempotency)
DROP TABLE IF EXISTS sales_order_details CASCADE;
DROP TABLE IF EXISTS sales_orders CASCADE;
DROP TABLE IF EXISTS purchase_order_details CASCADE;
DROP TABLE IF EXISTS purchase_orders CASCADE;
DROP TABLE IF EXISTS stock_movements CASCADE;
DROP TABLE IF EXISTS stock CASCADE;
DROP TABLE IF EXISTS warehouses CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS suppliers CASCADE;
DROP TABLE IF EXISTS categories CASCADE;

-- Hapus tipe ENUM jika sudah ada
DROP TYPE IF EXISTS movement_type;
DROP TYPE IF EXISTS order_status;
DROP TYPE IF EXISTS reference_type;

-- --- Tipe ENUM ---
-- (Menggunakan ENUM sebagai CHECK constraint)
CREATE TYPE movement_type AS ENUM (
  'IN', 
  'OUT', 
  'TRANSFER', 
  'ADJUSTMENT', 
  'RETURN'
);

CREATE TYPE order_status AS ENUM (
  'PENDING', 
  'PROCESSING', 
  'SHIPPED', 
  'COMPLETED', 
  'CANCELLED'
);

CREATE TYPE reference_type AS ENUM (
  'PURCHASE_ORDER',
  'SALES_ORDER',
  'STOCK_TRANSFER',
  'MANUAL_ADJUSTMENT'
);


-- --- Master Data ---

-- Tabel Kategori Produk
CREATE TABLE categories (
  category_id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL UNIQUE,
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Tabel Supplier
CREATE TABLE suppliers (
  supplier_id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  contact_person VARCHAR(255),
  email VARCHAR(255) UNIQUE,
  phone VARCHAR(50),
  address TEXT,
  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Tabel Master Produk
CREATE TABLE products (
  product_id SERIAL PRIMARY KEY,
  sku VARCHAR(100) NOT NULL UNIQUE,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  category_id INT NOT NULL REFERENCES categories(category_id),
  supplier_id INT NOT NULL REFERENCES suppliers(supplier_id),
  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
  -- Audit trail akan ditangani oleh trigger (Task 3)
);

-- Tabel Gudang
CREATE TABLE warehouses (
  warehouse_id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  location_code VARCHAR(50) UNIQUE,
  address TEXT,
  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


-- --- Data Transaksional & Stok ---

-- Tabel Stok Saat Ini (Snapshot)
-- Tabel ini adalah pivot many-to-many antara produk dan gudang
CREATE TABLE stock (
  product_id INT NOT NULL REFERENCES products(product_id),
  warehouse_id INT NOT NULL REFERENCES warehouses(warehouse_id),
  quantity_on_hand INT NOT NULL DEFAULT 0,
  reorder_point INT NOT NULL DEFAULT 10,
  safety_stock INT NOT NULL DEFAULT 5,
  updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  
  -- Composite Primary Key: Satu produk unik per gudang
  -- *** INI ADALAH BARIS YANG DIPERBAIKI ***
  PRIMARY KEY (product_id, warehouse_id)
);

-- Tabel Pergerakan Stok (Log/History)
-- Ini adalah inti dari pelacakan dan audit
CREATE TABLE stock_movements (
  movement_id BIGSERIAL PRIMARY KEY,
  product_id INT NOT NULL REFERENCES products(product_id),
  warehouse_id INT NOT NULL REFERENCES warehouses(warehouse_id),
  movement_type movement_type NOT NULL,
  quantity INT NOT NULL, -- Kuantitas pergerakan (bisa positif/negatif)
  reference_type reference_type, -- Jenis referensi (PO, SO, dll)
  reference_id INT, -- ID dari PO, SO, dll.
  movement_date TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  notes TEXT,
  
  -- Constraint untuk memastikan kuantitas sesuai
  CONSTRAINT check_quantity CHECK (quantity != 0) 
);

-- Tabel Purchase Orders (PO)
CREATE TABLE purchase_orders (
  po_id SERIAL PRIMARY KEY,
  supplier_id INT NOT NULL REFERENCES suppliers(supplier_id),
  warehouse_id INT NOT NULL REFERENCES warehouses(warehouse_id), -- Gudang tujuan
  order_date DATE NOT NULL DEFAULT CURRENT_DATE,
  expected_delivery_date DATE,
  status order_status NOT NULL DEFAULT 'PENDING',
  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Tabel Detail Purchase Order
CREATE TABLE purchase_order_details (
  po_detail_id SERIAL PRIMARY KEY,
  po_id INT NOT NULL REFERENCES purchase_orders(po_id) ON DELETE CASCADE,
  product_id INT NOT NULL REFERENCES products(product_id),
  quantity INT NOT NULL,
  unit_price DECIMAL(10, 2) NOT NULL,
  
  CONSTRAINT check_po_quantity CHECK (quantity > 0),
  -- Constraint: 1 produk unik per PO
  UNIQUE (po_id, product_id)
);

-- Tabel Sales Orders (SO)
CREATE TABLE sales_orders (
  so_id SERIAL PRIMARY KEY,
  customer_name VARCHAR(255), -- Asumsi tidak ada tabel customer
  order_date DATE NOT NULL DEFAULT CURRENT_DATE,
  status order_status NOT NULL DEFAULT 'PENDING',
  shipping_address TEXT,
  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Tabel Detail Sales Order
CREATE TABLE sales_order_details (
  so_detail_id SERIAL PRIMARY KEY,
  so_id INT NOT NULL REFERENCES sales_orders(so_id) ON DELETE CASCADE,
  product_id INT NOT NULL REFERENCES products(product_id),
  -- Perlu tahu barang diambil dari gudang mana
  warehouse_id INT NOT NULL REFERENCES warehouses(warehouse_id),
  quantity INT NOT NULL,
  unit_price DECIMAL(10, 2) NOT NULL,

  CONSTRAINT check_so_quantity CHECK (quantity > 0),
  -- Constraint: 1 produk unik per SO (dari gudang yg sama)
  UNIQUE (so_id, product_id, warehouse_id)
);


-- --- Indexes untuk Optimasi Query ---

-- Index pada tabel products
CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_products_name ON products(name);
CREATE INDEX idx_products_category_id ON products(category_id);
CREATE INDEX idx_products_supplier_id ON products(supplier_id);

-- Index pada tabel stock
CREATE INDEX idx_stock_warehouse_id ON stock(warehouse_id);

-- Index pada tabel stock_movements (sangat penting untuk analytics)
CREATE INDEX idx_movements_product_id ON stock_movements(product_id);
CREATE INDEX idx_movements_warehouse_id ON stock_movements(warehouse_id);
CREATE INDEX idx_movements_movement_date ON stock_movements(movement_date);
CREATE INDEX idx_movements_reference ON stock_movements(reference_type, reference_id);

-- Index pada tabel PO
CREATE INDEX idx_po_supplier_id ON purchase_orders(supplier_id);
CREATE INDEX idx_po_warehouse_id ON purchase_orders(warehouse_id);

-- Index pada tabel PO Details
CREATE INDEX idx_po_details_product_id ON purchase_order_details(product_id);

-- Index pada tabel SO
CREATE INDEX idx_so_order_date ON sales_orders(order_date);

-- Index pada tabel SO Details
CREATE INDEX idx_so_details_product_id ON sales_order_details(product_id);
CREATE INDEX idx_so_details_warehouse_id ON sales_order_details(warehouse_id);

COMMIT;