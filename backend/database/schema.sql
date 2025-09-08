-- ==============================
-- Core Financial Tables
-- ==============================

CREATE TABLE general_ledger (
    transaction_id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    account VARCHAR(100) NOT NULL, -- Revenue, COGS, OPEX, Tax, etc.
    store_id INT NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'PKR'
);

CREATE TABLE revenue (
    invoice_id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    store_id INT NOT NULL,
    product_category VARCHAR(100) NOT NULL,
    units_sold INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    total_revenue DECIMAL(15,2) NOT NULL
);

CREATE TABLE expenses (
    expense_id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    store_id INT NOT NULL,
    expense_category VARCHAR(100) NOT NULL, -- Rent, Salaries, Utilities, etc.
    amount DECIMAL(15,2) NOT NULL,
    approved_by VARCHAR(100)
);

CREATE TABLE pnl_statement (
    pnl_id SERIAL PRIMARY KEY,
    month DATE NOT NULL,
    store_id INT NOT NULL,
    revenue DECIMAL(15,2) NOT NULL,
    cogs DECIMAL(15,2) NOT NULL,
    gross_profit DECIMAL(15,2) NOT NULL,
    opex DECIMAL(15,2) NOT NULL,
    net_profit DECIMAL(15,2) NOT NULL,
    profit_margin DECIMAL(5,2) NOT NULL
);

CREATE TABLE cashflow (
    entry_id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    category VARCHAR(50) NOT NULL, -- Operating, Investing, Financing
    description TEXT,
    cash_in DECIMAL(15,2) DEFAULT 0,
    cash_out DECIMAL(15,2) DEFAULT 0,
    net_cashflow DECIMAL(15,2) NOT NULL
);

CREATE TABLE balance_sheet (
    bs_id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    store_id INT NOT NULL,
    assets_current DECIMAL(15,2),
    assets_fixed DECIMAL(15,2),
    liabilities_current DECIMAL(15,2),
    liabilities_longterm DECIMAL(15,2),
    equity DECIMAL(15,2)
);

CREATE TABLE cfo_kpis (
    kpi_id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    metric VARCHAR(100) NOT NULL, -- EBITDA, ROI, etc.
    value DECIMAL(15,2) NOT NULL
);

-- ==============================
-- Graph-Friendly Extensions
-- ==============================

CREATE TABLE region_sales (
    region_id SERIAL PRIMARY KEY,
    region_name VARCHAR(100) NOT NULL,
    date DATE NOT NULL,
    store_count INT NOT NULL,
    total_revenue DECIMAL(15,2) NOT NULL,
    total_units_sold INT NOT NULL,
    avg_ticket_size DECIMAL(10,2) NOT NULL
);

CREATE TABLE category_performance (
    category_id SERIAL PRIMARY KEY,
    product_category VARCHAR(100) NOT NULL,
    month DATE NOT NULL,
    units_sold INT NOT NULL,
    revenue DECIMAL(15,2) NOT NULL,
    gross_margin DECIMAL(5,2) NOT NULL
);

CREATE TABLE store_performance (
    store_id INT NOT NULL,
    city VARCHAR(100) NOT NULL,
    month DATE NOT NULL,
    footfall INT NOT NULL,
    conversion_rate DECIMAL(5,2) NOT NULL,
    revenue DECIMAL(15,2) NOT NULL,
    profit_margin DECIMAL(5,2) NOT NULL,
    PRIMARY KEY (store_id, month)
);

CREATE TABLE forecast_financials (
    forecast_id SERIAL PRIMARY KEY,
    month DATE NOT NULL,
    forecast_revenue DECIMAL(15,2) NOT NULL,
    forecast_cogs DECIMAL(15,2) NOT NULL,
    forecast_net_profit DECIMAL(15,2) NOT NULL
);

CREATE TABLE inventory (
    inventory_id SERIAL PRIMARY KEY,
    product_id INT NOT NULL,
    product_category VARCHAR(100) NOT NULL,
    store_id INT NOT NULL,
    date DATE NOT NULL,
    stock_in INT NOT NULL,
    stock_out INT NOT NULL,
    closing_stock INT NOT NULL
);

CREATE TABLE supplier_payments (
    payment_id SERIAL PRIMARY KEY,
    supplier_id INT NOT NULL,
    supplier_name VARCHAR(200) NOT NULL,
    date DATE NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    payment_status VARCHAR(50) NOT NULL -- Pending, Completed, Overdue
);

CREATE TABLE employee_costs (
    employee_id INT NOT NULL,
    store_id INT NOT NULL,
    role VARCHAR(100) NOT NULL,
    salary DECIMAL(15,2) NOT NULL,
    bonus DECIMAL(15,2) DEFAULT 0,
    total_cost DECIMAL(15,2) NOT NULL,
    month DATE NOT NULL,
    PRIMARY KEY (employee_id, month)
);
