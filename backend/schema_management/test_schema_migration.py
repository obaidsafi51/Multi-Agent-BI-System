"""
Schema Migration Test Suite.

This script provides comprehensive testing for schema migration implementation
including performance optimization and static dependency removal.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.append(str(backend_path))

from schema_management.schema_migration_orchestrator import (
    SchemaMigrationOrchestrator, run_schema_migration
)
from schema_management.performance_optimizer import OptimizationLevel
from schema_management.static_dependency_removal import (
    StaticDependencyScanner, DependencyType
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_static_dependency_scanning():
    """Test static dependency scanning functionality."""
    logger.info("Testing static dependency scanning...")
    
    try:
        project_root = str(Path(__file__).parent.parent.parent)
        scanner = StaticDependencyScanner(project_root)
        
        # Scan for dependencies
        dependencies = await scanner.scan_project()
        
        logger.info(f"Found {len(dependencies)} static dependencies")
        
        # Group by type
        by_type = {}
        for dep in dependencies:
            if dep.dependency_type not in by_type:
                by_type[dep.dependency_type] = 0
            by_type[dep.dependency_type] += 1
        
        logger.info("Dependencies by type:")
        for dep_type, count in by_type.items():
            logger.info(f"  {dep_type.value}: {count}")
        
        # Generate report
        report = scanner.generate_migration_report()
        logger.info(f"Migration report generated: {report['files_affected']} files affected")
        
        return True
        
    except Exception as e:
        logger.error(f"Dependency scanning test failed: {e}")
        return False


async def test_performance_optimization():
    """Test performance optimization components."""
    logger.info("Testing performance optimization...")
    
    try:
        from schema_management.dynamic_schema_manager import get_dynamic_schema_manager
        from schema_management.performance_optimizer import (
            SchemaDiscoveryOptimizer, IntelligentCacheWarmer, AdaptiveTTLManager
        )
        
        # Initialize components
        schema_manager = await get_dynamic_schema_manager()
        
        # Test schema discovery optimization
        optimizer = SchemaDiscoveryOptimizer(
            schema_manager.mcp_client,
            optimization_level=OptimizationLevel.INTERMEDIATE
        )
        
        logger.info("Schema discovery optimizer initialized")
        
        # Test adaptive TTL manager
        ttl_manager = AdaptiveTTLManager()
        test_ttl = ttl_manager.calculate_adaptive_ttl("financial_overview")
        logger.info(f"Adaptive TTL calculated: {test_ttl} seconds")
        
        # Test cache operations
        cache = schema_manager.cache
        await cache.set("test_perf", {"test": "data"}, ttl=300)
        cached_data = await cache.get_schema("test_perf")
        
        if cached_data:
            logger.info("Cache operations working correctly")
        else:
            logger.warning("Cache operations may have issues")
        
        return True
        
    except Exception as e:
        logger.error(f"Performance optimization test failed: {e}")
        return False


async def test_schema_migration_dry_run():
    """Test schema migration implementation with dry run."""
    logger.info("Testing schema migration implementation (dry run)...")
    
    try:
        project_root = str(Path(__file__).parent.parent.parent)
        
        # Create schema migration orchestrator
        orchestrator = SchemaMigrationOrchestrator(
            project_root=project_root,
            optimization_level=OptimizationLevel.BASIC,  # Use basic for testing
            enable_benchmarking=False,  # Disable benchmarking for speed
            backup_directory=f"{project_root}/test_backups"
        )
        
        # Test component initialization
        await orchestrator._initialize_components()
        logger.info("Schema migration components initialized successfully")
        
        # Test performance optimization
        perf_results = await orchestrator._execute_performance_optimization()
        logger.info(f"Performance optimization completed: {len(perf_results)} results")
        
        # Test static dependency scanning
        migration_results = await orchestrator._execute_static_dependency_removal()
        scan_results = migration_results.get("scan_results", {})
        
        if scan_results:
            total_deps = scan_results.get("summary", {}).get("total_dependencies", 0)
            logger.info(f"Found {total_deps} static dependencies")
        
        return True
        
    except Exception as e:
        logger.error(f"Schema migration dry run test failed: {e}")
        return False


async def test_connection_pool():
    """Test connection pool functionality."""
    logger.info("Testing connection pool...")
    
    try:
        from schema_management.connection_pool import MCPConnectionPool
        
        # Create connection pool
        pool = MCPConnectionPool(
            min_connections=2,
            max_connections=5,
            idle_timeout_seconds=60,
            max_connection_age_seconds=300
        )
        
        # Mock connection factory
        async def mock_connection_factory():
            return {"id": f"mock_{asyncio.get_event_loop().time()}", "status": "active"}
        
        async def mock_health_check(connection):
            return connection.get("status") == "active"
        
        # Initialize pool
        await pool.initialize(mock_connection_factory, mock_health_check)
        logger.info("Connection pool initialized")
        
        # Test connection acquisition
        connection = await pool.acquire_connection(timeout=5.0)
        logger.info(f"Connection acquired: {connection['id']}")
        
        # Test connection release
        await pool.release_connection(connection)
        logger.info("Connection released")
        
        # Get pool stats
        stats = await pool.get_pool_stats()
        logger.info(f"Pool stats: {stats['total_connections']} total connections")
        
        # Cleanup
        await pool.shutdown()
        logger.info("Connection pool shut down")
        
        return True
        
    except Exception as e:
        logger.error(f"Connection pool test failed: {e}")
        return False


async def test_cache_performance():
    """Test cache performance improvements."""
    logger.info("Testing cache performance...")
    
    try:
        from schema_management.dynamic_schema_manager import get_dynamic_schema_manager
        import time
        
        schema_manager = await get_dynamic_schema_manager()
        cache = schema_manager.cache
        
        # Test cache performance with multiple operations
        start_time = time.time()
        
        # Perform multiple cache operations
        for i in range(100):
            await cache.set(f"perf_test_{i}", {"data": f"value_{i}"}, ttl=300)
        
        set_time = time.time() - start_time
        logger.info(f"100 cache SET operations took {set_time:.3f} seconds")
        
        # Test cache retrieval performance
        start_time = time.time()
        hit_count = 0
        
        for i in range(100):
            result = await cache.get_schema(f"perf_test_{i}")
            if result:
                hit_count += 1
        
        get_time = time.time() - start_time
        hit_rate = hit_count / 100
        
        logger.info(f"100 cache GET operations took {get_time:.3f} seconds")
        logger.info(f"Cache hit rate: {hit_rate:.2%}")
        
        # Get cache statistics
        stats = cache.get_cache_stats()
        logger.info(f"Cache stats: {stats.total_entries} entries, {stats.hit_rate:.2%} hit rate")
        
        return True
        
    except Exception as e:
        logger.error(f"Cache performance test failed: {e}")
        return False


async def run_comprehensive_tests():
    """Run all schema migration tests."""
    logger.info("🧪 Starting schema migration comprehensive test suite...")
    
    test_results = {}
    
    # Test 1: Static dependency scanning
    test_results["dependency_scanning"] = await test_static_dependency_scanning()
    
    # Test 2: Performance optimization
    test_results["performance_optimization"] = await test_performance_optimization()
    
    # Test 3: Connection pool
    test_results["connection_pool"] = await test_connection_pool()
    
    # Test 4: Cache performance
    test_results["cache_performance"] = await test_cache_performance()
    
    # Test 5: Phase 5 dry run
    test_results["schema_migration_dry_run"] = await test_schema_migration_dry_run()
    
    # Summary
    passed_tests = sum(1 for result in test_results.values() if result)
    total_tests = len(test_results)
    
    logger.info("📊 Test Results Summary:")
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"  {test_name}: {status}")
    
    logger.info(f"📈 Overall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        logger.info("🎉 All Phase 5 tests passed! Ready for implementation.")
        return True
    else:
        logger.warning(f"⚠️ {total_tests - passed_tests} tests failed. Review issues before proceeding.")
        return False


async def run_quick_validation():
    """Run quick validation of Phase 5 components."""
    logger.info("🚀 Running quick Phase 5 validation...")
    
    try:
        # Test imports
        from schema_management.schema_migration_orchestrator import SchemaMigrationOrchestrator
        from schema_management.performance_optimizer import SchemaDiscoveryOptimizer
        from schema_management.connection_pool import MCPConnectionPool
        from schema_management.static_dependency_removal import StaticDependencyScanner
        
        logger.info("✅ All schema migration modules imported successfully")
        
        # Test basic functionality
        project_root = str(Path(__file__).parent.parent.parent)
        scanner = StaticDependencyScanner(project_root)
        
        # Quick dependency scan (just check a few files)
        test_files = list(Path(project_root).glob("**/*.py"))[:10]  # Just first 10 Python files
        
        dependency_count = 0
        for file_path in test_files:
            try:
                await scanner._scan_file(file_path)
                dependency_count += len([d for d in scanner.dependencies if d.file_path == str(file_path)])
            except Exception as e:
                logger.warning(f"Could not scan {file_path}: {e}")
        
        logger.info(f"✅ Quick scan found {dependency_count} dependencies in sample files")
        
        # Test schema migration initialization
        orchestrator = SchemaMigrationOrchestrator(
            project_root=project_root,
            optimization_level=OptimizationLevel.BASIC,
            enable_benchmarking=False
        )
        
        logger.info("✅ Schema migration orchestrator initialized")
        
        logger.info("🎉 Quick validation completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Quick validation failed: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Phase 5 Implementation Test Suite")
    parser.add_argument(
        "--mode",
        choices=["quick", "comprehensive"],
        default="quick",
        help="Test mode to run"
    )
    
    args = parser.parse_args()
    
    if args.mode == "quick":
        success = asyncio.run(run_quick_validation())
    else:
        success = asyncio.run(run_comprehensive_tests())
    
    if success:
        logger.info("✨ Phase 5 testing completed successfully!")
        sys.exit(0)
    else:
        logger.error("💥 Phase 5 testing failed!")
        sys.exit(1)
