# Dynamic Schema Management Implementation Plan

## Overview

This implementation plan provides a structured approach to migrating from static configuration to dynamic schema management in the AGENT BI system. The plan is divided into phases that can be executed iteratively while maintaining system functionality throughout the migration process.

## Implementation Phases

### Phase 1: Foundation and Core Infrastructure

- [x] 1. Create Dynamic Schema Management Infrastructure

  - Create new `backend/schema_management/` directory structure
  - Implement `DynamicSchemaManager` class with basic MCP integration
  - Create `EnhancedMCPClient` extending existing `BackendMCPClient`
  - Add configuration models for schema discovery, caching, and semantic mapping
  - Create error handling framework with fallback strategies
  - Implement basic logging and monitoring for schema operations
  - Write unit tests for core infrastructure components
  - _Requirements: 1.1, 1.4, 1.5, 6.1, 6.2, 10.1, 11.1_

- [x] 2. Implement Enhanced Schema Cache System

  - Create `EnhancedSchemaCache` class with TTL-based caching
  - Implement semantic metadata caching for business term mappings
  - Add cache warming strategies and prefetching capabilities
  - Create cache invalidation patterns and consistency mechanisms
  - Implement distributed cache synchronization across agents
  - Add cache performance monitoring and statistics collection
  - Create cache cleanup and memory management strategies
  - Write comprehensive unit tests for cache operations
  - _Requirements: 1.5, 6.1, 6.2, 6.3, 6.4, 6.5, 11.2, 11.3_

- [x] 3. Create Configuration Management System

  - Implement `ConfigurationManager` class with multi-source loading
  - Create configuration validation and hot-reload capabilities
  - Add environment-specific configuration support (dev/staging/prod)
  - Implement configuration versioning and rollback mechanisms
  - Create configuration API endpoints for runtime updates
  - Add configuration change notification system
  - Implement configuration backup and checkpoint creation
  - Write unit tests for configuration management functionality
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 7.1, 7.2, 7.3, 7.4, 7.5_

### Phase 2: Semantic Understanding and Query Intelligence

- [x] 4. Build Semantic Schema Mapper

  - Create `SemanticSchemaMapper` class with NLP-based analysis
  - Implement business term to database object mapping algorithms
  - Add similarity matching using cosine similarity and fuzzy matching
  - Create confidence scoring system for mapping quality assessment
  - Implement learning system for successful mapping reinforcement
  - Add support for synonyms and alternative term recognition
  - Create semantic metadata extraction from table/column comments
  - Write unit tests for semantic mapping accuracy and performance
  - _Requirements: 2.2, 2.3, 3.1, 3.2, 3.3, 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 5. Implement Intelligent Query Builder

  - Create `IntelligentQueryBuilder` class replacing static SQL templates
  - Implement dynamic SQL generation based on discovered schema
  - Add query optimization using discovered indexes and constraints
  - Create alternative query suggestion engine for failed queries
  - Implement query validation against real-time schema information
  - Add support for complex joins and aggregations based on schema relationships
  - Create query performance prediction and optimization recommendations
  - Write comprehensive unit tests for query generation and validation
  - _Requirements: 2.1, 2.4, 2.5, 10.2, 10.3, 11.4_

- [x] 6. Create Schema Change Detection System

  - Implement `SchemaChangeDetector` class with real-time monitoring
  - Add database trigger-based change detection for immediate notifications
  - Create change impact analysis and severity classification
  - Implement automatic cache invalidation upon schema changes
  - Add change notification system for agent synchronization
  - Create migration recommendation engine for breaking changes
  - Implement change audit logging and history tracking
  - Write unit tests for change detection accuracy and performance
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 9.1, 9.2, 11.5_

### Phase 3: Agent Integration and Migration

- [x] 7. Migrate NLP Agent to Dynamic Schema

  - Replace hardcoded SQL templates in `nlp-agent/main.py` with dynamic query builder
  - Update `generate_sql_from_intent()` to use semantic schema mapping
  - Integrate `DynamicSchemaManager` for real-time schema discovery
  - Replace static metric-to-table mappings with semantic understanding
  - Add query validation against discovered schema before execution
  - Update error handling to provide schema-aware suggestions
  - Implement fallback mechanisms for schema discovery failures
  - Write integration tests for NLP agent with dynamic schema
  - _Requirements: 2.1, 2.2, 2.5, 3.4, 9.4, 10.1, 10.2_

