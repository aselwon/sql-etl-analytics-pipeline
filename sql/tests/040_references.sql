SELECT
 (SELECT COUNT(*) FROM raw.orders o WHERE NOT EXISTS (SELECT 1 FROM raw.customers c WHERE c.customer_id = o.customer_id))
 + (SELECT COUNT(*) FROM raw.items i WHERE NOT EXISTS (SELECT 1 FROM raw.orders o WHERE o.order_id = i.order_id))
 + (SELECT COUNT(*) FROM raw.orders o WHERE NOT EXISTS (SELECT 1 FROM raw.items i WHERE i.order_id = o.order_id))
 AS violations;
