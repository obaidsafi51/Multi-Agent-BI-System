"""
Performance Benchmarking and Load Testing for Dynamic Schema Management.

This module provides comprehensive performance testing and benchmarking
capabilities for the dynamic schema management system.
"""

import asyncio
import logging
import time
import json
import statistics
import random
from typing import Dict, Any, Optional, List, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import aiohttp

from .dynamic_schema_manager import DynamicSchemaManager
from .performance_optimizer import (
    SchemaDiscoveryOptimizer, IntelligentCacheWarmer, 
    PerformanceMetrics, OptimizationLevel
)
from .connection_pool import MCPConnectionPool, OptimizedMCPClient

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Results from a performance benchmark."""
    test_name: str
    duration_seconds: float
    operations_count: int
    operations_per_second: float
    average_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    error_rate: float
    memory_usage_mb: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LoadTestConfig:
    """Configuration for load testing."""
    concurrent_users: int = 10
    duration_seconds: int = 60
    ramp_up_seconds: int = 10
    operations_per_user: int = 100
    think_time_seconds: float = 1.0
    max_errors_threshold: float = 0.05  # 5%
    target_response_time_ms: float = 5000  # 5 seconds


class SchemaBenchmarkSuite:
    """Comprehensive benchmark suite for schema management performance."""
    
    def __init__(
        self,
        schema_manager: DynamicSchemaManager,
        schema_optimizer: SchemaDiscoveryOptimizer,
        cache_warmer: IntelligentCacheWarmer,
        connection_pool: MCPConnectionPool
    ):
        """
        Initialize benchmark suite.
        
        Args:
            schema_manager: Dynamic schema manager instance
            schema_optimizer: Schema discovery optimizer
            cache_warmer: Cache warming component
            connection_pool: Connection pool for testing
        """
        self.schema_manager = schema_manager
        self.schema_optimizer = schema_optimizer
        self.cache_warmer = cache_warmer
        self.connection_pool = connection_pool
        
        # Benchmark results storage
        self.benchmark_results: List[BenchmarkResult] = []
        
        # Test data - initialize dynamically from schema
        self.test_databases = ["test_db_1", "test_db_2", "test_db_3"]
        self.test_tables = []  # Will be populated dynamically
        self.test_metrics = []  # Will be populated dynamically
        
    async def _initialize_test_data(self):
        """Initialize test data dynamically from schema."""
        from .manager import DynamicSchemaManager
        schema_manager = DynamicSchemaManager()
        await schema_manager.initialize()
        
        # Get tables dynamically
        self.test_tables = await schema_manager.get_table_names()
        
        # Extract metrics dynamically from first available table
        if self.test_tables:
            table_schema = await schema_manager.get_table_schema(self.test_tables[0])
            self.test_metrics = list(table_schema.get('columns', {}).keys())[:8]  # Limit to 8 for testing
    
    async def run_full_benchmark_suite(self) -> Dict[str, Any]:
        """
        Run the complete benchmark suite.
        
        Returns:
            Comprehensive benchmark results
        """
        # Initialize test data dynamically
        await self._initialize_test_data()
        logger.info("Starting full benchmark suite")
        start_time = time.time()
        
        suite_results = {
            "suite_start_time": datetime.now().isoformat(),
            "benchmarks": {},
            "summary": {},
            "recommendations": []
        }
        
        try:
            # 1. Schema Discovery Performance
            logger.info("Running schema discovery benchmarks")
            discovery_results = await self._benchmark_schema_discovery()
            suite_results["benchmarks"]["schema_discovery"] = discovery_results
            
            # 2. Cache Performance
            logger.info("Running cache performance benchmarks")
            cache_results = await self._benchmark_cache_performance()
            suite_results["benchmarks"]["cache_performance"] = cache_results
            
            # 3. Query Generation Performance
            logger.info("Running query generation benchmarks")
            query_results = await self._benchmark_query_generation()
            suite_results["benchmarks"]["query_generation"] = query_results
            
            # 4. Connection Pool Performance
            logger.info("Running connection pool benchmarks")
            pool_results = await self._benchmark_connection_pool()
            suite_results["benchmarks"]["connection_pool"] = pool_results
            
            # 5. Load Testing
            logger.info("Running load tests")
            load_results = await self._run_load_tests()
            suite_results["benchmarks"]["load_testing"] = load_results
            
            # 6. Memory and Resource Usage
            logger.info("Running resource usage tests")
            resource_results = await self._benchmark_resource_usage()
            suite_results["benchmarks"]["resource_usage"] = resource_results
            
            # Generate summary and recommendations
            suite_results["summary"] = self._generate_summary()
            suite_results["recommendations"] = self._generate_recommendations()
            
            total_duration = time.time() - start_time
            suite_results["total_duration_seconds"] = total_duration
            
            logger.info(f"Benchmark suite completed in {total_duration:.2f} seconds")
            
            return suite_results
            
        except Exception as e:
            logger.error(f"Benchmark suite failed: {e}")
            suite_results["error"] = str(e)
            return suite_results
    
    async def _benchmark_schema_discovery(self) -> Dict[str, Any]:
        """Benchmark schema discovery performance."""
        results = {}
        
        # Test different optimization levels
        optimization_levels = [
            OptimizationLevel.BASIC,
            OptimizationLevel.INTERMEDIATE,
            OptimizationLevel.AGGRESSIVE
        ]
        
        for level in optimization_levels:
            logger.info(f"Testing schema discovery with {level.value} optimization")
            
            # Create optimizer with specific level
            optimizer = SchemaDiscoveryOptimizer(
                self.schema_optimizer.mcp_client,
                optimization_level=level
            )
            
            # Run multiple discovery operations
            latencies = []
            errors = 0
            
            for i in range(10):  # 10 discovery operations
                try:
                    start_time = time.time()
                    
                    # Discover schema for test database
                    db_name = random.choice(self.test_databases)
                    schema_info = await optimizer.discover_schema_optimized(db_name)
                    
                    latency = (time.time() - start_time) * 1000  # Convert to ms
                    latencies.append(latency)
                    
                except Exception as e:
                    logger.warning(f"Schema discovery error: {e}")
                    errors += 1
            
            if latencies:
                result = BenchmarkResult(
                    test_name=f"schema_discovery_{level.value}",
                    duration_seconds=sum(latencies) / 1000,
                    operations_count=len(latencies),
                    operations_per_second=len(latencies) / (sum(latencies) / 1000) if latencies else 0,
                    average_latency_ms=statistics.mean(latencies),
                    p50_latency_ms=statistics.median(latencies),
                    p95_latency_ms=self._percentile(latencies, 0.95),
                    p99_latency_ms=self._percentile(latencies, 0.99),
                    error_rate=errors / (len(latencies) + errors),
                    memory_usage_mb=self._get_memory_usage(),
                    metadata={"optimization_level": level.value}
                )
                
                results[level.value] = result.__dict__
                self.benchmark_results.append(result)
        
        return results
    
    async def _benchmark_cache_performance(self) -> Dict[str, Any]:
        """Benchmark cache performance."""
        results = {}
        
        # Test cache operations
        cache_operations = [
            ("cache_get", self._benchmark_cache_get),
            ("cache_set", self._benchmark_cache_set),
            ("cache_warming", self._benchmark_cache_warming),
            ("cache_invalidation", self._benchmark_cache_invalidation)
        ]
        
        for op_name, op_func in cache_operations:
            logger.info(f"Benchmarking cache operation: {op_name}")
            
            try:
                result = await op_func()
                results[op_name] = result.__dict__
                self.benchmark_results.append(result)
                
            except Exception as e:
                logger.error(f"Cache benchmark {op_name} failed: {e}")
                results[op_name] = {"error": str(e)}
        
        return results
    
    async def _benchmark_cache_get(self) -> BenchmarkResult:
        """Benchmark cache get operations."""
        cache = self.schema_manager.cache
        latencies = []
        hits = 0
        misses = 0
        
        # Pre-populate cache with some data
        for i in range(50):
            await cache.set(
                f"test_operation_{i}",
                {"test_data": f"value_{i}"},
                ttl=300,
                test_param=f"param_{i}"
            )
        
        # Test get operations
        for i in range(200):
            start_time = time.time()
            
            # Mix of existing and non-existing keys
            if i < 100:
                key_param = f"param_{i % 50}"  # Should hit
                result = await cache.get("test_operation", test_param=key_param)
                if result:
                    hits += 1
                else:
                    misses += 1
            else:
                key_param = f"nonexistent_{i}"  # Should miss
                result = await cache.get("test_operation", test_param=key_param)
                misses += 1
            
            latency = (time.time() - start_time) * 1000
            latencies.append(latency)
        
        hit_rate = hits / (hits + misses) if (hits + misses) > 0 else 0
        
        return BenchmarkResult(
            test_name="cache_get",
            duration_seconds=sum(latencies) / 1000,
            operations_count=len(latencies),
            operations_per_second=len(latencies) / (sum(latencies) / 1000),
            average_latency_ms=statistics.mean(latencies),
            p50_latency_ms=statistics.median(latencies),
            p95_latency_ms=self._percentile(latencies, 0.95),
            p99_latency_ms=self._percentile(latencies, 0.99),
            error_rate=0.0,
            memory_usage_mb=self._get_memory_usage(),
            metadata={"hit_rate": hit_rate, "hits": hits, "misses": misses}
        )
    
    async def _benchmark_cache_set(self) -> BenchmarkResult:
        """Benchmark cache set operations."""
        cache = self.schema_manager.cache
        latencies = []
        errors = 0
        
        for i in range(100):
            start_time = time.time()
            
            try:
                await cache.set(
                    f"benchmark_set_{i}",
                    {"benchmark_data": f"value_{i}", "timestamp": time.time()},
                    ttl=300,
                    benchmark_param=f"param_{i}"
                )
                
            except Exception as e:
                logger.warning(f"Cache set error: {e}")
                errors += 1
            
            latency = (time.time() - start_time) * 1000
            latencies.append(latency)
        
        return BenchmarkResult(
            test_name="cache_set",
            duration_seconds=sum(latencies) / 1000,
            operations_count=len(latencies),
            operations_per_second=len(latencies) / (sum(latencies) / 1000),
            average_latency_ms=statistics.mean(latencies),
            p50_latency_ms=statistics.median(latencies),
            p95_latency_ms=self._percentile(latencies, 0.95),
            p99_latency_ms=self._percentile(latencies, 0.99),
            error_rate=errors / len(latencies) if latencies else 1.0,
            memory_usage_mb=self._get_memory_usage(),
            metadata={"total_errors": errors}
        )
    
    async def _benchmark_cache_warming(self) -> BenchmarkResult:
        """Benchmark cache warming performance."""
        start_time = time.time()
        
        try:
            # Warm cache with test databases
            warming_results = await self.cache_warmer.warm_cache_intelligently(
                self.test_databases,
                priority_tables=self.test_tables[:3]
            )
            
            duration = time.time() - start_time
            
            return BenchmarkResult(
                test_name="cache_warming",
                duration_seconds=duration,
                operations_count=warming_results.get("tables_warmed", 0),
                operations_per_second=warming_results.get("tables_warmed", 0) / duration,
                average_latency_ms=duration * 1000,
                p50_latency_ms=duration * 1000,
                p95_latency_ms=duration * 1000,
                p99_latency_ms=duration * 1000,
                error_rate=len(warming_results.get("errors", [])) / max(1, warming_results.get("tables_warmed", 1)),
                memory_usage_mb=self._get_memory_usage(),
                metadata=warming_results
            )
            
        except Exception as e:
            duration = time.time() - start_time
            return BenchmarkResult(
                test_name="cache_warming",
                duration_seconds=duration,
                operations_count=0,
                operations_per_second=0,
                average_latency_ms=duration * 1000,
                p50_latency_ms=duration * 1000,
                p95_latency_ms=duration * 1000,
                p99_latency_ms=duration * 1000,
                error_rate=1.0,
                memory_usage_mb=self._get_memory_usage(),
                metadata={"error": str(e)}
            )
    
    async def _benchmark_cache_invalidation(self) -> BenchmarkResult:
        """Benchmark cache invalidation performance."""
        cache = self.schema_manager.cache
        
        # Pre-populate cache
        for i in range(100):
            await cache.set(
                f"invalidation_test_{i}",
                {"data": f"value_{i}"},
                ttl=3600,
                test_param=f"param_{i}"
            )
        
        start_time = time.time()
        
        # Test invalidation
        invalidated_count = await cache.invalidate("invalidation_test_*")
        
        duration = time.time() - start_time
        
        return BenchmarkResult(
            test_name="cache_invalidation",
            duration_seconds=duration,
            operations_count=invalidated_count,
            operations_per_second=invalidated_count / duration if duration > 0 else 0,
            average_latency_ms=duration * 1000,
            p50_latency_ms=duration * 1000,
            p95_latency_ms=duration * 1000,
            p99_latency_ms=duration * 1000,
            error_rate=0.0,
            memory_usage_mb=self._get_memory_usage(),
            metadata={"invalidated_count": invalidated_count}
        )
    
    async def _benchmark_query_generation(self) -> Dict[str, Any]:
        """Benchmark query generation performance."""
        latencies = []
        errors = 0
        
        # Test query generation with different intents
        for i in range(50):
            try:
                start_time = time.time()
                
                # Create test intent
                intent = {
                    "metric_type": random.choice(self.test_metrics),
                    "time_period": random.choice(["monthly", "quarterly", "yearly"]),
                    "filters": {"department": f"dept_{i % 5}"}
                }
                
                # Generate query context
                query_context = await self.schema_manager.generate_query_context(intent)
                
                latency = (time.time() - start_time) * 1000
                latencies.append(latency)
                
            except Exception as e:
                logger.warning(f"Query generation error: {e}")
                errors += 1
        
        if latencies:
            result = BenchmarkResult(
                test_name="query_generation",
                duration_seconds=sum(latencies) / 1000,
                operations_count=len(latencies),
                operations_per_second=len(latencies) / (sum(latencies) / 1000),
                average_latency_ms=statistics.mean(latencies),
                p50_latency_ms=statistics.median(latencies),
                p95_latency_ms=self._percentile(latencies, 0.95),
                p99_latency_ms=self._percentile(latencies, 0.99),
                error_rate=errors / (len(latencies) + errors),
                memory_usage_mb=self._get_memory_usage(),
                metadata={"total_errors": errors}
            )
            
            self.benchmark_results.append(result)
            return {"query_generation": result.__dict__}
        else:
            return {"query_generation": {"error": "No successful operations"}}
    
    async def _benchmark_connection_pool(self) -> Dict[str, Any]:
        """Benchmark connection pool performance."""
        results = {}
        
        # Test connection acquisition and release
        acquisition_latencies = []
        release_latencies = []
        errors = 0
        
        for i in range(20):  # Test 20 connection operations
            try:
                # Acquire connection
                start_time = time.time()
                connection = await self.connection_pool.acquire_connection()
                acquisition_time = (time.time() - start_time) * 1000
                acquisition_latencies.append(acquisition_time)
                
                # Simulate work
                await asyncio.sleep(0.1)
                
                # Release connection
                start_time = time.time()
                await self.connection_pool.release_connection(connection)
                release_time = (time.time() - start_time) * 1000
                release_latencies.append(release_time)
                
            except Exception as e:
                logger.warning(f"Connection pool error: {e}")
                errors += 1
        
        # Get pool statistics
        pool_stats = await self.connection_pool.get_pool_stats()
        
        if acquisition_latencies:
            acquisition_result = BenchmarkResult(
                test_name="connection_acquisition",
                duration_seconds=sum(acquisition_latencies) / 1000,
                operations_count=len(acquisition_latencies),
                operations_per_second=len(acquisition_latencies) / (sum(acquisition_latencies) / 1000),
                average_latency_ms=statistics.mean(acquisition_latencies),
                p50_latency_ms=statistics.median(acquisition_latencies),
                p95_latency_ms=self._percentile(acquisition_latencies, 0.95),
                p99_latency_ms=self._percentile(acquisition_latencies, 0.99),
                error_rate=errors / (len(acquisition_latencies) + errors),
                memory_usage_mb=self._get_memory_usage(),
                metadata=pool_stats
            )
            
            results["connection_acquisition"] = acquisition_result.__dict__
            self.benchmark_results.append(acquisition_result)
        
        return results
    
    async def _run_load_tests(self) -> Dict[str, Any]:
        """Run load testing scenarios."""
        load_configs = [
            LoadTestConfig(concurrent_users=5, duration_seconds=30),
            LoadTestConfig(concurrent_users=10, duration_seconds=30),
            LoadTestConfig(concurrent_users=20, duration_seconds=30)
        ]
        
        results = {}
        
        for config in load_configs:
            logger.info(
                f"Running load test: {config.concurrent_users} users, "
                f"{config.duration_seconds}s duration"
            )
            
            try:
                result = await self._execute_load_test(config)
                results[f"load_test_{config.concurrent_users}_users"] = result
                
            except Exception as e:
                logger.error(f"Load test failed: {e}")
                results[f"load_test_{config.concurrent_users}_users"] = {"error": str(e)}
        
        return results
    
    async def _execute_load_test(self, config: LoadTestConfig) -> Dict[str, Any]:
        """Execute a single load test scenario."""
        start_time = time.time()
        
        # Statistics collection
        all_latencies = []
        all_errors = []
        user_results = []
        
        # Create semaphore for concurrent users
        semaphore = asyncio.Semaphore(config.concurrent_users)
        
        # Create user tasks
        user_tasks = []
        
        for user_id in range(config.concurrent_users):
            # Stagger user start times for ramp-up
            start_delay = (config.ramp_up_seconds * user_id) / config.concurrent_users
            
            task = asyncio.create_task(
                self._simulate_user_load(user_id, config, start_delay, semaphore)
            )
            user_tasks.append(task)
        
        # Wait for all users to complete
        user_results = await asyncio.gather(*user_tasks, return_exceptions=True)
        
        # Aggregate results
        total_operations = 0
        total_errors = 0
        
        for result in user_results:
            if isinstance(result, Exception):
                logger.error(f"User simulation failed: {result}")
                total_errors += 1
                continue
            
            if isinstance(result, dict):
                total_operations += result.get("operations", 0)
                total_errors += result.get("errors", 0)
                all_latencies.extend(result.get("latencies", []))
        
        total_duration = time.time() - start_time
        
        if all_latencies:
            return {
                "test_config": config.__dict__,
                "total_duration_seconds": total_duration,
                "total_operations": total_operations,
                "total_errors": total_errors,
                "operations_per_second": total_operations / total_duration,
                "error_rate": total_errors / (total_operations + total_errors) if (total_operations + total_errors) > 0 else 0,
                "average_latency_ms": statistics.mean(all_latencies),
                "p50_latency_ms": statistics.median(all_latencies),
                "p95_latency_ms": self._percentile(all_latencies, 0.95),
                "p99_latency_ms": self._percentile(all_latencies, 0.99),
                "max_latency_ms": max(all_latencies),
                "min_latency_ms": min(all_latencies),
                "concurrent_users": config.concurrent_users
            }
        else:
            return {
                "test_config": config.__dict__,
                "error": "No successful operations completed"
            }
    
    async def _simulate_user_load(
        self,
        user_id: int,
        config: LoadTestConfig,
        start_delay: float,
        semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        """Simulate load for a single user."""
        # Wait for start delay (ramp-up)
        await asyncio.sleep(start_delay)
        
        latencies = []
        errors = 0
        operations = 0
        
        end_time = time.time() + config.duration_seconds
        
        async with semaphore:
            while time.time() < end_time and operations < config.operations_per_user:
                try:
                    start_time = time.time()
                    
                    # Perform a typical operation (schema discovery + query generation)
                    metric_type = random.choice(self.test_metrics)
                    
                    # Find tables for metric
                    table_mappings = await self.schema_manager.find_tables_for_metric(metric_type)
                    
                    # Generate query context
                    intent = {
                        "metric_type": metric_type,
                        "time_period": random.choice(["monthly", "quarterly"]),
                        "user_id": user_id
                    }
                    query_context = await self.schema_manager.generate_query_context(intent)
                    
                    latency = (time.time() - start_time) * 1000
                    latencies.append(latency)
                    operations += 1
                    
                    # Think time between operations
                    if config.think_time_seconds > 0:
                        await asyncio.sleep(config.think_time_seconds)
                    
                except Exception as e:
                    logger.debug(f"User {user_id} operation error: {e}")
                    errors += 1
        
        return {
            "user_id": user_id,
            "operations": operations,
            "errors": errors,
            "latencies": latencies
        }
    
    async def _benchmark_resource_usage(self) -> Dict[str, Any]:
        """Benchmark memory and resource usage."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Initial measurements
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        initial_cpu = process.cpu_percent()
        
        # Perform intensive operations
        operations = []
        
        # Schema discoveries
        for _ in range(10):
            start_time = time.time()
            await self.schema_manager.discover_schema(force_refresh=True)
            operations.append(time.time() - start_time)
        
        # Cache warming
        start_time = time.time()
        await self.cache_warmer.warm_cache_intelligently(self.test_databases)
        operations.append(time.time() - start_time)
        
        # Query generations
        for _ in range(20):
            start_time = time.time()
            intent = {
                "metric_type": random.choice(self.test_metrics),
                "time_period": "monthly"
            }
            await self.schema_manager.generate_query_context(intent)
            operations.append(time.time() - start_time)
        
        # Final measurements
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        final_cpu = process.cpu_percent()
        
        return {
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "memory_increase_mb": final_memory - initial_memory,
            "initial_cpu_percent": initial_cpu,
            "final_cpu_percent": final_cpu,
            "total_operations": len(operations),
            "total_operation_time": sum(operations),
            "average_operation_time": statistics.mean(operations) if operations else 0
        }
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of data."""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile)
        index = min(index, len(sorted_data) - 1)
        return sorted_data[index]
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate benchmark summary."""
        if not self.benchmark_results:
            return {"error": "No benchmark results available"}
        
        # Overall statistics
        total_operations = sum(r.operations_count for r in self.benchmark_results)
        total_duration = sum(r.duration_seconds for r in self.benchmark_results)
        average_ops_per_sec = statistics.mean([r.operations_per_second for r in self.benchmark_results])
        average_latency = statistics.mean([r.average_latency_ms for r in self.benchmark_results])
        max_latency = max([r.p99_latency_ms for r in self.benchmark_results])
        average_error_rate = statistics.mean([r.error_rate for r in self.benchmark_results])
        
        # Performance grades
        performance_grade = self._calculate_performance_grade(average_latency, average_error_rate)
        
        return {
            "total_operations": total_operations,
            "total_duration_seconds": total_duration,
            "average_operations_per_second": average_ops_per_sec,
            "average_latency_ms": average_latency,
            "max_p99_latency_ms": max_latency,
            "average_error_rate": average_error_rate,
            "performance_grade": performance_grade,
            "benchmark_count": len(self.benchmark_results)
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        if not self.benchmark_results:
            return ["No benchmark data available for recommendations"]
        
        # Analyze results for recommendations
        avg_latency = statistics.mean([r.average_latency_ms for r in self.benchmark_results])
        avg_error_rate = statistics.mean([r.error_rate for r in self.benchmark_results])
        
        # Latency recommendations
        if avg_latency > 5000:  # 5 seconds
            recommendations.append(
                "High average latency detected. Consider implementing more aggressive caching, "
                "connection pooling optimization, or query optimization."
            )
        elif avg_latency > 2000:  # 2 seconds
            recommendations.append(
                "Moderate latency detected. Consider cache warming strategies and "
                "optimizing schema discovery algorithms."
            )
        
        # Error rate recommendations
        if avg_error_rate > 0.05:  # 5%
            recommendations.append(
                "High error rate detected. Review error handling, connection stability, "
                "and implement better retry mechanisms."
            )
        
        # Memory usage recommendations
        max_memory = max([r.memory_usage_mb for r in self.benchmark_results if r.memory_usage_mb > 0], default=0)
        if max_memory > 500:  # 500MB
            recommendations.append(
                "High memory usage detected. Consider implementing cache size limits, "
                "memory-efficient data structures, and garbage collection optimization."
            )
        
        # Connection pool recommendations
        pool_results = [r for r in self.benchmark_results if "connection" in r.test_name]
        if pool_results:
            avg_pool_latency = statistics.mean([r.average_latency_ms for r in pool_results])
            if avg_pool_latency > 100:  # 100ms
                recommendations.append(
                    "High connection acquisition latency. Consider increasing minimum "
                    "connection pool size or optimizing connection health checks."
                )
        
        # Performance grade recommendations
        performance_grade = self._calculate_performance_grade(avg_latency, avg_error_rate)
        if performance_grade in ["D", "F"]:
            recommendations.append(
                "Overall performance is below acceptable levels. Prioritize performance "
                "optimization, consider scaling resources, and review system architecture."
            )
        elif performance_grade == "C":
            recommendations.append(
                "Performance is marginal. Focus on optimization of the slowest components "
                "and implement proactive monitoring."
            )
        
        if not recommendations:
            recommendations.append(
                "Performance metrics are within acceptable ranges. Continue monitoring "
                "and consider optimization for future scale requirements."
            )
        
        return recommendations
    
    def _calculate_performance_grade(self, avg_latency: float, avg_error_rate: float) -> str:
        """Calculate performance grade based on latency and error rate."""
        # Grade based on latency (ms)
        if avg_latency < 1000 and avg_error_rate < 0.01:
            return "A"  # Excellent
        elif avg_latency < 2000 and avg_error_rate < 0.02:
            return "B"  # Good
        elif avg_latency < 5000 and avg_error_rate < 0.05:
            return "C"  # Acceptable
        elif avg_latency < 10000 and avg_error_rate < 0.10:
            return "D"  # Poor
        else:
            return "F"  # Unacceptable