- [x] 8. Migrate Data Agent to Dynamic Schema

  - Replace static cache tags in `data-agent/src/agent.py` with dynamic generation
  - Update `_generate_cache_tags()` to use discovered table information
  - Integrate semantic mapper for flexible metric-to-table mapping
  - Replace hardcoded table name references with dynamic discovery
  - Update data validation to use real-time schema information
  - Implement intelligent cache invalidation based on schema changes
  - Add schema-aware query optimization in the query optimizer
  - Write integration tests for Data agent with dynamic schema management
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 5.1, 5.2, 9.2, 10.1_

- [x] 9. Update Backend Gateway with Dynamic Configuration

  - Replace static SQL generation in `backend/main.py` fallback functions
  - Integrate `ConfigurationManager` for runtime configuration updates
  - Add schema discovery API endpoints for frontend consumption
  - Update `send_to_nlp_agent()` to include dynamic schema context
  - Implement configuration validation endpoints for admin interface
  - Add health checks for dynamic schema management components
  - Create monitoring endpoints for schema cache and configuration status
  - Write integration tests for backend gateway with dynamic schema
  - _Requirements: 4.1, 4.2, 7.1, 7.2, 7.3, 9.1, 9.3, 11.1, 11.5_

### Phase 4: Advanced Features and Optimization

- [x] 10. Implement AI-Enhanced Semantic Mapping with KIMI

  - Integrate KIMI API for semantic similarity analysis and business term mapping
  - Add query success pattern analysis using KIMI's conversation history
  - Create user feedback integration system for mapping quality enhancement
  - Implement intelligent caching of AI-generated semantic mappings
  - Add confidence scoring based on KIMI responses and historical success
  - Implement cost-aware API usage optimization and rate limiting for KIMI
  - Create fallback to basic fuzzy matching when KIMI is unavailable
  - Write unit tests for KIMI-enhanced semantic mapping functionality
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 11.4_

### Phase 5: Performance Optimization and Cleanup

- [x] 13. Performance Optimization and Tuning

  - ✅ Optimize schema discovery queries for large database schemas
  - ✅ Implement intelligent cache warming and prefetching strategies
  - ✅ Add query generation performance optimization with index hints
  - ✅ Create adaptive TTL strategies based on schema change frequency
  - ✅ Implement connection pooling optimization for MCP clients
  - ✅ Add lazy loading and pagination for large schema discovery results
  - ✅ Create performance benchmarking and continuous monitoring
  - ✅ Write performance tests and load testing scenarios
  - _Requirements: 6.4, 6.5, 10.4, 11.4_

- [x] 14. Remove Static Dependencies and Final Migration

  - ✅ Remove all hardcoded table names, column mappings, and SQL templates
  - ✅ Delete static schema configuration files and migration scripts
  - ✅ Update all agent imports to use dynamic schema management
  - ✅ Remove static fallback mechanisms and legacy code paths
  - ✅ Update documentation to reflect dynamic schema management approach
  - ✅ Create migration guides and troubleshooting documentation
  - ✅ Implement final validation tests for complete static dependency removal
  - ✅ Create rollback procedures and emergency static schema restoration
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 10.1, 10.2, 10.3, 10.4, 10.5_

## Detailed Implementation Tasks

### Task 1: Dynamic Schema Manager Core Implementation

