import re
from typing import List, Tuple


class SQLCleanupUtility:
    """Utility class for cleaning up SQL queries with malformed WHERE clauses and other issues."""
    
    def __init__(self):
        self.cleanup_rules = [
            (self._remove_where_and, "Remove 'WHERE AND' patterns"),
            (self._remove_consecutive_ands, "Remove multiple consecutive ANDs"),
            (self._remove_trailing_ands, "Remove trailing ANDs after WHERE"),
            (self._remove_empty_where_clauses, "Remove empty WHERE clauses"),
        ]
    
    def clean_sql(self, sql: str) -> str:
        """
        Apply all SQL cleanup rules to the input SQL string.
        
        Args:
            sql: The SQL string to clean
            
        Returns:
            Cleaned SQL string
        """
        cleaned_sql = sql
        for cleanup_func, description in self.cleanup_rules:
            cleaned_sql = cleanup_func(cleaned_sql)
        return cleaned_sql.strip()  # Strip trailing whitespace
    
    def _remove_where_and(self, sql: str) -> str:
        """Remove 'WHERE AND' patterns (with any whitespace)."""
        return re.sub(r'\bWHERE\s+AND\b', 'WHERE', sql, flags=re.IGNORECASE)
    
    def _remove_consecutive_ands(self, sql: str) -> str:
        """Remove multiple consecutive ANDs."""
        return re.sub(r'\bAND\s+AND\b', 'AND', sql, flags=re.IGNORECASE)
    
    def _remove_trailing_ands(self, sql: str) -> str:
        """Remove trailing AND after WHERE or at end of WHERE clause."""
        # Remove AND after WHERE
        sql = re.sub(r'(WHERE\s*)(AND\s*)+', r'\1', sql, flags=re.IGNORECASE)
        # Remove AND at end of line or before semicolon
        sql = re.sub(r'\s+AND\s*($|;)', r'\1', sql, flags=re.IGNORECASE)
        return sql
    
    def _remove_empty_where_clauses(self, sql: str) -> str:
        """Remove empty WHERE clauses (WHERE followed by nothing or only whitespace)."""
        return re.sub(r'\bWHERE\s*($|;)', r'\1', sql, flags=re.IGNORECASE)
    
    def validate_cleanup_result(self, original_sql: str, cleaned_sql: str) -> Tuple[bool, List[str]]:
        """
        Validate that the cleanup didn't break the SQL structure.
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check for basic SQL structure integrity
        if 'SELECT' not in cleaned_sql.upper() and 'SELECT' in original_sql.upper():
            issues.append("SELECT clause may have been removed")
        
        # Check for unmatched parentheses
        if cleaned_sql.count('(') != cleaned_sql.count(')'):
            issues.append("Unmatched parentheses after cleanup")
        
        # Check for orphaned WHERE keywords
        if re.search(r'\bWHERE\s*FROM\b', cleaned_sql, re.IGNORECASE):
            issues.append("WHERE clause appears before FROM clause")
        
        return len(issues) == 0, issues