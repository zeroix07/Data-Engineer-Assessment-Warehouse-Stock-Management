-- ###############################################################
-- Task 3.1: Stock Movement Function [cite: 91]
-- Fungsi ini adalah inti dari sistem. Fungsi ini:
-- 1. Mencatat pergerakan ke tabel 'stock_movements'.
-- 2. Memperbarui (UPSERT) tabel snapshot 'stock'.
-- ###############################################################
CREATE OR REPLACE FUNCTION record_stock_movement(
    p_product_id INT,
    p_warehouse_id INT,
    p_movement_type movement_type,
    p_quantity INT,
    p_reference_type reference_type,
    p_reference_id INT,
    p_notes TEXT
) 
RETURNS JSON AS $$
DECLARE
    v_current_stock INT;
    v_new_stock INT;
    v_movement_id BIGINT;
BEGIN
    -- 1. Masukkan ke tabel log (source of truth)
    INSERT INTO stock_movements (
        product_id, warehouse_id, movement_type, 
        quantity, reference_type, reference_id, notes, movement_date
    )
    VALUES (
        p_product_id, p_warehouse_id, p_movement_type, 
        p_quantity, p_reference_type, p_reference_id, p_notes, CURRENT_TIMESTAMP
    )
    RETURNING movement_id INTO v_movement_id;

    -- 2. Perbarui tabel snapshot 'stock' (UPSERT)
    -- Ini menangani kasus jika produk belum pernah ada di gudang ini
    INSERT INTO stock (product_id, warehouse_id, quantity_on_hand, updated_at)
    VALUES (p_product_id, p_warehouse_id, p_quantity, CURRENT_TIMESTAMP)
    ON CONFLICT (product_id, warehouse_id)
    DO UPDATE SET 
        quantity_on_hand = stock.quantity_on_hand + p_quantity,
        updated_at = CURRENT_TIMESTAMP
    RETURNING quantity_on_hand INTO v_new_stock;

    RETURN json_build_object(
        'status', 'success',
        'movement_id', v_movement_id,
        'product_id', p_product_id,
        'warehouse_id', p_warehouse_id,
        'new_quantity_on_hand', v_new_stock
    );

EXCEPTION
    WHEN OTHERS THEN
        RETURN json_build_object(
            'status', 'error',
            'message', SQLERRM
        );
END;
$$ LANGUAGE plpgsql;


-- ###############################################################
-- Task 3.2: Stock Transfer Function [cite: 101]
-- Fungsi ini meng-orkestrasi transfer antar gudang dengan
-- memanggil `record_stock_movement` dua kali.
-- ###############################################################
CREATE OR REPLACE FUNCTION transfer_stock(
    p_product_id INT,
    p_from_warehouse_id INT,
    p_to_warehouse_id INT,
    p_quantity INT,
    p_notes TEXT
)
RETURNS JSON AS $$
DECLARE
    v_current_stock INT;
    v_transfer_notes_out TEXT;
    v_transfer_notes_in TEXT;
    v_response_out JSON;
    v_response_in JSON;
BEGIN
    -- Validasi 1: Kuantitas harus positif
    IF p_quantity <= 0 THEN
        RETURN json_build_object('status', 'error', 'message', 'Kuantitas transfer harus lebih besar dari 0');
    END IF;

    -- Validasi 2: Gudang asal dan tujuan tidak boleh sama
    IF p_from_warehouse_id = p_to_warehouse_id THEN
        RETURN json_build_object('status', 'error', 'message', 'Gudang asal dan tujuan tidak boleh sama');
    END IF;

    -- Validasi 3: Cek ketersediaan stok di gudang asal
    SELECT quantity_on_hand INTO v_current_stock
    FROM stock
    WHERE product_id = p_product_id AND warehouse_id = p_from_warehouse_id;

    IF v_current_stock IS NULL OR v_current_stock < p_quantity THEN
        RETURN json_build_object(
            'status', 'error', 
            'message', 'Stok tidak mencukupi di gudang asal',
            'current_stock', COALESCE(v_current_stock, 0)
        );
    END IF;

    -- Buat catatan transfer
    v_transfer_notes_out := 'Transfer OUT ke ' || p_to_warehouse_id || '. ' || COALESCE(p_notes, '');
    v_transfer_notes_in := 'Transfer IN dari ' || p_from_warehouse_id || '. ' || COALESCE(p_notes, '');

    -- Panggil fungsi record_stock_movement (OUT dari gudang asal)
    -- Kuantitas adalah negatif
    v_response_out := record_stock_movement(
        p_product_id, p_from_warehouse_id, 'TRANSFER', 
        -p_quantity, 'STOCK_TRANSFER', NULL, v_transfer_notes_out
    );

    -- Panggil fungsi record_stock_movement (IN ke gudang tujuan)
    -- Kuantitas adalah positif
    v_response_in := record_stock_movement(
        p_product_id, p_to_warehouse_id, 'TRANSFER', 
        p_quantity, 'STOCK_TRANSFER', (v_response_out->>'movement_id')::BIGINT, v_transfer_notes_in
    );

    RETURN json_build_object(
        'status', 'success',
        'transfer_out', v_response_out,
        'transfer_in', v_response_in
    );