```python
# Location: backend/schema_management/dynamic_schema_manager.py

class DynamicSchemaManager:
    """Core manager for dynamic schema operations"""

    def __init__(self, mcp_client: EnhancedMCPClient, cache: EnhancedSchemaCache):
        self.mcp_client = mcp_client
        self.cache = cache
        self.semantic_mapper = SemanticSchemaMapper()
        self.change_detector = SchemaChangeDetector()
        self.query_builder = IntelligentQueryBuilder()

    async def discover_schema(self, force_refresh: bool = False) -> SchemaInfo:
        """Discover complete database schema with semantic analysis"""
        cache_key = "complete_schema"

        if not force_refresh:
            if cached := await self.cache.get_schema(cache_key):
                return cached

        # Discover schema from MCP server
        databases = await self.mcp_client.discover_databases()
        schema_info = SchemaInfo()

        for db in databases:
            tables = await self.mcp_client.get_tables(db.name)
            for table in tables:
                table_schema = await self.mcp_client.get_table_schema(db.name, table.name)
                enhanced_table = await self.semantic_mapper.analyze_table(table_schema)
                schema_info.tables.append(enhanced_table)

        # Cache with intelligent TTL
        ttl = await self._calculate_cache_ttl(schema_info)
        await self.cache.set_schema(cache_key, schema_info, ttl)

        return schema_info
```

### Task 2: Semantic Schema Mapper Implementation

```python
# Location: backend/schema_management/semantic_mapper.py

class SemanticSchemaMapper:
    """Maps business terms to database schema elements using semantic analysis"""

    def __init__(self, config: SemanticMappingConfig):
        self.config = config
        self.similarity_model = self._load_similarity_model()
        self.business_terms = self._load_business_terms()
        self.learned_mappings = {}

    async def map_business_term(self, term: str, context: str = None) -> List[SchemaMapping]:
        """Map business term to database schema elements"""
        # Check learned mappings first
        if learned := self.learned_mappings.get(term):
            return learned

        # Use semantic similarity
        candidates = await self._find_semantic_candidates(term, context)

        # Rank by confidence
        ranked_mappings = await self._rank_mappings(term, candidates)

        # Filter by confidence threshold
        valid_mappings = [
            mapping for mapping in ranked_mappings
            if mapping.confidence_score >= self.config.confidence_threshold
        ]

        return valid_mappings[:self.config.max_suggestions]

    async def _find_semantic_candidates(self, term: str, context: str) -> List[SchemaElement]:
        """Find schema elements semantically similar to business term"""
        # Implementation using word embeddings, fuzzy matching, etc.
        pass
```

### Task 2.1: AI-Enhanced Semantic Mapper with Hosted Models

