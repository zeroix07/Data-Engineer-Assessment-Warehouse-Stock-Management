-- Pastikan Anda terhubung ke database Anda
-- \c nama_database_anda

BEGIN;
RAISE NOTICE '--- Memulai Test Cases untuk Task 3 ---';

-- Pilih 1 produk dan 2 gudang untuk pengujian
-- (Gunakan ID yang Anda tahu ada di data Anda)
DEFINE test_product_id 10;
DEFINE test_warehouse_id_1 1;
DEFINE test_warehouse_id_2 2;


-- ###############################################################
-- Test 3.1: record_stock_movement
-- ###############################################################
RAISE NOTICE 'Test 3.1: Menjalankan record_stock_movement (ADJUSTMENT)...';

-- Cek stok awal
SELECT quantity_on_hand FROM stock WHERE product_id = :test_product_id AND warehouse_id = :test_warehouse_id_1;

-- Lakukan penyesuaian (misal: stok opname) +15
SELECT record_stock_movement(
    p_product_id := :test_product_id,
    p_warehouse_id := :test_warehouse_id_1,
    p_movement_type := 'ADJUSTMENT',
    p_quantity := 15,
    p_reference_type := 'MANUAL_ADJUSTMENT',
    p_reference_id := NULL,
    p_notes := 'Test case 3.1: Penyesuaian stok opname'
) AS adjustment_result;

-- Cek stok akhir
RAISE NOTICE 'Stok setelah penyesuaian:';
SELECT quantity_on_hand FROM stock WHERE product_id = :test_product_id AND warehouse_id = :test_warehouse_id_1;

-- Cek log pergerakan
SELECT * FROM stock_movements 
WHERE product_id = :test_product_id 
  AND warehouse_id = :test_warehouse_id_1 
  AND movement_type = 'ADJUSTMENT' 
ORDER BY movement_id DESC LIMIT 1;


-- ###############################################################
-- Test 3.2: transfer_stock
-- ###############################################################
RAISE NOTICE 'Test 3.2: Menjalankan transfer_stock...';

-- Cek stok awal di kedua gudang
RAISE NOTICE 'Stok awal Gudang 1:';
SELECT quantity_on_hand FROM stock WHERE product_id = :test_product_id AND warehouse_id = :test_warehouse_id_1;
RAISE NOTICE 'Stok awal Gudang 2:';
SELECT quantity_on_hand FROM stock WHERE product_id = :test_product_id AND warehouse_id = :test_warehouse_id_2;

-- Lakukan transfer 5 unit dari G1 ke G2
SELECT transfer_stock(
    p_product_id := :test_product_id,
    p_from_warehouse_id := :test_warehouse_id_1,
    p_to_warehouse_id := :test_warehouse_id_2,
    p_quantity := 5,
    p_notes := 'Test case 3.2: Transfer antar gudang'
) AS transfer_result;

-- Cek stok akhir di kedua gudang
RAISE NOTICE 'Stok akhir Gudang 1 (setelah transfer):';
SELECT quantity_on_hand FROM stock WHERE product_id = :test_product_id AND warehouse_id = :test_warehouse_id_1;
RAISE NOTICE 'Stok akhir Gudang 2 (setelah transfer):';
SELECT quantity_on_hand FROM stock WHERE product_id = :test_product_id AND warehouse_id = :test_warehouse_id_2;


-- ###############################################################
-- Test 3.3: check_reorder_points
-- ###############################################################
RAISE NOTICE 'Test 3.3: Menjalankan check_reorder_points...';

-- Tampilkan 10 produk teratas yang perlu di-reorder
SELECT * FROM check_reorder_points(NULL) LIMIT 10;

-- Tampilkan produk yang perlu reorder HANYA untuk gudang 1
RAISE NOTICE 'Test 3.3: Reorder untuk Gudang 1 saja...';
SELECT * FROM check_reorder_points(:test_warehouse_id_1) LIMIT 10;


-- ###############################################################
-- Test 3.4: calculate_stock_value
-- ###############################################################
RAISE NOTICE 'Test 3.4: Menjalankan calculate_stock_value (AVG)...';

-- Tampilkan 10 produk dengan nilai stok tertinggi
SELECT * FROM calculate_stock_value('AVG')
ORDER BY total_value DESC
LIMIT 10;


-- ###############################################################
-- Test 3.5: Audit Trigger
-- ###############################################################
RAISE NOTICE 'Test 3.5: Menjalankan test Audit Trigger...';

-- Lakukan UPDATE manual (nakal) pada tabel stock
RAISE NOTICE 'Melakukan UPDATE manual pada stok...';
UPDATE stock 
SET quantity_on_hand = 9999
WHERE product_id = :test_product_id AND warehouse_id = :test_warehouse_id_1;

-- Cek tabel audit log
RAISE NOTICE 'Cek isi tabel stock_audit_log:';
SELECT * FROM stock_audit_log
WHERE product_id = :test_product_id AND warehouse_id = :test_warehouse_id_1
ORDER BY log_id DESC
LIMIT 1;


RAISE NOTICE '--- Test Cases Selesai ---';
RAISE NOTICE '--- ROLLBACK SEMUA PERUBAHAN TEST ---';
ROLLBACK;