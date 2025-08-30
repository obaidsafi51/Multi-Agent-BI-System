import pytest
from .sql_cleanup_utility import SQLCleanupUtility


class TestSQLCleanupUtility:
    def setup_method(self):
        self.cleaner = SQLCleanupUtility()
    
    def test_clean_sql_removes_where_and(self):
        sql = "SELECT * FROM table WHERE AND condition = 1"
        cleaned = self.cleaner.clean_sql(sql)
        assert cleaned == "SELECT * FROM table WHERE condition = 1"
    
    def test_clean_sql_removes_consecutive_ands(self):
        sql = "SELECT * FROM table WHERE condition1 = 1 AND AND condition2 = 2"
        cleaned = self.cleaner.clean_sql(sql)
        assert cleaned == "SELECT * FROM table WHERE condition1 = 1 AND condition2 = 2"
    
    def test_clean_sql_removes_trailing_ands(self):
        sql = "SELECT * FROM table WHERE AND"
        cleaned = self.cleaner.clean_sql(sql)
        assert cleaned == "SELECT * FROM table"
    
    def test_clean_sql_removes_empty_where(self):
        sql = "SELECT * FROM table WHERE"
        cleaned = self.cleaner.clean_sql(sql)
        assert cleaned == "SELECT * FROM table"
    
    def test_validate_cleanup_result_valid(self):
        original = "SELECT * FROM table WHERE condition = 1"
        cleaned = "SELECT * FROM table WHERE condition = 1"
        is_valid, issues = self.cleaner.validate_cleanup_result(original, cleaned)
        assert is_valid is True
        assert issues == []
    
    def test_validate_cleanup_result_invalid_parentheses(self):
        original = "SELECT * FROM table WHERE (condition = 1"
        cleaned = self.cleaner.clean_sql(original)  # Use actual cleaned SQL
        is_valid, issues = self.cleaner.validate_cleanup_result(original, cleaned)
        assert is_valid is False
        assert "Unmatched parentheses after cleanup" in issues  # Match the exact string