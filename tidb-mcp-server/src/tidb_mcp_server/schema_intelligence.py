"""
Schema Intelligence Module for Universal MCP Server.

This module provides advanced schema intelligence capabilities including:
- Business term mapping to database schemas
- Query intent analysis 
- Schema optimization suggestions
- Semantic analysis of database structures
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class BusinessMapping:
    """Represents a mapping between business terms and schema elements."""
    business_term: str
    schema_element_type: str  # 'table', 'column', 'view'
    database_name: str
    table_name: str
    column_name: Optional[str] = None
    confidence_score: float = 0.0
    mapping_type: str = "semantic"  # 'semantic', 'exact', 'learned'
    context: Optional[str] = None
    last_used: Optional[datetime] = None
    usage_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        if self.last_used:
            data['last_used'] = self.last_used.isoformat()
        return data

@dataclass
class QueryIntent:
    """Represents analyzed query intent from natural language."""
    original_query: str
    intent_type: str  # 'select', 'aggregate', 'compare', 'trend'
    entities: List[str]  # Identified entities (tables, metrics)
    metrics: List[str]  # Identified metrics
    filters: Dict[str, Any]  # Identified filters
    time_dimension: Optional[str] = None
    grouping: List[str] = None
    confidence_score: float = 0.0
    suggested_mappings: List[BusinessMapping] = None

    def __post_init__(self):
        if self.grouping is None:
            self.grouping = []
        if self.suggested_mappings is None:
            self.suggested_mappings = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'original_query': self.original_query,
            'intent_type': self.intent_type,
            'entities': self.entities,
            'metrics': self.metrics,
            'filters': self.filters,
            'time_dimension': self.time_dimension,
            'grouping': self.grouping,
            'confidence_score': self.confidence_score,
            'suggested_mappings': [mapping.to_dict() for mapping in self.suggested_mappings]
        }

@dataclass
class SchemaOptimization:
    """Represents a schema optimization suggestion."""
    optimization_type: str  # 'index', 'partitioning', 'denormalization', 'caching'
    target_table: str
    target_columns: List[str]
    description: str
    expected_benefit: str
    implementation_complexity: str  # 'low', 'medium', 'high'
    estimated_impact: float  # 0.0 to 1.0
    sql_commands: List[str] = None

    def __post_init__(self):
        if self.sql_commands is None:
            self.sql_commands = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class SchemaIntelligenceEngine:
    """
    Advanced schema intelligence engine for semantic analysis and optimization.
    """

    def __init__(self, schema_inspector=None, query_executor=None, cache_manager=None):
        self.schema_inspector = schema_inspector
        self.query_executor = query_executor
        self.cache_manager = cache_manager
        self.business_mappings: Dict[str, List[BusinessMapping]] = {}
        self.learned_patterns: Dict[str, Dict] = {}
        
        # Initialize with common business term patterns
        self._initialize_business_patterns()

    def _initialize_business_patterns(self):
        """Initialize common business term patterns."""
        self.business_patterns = {
            'revenue': ['revenue', 'sales', 'income', 'earnings', 'turnover'],
            'profit': ['profit', 'margin', 'earning', 'net_income', 'gross_profit'],
            'expense': ['expense', 'cost', 'expenditure', 'spending', 'outlay'],
            'customer': ['customer', 'client', 'user', 'account', 'member'],
            'product': ['product', 'item', 'sku', 'service', 'offering'],
            'date': ['date', 'time', 'period', 'timestamp', 'created_at', 'updated_at'],
            'quantity': ['quantity', 'amount', 'count', 'volume', 'number'],
            'price': ['price', 'rate', 'cost', 'fee', 'charge'],
            'location': ['location', 'region', 'country', 'city', 'address'],
            'status': ['status', 'state', 'condition', 'flag', 'active']
        }

    async def discover_business_mappings(
        self, 
        business_terms: List[str] = None,
        databases: List[str] = None,
        confidence_threshold: float = 0.6
    ) -> List[BusinessMapping]:
        """
        Discover mappings between business terms and database schema elements.
        
        Args:
            business_terms: List of business terms to map (if None, uses common terms)
            databases: List of databases to analyze (if None, analyzes all)
            confidence_threshold: Minimum confidence score for mappings
            
        Returns:
            List of discovered business mappings
        """
        logger.info(f"Discovering business mappings (threshold: {confidence_threshold})")
        
        if business_terms is None:
            business_terms = list(self.business_patterns.keys())
        
        if databases is None and self.schema_inspector:
            try:
                db_info = self.schema_inspector.get_databases()
                databases = [db.name for db in db_info if db.accessible]
            except Exception as e:
                logger.error(f"Failed to get databases: {e}")
                databases = []
        
        mappings = []
        
        for business_term in business_terms:
            term_mappings = await self._analyze_business_term(
                business_term, databases, confidence_threshold
            )
            mappings.extend(term_mappings)
            
            # Cache the mappings
            self.business_mappings[business_term] = term_mappings
        
        logger.info(f"Discovered {len(mappings)} business mappings")
        return mappings

    async def _analyze_business_term(
        self, 
        business_term: str, 
        databases: List[str], 
        confidence_threshold: float
    ) -> List[BusinessMapping]:
        """Analyze a single business term for schema mappings."""
        mappings = []
        patterns = self.business_patterns.get(business_term, [business_term])
        
        if not self.schema_inspector:
            logger.warning("Schema inspector not available for business term analysis")
            return mappings
        
        for database in databases:
            try:
                # Get all tables in the database
                tables = self.schema_inspector.get_tables(database)
                
                for table in tables:
                    # Analyze table name
                    table_confidence = self._calculate_name_similarity(
                        business_term, table.name, patterns
                    )
                    
                    if table_confidence >= confidence_threshold:
                        mapping = BusinessMapping(
                            business_term=business_term,
                            schema_element_type='table',
                            database_name=database,
                            table_name=table.name,
                            confidence_score=table_confidence,
                            mapping_type='semantic'
                        )
                        mappings.append(mapping)
                    
                    # Analyze column names
                    try:
                        schema = self.schema_inspector.get_table_schema(database, table.name)
                        for column in schema.columns:
                            column_confidence = self._calculate_name_similarity(
                                business_term, column.name, patterns
                            )
                            
                            if column_confidence >= confidence_threshold:
                                mapping = BusinessMapping(
                                    business_term=business_term,
                                    schema_element_type='column',
                                    database_name=database,
                                    table_name=table.name,
                                    column_name=column.name,
                                    confidence_score=column_confidence,
                                    mapping_type='semantic'
                                )
                                mappings.append(mapping)
                    except Exception as e:
                        logger.debug(f"Failed to get schema for {database}.{table.name}: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Error analyzing database {database}: {e}")
                continue
        
        return mappings

    def _calculate_name_similarity(
        self, 
        business_term: str, 
        schema_name: str, 
        patterns: List[str]
    ) -> float:
        """Calculate similarity score between business term and schema element name."""
        schema_lower = schema_name.lower()
        business_lower = business_term.lower()
        
        # Exact match gets highest score
        if business_lower == schema_lower:
            return 1.0
        
        # Check if business term is contained in schema name
        if business_lower in schema_lower:
            return 0.9
        
        # Check if schema name is contained in business term
        if schema_lower in business_lower:
            return 0.8
        
        # Check pattern matches
        max_pattern_score = 0.0
        for pattern in patterns:
            if pattern.lower() in schema_lower:
                max_pattern_score = max(max_pattern_score, 0.7)
            elif any(word in schema_lower for word in pattern.lower().split('_')):
                max_pattern_score = max(max_pattern_score, 0.6)
        
        # Use fuzzy string matching for additional similarity
        similarity_score = self._fuzzy_similarity(business_lower, schema_lower)
        
        return max(max_pattern_score, similarity_score)

    def _fuzzy_similarity(self, str1: str, str2: str) -> float:
        """Calculate fuzzy similarity between two strings."""
        # Simple implementation using character overlap
        if not str1 or not str2:
            return 0.0
        
        # Calculate character overlap
        overlap = len(set(str1) & set(str2))
        total_chars = len(set(str1) | set(str2))
        
        if total_chars == 0:
            return 0.0
        
        return min(0.5, overlap / total_chars)  # Cap at 0.5 for fuzzy matches

    async def analyze_query_intent(
        self, 
        natural_language_query: str,
        context: Dict[str, Any] = None
    ) -> QueryIntent:
        """
        Analyze natural language query to extract intent and suggest mappings.
        
        Args:
            natural_language_query: Natural language query from user
            context: Optional context information (user preferences, history)
            
        Returns:
            Analyzed query intent with suggested mappings
        """
        logger.info(f"Analyzing query intent: {natural_language_query[:100]}...")
        
        # Normalize the query
        query_lower = natural_language_query.lower()
        
        # Extract intent type
        intent_type = self._extract_intent_type(query_lower)
        
        # Extract entities (business terms, metrics)
        entities = self._extract_entities(query_lower)
        metrics = self._extract_metrics(query_lower)
        
        # Extract filters and conditions
        filters = self._extract_filters(query_lower)
        
        # Extract time dimension
        time_dimension = self._extract_time_dimension(query_lower)
        
        # Extract grouping information
        grouping = self._extract_grouping(query_lower)
        
        # Calculate confidence score
        confidence_score = self._calculate_intent_confidence(
            intent_type, entities, metrics, filters
        )
        
        # Get suggested mappings for identified terms
        suggested_mappings = []
        all_terms = set(entities + metrics)
        
        for term in all_terms:
            if term in self.business_mappings:
                suggested_mappings.extend(self.business_mappings[term])
            else:
                # Perform on-demand mapping discovery
                term_mappings = await self._analyze_business_term(
                    term, [], 0.6  # Use cached databases if available
                )
                suggested_mappings.extend(term_mappings)
        
        intent = QueryIntent(
            original_query=natural_language_query,
            intent_type=intent_type,
            entities=entities,
            metrics=metrics,
            filters=filters,
            time_dimension=time_dimension,
            grouping=grouping,
            confidence_score=confidence_score,
            suggested_mappings=suggested_mappings
        )
        
        logger.info(f"Query intent analyzed: type={intent_type}, confidence={confidence_score:.2f}")
        return intent

    def _extract_intent_type(self, query: str) -> str:
        """Extract the primary intent type from the query."""
        if any(word in query for word in ['compare', 'comparison', 'vs', 'versus', 'against']):
            return 'compare'
        elif any(word in query for word in ['trend', 'over time', 'growth', 'change']):
            return 'trend'
        elif any(word in query for word in ['sum', 'total', 'average', 'count', 'max', 'min']):
            return 'aggregate'
        else:
            return 'select'

    def _extract_entities(self, query: str) -> List[str]:
        """Extract business entities from the query."""
        entities = []
        
        # Look for known business terms
        for business_term, patterns in self.business_patterns.items():
            for pattern in patterns:
                if pattern in query:
                    entities.append(business_term)
                    break
        
        return list(set(entities))  # Remove duplicates

    def _extract_metrics(self, query: str) -> List[str]:
        """Extract specific metrics from the query."""
        metrics = []
        
        # Common metric patterns
        metric_patterns = {
            'revenue': ['revenue', 'sales', 'income'],
            'profit': ['profit', 'margin', 'earnings'],
            'count': ['count', 'number', 'quantity'],
            'average': ['average', 'avg', 'mean'],
            'total': ['total', 'sum']
        }
        
        for metric, patterns in metric_patterns.items():
            if any(pattern in query for pattern in patterns):
                metrics.append(metric)
        
        return metrics

    def _extract_filters(self, query: str) -> Dict[str, Any]:
        """Extract filter conditions from the query."""
        filters = {}
        
        # Time-based filters
        if 'this year' in query or 'current year' in query:
            filters['time_filter'] = 'current_year'
        elif 'last year' in query or 'previous year' in query:
            filters['time_filter'] = 'previous_year'
        elif 'this month' in query or 'current month' in query:
            filters['time_filter'] = 'current_month'
        
        # Extract specific values using regex
        # Look for patterns like "greater than 100", "above 1000", etc.
        value_patterns = [
            r'(?:greater than|above|more than)\s+(\d+(?:\.\d+)?)',
            r'(?:less than|below|under)\s+(\d+(?:\.\d+)?)',
            r'(?:equal to|equals)\s+(\d+(?:\.\d+)?)'
        ]
        
        for pattern in value_patterns:
            matches = re.findall(pattern, query)
            if matches:
                filters['value_conditions'] = matches
        
        return filters

    def _extract_time_dimension(self, query: str) -> Optional[str]:
        """Extract time dimension information from the query."""
        if any(word in query for word in ['daily', 'day', 'date']):
            return 'daily'
        elif any(word in query for word in ['weekly', 'week']):
            return 'weekly'
        elif any(word in query for word in ['monthly', 'month']):
            return 'monthly'
        elif any(word in query for word in ['quarterly', 'quarter']):
            return 'quarterly'
        elif any(word in query for word in ['yearly', 'year', 'annual']):
            return 'yearly'
        
        return None

    def _extract_grouping(self, query: str) -> List[str]:
        """Extract grouping information from the query."""
        grouping = []
        
        if 'by' in query:
            # Look for "by [something]" patterns
            by_matches = re.findall(r'by\s+(\w+)', query)
            grouping.extend(by_matches)
        
        # Look for common grouping terms
        group_terms = ['category', 'region', 'department', 'product', 'customer']
        for term in group_terms:
            if term in query:
                grouping.append(term)
        
        return list(set(grouping))

    def _calculate_intent_confidence(
        self, 
        intent_type: str, 
        entities: List[str], 
        metrics: List[str], 
        filters: Dict[str, Any]
    ) -> float:
        """Calculate confidence score for the extracted intent."""
        score = 0.0
        
        # Base score for having an intent type
        if intent_type != 'select':
            score += 0.2
        
        # Score for identified entities
        score += min(0.3, len(entities) * 0.1)
        
        # Score for identified metrics
        score += min(0.3, len(metrics) * 0.15)
        
        # Score for filters
        score += min(0.2, len(filters) * 0.1)
        
        return min(1.0, score)

    async def suggest_schema_optimizations(
        self,
        database: str = None,
        query_patterns: List[str] = None,
        performance_threshold: float = 0.5
    ) -> List[SchemaOptimization]:
        """
        Suggest schema optimizations based on usage patterns and performance.
        
        Args:
            database: Target database (if None, analyzes all databases)
            query_patterns: Common query patterns to optimize for
            performance_threshold: Minimum impact threshold for suggestions
            
        Returns:
            List of schema optimization suggestions
        """
        logger.info(f"Generating schema optimization suggestions for {database or 'all databases'}")
        
        optimizations = []
        
        if not self.schema_inspector:
            logger.warning("Schema inspector not available for optimization analysis")
            return optimizations
        
        databases_to_analyze = []
        if database:
            databases_to_analyze = [database]
        else:
            try:
                db_info = self.schema_inspector.get_databases()
                databases_to_analyze = [db.name for db in db_info if db.accessible]
            except Exception as e:
                logger.error(f"Failed to get databases for optimization: {e}")
                return optimizations
        
        for db_name in databases_to_analyze:
            try:
                # Get tables in the database
                tables = self.schema_inspector.get_tables(db_name)
                
                for table in tables:
                    # Analyze each table for optimization opportunities
                    table_optimizations = await self._analyze_table_optimizations(
                        db_name, table, performance_threshold
                    )
                    optimizations.extend(table_optimizations)
                    
            except Exception as e:
                logger.error(f"Error analyzing database {db_name} for optimizations: {e}")
                continue
        
        # Sort optimizations by estimated impact
        optimizations.sort(key=lambda x: x.estimated_impact, reverse=True)
        
        logger.info(f"Generated {len(optimizations)} optimization suggestions")
        return optimizations

    async def _analyze_table_optimizations(
        self,
        database: str,
        table,
        performance_threshold: float
    ) -> List[SchemaOptimization]:
        """Analyze a single table for optimization opportunities."""
        optimizations = []
        
        try:
            # Get table schema
            schema = self.schema_inspector.get_table_schema(database, table.name)
            
            # Check for missing indexes
            index_suggestions = self._suggest_indexes(database, table, schema)
            optimizations.extend(index_suggestions)
            
            # Check for partitioning opportunities
            partition_suggestions = self._suggest_partitioning(database, table, schema)
            optimizations.extend(partition_suggestions)
            
            # Check for denormalization opportunities
            denorm_suggestions = self._suggest_denormalization(database, table, schema)
            optimizations.extend(denorm_suggestions)
            
        except Exception as e:
            logger.debug(f"Error analyzing table {database}.{table.name}: {e}")
        
        # Filter by performance threshold
        return [opt for opt in optimizations if opt.estimated_impact >= performance_threshold]

    def _suggest_indexes(self, database: str, table, schema) -> List[SchemaOptimization]:
        """Suggest index optimizations for a table."""
        suggestions = []
        
        # Look for columns that might benefit from indexes
        for column in schema.columns:
            # Foreign key columns should have indexes
            if column.is_foreign_key and not self._has_index_on_column(schema, column.name):
                suggestion = SchemaOptimization(
                    optimization_type='index',
                    target_table=f"{database}.{table.name}",
                    target_columns=[column.name],
                    description=f"Add index on foreign key column '{column.name}'",
                    expected_benefit="Improved JOIN performance and referential integrity checks",
                    implementation_complexity='low',
                    estimated_impact=0.7,
                    sql_commands=[f"CREATE INDEX idx_{table.name}_{column.name} ON {table.name}({column.name})"]
                )
                suggestions.append(suggestion)
            
            # Date/timestamp columns often benefit from indexes
            if 'date' in column.name.lower() or 'time' in column.name.lower():
                if not self._has_index_on_column(schema, column.name):
                    suggestion = SchemaOptimization(
                        optimization_type='index',
                        target_table=f"{database}.{table.name}",
                        target_columns=[column.name],
                        description=f"Add index on date/time column '{column.name}' for time-based queries",
                        expected_benefit="Improved performance for date range queries and time-based filtering",
                        implementation_complexity='low',
                        estimated_impact=0.6,
                        sql_commands=[f"CREATE INDEX idx_{table.name}_{column.name} ON {table.name}({column.name})"]
                    )
                    suggestions.append(suggestion)
        
        return suggestions

    def _suggest_partitioning(self, database: str, table, schema) -> List[SchemaOptimization]:
        """Suggest partitioning optimizations for large tables."""
        suggestions = []
        
        # Only suggest partitioning for large tables
        if table.rows and table.rows > 1000000:  # More than 1M rows
            # Look for date columns suitable for partitioning
            for column in schema.columns:
                if ('date' in column.name.lower() or 'time' in column.name.lower() or 
                    'created' in column.name.lower()):
                    suggestion = SchemaOptimization(
                        optimization_type='partitioning',
                        target_table=f"{database}.{table.name}",
                        target_columns=[column.name],
                        description=f"Consider partitioning large table by '{column.name}'",
                        expected_benefit="Improved query performance and maintenance operations for large dataset",
                        implementation_complexity='high',
                        estimated_impact=0.8,
                        sql_commands=[
                            f"-- Example partitioning by {column.name}",
                            f"ALTER TABLE {table.name} PARTITION BY RANGE (YEAR({column.name})) (",
                            f"  PARTITION p2023 VALUES LESS THAN (2024),",
                            f"  PARTITION p2024 VALUES LESS THAN (2025),",
                            f"  PARTITION pmax VALUES LESS THAN MAXVALUE",
                            f");"
                        ]
                    )
                    suggestions.append(suggestion)
                    break  # Only suggest one partitioning strategy per table
        
        return suggestions

    def _suggest_denormalization(self, database: str, table, schema) -> List[SchemaOptimization]:
        """Suggest denormalization opportunities for performance."""
        suggestions = []
        
        # This is a simplified heuristic - in practice, this would require
        # more sophisticated analysis of query patterns
        if len(schema.columns) < 5 and table.rows and table.rows > 100000:
            suggestion = SchemaOptimization(
                optimization_type='denormalization',
                target_table=f"{database}.{table.name}",
                target_columns=[col.name for col in schema.columns],
                description=f"Consider denormalizing frequently joined data into '{table.name}'",
                expected_benefit="Reduced JOIN operations for frequently accessed data combinations",
                implementation_complexity='medium',
                estimated_impact=0.5,
                sql_commands=[
                    f"-- Analyze JOIN patterns with {table.name}",
                    f"-- Consider adding computed columns or materialized views"
                ]
            )
            suggestions.append(suggestion)
        
        return suggestions

    def _has_index_on_column(self, schema, column_name: str) -> bool:
        """Check if a column has an index."""
        for index in schema.indexes:
            if column_name in index.columns:
                return True
        return False

    def learn_from_successful_mapping(
        self,
        business_term: str,
        mapping: BusinessMapping,
        success_score: float = 1.0
    ):
        """Learn from successful mappings to improve future suggestions."""
        logger.info(f"Learning from successful mapping: {business_term} -> {mapping.table_name}.{mapping.column_name}")
        
        # Update mapping usage statistics
        mapping.usage_count += 1
        mapping.last_used = datetime.now()
        mapping.confidence_score = min(1.0, mapping.confidence_score + 0.1 * success_score)
        
        # Store learned pattern
        if business_term not in self.learned_patterns:
            self.learned_patterns[business_term] = {}
        
        pattern_key = f"{mapping.database_name}.{mapping.table_name}"
        if mapping.column_name:
            pattern_key += f".{mapping.column_name}"
        
        if pattern_key not in self.learned_patterns[business_term]:
            self.learned_patterns[business_term][pattern_key] = {
                'usage_count': 0,
                'success_rate': 0.0,
                'total_attempts': 0
            }
        
        pattern_data = self.learned_patterns[business_term][pattern_key]
        pattern_data['usage_count'] += 1
        pattern_data['total_attempts'] += 1
        pattern_data['success_rate'] = (
            pattern_data['success_rate'] * (pattern_data['total_attempts'] - 1) + success_score
        ) / pattern_data['total_attempts']

    def get_intelligence_stats(self) -> Dict[str, Any]:
        """Get statistics about schema intelligence operations."""
        return {
            'business_mappings_count': sum(len(mappings) for mappings in self.business_mappings.values()),
            'learned_patterns_count': len(self.learned_patterns),
            'business_terms_analyzed': len(self.business_mappings),
            'pattern_categories': len(self.business_patterns)
        }


# Global instance
_schema_intelligence: Optional[SchemaIntelligenceEngine] = None

def get_schema_intelligence() -> SchemaIntelligenceEngine:
    """Get or create the global schema intelligence engine."""
    global _schema_intelligence
    if _schema_intelligence is None:
        _schema_intelligence = SchemaIntelligenceEngine()
    return _schema_intelligence

def initialize_schema_intelligence(schema_inspector=None, query_executor=None, cache_manager=None):
    """Initialize the schema intelligence engine with dependencies."""
    global _schema_intelligence
    _schema_intelligence = SchemaIntelligenceEngine(
        schema_inspector=schema_inspector,
        query_executor=query_executor,
        cache_manager=cache_manager
    )
    return _schema_intelligence


# MCP Tool Implementation Functions

async def discover_business_mappings_impl(
    business_terms: Optional[List[str]] = None,
    databases: Optional[List[str]] = None,
    confidence_threshold: float = 0.6
) -> Dict[str, Any]:
    """MCP tool implementation for discovering business mappings."""
    try:
        engine = get_schema_intelligence()
        
        # Use provided terms or default financial terms
        if business_terms is None:
            business_terms = ['revenue', 'profit', 'expenses', 'cash_flow']
        
        mappings = {}
        total_mappings = 0
        
        for term in business_terms:
            term_mappings = await engine.discover_business_mappings(
                term, databases, confidence_threshold
            )
            mappings[term] = [mapping.to_dict() for mapping in term_mappings]
            total_mappings += len(term_mappings)
        
        return {
            "success": True,
            "mappings": mappings,
            "total_mappings": total_mappings,
            "confidence_threshold": confidence_threshold
        }
    except Exception as e:
        logger.error(f"Business mapping discovery failed: {e}")
        return {"success": False, "error": str(e)}


async def analyze_query_intent_impl(
    natural_language_query: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """MCP tool implementation for analyzing query intent."""
    try:
        engine = get_schema_intelligence()
        intent = await engine.analyze_query_intent(natural_language_query, context)
        
        return {
            "success": True,
            "intent": asdict(intent),
            "suggested_sql": await engine.generate_sql_from_intent(intent),
            "confidence_score": intent.confidence_score
        }
    except Exception as e:
        logger.error(f"Query intent analysis failed: {e}")
        return {"success": False, "error": str(e)}


async def suggest_schema_optimizations_impl(
    database: Optional[str] = None,
    query_patterns: Optional[List[str]] = None,
    performance_threshold: float = 0.5
) -> Dict[str, Any]:
    """MCP tool implementation for suggesting schema optimizations."""
    try:
        engine = get_schema_intelligence()
        optimizations = await engine.suggest_optimizations(
            database, query_patterns, performance_threshold
        )
        
        return {
            "success": True,
            "optimizations": optimizations,
            "database": database,
            "performance_threshold": performance_threshold
        }
    except Exception as e:
        logger.error(f"Schema optimization analysis failed: {e}")
        return {"success": False, "error": str(e)}


async def get_schema_intelligence_stats_impl() -> Dict[str, Any]:
    """MCP tool implementation for getting schema intelligence statistics."""
    try:
        engine = get_schema_intelligence()
        stats = engine.get_intelligence_stats()
        
        return {
            "success": True,
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get schema intelligence stats: {e}")
        return {"success": False, "error": str(e)}


async def learn_from_successful_mapping_impl(
    business_term: str,
    database_name: str,
    table_name: str,
    column_name: Optional[str] = None,
    success_score: float = 1.0
) -> Dict[str, Any]:
    """MCP tool implementation for learning from successful mappings."""
    try:
        engine = get_schema_intelligence()
        
        # Create mapping and learn from it
        mapping = BusinessMapping(
            business_term=business_term,
            schema_element_type="column" if column_name else "table",
            database_name=database_name,
            table_name=table_name,
            column_name=column_name,
            confidence_score=min(0.95, 0.7 + success_score * 0.25),
            mapping_type="learned"
        )
        
        engine.learn_from_successful_mapping(mapping, success_score)
        
        return {
            "success": True,
            "message": f"Learned mapping: {business_term} -> {database_name}.{table_name}.{column_name or '*'}",
            "confidence_boost": success_score * 0.25
        }
    except Exception as e:
        logger.error(f"Learning from successful mapping failed: {e}")
        return {"success": False, "error": str(e)}
