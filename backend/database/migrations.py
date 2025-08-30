"""
Database migration utilities for TiDB using pure PyMySQL
Implements the financial data schema from the design document
"""

import logging
from typing import List, Dict, Any
from .connection import tidb_connection, get_database
import pymysql

logger = logging.getLogger(__name__)


class TiDBMigration:
    """TiDB migration manager following TiDB Cloud best practices"""
    
    def __init__(self):
        # Use the global database manager for consistency
        self.db_manager = get_database()
    
    def create_financial_tables(self) -> bool:
        """Create all financial data tables as defined in the design document"""
        
        tables = {
            "financial_overview": """
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
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            
            "cash_flow": """
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
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            
            "budget_tracking": """
                CREATE TABLE IF NOT EXISTS budget_tracking (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    department VARCHAR(100) NOT NULL,
                    period_date DATE NOT NULL,
                    budgeted_amount DECIMAL(15,2),
                    actual_amount DECIMAL(15,2),
                    variance_amount DECIMAL(15,2),
                    variance_percentage DECIMAL(5,2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_department_period (department, period_date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            
            "investments": """
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
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            
            "financial_ratios": """
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
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        }
        
        try:
            with tidb_connection(autocommit=True) as conn:
                with conn.cursor() as cursor:
                    for table_name, create_sql in tables.items():
                        logger.info(f"Creating table: {table_name}")
                        cursor.execute(create_sql)
                        logger.info(f"✅ Table {table_name} created successfully")
            
            logger.info("✅ All financial tables created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create financial tables: {e}")
            return False
    
    def create_personalization_tables(self) -> bool:
        """Create user personalization tables"""
        
        tables = {
            "user_preferences": """
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    user_id VARCHAR(100) NOT NULL,
                    preference_type VARCHAR(50) NOT NULL,
                    preference_value JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_user_type (user_id, preference_type)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            
            "query_history": """
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
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            
            "user_behavior": """
                CREATE TABLE IF NOT EXISTS user_behavior (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    user_id VARCHAR(100) NOT NULL,
                    session_id VARCHAR(100),
                    action_type VARCHAR(50),
                    action_data JSON,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_user_session (user_id, session_id),
                    INDEX idx_timestamp (timestamp)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        }
        
        try:
            with tidb_connection(autocommit=True) as conn:
                with conn.cursor() as cursor:
                    for table_name, create_sql in tables.items():
                        logger.info(f"Creating table: {table_name}")
                        cursor.execute(create_sql)
                        logger.info(f"✅ Table {table_name} created successfully")
            
            logger.info("✅ All personalization tables created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create personalization tables: {e}")
            return False
    
    def insert_sample_data(self) -> bool:
        """Insert sample financial data for testing"""
        
        try:
            with tidb_connection(autocommit=True) as conn:
                with conn.cursor() as cursor:
                    # Sample financial overview data
                    financial_data = [
                        ('2024-01-31', 'monthly', 1500000.00, 900000.00, 250000.00, 650000.00),
                        ('2024-02-29', 'monthly', 1650000.00, 990000.00, 280000.00, 710000.00),
                        ('2024-03-31', 'monthly', 1750000.00, 1050000.00, 320000.00, 730000.00),
                        ('2024-03-31', 'quarterly', 4900000.00, 2940000.00, 850000.00, 2090000.00),
                    ]
                    
                    cursor.executemany("""
                        INSERT INTO financial_overview 
                        (period_date, period_type, revenue, gross_profit, net_profit, operating_expenses)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, financial_data)
                    
                    # Sample cash flow data
                    cash_flow_data = [
                        ('2024-01-31', 300000.00, -150000.00, -50000.00, 100000.00, 1100000.00),
                        ('2024-02-29', 350000.00, -200000.00, -75000.00, 75000.00, 1175000.00),
                        ('2024-03-31', 400000.00, -100000.00, -25000.00, 275000.00, 1450000.00),
                    ]
                    
                    cursor.executemany("""
                        INSERT INTO cash_flow 
                        (period_date, operating_cash_flow, investing_cash_flow, financing_cash_flow, net_cash_flow, cash_balance)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, cash_flow_data)
                    
                    # Sample budget tracking data
                    budget_data = [
                        ('Engineering', '2024-03-31', 500000.00, 485000.00, -15000.00, -3.00),
                        ('Marketing', '2024-03-31', 200000.00, 215000.00, 15000.00, 7.50),
                        ('Sales', '2024-03-31', 300000.00, 295000.00, -5000.00, -1.67),
                    ]
                    
                    cursor.executemany("""
                        INSERT INTO budget_tracking 
                        (department, period_date, budgeted_amount, actual_amount, variance_amount, variance_percentage)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, budget_data)
                    
                    # Sample investment data
                    investment_data = [
                        ('Tech Startup A', 'Technology', 100000.00, 125000.00, 25.00, 'active', '2023-06-01', None),
                        ('Real Estate Fund', 'Real Estate', 500000.00, 550000.00, 10.00, 'active', '2023-01-15', None),
                        ('Bond Portfolio', 'Fixed Income', 200000.00, 208000.00, 4.00, 'active', '2023-03-01', None),
                    ]
                    
                    cursor.executemany("""
                        INSERT INTO investments 
                        (investment_name, investment_category, initial_amount, current_value, roi_percentage, status, start_date, end_date)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, investment_data)
                    
                    # Sample financial ratios
                    ratio_data = [
                        ('2024-03-31', 0.65, 2.1, 1.8, 60.0, 18.3),
                        ('2024-02-29', 0.68, 2.0, 1.7, 60.0, 17.0),
                        ('2024-01-31', 0.70, 1.9, 1.6, 60.0, 16.7),
                    ]
                    
                    cursor.executemany("""
                        INSERT INTO financial_ratios 
                        (period_date, debt_to_equity, current_ratio, quick_ratio, gross_margin, net_margin)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, ratio_data)
            
            logger.info("✅ Sample data inserted successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to insert sample data: {e}")
            return False
    
    def run_migrations(self) -> bool:
        """Run all migrations"""
        logger.info("🚀 Starting TiDB migrations...")
        
        steps = [
            ("Financial Tables", self.create_financial_tables),
            ("Personalization Tables", self.create_personalization_tables),
            ("Sample Data", self.insert_sample_data),
        ]
        
        for step_name, step_func in steps:
            logger.info(f"\n--- {step_name} ---")
            if not step_func():
                logger.error(f"❌ Migration failed at step: {step_name}")
                return False
        
        logger.info("\n🎉 All migrations completed successfully!")
        return True


def main():
    """Run migrations"""
    logging.basicConfig(level=logging.INFO)
    
    migration = TiDBMigration()
    success = migration.run_migrations()
    
    if not success:
        exit(1)


if __name__ == "__main__":
    main()