```python
# Location: backend/schema_management/ai_semantic_mapper.py

import asyncio
import os
from typing import List, Dict, Optional, Any
import json
import aiohttp
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class SemanticMapping:
    table_name: str
    column_name: str
    confidence_score: float
    mapping_type: str  # 'exact', 'partial', 'synonym'
    ai_explanation: str
    source_api: str

class AISemanticMapper:
    """Maps business terms using KIMI API with fuzzy matching fallback"""

    def __init__(self, config: SemanticMappingConfig):
        self.config = config
        self.kimi_api_key = os.getenv('KIMI_API_KEY')
        self.mapping_cache = {}
        self.api_usage_tracker = {}

    async def map_business_term(self, term: str, schema_elements: List[Dict], context: str = None) -> List[SemanticMapping]:
        """Map business term using KIMI API with fallback to fuzzy matching"""

        # Check cache first
        cache_key = f"{term}:{hash(str(schema_elements))}"
        if cache_key in self.mapping_cache:
            cached_result = self.mapping_cache[cache_key]
            if datetime.now() - cached_result['timestamp'] < timedelta(hours=24):
                return cached_result['mappings']

        # Try KIMI API first
        try:
            if await self._is_kimi_available():
                mappings = await self._map_with_kimi(term, schema_elements, context)

                # Cache successful result
                self.mapping_cache[cache_key] = {
                    'mappings': mappings,
                    'timestamp': datetime.now()
                }

                return mappings

        except Exception as e:
            logger.warning(f"Failed to use KIMI for semantic mapping: {e}")

        # Fallback to basic fuzzy matching if KIMI fails
        return await self._fallback_fuzzy_matching(term, schema_elements)

    async def _map_with_kimi(self, term: str, schema_elements: List[Dict], context: str = None) -> List[SemanticMapping]:
        """Use KIMI API for semantic mapping"""

        # Rate limiting check
        if not await self._check_rate_limit('kimi'):
            raise Exception("KIMI API rate limit exceeded")

        prompt = self._build_kimi_prompt(term, schema_elements, context)

        async with aiohttp.ClientSession() as session:
            headers = {
                'Authorization': f'Bearer {self.kimi_api_key}',
                'Content-Type': 'application/json'
            }

            payload = {
                'model': 'moonshot-v1-8k',
                'messages': [
                    {'role': 'system', 'content': self._get_system_prompt()},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.1
            }

            async with session.post('https://api.moonshot.ai/v1/chat/completions',
                                  headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return await self._parse_kimi_response(result, term)
                else:
                    raise Exception(f"KIMI API error: {response.status}")

    def _build_kimi_prompt(self, term: str, schema_elements: List[Dict], context: str = None) -> str:
        """Build prompt for KIMI API"""
        schema_desc = "\n".join([
            f"- {elem['table_name']}.{elem['column_name']}: {elem.get('description', 'No description')}"
            for elem in schema_elements
        ])

        return f"""
        Business Term: "{term}"
        Context: {context or "None provided"}

        Available Database Schema Elements:
        {schema_desc}

        Please identify which schema elements best match the business term "{term}".
        Return your response as JSON with this structure:
        {{
            "mappings": [
                {{
                    "table_name": "table_name",
                    "column_name": "column_name",
                    "confidence_score": 0.95,
                    "mapping_type": "exact|partial|synonym",
                    "explanation": "Why this mapping makes sense"
                }}
            ]
        }}

        Only include mappings with confidence score > 0.7.
        """

    def _get_system_prompt(self) -> str:
        """Get system prompt for AI models"""
        return """You are an expert database schema analyst. Your job is to map business terms to database schema elements (tables and columns).

        Consider:
        - Exact matches have highest confidence
        - Synonym matches have medium confidence
        - Partial or contextual matches have lower confidence
        - Business context and domain knowledge
        - Common naming conventions in databases

        Always explain your reasoning and provide confidence scores between 0.0 and 1.0."""

    async def _is_kimi_available(self) -> bool:
        """Check if KIMI API is available and configured"""
        return bool(self.kimi_api_key)

    async def _check_rate_limit(self, service: str) -> bool:
        """Check if we're within rate limits for KIMI"""
        now = datetime.now()
        usage_key = f"kimi_{now.strftime('%H')}"  # Per hour tracking

        if usage_key not in self.api_usage_tracker:
            self.api_usage_tracker[usage_key] = 0

        # KIMI free tier: 50 requests per hour
        return self.api_usage_tracker[usage_key] < 50

    async def _fallback_fuzzy_matching(self, term: str, schema_elements: List[Dict]) -> List[SemanticMapping]:
        """Fallback to basic fuzzy string matching when KIMI is unavailable"""
        from difflib import SequenceMatcher

        mappings = []
        for element in schema_elements:
            # Check similarity with table name
            table_similarity = SequenceMatcher(None, term.lower(), element['table_name'].lower()).ratio()

            # Check similarity with column name
            column_similarity = SequenceMatcher(None, term.lower(), element['column_name'].lower()).ratio()

            # Use the higher similarity
            max_similarity = max(table_similarity, column_similarity)

            if max_similarity > 0.6:  # Basic threshold
                mappings.append(SemanticMapping(
                    table_name=element['table_name'],
                    column_name=element['column_name'],
                    confidence_score=max_similarity,
                    mapping_type='fuzzy',
                    ai_explanation=f"Fuzzy string matching: {max_similarity:.2f}",
                    source_api='fallback'
                ))

        return sorted(mappings, key=lambda x: x.confidence_score, reverse=True)[:3]
```

### Task 3: Intelligent Query Builder Implementation

