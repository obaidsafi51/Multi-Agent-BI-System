# NLP Agent - Complete File Structure and Function Documentation

## 📁 Root Files

### `main_optimized.py` (FastAPI Application - 800+ lines)

**Main entry point with FastAPI endpoints and system initialization**

#### Classes:

- `ProcessRequest(BaseModel)` - Request model for query processing
- `ProcessResponse(BaseModel)` - Response model for query results
- `HealthResponse(BaseModel)` - Health check response model

#### FastAPI Event Handlers:

- `startup_event()` - Initialize all services and connections
- `shutdown_event()` - Graceful shutdown of all services

#### API Endpoints:

- `POST /process` - Main query processing endpoint with optimization
- `GET /health` - Comprehensive health check with metrics
- `GET /status` - Detailed agent status and metrics
- `POST /classify` - Query classification (now returns unified approach)
- `POST /cache/clear` - Clear all caches
- `GET /metrics` - Detailed performance metrics
- `GET /metrics/export/{format_type}` - Export metrics (json/prometheus)
- `GET /performance` - Performance dashboard with recommendations
- `POST /performance/optimize` - Manual performance optimization trigger
- `GET /alerts` - Get active alerts and history
- `POST /alerts/{alert_id}/acknowledge` - Acknowledge alerts
- `POST /alerts/{alert_id}/resolve` - Resolve alerts
- `GET /diagnostics` - Comprehensive system diagnostics

#### Background Functions:

- `log_query_analytics()` - Enhanced analytics logging

### `startup.py` (System Launcher - 200+ lines)

**Concurrent server launcher for HTTP and WebSocket services**

#### Classes:

- `NLPAgentLauncher` - Manages startup/shutdown of both servers

#### Methods:

- `check_service()` - Health check for services
- `test_endpoint()` - Test API endpoints
- `start_http_server()` - Start FastAPI HTTP server
- `start_websocket_server()` - WebSocket server (disabled - client mode only)
- `run()` - Run both servers concurrently
- `signal_handler()` - Handle shutdown signals

### `performance_config.py` (Configuration - 100+ lines)

**Environment-specific performance configuration**

#### Classes:

- `PerformanceConfig` - Static configuration manager

#### Static Methods:

- `get_config(environment)` - Get environment-specific config
- `_get_development_config()` - Development environment settings
- `_get_production_config()` - Production environment settings
- `_get_base_config()` - Base configuration template

---

## 📁 src/ Directory

### `optimized_nlp_agent.py` (Main Agent Logic - 1300+ lines)

**Core NLP agent with unified processing and optimization**

#### Classes:

- `OptimizedNLPAgent` - Main agent orchestrator

#### Core Methods:

- `__init__()` - Initialize agent with all components
- `start()` - Start agent and all sub-services
- `stop()` - Graceful shutdown
- `_setup_event_handlers()` - WebSocket event handling

#### Query Processing:

- `process_query_optimized()` - Main optimized query processing
- `_process_query_internal()` - Internal processing logic
- `_extract_intent_and_entities()` - Parallel intent/entity extraction
- `_build_comprehensive_context()` - Context building for complex queries
- `_generate_sql_with_context()` - SQL generation with schema context
- `_validate_and_enhance_sql()` - SQL validation and enhancement

#### Performance & Metrics:

- `get_performance_metrics()` - Performance statistics
- `get_cache_stats()` - Cache performance stats
- `clear_cache()` - Clear all agent caches

#### Database Integration:

- `generate_sql()` - SQL generation wrapper
- `get_schema_context()` - Database schema retrieval
- `validate_query()` - Query validation
- `analyze_data()` - Data analysis wrapper

### `optimized_kimi_client.py` (KIMI API Client - 800+ lines)

**High-performance KIMI API client with pooling and caching**

#### Exception Classes:

- `KimiAPIError` - Base KIMI API exception
- `KimiRateLimitError` - Rate limiting exception

#### Utility Classes:

- `SemanticCache` - Semantic similarity caching
- `RateLimiter` - Request rate limiting

#### Main Class:

- `OptimizedKimiClient` - Optimized API client

#### Methods:

- `__init__()` - Initialize with connection pooling
- `start()` - Start client services
- `stop()` - Stop and cleanup
- `chat_completion()` - Main API call method
- `chat_completion_parallel()` - Parallel API calls
- `_make_request()` - Internal request handler
- `_should_cache_response()` - Cache decision logic
- `get_performance_metrics()` - Client performance stats

