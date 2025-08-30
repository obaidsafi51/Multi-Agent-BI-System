"""
Shared data types for the Schema Knowledge Base component.
This module contains all shared data structures to avoid circular imports.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class PeriodType(Enum):
    """Types of time periods"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class DatabaseType(Enum):
    """Supported database types"""
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    MSSQL = "mssql"


@dataclass
class GeneratedQuery:
    """Represents a generated SQL query with metadata"""
    sql: str
    parameters: Dict[str, Any]
    template_name: str
    estimated_complexity: str
    supports_caching: bool = True


@dataclass
class OptimizationResult:
    """Result of query optimization"""
    original_sql: str
    optimized_sql: str
    applied_optimizations: List[str]
    performance_score: int
    warnings: List[str]
    database_specific: bool = False


@dataclass
class OptimizationRule:
    """Represents a query optimization rule"""
    name: str
    condition: Dict[str, Any]
    action: Dict[str, Any]
    priority: int = 1
    enabled: bool = True


@dataclass
class TermMapping:
    """Represents a mapping between business term and database schema"""
    business_term: str
    database_mapping: str
    synonyms: List[str]
    category: str
    data_type: str
    aggregation_methods: List[str]
    confidence_score: float = 1.0
    description: str = ""


@dataclass
class SimilarityMatch:
    """Represents a similarity match result"""
    term: str
    canonical_term: str
    similarity_score: float
    match_type: str  # exact, fuzzy, phonetic, semantic
    confidence: float


@dataclass
class TimePeriod:
    """Represents a processed time period"""
    start_date: Any  # Using Any to avoid datetime import issues
    end_date: Any
    period_type: PeriodType
    period_label: str
    fiscal_year: Optional[int] = None
    quarter: Optional[int] = None
    month: Optional[int] = None
    year: Optional[int] = None
    is_partial: bool = False
    confidence: float = 1.0


@dataclass
class ComparisonPeriod:
    """Represents a comparison period with context"""
    current_period: TimePeriod
    comparison_period: TimePeriod
    comparison_type: str  # yoy, qoq, mom, etc.
    growth_calculation: str


@dataclass
class QueryTemplate:
    """Represents a SQL query template with metadata"""
    name: str
    template: str
    description: str
    parameters: Dict[str, Any]
    supports_aggregation: bool
    supports_comparison: bool
    category: str = "general"