```python
# Location: backend/schema_management/query_builder.py

class IntelligentQueryBuilder:
    """Builds SQL queries dynamically using discovered schema"""

    async def build_query(self, intent: QueryIntent, schema_context: SchemaContext) -> QueryResult:
        """Build SQL query from intent using dynamic schema"""

        # Find relevant tables for metrics
        table_mappings = await self._find_tables_for_metrics(intent.metric_type, schema_context)

        if not table_mappings:
            raise QueryBuildError(f"No tables found for metric: {intent.metric_type}")

        # Select best table based on data quality and completeness
        primary_table = await self._select_primary_table(table_mappings, intent)

        # Build SELECT clause
        select_clause = await self._build_select_clause(intent, primary_table)

        # Build FROM clause with intelligent joins
        from_clause = await self._build_from_clause(primary_table, schema_context)

        # Build WHERE clause with dynamic filters
        where_clause = await self._build_where_clause(intent, primary_table)

        # Build GROUP BY and ORDER BY clauses
        group_by_clause = await self._build_group_by_clause(intent, primary_table)
        order_by_clause = await self._build_order_by_clause(intent, primary_table)

        # Combine into final query
        query = self._combine_query_parts(
            select_clause, from_clause, where_clause,
            group_by_clause, order_by_clause
        )

        return QueryResult(
            sql=query,
            parameters={},
            estimated_rows=await self._estimate_result_size(query),
            optimization_hints=await self._generate_optimization_hints(query, schema_context)
        )
```

### Task 4: Agent Integration Example (NLP Agent)

```python
# Location: agents/nlp-agent/src/dynamic_nlp_agent.py

class DynamicNLPAgent(NLPAgent):
    """Enhanced NLP Agent with dynamic schema management"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.schema_manager = DynamicSchemaManager()
        self.query_builder = IntelligentQueryBuilder()
        self.ai_semantic_mapper = AISemanticMapper()  # Use AI-enhanced semantic mapper

    async def process_query(self, query: str, user_id: str, session_id: str, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """Process query with dynamic schema discovery"""

        # Extract intent using KIMI as before
        intent = await self.query_parser.parse_intent(query, context)

        # Discover current schema
        schema_context = await self.schema_manager.discover_schema()

        # Map intent to actual database elements using AI-enhanced semantic mapping
        schema_elements = await self.schema_manager.get_all_schema_elements()
        table_mappings = await self.ai_semantic_mapper.map_business_term(
            intent.metric_type,
            schema_elements,
            context=f"User query: {query}"
        )

        # Filter for high-confidence table mappings
        high_confidence_mappings = [
            mapping for mapping in table_mappings
            if mapping.confidence_score > 0.8
        ]

        if not high_confidence_mappings:
            # Try with lower confidence threshold and suggest alternatives
            all_mappings = [m for m in table_mappings if m.confidence_score > 0.6]
            if all_mappings:
                suggestions = [f"{m.table_name}.{m.column_name} ({m.confidence_score:.2f})" for m in all_mappings[:3]]
                return ProcessingResult(
                    success=False,
                    error=f"No high-confidence matches found for '{intent.metric_type}'. Did you mean: {', '.join(suggestions)}?",
                    suggestions=suggestions,
                    ai_explanations=[m.ai_explanation for m in all_mappings[:3]]
                )
            else:
                return ProcessingResult(
                    success=False,
                    error=f"No relevant data found for '{intent.metric_type}'. Please try rephrasing your query.",
                    suggestions=[]
                )

        # Build query dynamically
        query_result = await self.query_builder.build_query(intent, schema_context)

        # Create enhanced query context
        enhanced_context = QueryContext(
            intent=intent,
            table_mappings=table_mappings,
            column_mappings=column_mappings,
            discovered_schema=schema_context,
            generated_query=query_result.sql
        )

        return ProcessingResult(
            success=True,
            intent=intent,
            sql_query=query_result.sql,
            query_context=enhanced_context,
            processing_time_ms=query_result.processing_time_ms
        )
```

## Testing Strategy

### Comprehensive Test Suite Structure

```
tests/dynamic_schema_management/
├── unit/
│   ├── test_dynamic_schema_manager.py
│   ├── test_semantic_mapper.py
│   ├── test_query_builder.py
│   ├── test_configuration_manager.py
│   ├── test_change_detector.py
│   └── test_enhanced_cache.py
├── integration/
│   ├── test_nlp_agent_integration.py
│   ├── test_data_agent_integration.py
│   ├── test_backend_integration.py
│   ├── test_mcp_integration.py
│   └── test_cross_agent_sync.py
├── performance/
│   ├── test_schema_discovery_performance.py
│   ├── test_query_generation_performance.py
│   ├── test_cache_performance.py
│   └── test_load_testing.py
├── migration/
│   ├── test_backward_compatibility.py
│   ├── test_static_to_dynamic_migration.py
│   ├── test_rollback_scenarios.py
│   └── test_data_integrity.py
└── fixtures/
    ├── sample_schemas/
    ├── test_configurations/
    ├── mock_databases/
    └── performance_baselines/
```

