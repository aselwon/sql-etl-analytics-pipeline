SELECT
 (SELECT COUNT(*) FROM (SELECT order_id FROM raw.orders GROUP BY order_id HAVING COUNT(*) > 1) duplicates)
 + (SELECT COUNT(*) FROM (SELECT customer_id FROM raw.customers GROUP BY customer_id HAVING COUNT(*) > 1) duplicates)
 AS violations;
