-- AI CFO Database Initialization Script
-- This script creates the database and tables for the AI CFO BI Agent

-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS ai_cfo_db;
USE ai_cfo_db;

-- Company Financial Overview
CREATE TABLE IF NOT EXISTS financial_overview (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    period_date DATE NOT NULL,
    period_type ENUM('daily', 'monthly', 'quarterly', 'yearly') NOT NULL,
    revenue DECIMAL(15,2),
    gross_profit DECIMAL(15,2),
    net_profit DECIMAL(15,2),
    operating_expenses DECIMAL(15,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_period_date (period_date),
    INDEX idx_period_type (period_type)
);

-- Cash Flow Data
CREATE TABLE IF NOT EXISTS cash_flow (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    period_date DATE NOT NULL,
    operating_cash_flow DECIMAL(15,2),
    investing_cash_flow DECIMAL(15,2),
    financing_cash_flow DECIMAL(15,2),
    net_cash_flow DECIMAL(15,2),
    cash_balance DECIMAL(15,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_period_date (period_date)
);

-- Budget Tracking
CREATE TABLE IF NOT EXISTS budget_tracking (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    department VARCHAR(100) NOT NULL,
    period_date DATE NOT NULL,
    budgeted_amount DECIMAL(15,2),
    actual_amount DECIMAL(15,2),
    variance_amount DECIMAL(15,2),
    variance_percentage DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_period_date (period_date),
    INDEX idx_department_period (department, period_date)
);

-- Investment Performance
CREATE TABLE IF NOT EXISTS investments (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    investment_name VARCHAR(200) NOT NULL,
    investment_category VARCHAR(100),
    initial_amount DECIMAL(15,2),
    current_value DECIMAL(15,2),
    roi_percentage DECIMAL(5,2),
    status ENUM('active', 'completed', 'terminated'),
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_category (investment_category)
);

-- Financial Ratios
CREATE TABLE IF NOT EXISTS financial_ratios (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    period_date DATE NOT NULL,
    debt_to_equity DECIMAL(5,2),
    current_ratio DECIMAL(5,2),
    quick_ratio DECIMAL(5,2),
    gross_margin DECIMAL(5,2),
    net_margin DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_period_date (period_date)
);

-- User Preferences
CREATE TABLE IF NOT EXISTS user_preferences (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(100) NOT NULL,
    preference_type VARCHAR(50) NOT NULL,
    preference_value JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_type (user_id, preference_type)
);

-- Query History
CREATE TABLE IF NOT EXISTS query_history (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(100) NOT NULL,
    query_text TEXT NOT NULL,
    query_intent JSON,
    response_data JSON,
    satisfaction_rating TINYINT,
    processing_time_ms INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
);

-- User Behavior Analytics
CREATE TABLE IF NOT EXISTS user_behavior (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(100) NOT NULL,
    session_id VARCHAR(100),
    action_type VARCHAR(50),
    action_data JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_session (user_id, session_id),
    INDEX idx_timestamp (timestamp)
);

-- Insert some sample data for testing
INSERT IGNORE INTO financial_overview (period_date, period_type, revenue, gross_profit, net_profit, operating_expenses) VALUES
('2024-01-01', 'monthly', 1000000.00, 600000.00, 150000.00, 450000.00),
('2024-02-01', 'monthly', 1200000.00, 720000.00, 180000.00, 540000.00),
('2024-03-01', 'monthly', 1100000.00, 660000.00, 165000.00, 495000.00),
('2024-01-01', 'quarterly', 3300000.00, 1980000.00, 495000.00, 1485000.00);

INSERT IGNORE INTO cash_flow (period_date, operating_cash_flow, investing_cash_flow, financing_cash_flow, net_cash_flow, cash_balance) VALUES
('2024-01-01', 200000.00, -50000.00, -30000.00, 120000.00, 500000.00),
('2024-02-01', 250000.00, -60000.00, -40000.00, 150000.00, 650000.00),
('2024-03-01', 220000.00, -55000.00, -35000.00, 130000.00, 780000.00);

INSERT IGNORE INTO budget_tracking (department, period_date, budgeted_amount, actual_amount, variance_amount, variance_percentage) VALUES
('Marketing', '2024-01-01', 100000.00, 95000.00, -5000.00, -5.00),
('Sales', '2024-01-01', 150000.00, 160000.00, 10000.00, 6.67),
('Engineering', '2024-01-01', 200000.00, 195000.00, -5000.00, -2.50);

-- Create a health check table for database connectivity testing
CREATE TABLE IF NOT EXISTS health_check (
    id INT PRIMARY KEY AUTO_INCREMENT,
    status VARCHAR(10) DEFAULT 'healthy',
    last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

INSERT IGNORE INTO health_check (status) VALUES ('healthy');