"""
Main Schema Knowledge Base component that orchestrates all sub-components.

This version integrates with MCP-based dynamic schema management while maintaining
business logic components like term mapping, query templates, and metrics.
"""

import json
import os
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import date

from .term_mapper import TermMapper
from .query_template_engine import QueryTemplateEngine
from .similarity_matcher import SimilarityMatcher
from .time_processor import TimeProcessor
from .mcp_schema_adapter import MCPSchemaAdapter
from .types import (
    TermMapping, 
    GeneratedQuery, 
    SimilarityMatch, 
    TimePeriod, 
    ComparisonPeriod,
    DatabaseType
)

from ..models.core import QueryIntent, FinancialEntity, ErrorResponse

class SchemaKnowledgeBase:
    """
    Main Schema Knowledge Base component that provides CFO terminology mapping,
    query template processing, and intelligent time period handling.
    
    Now integrates with MCP-based dynamic schema management for real-time
    schema discovery while maintaining business logic and term mappings.
    """
    
    def __init__(self, config_path: Optional[str] = None, fiscal_year_start_month: int = 1,
                 mcp_client: Optional[Any] = None):
        """Initialize the Schema Knowledge Base with all sub-components"""
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), "config")
        
        self.config_path = Path(config_path)
        
        # Initialize MCP adapter for dynamic schema management
        self.mcp_adapter = MCPSchemaAdapter(mcp_client=mcp_client)
        
        # Initialize business logic sub-components
        self.term_mapper = TermMapper(config_path)
        self.query_engine = QueryTemplateEngine(config_path)
        self.similarity_matcher = SimilarityMatcher()
        self.time_processor = TimeProcessor(fiscal_year_start_month)
        
        # Load metrics configuration
        self.metrics_config = self._load_metrics_config()
        
        # Performance tracking
        self.query_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
    
    def _load_metrics_config(self) -> Dict[str, Any]:
        """Load metrics configuration"""
        try:
            metrics_file = self.config_path / "metrics_config.json"
            with open(metrics_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            return {}
    
    def process_query_intent(self, natural_language_query: str, 
                           reference_date: Optional[date] = None) -> QueryIntent:
        """
        Process a natural language query and extract structured intent.
        This is the main entry point for query processing.
        """
        
        # Extract financial entities from the query
        entities = self.extract_financial_entities(natural_language_query)
        
        # Process time periods
        time_period = self.extract_time_period(natural_language_query, reference_date)
        
        # Determine aggregation level
        aggregation_level = self._determine_aggregation_level(natural_language_query, time_period)
        
        # Extract filters
        filters = self._extract_filters(natural_language_query, entities)
        
        # Detect comparison periods
        comparison_periods = self._extract_comparison_periods(natural_language_query, time_period)
        
        # Suggest visualization
        visualization_hint = self._suggest_visualization(entities, time_period)
        
        # Determine primary metric
        primary_metric = self._determine_primary_metric(entities)
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence(entities, time_period)
        
        return QueryIntent(
            metric_type=primary_metric,
            time_period=time_period.period_label if time_period else "current year",
            aggregation_level=aggregation_level,
            filters=filters,
            comparison_periods=comparison_periods,
            visualization_hint=visualization_hint,
            confidence_score=confidence_score
        )
    
    def extract_financial_entities(self, query: str) -> List[FinancialEntity]:
        """Extract and map financial entities from natural language query"""
        entities = []
        words = query.lower().split()
        
        # Try to map individual words and phrases
        for i in range(len(words)):
            # Try single words
            entity = self.term_mapper.map_term(words[i])
            if entity:
                entities.append(entity)
            
            # Try two-word phrases
            if i < len(words) - 1:
                phrase = f"{words[i]} {words[i+1]}"
                entity = self.term_mapper.map_term(phrase)
                if entity:
                    entities.append(entity)
            
            # Try three-word phrases
            if i < len(words) - 2:
                phrase = f"{words[i]} {words[i+1]} {words[i+2]}"
                entity = self.term_mapper.map_term(phrase)
                if entity:
                    entities.append(entity)
        
        # Remove duplicates while preserving order
        unique_entities = []
        seen_values = set()
        for entity in entities:
            if entity.entity_value not in seen_values:
                unique_entities.append(entity)
                seen_values.add(entity.entity_value)
        
        return unique_entities
    
    def extract_time_period(self, query: str, reference_date: Optional[date] = None) -> Optional[TimePeriod]:
        """Extract time period from natural language query"""
        try:
            return self.time_processor.parse_time_period(query, reference_date)
        except Exception:
            # Fallback to current year if parsing fails
            return self.time_processor.parse_time_period("this year", reference_date)
    
    def generate_sql_query(self, query_intent: QueryIntent) -> GeneratedQuery:
        """Generate SQL query from structured query intent"""
        cache_key = self._create_cache_key(query_intent)
        
        # Check cache first
        if cache_key in self.query_cache:
            self.cache_hits += 1
            return self.query_cache[cache_key]
        
        self.cache_misses += 1
        
        # Generate new query
        generated_query = self.query_engine.generate_query(query_intent)
        
        # Optimize the query
        optimized_query = self.query_engine.optimize_query(generated_query)
        
        # Cache the result
        if optimized_query.supports_caching:
            self.query_cache[cache_key] = optimized_query
        
        return optimized_query
    
    def find_similar_terms(self, unknown_term: str, limit: int = 5) -> List[SimilarityMatch]:
        """Find similar terms for unknown financial terminology"""
        known_terms = self.term_mapper.get_all_terms()
        return self.similarity_matcher.find_best_matches(unknown_term, known_terms, limit)
    
    def suggest_query_corrections(self, failed_query: str) -> ErrorResponse:
        """Suggest corrections for failed queries"""
        entities = self.extract_financial_entities(failed_query)
        
        if not entities:
            # No entities found, try similarity matching
            words = failed_query.lower().split()
            suggestions = []
            
            for word in words:
                similar_terms = self.find_similar_terms(word, 3)
                for match in similar_terms:
                    suggestions.append(match.canonical_term)
            
            # Remove duplicates
            suggestions = list(set(suggestions))[:5]
            
            return ErrorResponse(
                error_type="unknown_terms",
                message="I couldn't understand some terms in your query. Did you mean:",
                suggestions=suggestions,
                recovery_action="clarification",
                error_code="SKB_001"
            )
        
        # Check for low confidence entities
        low_confidence_entities = [e for e in entities if e.confidence_score < 0.8]
        
        if low_confidence_entities:
            suggestions = []
            for entity in low_confidence_entities:
                similar = self.find_similar_terms(entity.entity_value, 2)
                suggestions.extend([match.canonical_term for match in similar])
            
            return ErrorResponse(
                error_type="ambiguous_terms",
                message="Some terms in your query might be unclear. Consider using:",
                suggestions=list(set(suggestions))[:5],
                recovery_action="clarification",
                error_code="SKB_002"
            )
        
        # Query seems fine, might be a data or execution issue
        return ErrorResponse(
            error_type="processing_error",
            message="Your query looks correct, but there might be a data or system issue.",
            suggestions=["Try a different time period", "Check if data is available", "Simplify the query"],
            recovery_action="retry",
            error_code="SKB_003"
        )
    
    def get_query_enhancement_suggestions(self, query_intent: QueryIntent) -> List[str]:
        """Suggest enhancements to improve query insights"""
        suggestions = []
        
        # Suggest comparisons if none exist
        if not query_intent.comparison_periods:
            suggestions.append("Add year-over-year comparison")
            suggestions.append("Compare with previous quarter")
        
        # Suggest breakdowns
        if query_intent.metric_type in ["revenue", "profit", "expenses"]:
            suggestions.append("Break down by department")
            suggestions.append("Show monthly trend")
        
        # Suggest related metrics
        related_metrics = self.term_mapper.get_related_terms(query_intent.metric_type)
        if related_metrics:
            suggestions.append(f"Also analyze {related_metrics[0]}")
        
        # Suggest visualization improvements
        if query_intent.visualization_hint == "table":
            suggestions.append("Visualize as a chart")
        
        return suggestions[:4]  # Return top 4 suggestions
    
    def validate_query_intent(self, query_intent: QueryIntent) -> Dict[str, Any]:
        """Validate query intent for completeness and correctness"""
        errors = []
        warnings = []
        
        # Validate metric type
        if not query_intent.metric_type:
            errors.append("No financial metric specified")
        else:
            entity = self.term_mapper.map_term(query_intent.metric_type)
            if not entity:
                warnings.append(f"Unknown metric type: {query_intent.metric_type}")
        
        # Validate time period
        if query_intent.time_period:
            time_period = self.extract_time_period(query_intent.time_period)
            if time_period:
                time_validation = self.time_processor.validate_time_period(time_period)
                if not time_validation["is_valid"]:
                    errors.extend(time_validation["errors"])
                warnings.extend(time_validation["warnings"])
        
        # Validate term combinations
        if query_intent.filters:
            for filter_key, filter_value in query_intent.filters.items():
                entity = self.term_mapper.map_term(filter_key)
                if not entity:
                    warnings.append(f"Unknown filter term: {filter_key}")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "confidence_score": query_intent.confidence_score
        }
    
    def get_metric_metadata(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific metric"""
        metric_definitions = self.metrics_config.get("metric_definitions", {})
        return metric_definitions.get(metric_name)
    
    def get_visualization_config(self, metric_name: str) -> Dict[str, Any]:
        """Get visualization configuration for a metric"""
        metadata = self.get_metric_metadata(metric_name)
        if metadata and "visualization_preferences" in metadata:
            return metadata["visualization_preferences"]
        
        # Default visualization config
        return {
            "primary_chart": "line",
            "secondary_charts": ["bar"],
            "color_scheme": "blue",
            "show_trend": True,
            "show_comparison": False
        }
    
    def _determine_aggregation_level(self, query: str, time_period: Optional[TimePeriod]) -> str:
        """Determine appropriate aggregation level"""
        query_lower = query.lower()
        
        # Explicit aggregation mentions
        if any(term in query_lower for term in ["daily", "day by day"]):
            return "daily"
        elif any(term in query_lower for term in ["weekly", "week by week"]):
            return "weekly"
        elif any(term in query_lower for term in ["monthly", "month by month"]):
            return "monthly"
        elif any(term in query_lower for term in ["quarterly", "quarter by quarter"]):
            return "quarterly"
        elif any(term in query_lower for term in ["yearly", "year by year", "annually"]):
            return "yearly"
        
        # Infer from time period
        if time_period:
            if time_period.period_type.value == "daily":
                return "daily"
            elif time_period.period_type.value == "weekly":
                return "weekly"
            elif time_period.period_type.value == "monthly":
                return "monthly"
            elif time_period.period_type.value == "quarterly":
                return "quarterly"
            elif time_period.period_type.value == "yearly":
                return "yearly"
        
        # Default to monthly
        return "monthly"
    
    def _extract_filters(self, query: str, entities: List[FinancialEntity]) -> Dict[str, Any]:
        """Extract filters from query and entities"""
        filters = {}
        
        # Look for department mentions
        department_entities = [e for e in entities if e.entity_type == "department"]
        if department_entities:
            filters["department"] = department_entities[0].entity_value
        
        # Look for status mentions
        query_lower = query.lower()
        if "active" in query_lower:
            filters["status"] = "active"
        elif "completed" in query_lower:
            filters["status"] = "completed"
        elif "terminated" in query_lower:
            filters["status"] = "terminated"
        
        return filters
    
    def _extract_comparison_periods(self, query: str, base_period: Optional[TimePeriod]) -> List[str]:
        """Extract comparison period expressions"""
        comparison_periods = []
        query_lower = query.lower()
        
        # Look for comparison keywords
        comparison_patterns = [
            "vs last year", "compared to last year", "year over year", "yoy",
            "vs last quarter", "compared to last quarter", "quarter over quarter", "qoq",
            "vs last month", "compared to last month", "month over month", "mom",
            "vs previous", "compared to previous", "period over period", "pop"
        ]
        
        for pattern in comparison_patterns:
            if pattern in query_lower:
                comparison_periods.append(pattern)
        
        return comparison_periods
    
    def _suggest_visualization(self, entities: List[FinancialEntity], 
                             time_period: Optional[TimePeriod]) -> Optional[str]:
        """Suggest appropriate visualization type"""
        if not entities:
            return "table"
        
        primary_entity = entities[0]
        metadata = self.get_metric_metadata(primary_entity.entity_value)
        
        if metadata and "visualization_preferences" in metadata:
            return metadata["visualization_preferences"]["primary_chart"]
        
        # Default suggestions based on metric type
        metric_type = primary_entity.entity_value
        
        if metric_type in ["revenue", "profit", "cash_flow"]:
            return "line"
        elif metric_type in ["budget_variance", "roi"]:
            return "bar"
        elif metric_type in ["debt_to_equity", "current_ratio"]:
            return "gauge"
        else:
            return "line"
    
    def _determine_primary_metric(self, entities: List[FinancialEntity]) -> str:
        """Determine the primary metric from extracted entities"""
        if not entities:
            return "revenue"  # Default
        
        # Filter out department entities
        metric_entities = [e for e in entities if e.entity_type == "metric"]
        
        if metric_entities:
            # Return the first metric entity with highest confidence
            metric_entities.sort(key=lambda x: x.confidence_score, reverse=True)
            return metric_entities[0].entity_value
        
        # Fallback to first entity
        return entities[0].entity_value
    
    def _calculate_confidence(self, entities: List[FinancialEntity], 
                            time_period: Optional[TimePeriod]) -> float:
        """Calculate overall confidence score for query intent"""
        if not entities:
            return 0.3
        
        # Average entity confidence
        entity_confidence = sum(e.confidence_score for e in entities) / len(entities)
        
        # Time period confidence
        time_confidence = time_period.confidence if time_period else 0.5
        
        # Weighted average
        overall_confidence = (entity_confidence * 0.7) + (time_confidence * 0.3)
        
        return min(overall_confidence, 1.0)
    
    def _create_cache_key(self, query_intent: QueryIntent) -> str:
        """Create cache key for query intent"""
        key_parts = [
            query_intent.metric_type,
            query_intent.time_period,
            query_intent.aggregation_level,
            str(sorted(query_intent.filters.items())),
            str(sorted(query_intent.comparison_periods))
        ]
        return "|".join(key_parts)
    
    async def validate_business_term_mappings(self) -> Dict[str, Any]:
        """
        Validate all business term mappings against actual database schema using MCP.
        
        Returns:
            Validation results with detailed information
        """
        # Get all term mappings from business terms configuration
        term_mappings = {}
        for term, mapping in self.term_mapper.term_mappings.items():
            if mapping.database_mapping:
                term_mappings[term] = mapping.database_mapping
        
        # Validate against actual schema using MCP
        validation_results = await self.mcp_adapter.validate_business_term_mappings(term_mappings)
        
        # Compile detailed validation report
        total_terms = len(term_mappings)
        valid_terms = sum(validation_results.values())
        invalid_terms = [term for term, valid in validation_results.items() if not valid]
        
        return {
            "total_terms": total_terms,
            "valid_terms": valid_terms,
            "invalid_terms": invalid_terms,
            "validation_rate": (valid_terms / total_terms * 100) if total_terms > 0 else 0,
            "validation_details": validation_results,
            "requires_attention": len(invalid_terms) > 0
        }
    
    async def get_available_metrics(self) -> List[Dict[str, Any]]:
        """
        Get list of available metrics with their database mappings validated against MCP.
        
        Returns:
            List of available metrics with validation status
        """
        metrics = []
        
        for term, mapping in self.term_mapper.term_mappings.items():
            if mapping.category in ["income_statement", "cash_flow_statement", "balance_sheet", "financial_ratios"]:
                # Check if the mapping is valid using MCP
                schema_info = await self.mcp_adapter.resolve_business_term_to_schema(term, mapping.database_mapping)
                
                metric_info = {
                    "term": term,
                    "description": mapping.description,
                    "category": mapping.category,
                    "data_type": mapping.data_type,
                    "aggregation_methods": mapping.aggregation_methods,
                    "database_mapping": mapping.database_mapping,
                    "is_available": schema_info is not None,
                    "synonyms": mapping.synonyms
                }
                
                if schema_info:
                    metric_info.update({
                        "table": schema_info.table,
                        "database": schema_info.database,
                        "column_count": len(schema_info.columns),
                        "row_count": schema_info.row_count
                    })
                
                metrics.append(metric_info)
        
        return metrics
    
    async def generate_dynamic_sql_query(self, query_intent: QueryIntent, 
                                       target_database: Optional[str] = None) -> GeneratedQuery:
        """
        Generate SQL query using both business logic and dynamic schema from MCP.
        
        Args:
            query_intent: Structured query intent
            target_database: Optional target database (uses first available if None)
            
        Returns:
            Generated query with validation against actual schema
        """
        cache_key = self._create_cache_key(query_intent)
        
        # Check cache first
        if cache_key in self.query_cache:
            self.cache_hits += 1
            return self.query_cache[cache_key]
        
        self.cache_misses += 1
        
        try:
            # Get database context
            if not target_database:
                databases = await self.mcp_adapter.get_available_databases()
                if not databases:
                    raise RuntimeError("No databases available from MCP server")
                target_database = databases[0]
            
            # Resolve business terms to actual schema
            primary_metric = query_intent.metric_type
            term_mapping = self.term_mapper.get_term_mapping(primary_metric)
            
            if not term_mapping or not term_mapping.database_mapping:
                raise ValueError(f"No database mapping found for metric: {primary_metric}")
            
            # Validate mapping against actual schema
            schema_info = await self.mcp_adapter.resolve_business_term_to_schema(
                primary_metric, term_mapping.database_mapping
            )
            
            if not schema_info:
                raise ValueError(f"Database mapping not found in actual schema: {term_mapping.database_mapping}")
            
            # Generate query using existing query engine with validated schema
            generated_query = self.query_engine.generate_query(query_intent)
            
            # Enhance query with actual schema information
            enhanced_query = self._enhance_query_with_schema(generated_query, schema_info)
            
            # Cache the result
            if enhanced_query.supports_caching:
                self.query_cache[cache_key] = enhanced_query
            
            return enhanced_query
            
        except Exception as e:
            # Return error query
            return GeneratedQuery(
                sql_query="",
                query_type="error",
                estimated_execution_time=0,
                supports_caching=False,
                optimization_notes=[f"Error generating query: {str(e)}"],
                parameters={}
            )
    
    def _enhance_query_with_schema(self, generated_query: GeneratedQuery, 
                                 schema_info: Any) -> GeneratedQuery:
        """
        Enhance generated query with actual schema information from MCP.
        
        Args:
            generated_query: Query generated by template engine
            schema_info: Schema information from MCP
            
        Returns:
            Enhanced query with better optimization
        """
        # Add schema-aware optimizations
        optimization_notes = list(generated_query.optimization_notes)
        
        # Add index information if available
        if schema_info.indexes:
            index_names = [idx.get("name", "") for idx in schema_info.indexes]
            optimization_notes.append(f"Available indexes: {', '.join(index_names)}")
        
        # Add row count information for cost estimation
        if schema_info.row_count:
            optimization_notes.append(f"Estimated table size: {schema_info.row_count:,} rows")
            
            # Adjust execution time estimate based on table size
            if schema_info.row_count > 1000000:
                estimated_time = generated_query.estimated_execution_time * 2
                optimization_notes.append("Large table detected - consider adding LIMIT clause")
            else:
                estimated_time = generated_query.estimated_execution_time
        else:
            estimated_time = generated_query.estimated_execution_time
        
        return GeneratedQuery(
            sql_query=generated_query.sql_query,
            query_type=generated_query.query_type,
            estimated_execution_time=estimated_time,
            supports_caching=generated_query.supports_caching,
            optimization_notes=optimization_notes,
            parameters=generated_query.parameters
        )
    
    async def refresh_schema_knowledge(self, database: Optional[str] = None) -> Dict[str, Any]:
        """
        Refresh schema knowledge by updating MCP cache and validating mappings.
        
        Args:
            database: Optional database to refresh (refreshes all if None)
            
        Returns:
            Refresh results summary
        """
        try:
            # Refresh MCP schema cache
            await self.mcp_adapter.refresh_schema_cache(database=database)
            
            # Validate business term mappings after refresh
            validation_results = await self.validate_business_term_mappings()
            
            # Get updated metrics availability
            available_metrics = await self.get_available_metrics()
            available_count = sum(1 for m in available_metrics if m["is_available"])
            
            return {
                "refresh_timestamp": date.today().isoformat(),
                "database_refreshed": database or "all",
                "validation_results": validation_results,
                "available_metrics_count": available_count,
                "total_metrics_count": len(available_metrics),
                "mcp_cache_stats": self.mcp_adapter.get_cache_stats(),
                "success": True
            }
            
        except Exception as e:
            return {
                "refresh_timestamp": date.today().isoformat(),
                "database_refreshed": database or "all",
                "error": str(e),
                "success": False
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check including MCP connectivity.
        
        Returns:
            Health check results
        """
        health_status = {
            "timestamp": date.today().isoformat(),
            "components": {},
            "overall_healthy": True,
            "warnings": [],
            "errors": []
        }
        
        try:
            # Check MCP adapter health
            mcp_health = await self.mcp_adapter.health_check()
            health_status["components"]["mcp_adapter"] = mcp_health
            
            if not mcp_health.get("databases_accessible", False):
                health_status["warnings"].append("MCP databases not accessible")
                health_status["overall_healthy"] = False
            
            # Check business logic components
            health_status["components"]["term_mapper"] = {
                "total_terms": len(self.term_mapper.term_mappings),
                "categories": len(set(m.category for m in self.term_mapper.term_mappings.values())),
                "healthy": True
            }
            
            health_status["components"]["query_engine"] = {
                "templates_loaded": len(getattr(self.query_engine, 'templates', {})),
                "healthy": True
            }
            
            health_status["components"]["cache"] = {
                "query_cache_size": len(self.query_cache),
                "cache_hit_rate": (self.cache_hits / (self.cache_hits + self.cache_misses) * 100) if (self.cache_hits + self.cache_misses) > 0 else 0,
                "healthy": True
            }
            
        except Exception as e:
            health_status["errors"].append(f"Health check error: {str(e)}")
            health_status["overall_healthy"] = False
        
        return health_status
        """Get knowledge base statistics"""
        term_stats = self.term_mapper.get_term_statistics()
        
        return {
            "term_mappings": term_stats,
            "available_templates": len(self.query_engine.templates),
            "cache_performance": {
                "hits": self.cache_hits,
                "misses": self.cache_misses,
                "hit_rate": self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
            },
            "similarity_threshold": self.similarity_matcher.similarity_threshold
        }
    
    def clear_cache(self) -> None:
        """Clear query cache"""
        self.query_cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
    
    def update_similarity_threshold(self, threshold: float) -> None:
        """Update similarity matching threshold"""
        self.similarity_matcher.set_similarity_threshold(threshold)
    
    def add_custom_term_mapping(self, business_term: str, database_mapping: str, 
                              synonyms: List[str], category: str = "custom") -> None:
        """Add custom term mapping"""
        # This would require extending the term mapper to support runtime additions
        # For now, we'll store it in memory
        pass
    
    def configure_database_optimization(self, database_type: str = "mysql") -> None:
        """Configure database-specific optimizations"""
        # Map string to enum
        db_type_mapping = {
            "mysql": DatabaseType.MYSQL,
            "postgresql": DatabaseType.POSTGRESQL,
            "sqlite": DatabaseType.SQLITE,
            "mssql": DatabaseType.MSSQL
        }
        
        if database_type.lower() in db_type_mapping:
            # This would be used by the query engine's optimizer
            # For now, we store it for future use
            self._database_type = db_type_mapping[database_type.lower()]
        else:
            raise ValueError(f"Unsupported database type: {database_type}")
    
    def get_optimization_config(self) -> Dict[str, Any]:
        """Get current optimization configuration"""
        from .query_optimizer import QueryOptimizer
        
        optimizer = QueryOptimizer(
            config_path=os.path.join(os.path.dirname(__file__), "config"),
            database_type=getattr(self, '_database_type', DatabaseType.MYSQL)
        )
        
        return {
            "database_type": optimizer.database_type.value,
            "optimization_rules": len(optimizer.optimization_rules),
            "statistics": optimizer.get_optimization_statistics(),
            "validation": optimizer.validate_optimization_config()
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get knowledge base statistics including MCP integration"""
        term_stats = self.term_mapper.get_term_statistics()
        
        stats = {
            "term_mappings": term_stats,
            "available_templates": len(getattr(self.query_engine, 'templates', {})),
            "cache_performance": {
                "hits": self.cache_hits,
                "misses": self.cache_misses,
                "hit_rate": self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
            },
            "similarity_threshold": self.similarity_matcher.similarity_threshold,
            "mcp_integration": {
                "adapter_available": self.mcp_adapter is not None,
                "cache_stats": self.mcp_adapter.get_cache_stats() if self.mcp_adapter else {}
            }
        }
        
        return stats