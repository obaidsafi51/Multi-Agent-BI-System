-- AI CFO BI Agent Database Schema
-- TiDB Database Schema for Financial Data and User Personalization

-- ============================================================================
-- FINANCIAL DATA TABLES
-- ============================================================================

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
    INDEX idx_period_type (period_type),
    INDEX idx_period_date_type (period_date, period_type)
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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_department_period (department, period_date),
    INDEX idx_period_date (period_date)
);

-- Investment Performance
CREATE TABLE IF NOT EXISTS investments (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    investment_name VARCHAR(200) NOT NULL,
    investment_category VARCHAR(100),
    initial_amount DECIMAL(15,2),
    current_value DECIMAL(15,2),
    roi_percentage DECIMAL(5,2),
    status ENUM('active', 'completed', 'terminated') DEFAULT 'active',
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_category (investment_category),
    INDEX idx_start_date (start_date)
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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_period_date (period_date)
);

-- ============================================================================
-- USER PERSONALIZATION TABLES
-- ============================================================================

-- User Preferences
CREATE TABLE IF NOT EXISTS user_preferences (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(100) NOT NULL,
    preference_type VARCHAR(50) NOT NULL,
    preference_value JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_type (user_id, preference_type),
    INDEX idx_user_id (user_id)
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
    INDEX idx_created_at (created_at),
    INDEX idx_user_created (user_id, created_at)
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
    INDEX idx_timestamp (timestamp),
    INDEX idx_action_type (action_type)
);