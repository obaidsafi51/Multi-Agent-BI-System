"""
Query Success Pattern Analysis for AI-Enhanced Semantic Mapping.

This module analyzes query success patterns to improve semantic mapping
accuracy and provide intelligent suggestions based on historical success.
"""

import asyncio
import json
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
import statistics
import hashlib

try:
    from .ai_semantic_mapper import AISemanticMapping
    from .models import TableSchema, ColumnInfo
    from .config import MCPSchemaConfig
except ImportError:
    # Fallback for direct execution
    from ai_semantic_mapper import AISemanticMapping
    from models import TableSchema, ColumnInfo
    from config import MCPSchemaConfig

logger = logging.getLogger(__name__)


class QueryExecutionStatus(Enum):
    """Query execution status."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL_SUCCESS = "partial_success"
    TIMEOUT = "timeout"
    ERROR = "error"


class QueryComplexity(Enum):
    """Query complexity levels."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


@dataclass
class QueryExecutionRecord:
    """Record of query execution with mapping context."""
    
    id: str
    user_id: str
    session_id: str
    timestamp: datetime
    business_query: str
    generated_sql: str
    execution_status: QueryExecutionStatus
    execution_time_ms: int
    rows_returned: int
    error_message: Optional[str] = None
    
    # Mapping context
    mapped_terms: List[str] = None
    used_mappings: List[Dict[str, Any]] = None
    ai_confidence_scores: List[float] = None
    
    # Query characteristics
    complexity: Optional[QueryComplexity] = None
    tables_used: List[str] = None
    columns_used: List[str] = None
    joins_count: int = 0
    aggregations_used: List[str] = None
    
    # User context
    user_expertise_level: str = "unknown"
    query_intent: str = ""
    
    def __post_init__(self):
        if self.mapped_terms is None:
            self.mapped_terms = []
        if self.used_mappings is None:
            self.used_mappings = []
        if self.ai_confidence_scores is None:
            self.ai_confidence_scores = []
        if self.tables_used is None:
            self.tables_used = []
        if self.columns_used is None:
            self.columns_used = []
        if self.aggregations_used is None:
            self.aggregations_used = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary."""
        data = asdict(self)
        data['execution_status'] = self.execution_status.value
        if self.complexity:
            data['complexity'] = self.complexity.value
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class MappingSuccessPattern:
    """Pattern of successful semantic mappings."""
    
    business_term: str
    successful_mappings: List[str]
    success_rate: float
    avg_confidence: float
    usage_count: int
    last_used: datetime
    
    # Context patterns
    common_contexts: List[str] = None
    user_types: Set[str] = None
    typical_complexity: QueryComplexity = QueryComplexity.SIMPLE
    
    # Performance metrics
    avg_execution_time_ms: float = 0.0
    avg_rows_returned: float = 0.0
    
    def __post_init__(self):
        if self.common_contexts is None:
            self.common_contexts = []
        if self.user_types is None:
            self.user_types = set()


@dataclass
class QuerySuccessAnalytics:
    """Analytics from query success pattern analysis."""
    
    total_queries: int = 0
    success_rate: float = 0.0
    avg_execution_time_ms: float = 0.0
    
    # Mapping performance
    mapping_accuracy: float = 0.0
    high_confidence_success_rate: float = 0.0
    low_confidence_success_rate: float = 0.0
    
    # Pattern insights
    most_successful_terms: List[Tuple[str, float]] = None
    problematic_terms: List[Tuple[str, float]] = None
    optimal_confidence_threshold: float = 0.7
    
    # User insights
    user_success_patterns: Dict[str, float] = None
    
    def __post_init__(self):
        if self.most_successful_terms is None:
            self.most_successful_terms = []
        if self.problematic_terms is None:
            self.problematic_terms = []
        if self.user_success_patterns is None:
            self.user_success_patterns = {}


class QueryPatternAnalyzer:
    """Analyzer for query execution patterns and mapping success."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.min_pattern_threshold = config.get('min_pattern_threshold', 10)
        self.success_rate_threshold = config.get('success_rate_threshold', 0.8)
        self.confidence_buckets = config.get('confidence_buckets', [0.5, 0.7, 0.8, 0.9])
        
        # Pattern storage
        self.success_patterns: Dict[str, MappingSuccessPattern] = {}
        self.confidence_success_rates: Dict[float, List[bool]] = defaultdict(list)
        self.user_success_tracking: Dict[str, List[bool]] = defaultdict(list)
        
        logger.info("Query pattern analyzer initialized")
    
    def analyze_query_execution(self, record: QueryExecutionRecord) -> Dict[str, Any]:
        """Analyze a query execution record and update patterns."""
        analysis_results = {
            'patterns_updated': [],
            'insights_generated': [],
            'recommendations': []
        }
        
        try:
            # Update success patterns for each mapped term
            for i, term in enumerate(record.mapped_terms):
                if i < len(record.used_mappings):
                    mapping_info = record.used_mappings[i]
                    confidence = record.ai_confidence_scores[i] if i < len(record.ai_confidence_scores) else 0.0
                    
                    self._update_mapping_pattern(
                        term, 
                        mapping_info, 
                        record.execution_status == QueryExecutionStatus.SUCCESS,
                        confidence,
                        record
                    )
                    analysis_results['patterns_updated'].append(term)
            
            # Update confidence-based success tracking
            if record.ai_confidence_scores:
                avg_confidence = statistics.mean(record.ai_confidence_scores)
                success = record.execution_status == QueryExecutionStatus.SUCCESS
                self._update_confidence_tracking(avg_confidence, success)
            
            # Update user success tracking
            self.user_success_tracking[record.user_id].append(
                record.execution_status == QueryExecutionStatus.SUCCESS
            )
            
            # Generate insights
            insights = self._generate_execution_insights(record)
            analysis_results['insights_generated'] = insights
            
            # Generate recommendations
            recommendations = self._generate_recommendations(record)
            analysis_results['recommendations'] = recommendations
            
            logger.debug(f"Analyzed query execution {record.id}: {len(analysis_results['patterns_updated'])} patterns updated")
            
        except Exception as e:
            logger.error(f"Error analyzing query execution: {e}")
        
        return analysis_results
    
    def _update_mapping_pattern(
        self, 
        business_term: str, 
        mapping_info: Dict[str, Any], 
        success: bool, 
        confidence: float,
        record: QueryExecutionRecord
    ):
        """Update success pattern for a business term mapping."""
        mapping_key = f"{mapping_info.get('table_name', '')}.{mapping_info.get('column_name', '')}"
        
        if business_term not in self.success_patterns:
            self.success_patterns[business_term] = MappingSuccessPattern(
                business_term=business_term,
                successful_mappings=[],
                success_rate=0.0,
                avg_confidence=0.0,
                usage_count=0,
                last_used=record.timestamp,
                common_contexts=[],
                user_types=set(),
                typical_complexity=record.complexity or QueryComplexity.SIMPLE,
                avg_execution_time_ms=0.0,
                avg_rows_returned=0.0
            )
        
        pattern = self.success_patterns[business_term]
        
        # Update basic metrics
        pattern.usage_count += 1
        pattern.last_used = record.timestamp
        
        # Update success rate
        if success and mapping_key not in pattern.successful_mappings:
            pattern.successful_mappings.append(mapping_key)
        
        # Calculate new success rate
        # This is a simplified calculation - in practice, you'd track individual successes/failures
        pattern.success_rate = len(pattern.successful_mappings) / max(pattern.usage_count, 1)
        
        # Update confidence tracking
        pattern.avg_confidence = (
            (pattern.avg_confidence * (pattern.usage_count - 1) + confidence) / pattern.usage_count
        )
        
        # Update context information
        if record.query_intent and record.query_intent not in pattern.common_contexts:
            pattern.common_contexts.append(record.query_intent)
            # Keep only most recent contexts
            if len(pattern.common_contexts) > 5:
                pattern.common_contexts = pattern.common_contexts[-5:]
        
        # Update user types
        pattern.user_types.add(record.user_expertise_level)
        
        # Update performance metrics
        pattern.avg_execution_time_ms = (
            (pattern.avg_execution_time_ms * (pattern.usage_count - 1) + record.execution_time_ms) / 
            pattern.usage_count
        )
        pattern.avg_rows_returned = (
            (pattern.avg_rows_returned * (pattern.usage_count - 1) + record.rows_returned) / 
            pattern.usage_count
        )
    
    def _update_confidence_tracking(self, confidence: float, success: bool):
        """Update confidence-based success tracking."""
        # Find appropriate confidence bucket
        bucket = 0.5  # Default bucket
        for threshold in sorted(self.confidence_buckets):
            if confidence >= threshold:
                bucket = threshold
            else:
                break
        
        self.confidence_success_rates[bucket].append(success)
        
        # Keep only recent results for each bucket
        max_samples = 100
        if len(self.confidence_success_rates[bucket]) > max_samples:
            self.confidence_success_rates[bucket] = self.confidence_success_rates[bucket][-max_samples:]
    
    def _generate_execution_insights(self, record: QueryExecutionRecord) -> List[str]:
        """Generate insights from query execution."""
        insights = []
        
        # Check for low-confidence successful queries
        if (record.execution_status == QueryExecutionStatus.SUCCESS and 
            record.ai_confidence_scores and 
            max(record.ai_confidence_scores) < 0.6):
            insights.append("Low-confidence mapping succeeded - consider lowering confidence threshold")
        
        # Check for high-confidence failed queries
        if (record.execution_status != QueryExecutionStatus.SUCCESS and 
            record.ai_confidence_scores and 
            min(record.ai_confidence_scores) > 0.8):
            insights.append("High-confidence mapping failed - investigate mapping accuracy")
        
        # Check for performance issues
        if record.execution_time_ms > 5000:  # 5 seconds
            insights.append("Slow query execution - consider query optimization")
        
        # Check for complexity vs success correlation
        if (record.complexity in [QueryComplexity.COMPLEX, QueryComplexity.VERY_COMPLEX] and
            record.execution_status != QueryExecutionStatus.SUCCESS):
            insights.append("Complex query failed - may need better mapping strategy")
        
        return insights
    
    def _generate_recommendations(self, record: QueryExecutionRecord) -> List[str]:
        """Generate recommendations based on execution patterns."""
        recommendations = []
        
        # Recommend confidence threshold adjustments
        for term in record.mapped_terms:
            if term in self.success_patterns:
                pattern = self.success_patterns[term]
                if pattern.usage_count >= self.min_pattern_threshold:
                    if pattern.success_rate > 0.9 and pattern.avg_confidence < 0.7:
                        recommendations.append(f"Consider lowering confidence threshold for '{term}'")
                    elif pattern.success_rate < 0.5 and pattern.avg_confidence > 0.8:
                        recommendations.append(f"Review mapping strategy for '{term}' - high confidence but low success")
        
        # Recommend alternative mappings
        if record.execution_status != QueryExecutionStatus.SUCCESS:
            for term in record.mapped_terms:
                if term in self.success_patterns:
                    pattern = self.success_patterns[term]
                    if pattern.successful_mappings:
                        recommendations.append(f"Try alternative mapping for '{term}': {pattern.successful_mappings[0]}")
        
        return recommendations
    
    def get_optimal_confidence_threshold(self, business_term: Optional[str] = None) -> float:
        """Calculate optimal confidence threshold based on success patterns."""
        if business_term and business_term in self.success_patterns:
            # Term-specific threshold
            pattern = self.success_patterns[business_term]
            if pattern.usage_count >= self.min_pattern_threshold:
                # Use pattern's average confidence as a starting point
                return max(0.5, pattern.avg_confidence - 0.1)
        
        # Global threshold based on confidence bucket analysis
        best_threshold = 0.7
        best_success_rate = 0.0
        
        for threshold, successes in self.confidence_success_rates.items():
            if len(successes) >= 10:  # Minimum sample size
                success_rate = sum(successes) / len(successes)
                if success_rate > best_success_rate:
                    best_success_rate = success_rate
                    best_threshold = threshold
        
        return best_threshold
    
    def get_mapping_recommendations(
        self, 
        business_term: str, 
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get mapping recommendations based on success patterns."""
        recommendations = []
        
        if business_term in self.success_patterns:
            pattern = self.success_patterns[business_term]
            
            for mapping in pattern.successful_mappings:
                recommendation = {
                    'mapping': mapping,
                    'success_rate': pattern.success_rate,
                    'confidence_boost': 0.1 if pattern.success_rate > 0.8 else 0.0,
                    'usage_count': pattern.usage_count,
                    'avg_execution_time_ms': pattern.avg_execution_time_ms,
                    'typical_complexity': pattern.typical_complexity.value if pattern.typical_complexity else 'unknown'
                }
                recommendations.append(recommendation)
        
        # Add user-specific recommendations if user data available
        if user_id and user_id in self.user_success_tracking:
            user_successes = self.user_success_tracking[user_id]
            user_success_rate = sum(user_successes) / len(user_successes) if user_successes else 0.0
            
            # Adjust recommendations based on user success rate
            for rec in recommendations:
                if user_success_rate > 0.8:
                    rec['confidence_boost'] += 0.05  # Boost for successful users
                elif user_success_rate < 0.5:
                    rec['confidence_boost'] -= 0.05  # Reduce for unsuccessful users
        
        return sorted(recommendations, key=lambda x: x['success_rate'], reverse=True)


class QuerySuccessPatternAnalysis:
    """
    Main class for analyzing query success patterns to improve semantic mapping.
    
    Tracks query execution outcomes, analyzes patterns, and provides
    intelligent recommendations for improving mapping accuracy.
    """
    
    def __init__(self, config: MCPSchemaConfig):
        self.config = config
        self.pattern_config = config.semantic_mapping.get('pattern_analysis', {})
        
        # Storage
        self.execution_records: deque = deque(maxlen=self.pattern_config.get('max_records', 10000))
        
        # Analyzer
        self.pattern_analyzer = QueryPatternAnalyzer(
            self.pattern_config.get('analyzer_config', {})
        )
        
        # Analytics cache
        self.analytics_cache: Optional[QuerySuccessAnalytics] = None
        self.analytics_cache_expiry: Optional[datetime] = None
        self.analytics_cache_ttl = timedelta(hours=2)
        
        logger.info("Query success pattern analysis initialized")
    
    async def record_query_execution(
        self,
        user_id: str,
        session_id: str,
        business_query: str,
        generated_sql: str,
        execution_status: QueryExecutionStatus,
        execution_time_ms: int,
        rows_returned: int,
        mapped_terms: List[str],
        used_mappings: List[Dict[str, Any]],
        ai_confidence_scores: List[float],
        error_message: Optional[str] = None,
        user_expertise_level: str = "unknown",
        query_intent: str = ""
    ) -> str:
        """Record a query execution for pattern analysis."""
        
        record_id = f"qe_{int(datetime.utcnow().timestamp())}_{user_id}"
        
        # Analyze query complexity
        complexity = self._analyze_query_complexity(generated_sql)
        
        # Extract table and column information
        tables_used, columns_used, joins_count, aggregations = self._extract_query_info(generated_sql)
        
        record = QueryExecutionRecord(
            id=record_id,
            user_id=user_id,
            session_id=session_id,
            timestamp=datetime.utcnow(),
            business_query=business_query,
            generated_sql=generated_sql,
            execution_status=execution_status,
            execution_time_ms=execution_time_ms,
            rows_returned=rows_returned,
            error_message=error_message,
            mapped_terms=mapped_terms,
            used_mappings=used_mappings,
            ai_confidence_scores=ai_confidence_scores,
            complexity=complexity,
            tables_used=tables_used,
            columns_used=columns_used,
            joins_count=joins_count,
            aggregations_used=aggregations,
            user_expertise_level=user_expertise_level,
            query_intent=query_intent
        )
        
        # Store record
        self.execution_records.append(record)
        
        # Analyze patterns
        analysis_results = self.pattern_analyzer.analyze_query_execution(record)
        
        # Invalidate analytics cache
        self.analytics_cache = None
        self.analytics_cache_expiry = None
        
        logger.info(f"Recorded query execution {record_id} with {len(analysis_results['patterns_updated'])} pattern updates")
        return record_id
    
    def _analyze_query_complexity(self, sql: str) -> QueryComplexity:
        """Analyze SQL query complexity."""
        sql_lower = sql.lower()
        
        complexity_score = 0
        
        # Count indicators of complexity
        if 'join' in sql_lower:
            complexity_score += sql_lower.count('join')
        
        if 'subselect' in sql_lower or 'exists' in sql_lower:
            complexity_score += 2
        
        if any(agg in sql_lower for agg in ['group by', 'having', 'window']):
            complexity_score += 1
        
        if any(func in sql_lower for func in ['case when', 'coalesce', 'cast']):
            complexity_score += 1
        
        # Classify complexity
        if complexity_score == 0:
            return QueryComplexity.SIMPLE
        elif complexity_score <= 2:
            return QueryComplexity.MODERATE
        elif complexity_score <= 4:
            return QueryComplexity.COMPLEX
        else:
            return QueryComplexity.VERY_COMPLEX
    
    def _extract_query_info(self, sql: str) -> Tuple[List[str], List[str], int, List[str]]:
        """Extract tables, columns, joins, and aggregations from SQL."""
        # This is a simplified extraction - in practice, you'd use a proper SQL parser
        sql_lower = sql.lower()
        
        # Extract table names (simplified)
        tables = []
        if 'from' in sql_lower:
            # Basic table extraction - would need proper SQL parsing for production
            tables = ['extracted_table']  # Placeholder
        
        # Extract column names (simplified)
        columns = []
        if 'select' in sql_lower:
            columns = ['extracted_column']  # Placeholder
        
        # Count joins
        joins_count = sql_lower.count('join')
        
        # Extract aggregations
        aggregations = []
        agg_functions = ['sum', 'count', 'avg', 'max', 'min', 'group_concat']
        for agg in agg_functions:
            if agg in sql_lower:
                aggregations.append(agg)
        
        return tables, columns, joins_count, aggregations
    
    def get_mapping_confidence_adjustment(
        self, 
        business_term: str, 
        suggested_mapping: str, 
        base_confidence: float
    ) -> float:
        """Get confidence adjustment based on success patterns."""
        recommendations = self.pattern_analyzer.get_mapping_recommendations(business_term)
        
        for rec in recommendations:
            if rec['mapping'] == suggested_mapping:
                adjustment = rec.get('confidence_boost', 0.0)
                return min(base_confidence + adjustment, 1.0)
        
        return base_confidence
    
    def get_optimal_confidence_threshold(self, business_term: Optional[str] = None) -> float:
        """Get optimal confidence threshold for mappings."""
        return self.pattern_analyzer.get_optimal_confidence_threshold(business_term)
    
    def get_success_analytics(self, force_refresh: bool = False) -> QuerySuccessAnalytics:
        """Get comprehensive success analytics."""
        # Check cache
        if (not force_refresh and 
            self.analytics_cache is not None and 
            self.analytics_cache_expiry is not None and
            datetime.utcnow() < self.analytics_cache_expiry):
            return self.analytics_cache
        
        # Calculate analytics
        analytics = self._calculate_success_analytics()
        
        # Cache results
        self.analytics_cache = analytics
        self.analytics_cache_expiry = datetime.utcnow() + self.analytics_cache_ttl
        
        return analytics
    
    def _calculate_success_analytics(self) -> QuerySuccessAnalytics:
        """Calculate comprehensive success analytics."""
        if not self.execution_records:
            return QuerySuccessAnalytics()
        
        records = list(self.execution_records)
        total_queries = len(records)
        
        # Basic success metrics
        successful_queries = [r for r in records if r.execution_status == QueryExecutionStatus.SUCCESS]
        success_rate = len(successful_queries) / total_queries * 100
        
        # Average execution time
        avg_execution_time = statistics.mean([r.execution_time_ms for r in records])
        
        # Confidence-based analysis
        high_confidence_records = [r for r in records if r.ai_confidence_scores and max(r.ai_confidence_scores) >= 0.8]
        low_confidence_records = [r for r in records if r.ai_confidence_scores and max(r.ai_confidence_scores) < 0.6]
        
        high_conf_success = len([r for r in high_confidence_records if r.execution_status == QueryExecutionStatus.SUCCESS])
        low_conf_success = len([r for r in low_confidence_records if r.execution_status == QueryExecutionStatus.SUCCESS])
        
        high_conf_success_rate = (high_conf_success / len(high_confidence_records) * 100) if high_confidence_records else 0
        low_conf_success_rate = (low_conf_success / len(low_confidence_records) * 100) if low_confidence_records else 0
        
        # Term analysis
        term_success_rates = {}
        for term, pattern in self.pattern_analyzer.success_patterns.items():
            if pattern.usage_count >= 5:  # Minimum usage threshold
                term_success_rates[term] = pattern.success_rate
        
        most_successful = sorted(term_success_rates.items(), key=lambda x: x[1], reverse=True)[:10]
        problematic = sorted(term_success_rates.items(), key=lambda x: x[1])[:10]
        
        # User success patterns
        user_patterns = {}
        for user_id, successes in self.pattern_analyzer.user_success_tracking.items():
            if len(successes) >= 5:  # Minimum query threshold
                user_patterns[user_id] = sum(successes) / len(successes) * 100
        
        # Optimal confidence threshold
        optimal_threshold = self.pattern_analyzer.get_optimal_confidence_threshold()
        
        return QuerySuccessAnalytics(
            total_queries=total_queries,
            success_rate=success_rate,
            avg_execution_time_ms=avg_execution_time,
            high_confidence_success_rate=high_conf_success_rate,
            low_confidence_success_rate=low_conf_success_rate,
            most_successful_terms=most_successful,
            problematic_terms=problematic,
            optimal_confidence_threshold=optimal_threshold,
            user_success_patterns=user_patterns
        )
    
    def export_pattern_data(self, format: str = "json") -> str:
        """Export pattern analysis data."""
        if format.lower() == "json":
            data = {
                'execution_records': [record.to_dict() for record in self.execution_records],
                'success_patterns': {
                    term: asdict(pattern) for term, pattern in self.pattern_analyzer.success_patterns.items()
                },
                'analytics': asdict(self.get_success_analytics()),
                'export_timestamp': datetime.utcnow().isoformat()
            }
            return json.dumps(data, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get pattern analysis system status."""
        return {
            'execution_records_count': len(self.execution_records),
            'success_patterns_count': len(self.pattern_analyzer.success_patterns),
            'confidence_buckets': list(self.pattern_analyzer.confidence_success_rates.keys()),
            'tracked_users': len(self.pattern_analyzer.user_success_tracking),
            'cache_status': {
                'analytics_cached': self.analytics_cache is not None,
                'cache_expiry': self.analytics_cache_expiry.isoformat() if self.analytics_cache_expiry else None
            }
        }
