SELECT COUNT(*) AS violations FROM raw.items
WHERE quantity <= 0 OR unit_price < 0 OR quantity * unit_price < 0;
