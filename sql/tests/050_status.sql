SELECT COUNT(*) AS violations FROM raw.orders WHERE status NOT IN ('completed', 'cancelled', 'pending');
