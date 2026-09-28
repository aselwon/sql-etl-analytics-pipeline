CREATE SCHEMA IF NOT EXISTS raw;
-- Keep business constraints in explicit DQ tests so broken dumps are inspectable.
CREATE TABLE IF NOT EXISTS raw.customers (
    customer_id bigint, customer_name text, signup_date date
);
CREATE TABLE IF NOT EXISTS raw.orders (
    order_id bigint, customer_id bigint, order_date date, status text
);
CREATE TABLE IF NOT EXISTS raw.items (
    order_id bigint, product_id bigint, product_name text,
    quantity integer, unit_price numeric(12,2)
);
