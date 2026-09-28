CREATE OR REPLACE VIEW marts.order_revenue AS
SELECT o.order_id, o.customer_id, o.order_date, SUM(i.line_revenue) AS revenue
FROM staging.orders o JOIN staging.items i USING (order_id)
WHERE o.status = 'completed'
GROUP BY o.order_id, o.customer_id, o.order_date;

CREATE OR REPLACE VIEW marts.daily_revenue AS
SELECT order_date AS day, SUM(revenue) AS revenue, COUNT(*) AS orders
FROM marts.order_revenue GROUP BY order_date;

CREATE OR REPLACE VIEW marts.top_products AS
SELECT i.product_id, MIN(i.product_name) AS product_name,
       SUM(i.quantity) AS units_sold, SUM(i.line_revenue) AS revenue
FROM staging.items i JOIN staging.orders o USING (order_id)
WHERE o.status = 'completed'
GROUP BY i.product_id;

-- Cohort month is the first completed purchase, not signup. Activity is a
-- distinct purchasing customer per calendar month (month zero is 100%).
CREATE OR REPLACE VIEW marts.cohort_retention AS
WITH first_purchase AS (
    SELECT customer_id, DATE_TRUNC('month', MIN(order_date))::date AS cohort_month
    FROM marts.order_revenue GROUP BY customer_id
), sizes AS (
    SELECT cohort_month, COUNT(*) AS cohort_size FROM first_purchase GROUP BY cohort_month
), activity AS (
    SELECT DISTINCT f.customer_id, f.cohort_month,
           DATE_TRUNC('month', o.order_date)::date AS activity_month
    FROM first_purchase f JOIN marts.order_revenue o USING (customer_id)
)
SELECT a.cohort_month,
       (EXTRACT(year FROM a.activity_month)::int - EXTRACT(year FROM a.cohort_month)::int) * 12
        + EXTRACT(month FROM a.activity_month)::int - EXTRACT(month FROM a.cohort_month)::int AS month_number,
       s.cohort_size, COUNT(*) AS active_customers,
       ROUND(COUNT(*)::numeric / s.cohort_size, 4) AS retention_rate
FROM activity a JOIN sizes s USING (cohort_month)
GROUP BY a.cohort_month, a.activity_month, s.cohort_size;

CREATE OR REPLACE VIEW marts.kpis AS
WITH buyers AS (
    SELECT customer_id, COUNT(*) AS purchases FROM marts.order_revenue GROUP BY customer_id
)
SELECT COALESCE(SUM(revenue), 0) AS revenue, COUNT(*) AS completed_orders,
       COUNT(DISTINCT customer_id) AS purchasing_customers,
       COALESCE(ROUND(AVG(revenue), 2), 0) AS average_order_value,
       (SELECT COUNT(*) FROM buyers WHERE purchases > 1) AS repeat_customers,
       (SELECT COALESCE(SUM(units_sold), 0) FROM marts.top_products) AS units_sold
FROM marts.order_revenue;