### Performance Benchmarks

```python
class DynamicSchemaPerformanceBenchmarks:
    """Performance targets for dynamic schema management"""

    # Discovery performance targets
    SCHEMA_DISCOVERY_MAX_TIME = 30.0  # seconds
    SEMANTIC_MAPPING_MAX_TIME = 5.0   # seconds
    QUERY_GENERATION_MAX_TIME = 10.0  # seconds

    # Cache performance targets
    CACHE_HIT_RATE_TARGET = 0.85
    CACHE_OPERATION_MAX_TIME = 1.0  # second

    # Accuracy targets
    SEMANTIC_MAPPING_ACCURACY = 0.85
    QUERY_GENERATION_SUCCESS_RATE = 0.90
    SCHEMA_CHANGE_DETECTION_ACCURACY = 0.95

    # System performance targets
    SYSTEM_RESPONSE_TIME_P95 = 10.0  # seconds
    CONCURRENT_USER_SUPPORT = 50
    MEMORY_USAGE_MAX_INCREASE = 0.20  # 20% over static system
```

## Rollback Strategy

### Emergency Rollback Procedures

```python
class EmergencyRollbackManager:
    """Manages emergency rollback to static schema management"""

    async def initiate_emergency_rollback(self, reason: str) -> RollbackResult:
        """Rollback to static schema management in case of critical issues"""

        logger.critical(f"Initiating emergency rollback: {reason}")

        # 1. Disable dynamic schema management
        await self.config_manager.set_configuration("dynamic_schema.enabled", False)

        # 2. Restore static configuration
        await self._restore_static_configurations()

        # 3. Clear dynamic caches
        await self.cache_manager.clear_all_dynamic_caches()

        # 4. Restart affected agents with static mode
        await self._restart_agents_static_mode()

        # 5. Validate system functionality
        validation_result = await self._validate_static_mode_functionality()

        return RollbackResult(
            success=validation_result.success,
            rollback_time_ms=validation_result.rollback_duration,
            affected_components=validation_result.affected_components,
            restoration_status=validation_result.restoration_status
        )
```

## AI-Enhanced Semantic Mapping Configuration

### Hosted Model Configuration

To implement the AI-enhanced semantic mapping using KIMI API:

#### KIMI (Moonshot AI)

```bash
# Environment variables needed
KIMI_API_KEY=your_kimi_api_key_here

# Rate limits (free tier)
- 50 requests per hour
- 200 requests per day
- Cost: Free for basic usage
```

### Cost-Effective Usage Strategy

1. **Caching Strategy**: Cache KIMI responses for 24 hours to minimize API calls
2. **Confidence Thresholds**: Only use KIMI for complex mappings; use fuzzy matching for obvious ones
3. **Rate Limiting**: Implement smart rate limiting to stay within KIMI free tier
4. **Fallback Strategy**: Use fuzzy string matching when KIMI is unavailable

### Performance Optimizations

```python
# Example configuration for cost-effective KIMI usage
SEMANTIC_MAPPING_CONFIG = {
    "confidence_threshold": 0.7,
    "max_suggestions": 5,
    "cache_ttl_hours": 24,
    "use_fuzzy_first": True,  # Try fuzzy matching before KIMI
    "fuzzy_threshold": 0.8,   # Only use KIMI if fuzzy matching fails
    "rate_limit_buffer": 0.8  # Use only 80% of KIMI rate limit
}
```

This approach allows you to leverage KIMI's powerful AI capabilities for semantic mapping while maintaining cost-effectiveness through intelligent caching and fuzzy matching fallback strategies.

This comprehensive implementation plan provides a structured approach to migrating the system from static configuration to dynamic schema management while maintaining reliability, performance, and the ability to rollback if needed.
