SELECT
 (SELECT COUNT(*) FROM raw.customers WHERE customer_id IS NULL OR customer_name IS NULL OR signup_date IS NULL)
 + (SELECT COUNT(*) FROM raw.orders WHERE order_id IS NULL OR customer_id IS NULL OR order_date IS NULL OR status IS NULL)
 + (SELECT COUNT(*) FROM raw.items WHERE order_id IS NULL OR product_id IS NULL OR product_name IS NULL OR quantity IS NULL OR unit_price IS NULL)
 AS violations;