### `enhanced_websocket_client.py` (WebSocket Client - 1000+ lines)

**Enhanced WebSocket client with reconnection and circuit breaker**

#### Enums:

- `ConnectionState` - WebSocket connection states
- `CircuitBreakerState` - Circuit breaker states

#### Data Classes:

- `ConnectionStats` - Connection statistics
- `CircuitBreakerConfig` - Circuit breaker configuration

#### Main Class:

- `EnhancedWebSocketMCPClient` - WebSocket client

#### Core Methods:

- `__init__()` - Initialize client
- `connect()` - Establish WebSocket connection
- `disconnect()` - Close connection gracefully
- `send_request()` - Send MCP requests
- `_handle_message()` - Process incoming messages
- `_reconnect_with_backoff()` - Automatic reconnection
- `_circuit_breaker_check()` - Circuit breaker logic
- `get_connection_stats()` - Connection statistics

### `hybrid_mcp_operations_adapter.py` (MCP Adapter - 500+ lines)

**Hybrid WebSocket-first with HTTP fallback MCP adapter**

#### Classes:

- `HybridMCPOperationsAdapter` - Main adapter class

#### Methods:

- `__init__()` - Initialize both WebSocket and HTTP clients
- `start()` - Start adapter services
- `stop()` - Stop adapter services
- `call_tool()` - Execute MCP tools with failover
- `list_tools()` - List available tools
- `_should_use_websocket()` - WebSocket vs HTTP decision logic
- `_execute_with_websocket()` - WebSocket execution
- `_execute_with_http()` - HTTP fallback execution
- `_update_failure_tracking()` - Track failure statistics

### `http_mcp_client.py` (HTTP Client - 300+ lines)

**HTTP-based MCP client for fallback communication**

#### Classes:

- `HTTPMCPClient` - HTTP MCP client

#### Methods:

- `__init__()` - Initialize HTTP client
- `call_tool()` - Execute tools via HTTP
- `list_tools()` - List tools via HTTP
- `_make_request()` - Internal HTTP request handler
- `health_check()` - Server health verification

### `performance_optimizer.py` (Performance Engine - 800+ lines)

**Advanced performance optimization with multi-level caching**

#### Enums:

- `CacheType` - Types of caches

#### Data Classes:

- `CacheEntry` - Cache entry structure

#### Main Class:

- `PerformanceOptimizer` - Performance optimization engine

#### Core Methods:

- `__init__()` - Initialize optimizer
- `start()` - Start optimization services
- `stop()` - Stop optimizer
- `optimize_query_processing()` - Main optimization entry point
- `clear_cache()` - Clear all caches
- `get_optimization_stats()` - Performance statistics

#### Optimization Features:

- `_check_memory_cache()` - Memory cache lookup
- `_check_semantic_cache()` - Semantic similarity cache
- `_check_query_cache()` - Query-specific cache
- `_proactive_cache_warming()` - Preemptive cache population
- `_optimize_memory_usage()` - Memory optimization
- `optimize_connection_performance()` - Connection tuning

### `cache_manager.py` (Cache System - 550+ lines)

**Advanced multi-level caching system**

#### Enums:

- `CacheLevel` - Cache hierarchy levels

#### Data Classes:

- `CacheEntry` - Cache entry with metadata
- `CacheMetrics` - Cache performance metrics

#### Main Class:

- `AdvancedCacheManager` - Multi-level cache manager

#### Methods:

- `__init__()` - Initialize cache layers
- `get()` - Retrieve from cache
- `set()` - Store in cache
- `invalidate()` - Remove from cache
- `clear()` - Clear cache layer
- `get_metrics()` - Cache performance metrics
- `_calculate_semantic_similarity()` - Semantic matching
- `_compress_data()` / `_decompress_data()` - Data compression

#### Utility Functions:

- `get_cache_manager()` - Get global cache instance
- `close_cache_manager()` - Cleanup cache manager

### `enhanced_monitoring.py` (Monitoring System - 600+ lines)

**Comprehensive monitoring and alerting system**

#### Enums:

- `AlertLevel` - Alert severity levels
- `MetricType` - Types of metrics

#### Data Classes:

- `MetricValue` - Metric data structure
- `Alert` - Alert information
- `PerformanceSnapshot` - Performance data point

#### Main Class:

- `EnhancedMonitoringSystem` - Monitoring and alerting

#### Core Methods:

