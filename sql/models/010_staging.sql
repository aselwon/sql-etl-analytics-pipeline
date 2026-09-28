CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS marts;
-- Snapshot tables prevent a later bad ingest from changing published analytics.
DROP TABLE IF EXISTS staging.customers, staging.orders, staging.items CASCADE;
CREATE TABLE staging.customers AS SELECT * FROM raw.customers;
CREATE TABLE staging.orders AS SELECT * FROM raw.orders;
CREATE TABLE staging.items AS
SELECT *, quantity * unit_price AS line_revenue FROM raw.items;
