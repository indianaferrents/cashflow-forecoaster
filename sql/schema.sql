CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    registration_date DATE,
    region VARCHAR(50),
    segment VARCHAR(50)
);

CREATE TABLE transactions (
    transaction_id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    transaction_date DATE,
    amount DECIMAL(10,2),
    payment_method VARCHAR(20),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE cashflow (
    date DATE PRIMARY KEY,
    total_revenue DECIMAL(12,2)
);