EXCEPTION
    WHEN OTHERS THEN
        RETURN json_build_object(
            'status', 'error',
            'message', SQLERRM
        );
END;
$$ LANGUAGE plpgsql;


-- ###############################################################
-- Task 3.3: Reorder Alert Function [cite: 115]
-- Fungsi ini mengembalikan tabel produk yang stoknya
-- telah mencapai atau di bawah reorder point.
-- ###############################################################
CREATE OR REPLACE FUNCTION check_reorder_points(
    p_warehouse_id INT DEFAULT NULL
) 
RETURNS TABLE (
    product_id INT,
    sku VARCHAR,
    product_name VARCHAR,
    warehouse_id INT,
    warehouse_name VARCHAR,
    quantity_on_hand INT,
    reorder_point INT,
    deficit INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.product_id,
        p.sku,
        p.name AS product_name,
        s.warehouse_id,
        w.name AS warehouse_name,
        s.quantity_on_hand,
        s.reorder_point,
        (s.reorder_point - s.quantity_on_hand) AS deficit
    FROM stock s
    JOIN products p ON s.product_id = p.product_id
    JOIN warehouses w ON s.warehouse_id = w.warehouse_id
    WHERE 
        s.quantity_on_hand <= s.reorder_point
        AND s.quantity_on_hand > 0 -- Asumsi kita tidak reorder yang stoknya 0
        -- Filter berdasarkan warehouse jika parameter diberikan
        AND (p_warehouse_id IS NULL OR s.warehouse_id = p_warehouse_id);
END;
$$ LANGUAGE plpgsql;


-- ###############################################################
-- Task 3.4: Stock Valuation Function [cite: 118]
-- Fungsi ini menghitung nilai total stok berdasarkan
-- metode valuasi yang dipilih.
-- ###############################################################
CREATE OR REPLACE FUNCTION calculate_stock_value(
    p_method VARCHAR(10) -- 'FIFO', 'LIFO', 'AVG'
) 
RETURNS TABLE (
    product_id INT,
    product_name VARCHAR,
    total_quantity BIGINT,
    weighted_avg_cost DECIMAL,
    total_value DECIMAL
) AS $$
BEGIN
    IF p_method = 'AVG' THEN
        -- Metode AVG: Menggunakan Weighted Average Cost dari semua PO yang 'COMPLETED'
        RETURN QUERY
        WITH 
        -- 1. Hitung biaya rata-rata tertimbang per produk dari PO yang selesai
        product_avg_cost AS (
            SELECT
                pod.product_id,
                -- Mencegah pembagian dengan nol
                CASE 
                    WHEN SUM(pod.quantity) = 0 THEN 0
                    ELSE SUM(pod.quantity * pod.unit_price) / SUM(pod.quantity)
                END AS avg_cost
            FROM purchase_order_details pod
            JOIN purchase_orders po ON pod.po_id = po.po_id
            WHERE po.status = 'COMPLETED'
            GROUP BY pod.product_id
        ),
        -- 2. Agregat stok total per produk di semua gudang
        total_stock_per_product AS (
            SELECT
                s.product_id,
                SUM(s.quantity_on_hand) AS total_quantity
            FROM stock s
            GROUP BY s.product_id
        )
        -- 3. Gabungkan semua
        SELECT 
            ts.product_id,
            p.name AS product_name,
            ts.total_quantity,
            COALESCE(pac.avg_cost, 0.00)::DECIMAL(12, 2) AS weighted_avg_cost,
            (ts.total_quantity * COALESCE(pac.avg_cost, 0.00))::DECIMAL(16, 2) AS total_value
        FROM total_stock_per_product ts
        JOIN products p ON ts.product_id = p.product_id
        LEFT JOIN product_avg_cost pac ON ts.product_id = pac.product_id
        WHERE ts.total_quantity > 0;

    ELSE
        -- Metode FIFO/LIFO sangat kompleks dalam SQL murni dan
        -- biasanya ditangani di lapisan aplikasi atau ETL.
        -- Kita lempar error jika metode tsb dipilih.
        RAISE EXCEPTION 'Metode % belum diimplementasikan. Gunakan ''AVG''.', p_method;
    END IF;
END;
$$ LANGUAGE plpgsql;