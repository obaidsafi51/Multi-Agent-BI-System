#!/usr/bin/env python3
"""
Manual query test to verify actual data in TiDB for the data agent.
"""

import os
import pymysql
import urllib.parse
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/home/obaidsafi31/Desktop/Agentic BI /.env")

def test_financial_data():
    """Test actual financial data queries."""
    print("Testing Financial Data Queries")
    print("=" * 35)
    
    try:
        # Connect to database
        url = os.getenv('DATABASE_URL')
        parsed = urllib.parse.urlparse(url)
        
        connection = pymysql.connect(
            host=parsed.hostname,
            port=parsed.port or 4000,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path[1:] if parsed.path else '',
            charset='utf8mb4',
            ssl={'check_hostname': False, 'verify_mode': 0},
            connect_timeout=10,
            autocommit=True
        )
        
        with connection.cursor() as cursor:
            # Test 1: Check all tables
            print("Available Tables:")
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                count = cursor.fetchone()[0]
                print(f"  {table[0]}: {count} records")
            
            print("\nSample Data:")
            
            # Test 2: Sample financial overview data
            print("\nFinancial Overview (Revenue Data):")
            cursor.execute("""
                SELECT period_date, revenue, gross_profit, net_profit 
                FROM financial_overview 
                ORDER BY period_date DESC 
                LIMIT 5
            """)
            revenue_data = cursor.fetchall()
            for row in revenue_data:
                print(f"  {row[0]}: Revenue=${row[1]:,.2f}, Gross=${row[2]:,.2f}, Net=${row[3]:,.2f}")
            
            # Test 3: Sample budget tracking data
            print("\nBudget Tracking:")
            cursor.execute("""
                SELECT period_date, budgeted_amount, actual_amount, variance_percentage
                FROM budget_tracking 
                ORDER BY period_date DESC 
                LIMIT 5
            """)
            budget_data = cursor.fetchall()
            for row in budget_data:
                print(f"  {row[0]}: Budget=${row[1]:,.2f}, Actual=${row[2]:,.2f}, Variance={row[3]:.1f}%")
            
            # Test 4: Sample cash flow data
            print("\nCash Flow:")
            cursor.execute("""
                SELECT period_date, operating_cash_flow, investing_cash_flow, financing_cash_flow, net_cash_flow
                FROM cash_flow 
                ORDER BY period_date DESC 
                LIMIT 3
            """)
            cashflow_data = cursor.fetchall()
            for row in cashflow_data:
                print(f"  {row[0]}: Operating=${row[1]:,.2f}, Net=${row[4]:,.2f}")
            
            # Test 5: Generate a sample query that the data agent would create
            print("\nSample Data Agent Query (Monthly Revenue 2024):")
            cursor.execute("""
                SELECT 
                    DATE_FORMAT(period_date, '%Y-%m') as period,
                    SUM(revenue) as total_revenue,
                    COUNT(*) as record_count
                FROM financial_overview 
                WHERE period_date BETWEEN '2024-01-01' AND '2024-12-31'
                GROUP BY DATE_FORMAT(period_date, '%Y-%m')
                ORDER BY period
                LIMIT 10
            """)
            
            monthly_data = cursor.fetchall()
            for row in monthly_data:
                print(f"  {row[0]}: ${row[1]:,.2f} ({row[2]} records)")
        
        connection.close()
        
        print("\n✅ All financial data tests successful!")
        print("The database contains comprehensive financial data for the Data Agent.")
        
        return True
        
    except Exception as e:
        print(f"❌ Financial data test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_financial_data()
    exit(0 if success else 1)
