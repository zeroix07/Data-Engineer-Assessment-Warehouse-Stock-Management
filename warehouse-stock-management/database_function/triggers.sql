-- ###############################################################
-- Task 3.5: Audit Trigger 
-- Membuat tabel audit dan trigger untuk melacak
-- perubahan manual atau tidak terduga pada tabel 'stock'.
-- ###############################################################

-- 1. Buat Tabel Audit (jika belum ada)
-- Tabel ini akan menyimpan histori perubahan PADA TABEL 'stock'
CREATE TABLE IF NOT EXISTS stock_audit_log (
    log_id BIGSERIAL PRIMARY KEY,
    changed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    operation_type VARCHAR(10) NOT NULL, -- INSERT, UPDATE, DELETE
    user_name TEXT DEFAULT CURRENT_USER,
    product_id INT,
    warehouse_id INT,
    old_quantity INT,
    new_quantity INT
);

-- 2. Buat Fungsi Trigger Audit
CREATE OR REPLACE FUNCTION audit_stock_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'UPDATE') THEN
        -- Hanya catat jika kuantitas benar-benar berubah
        IF OLD.quantity_on_hand IS DISTINCT FROM NEW.quantity_on_hand THEN
            INSERT INTO stock_audit_log (operation_type, product_id, warehouse_id, old_quantity, new_quantity)
            VALUES ('UPDATE', OLD.product_id, OLD.warehouse_id, OLD.quantity_on_hand, NEW.quantity_on_hand);
        END IF;
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        INSERT INTO stock_audit_log (operation_type, product_id, warehouse_id, old_quantity)
        VALUES ('DELETE', OLD.product_id, OLD.warehouse_id, OLD.quantity_on_hand);
        RETURN OLD;
    ELSIF (TG_OP = 'INSERT') THEN
        INSERT INTO stock_audit_log (operation_type, product_id, warehouse_id, new_quantity)
        VALUES ('INSERT', NEW.product_id, NEW.warehouse_id, NEW.quantity_on_hand);
        RETURN NEW;
    END IF;
    RETURN NULL; -- Hasil tidak relevan untuk trigger AFTER
END;
$$ LANGUAGE plpgsql;

-- 3. Terapkan Trigger ke tabel 'stock'
-- Kita gunakan trigger 'AFTER' agar kita mencatat apa yang *sebenarnya* terjadi
-- Kita juga tidak ingin trigger ini aktif saat 'record_stock_movement' berjalan,
-- karena itu akan mencatat perubahan yang *diharapkan*.
-- Trigger ini lebih untuk melacak perubahan manual/ad-hoc.

-- Hapus trigger lama jika ada, agar skrip ini idempotent
DROP TRIGGER IF EXISTS trg_stock_audit ON stock;

CREATE TRIGGER trg_stock_audit
AFTER INSERT OR UPDATE OR DELETE ON stock
FOR EACH ROW
-- Kita tambahkan kondisi WHEN agar trigger ini HANYA aktif
-- jika perubahan TIDAK berasal dari fungsi 'record_stock_movement'.
-- Ini MENGASUMSIKAN fungsi dijalankan oleh user/role tertentu,
-- atau kita bisa set GUC (misal SET session.is_bulk_load = true)
-- Untuk kesederhanaan, kita akan mencatat SEMUA perubahan.
-- Dalam skenario nyata, kita akan memfilter perubahan dari aplikasi.
-- WHEN (current_setting('session.app_user', true) IS NULL)
EXECUTE FUNCTION audit_stock_changes();


-- ###############################################################
-- BONUS: Trigger untuk 'updated_at'
-- Fungsi generik untuk memperbarui kolom 'updated_at'
-- pada tabel master (misalnya 'products')
-- ###############################################################

CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Terapkan ke tabel 'products'
DROP TRIGGER IF EXISTS trg_products_updated_at ON products;
CREATE TRIGGER trg_products_updated_at
BEFORE UPDATE ON products
FOR EACH ROW
EXECUTE FUNCTION trigger_set_updated_at();