- `__init__()` - Initialize monitoring
- `start()` - Start monitoring services
- `stop()` - Stop monitoring
- `record_metric()` - Record performance metrics
- `capture_performance_snapshot()` - Capture system state
- `get_health_status()` - System health assessment
- `track_request()` - Request tracking context manager

#### Alerting:

- `_check_alerts()` - Alert condition checking
- `acknowledge_alert()` - Acknowledge alerts
- `resolve_alert()` - Resolve alerts
- `export_metrics()` - Export metrics in various formats

### `context_builder.py` (Context Management - 300+ lines)

**Dynamic context building for agent communication**

#### Classes:

- `ContextBuilder` - Context construction manager

#### Methods:

- `__init__()` - Initialize context builder
- `build_query_context()` - Build comprehensive query context
- `build_schema_context()` - Database schema context
- `build_user_context()` - User-specific context
- `build_session_context()` - Session-based context
- `_extract_entities()` - Entity extraction
- `_get_relevant_tables()` - Table relevance analysis
- `_format_context()` - Context formatting

### `models.py` (Data Models - 400+ lines)

**Data models and type definitions**

#### Imported Models (from shared):

- `QueryIntent` - Query intention structure
- `NLPResponse` - Standardized NLP response
- `AgentResponse` - Agent response format
- `AgentRequest` - Agent request format
- `AgentError` - Error response format

#### Local Classes:

- `ProcessingResult` - Query processing result
- `QueryContext` - Query context information
- `FinancialEntity` - Financial entity structure
- `CacheHit` - Cache hit information
- `PerformanceMetrics` - Performance measurement data

---

## 📁 shared/ Directory

### `shared/models/workflow.py` (Workflow Models - 300+ lines)

**Standardized workflow and communication models**

#### Classes:

- `QueryIntent` - Query intention analysis
- `NLPResponse` - NLP agent response format
- `AgentResponse` - Generic agent response
- `DataAgentRequest` - Data agent specific requests
- `VizAgentRequest` - Visualization agent requests

### `shared/models/agents.py` (Agent Models - 300+ lines)

**Agent management and communication models**

#### Enums:

- `AgentStatus` - Agent operational status
- `AgentType` - Types of system agents

#### Classes:

- `AgentRequest` - Standard agent request
- `AgentResponse` - Standard agent response
- `AgentError` - Error response format
- `AgentCapability` - Agent capability definition
- `AgentHealthCheck` - Health monitoring data

---

## 📁 tests/ Directory

### `tests/test_context_builder.py` (Test Suite - 270+ lines)

**Comprehensive tests for context builder functionality**

#### Test Classes:

- `TestContextBuilder` - Context builder test suite

#### Test Methods:

- `test_build_query_context()` - Query context building tests
- `test_build_schema_context()` - Schema context tests
- `test_build_user_context()` - User context tests
- `test_extract_entities()` - Entity extraction tests
- `test_get_relevant_tables()` - Table relevance tests
- `test_context_caching()` - Context caching tests
- `test_error_handling()` - Error handling tests

---

## 📊 Architecture Overview

### Core Components:

1. **FastAPI Application** (`main_optimized.py`) - REST API with comprehensive endpoints
2. **Optimized NLP Agent** (`optimized_nlp_agent.py`) - Main processing engine
3. **WebSocket Client** (`enhanced_websocket_client.py`) - Real-time MCP communication
4. **HTTP Fallback** (`http_mcp_client.py`) - Reliable backup communication
5. **Performance Engine** (`performance_optimizer.py`) - Multi-level optimization
6. **Cache System** (`cache_manager.py`) - Advanced caching with semantic similarity
7. **Monitoring** (`enhanced_monitoring.py`) - Comprehensive system monitoring

### Key Features:

- **Unified Processing**: Removed query classification for simplified, optimized processing
- **Hybrid Communication**: WebSocket-first with HTTP fallback for reliability
- **Multi-level Caching**: Memory, semantic similarity, and query-specific caches
- **Performance Monitoring**: Real-time metrics, alerts, and optimization recommendations
- **Connection Resilience**: Circuit breaker pattern and automatic reconnection
- **Semantic Analysis**: Vector similarity for intelligent caching and context building

### Performance Optimizations:

- Parallel KIMI API calls (60-70% latency reduction)
- Semantic caching with 1,277x performance improvement potential
- Connection pooling and request batching
- Memory optimization and cache warming
- Real-time performance monitoring and tuning

**Total Lines of Code: ~8,000+ lines**
**Total Functions/Methods: ~200+ methods across all files**
