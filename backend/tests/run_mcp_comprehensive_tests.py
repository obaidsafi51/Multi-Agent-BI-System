"""
Comprehensive test runner for MCP Schema Management system.

This script runs all MCP-related tests including unit tests, integration tests,
performance benchmarks, and compatibility tests.
"""

import sys
import os
import subprocess
import argparse
from typing import List, Dict, Any
import time


class MCPTestRunner:
    """Test runner for MCP Schema Management tests."""
    
    def __init__(self):
        self.test_categories = {
            'unit': [
                'test_mcp_schema_manager.py',
                'test_dynamic_data_validator.py',
                'test_mcp_cache_layer.py',
                'test_mcp_client.py'
            ],
            'integration': [
                'test_mcp_integration.py',
                'test_mcp_end_to_end_validation.py'
            ],
            'performance': [
                'test_mcp_performance_benchmarks.py'
            ],
            'fallback': [
                'test_mcp_fallback_mechanisms.py'
            ],
            'compatibility': [
                'test_mcp_backward_compatibility.py'
            ],
            'real_server': [
                'test_mcp_real_server.py'
            ],
            'comprehensive': [
                'test_mcp_comprehensive_suite.py'
            ]
        }
        
        self.results = {}
    
    def run_test_category(self, category: str, verbose: bool = False, fail_fast: bool = False) -> Dict[str, Any]:
        """Run tests for a specific category."""
        if category not in self.test_categories:
            raise ValueError(f"Unknown test category: {category}")
        
        print(f"\n{'='*60}")
        print(f"Running {category.upper()} tests")
        print(f"{'='*60}")
        
        category_results = {
            'category': category,
            'tests': {},
            'total_passed': 0,
            'total_failed': 0,
            'total_time': 0
        }
        
        for test_file in self.test_categories[category]:
            print(f"\nRunning {test_file}...")
            
            start_time = time.time()
            result = self.run_single_test(test_file, category, verbose, fail_fast)
            end_time = time.time()
            
            test_time = end_time - start_time
            category_results['tests'][test_file] = {
                'passed': result['passed'],
                'failed': result['failed'],
                'return_code': result['return_code'],
                'time': test_time,
                'output': result['output']
            }
            
            category_results['total_passed'] += result['passed']
            category_results['total_failed'] += result['failed']
            category_results['total_time'] += test_time
            
            if result['return_code'] != 0:
                print(f"❌ {test_file} FAILED")
                if fail_fast:
                    print("Stopping due to --fail-fast")
                    break
            else:
                print(f"✅ {test_file} PASSED")
        
        return category_results
    
    def run_single_test(self, test_file: str, category: str, verbose: bool = False, fail_fast: bool = False) -> Dict[str, Any]:
        """Run a single test file."""
        cmd = [
            sys.executable, '-m', 'pytest',
            f'backend/tests/{test_file}',
            '-v' if verbose else '-q',
            '--tb=short',
            f'-m={category}' if category in ['real_server', 'benchmark', 'e2e', 'compatibility'] else '',
            '--disable-warnings'
        ]
        
        # Remove empty strings from command
        cmd = [arg for arg in cmd if arg]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per test file
            )
            
            output = result.stdout + result.stderr
            
            # Parse pytest output to get test counts
            passed = output.count(' PASSED')
            failed = output.count(' FAILED')
            
            return {
                'passed': passed,
                'failed': failed,
                'return_code': result.returncode,
                'output': output
            }
            
        except subprocess.TimeoutExpired:
            return {
                'passed': 0,
                'failed': 1,
                'return_code': -1,
                'output': f"Test {test_file} timed out after 5 minutes"
            }
        except Exception as e:
            return {
                'passed': 0,
                'failed': 1,
                'return_code': -1,
                'output': f"Error running {test_file}: {str(e)}"
            }
    
    def run_all_tests(self, categories: List[str] = None, verbose: bool = False, fail_fast: bool = False) -> Dict[str, Any]:
        """Run all tests or specified categories."""
        if categories is None:
            categories = ['unit', 'integration', 'fallback', 'compatibility']  # Exclude performance and real_server by default
        
        print("MCP Schema Management Comprehensive Test Suite")
        print("=" * 60)
        
        all_results = {
            'categories': {},
            'summary': {
                'total_passed': 0,
                'total_failed': 0,
                'total_time': 0,
                'categories_run': len(categories)
            }
        }
        
        for category in categories:
            try:
                category_result = self.run_test_category(category, verbose, fail_fast)
                all_results['categories'][category] = category_result
                
                all_results['summary']['total_passed'] += category_result['total_passed']
                all_results['summary']['total_failed'] += category_result['total_failed']
                all_results['summary']['total_time'] += category_result['total_time']
                
                if category_result['total_failed'] > 0 and fail_fast:
                    print(f"\nStopping test run due to failures in {category} category")
                    break
                    
            except Exception as e:
                print(f"Error running {category} tests: {e}")
                all_results['categories'][category] = {
                    'category': category,
                    'error': str(e),
                    'total_passed': 0,
                    'total_failed': 1,
                    'total_time': 0
                }
                all_results['summary']['total_failed'] += 1
        
        return all_results
    
    def print_summary(self, results: Dict[str, Any]):
        """Print test results summary."""
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        
        summary = results['summary']
        
        for category, category_result in results['categories'].items():
            if 'error' in category_result:
                print(f"❌ {category.upper()}: ERROR - {category_result['error']}")
            else:
                passed = category_result['total_passed']
                failed = category_result['total_failed']
                time_taken = category_result['total_time']
                
                status = "✅ PASSED" if failed == 0 else "❌ FAILED"
                print(f"{status} {category.upper()}: {passed} passed, {failed} failed ({time_taken:.2f}s)")
        
        print(f"\n{'='*60}")
        total_tests = summary['total_passed'] + summary['total_failed']
        overall_status = "✅ PASSED" if summary['total_failed'] == 0 else "❌ FAILED"
        
        print(f"{overall_status} OVERALL: {summary['total_passed']}/{total_tests} tests passed")
        print(f"Total time: {summary['total_time']:.2f} seconds")
        print(f"Categories run: {summary['categories_run']}")
        
        if summary['total_failed'] > 0:
            print(f"\n⚠️  {summary['total_failed']} tests failed. Check output above for details.")
            return False
        else:
            print(f"\n🎉 All tests passed!")
            return True
    
    def run_quick_smoke_test(self) -> bool:
        """Run a quick smoke test to verify basic functionality."""
        print("Running quick smoke test...")
        
        smoke_tests = [
            'test_mcp_schema_manager.py::TestMCPSchemaManager::test_connect_success',
            'test_dynamic_data_validator.py::TestDynamicValidationConfig::test_default_config',
            'test_mcp_cache_layer.py::TestMCPCacheLayer::test_cache_key_generation_consistency'
        ]
        
        for test in smoke_tests:
            cmd = [
                sys.executable, '-m', 'pytest',
                f'backend/tests/{test}',
                '-v', '--tb=short', '--disable-warnings'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ Smoke test failed: {test}")
                print(result.stdout)
                print(result.stderr)
                return False
            else:
                print(f"✅ Smoke test passed: {test}")
        
        print("🎉 Smoke test completed successfully!")
        return True


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(description='Run MCP Schema Management tests')
    
    parser.add_argument(
        '--categories', '-c',
        nargs='+',
        choices=['unit', 'integration', 'performance', 'fallback', 'compatibility', 'real_server', 'comprehensive', 'all'],
        default=['unit', 'integration', 'fallback', 'compatibility'],
        help='Test categories to run'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    parser.add_argument(
        '--fail-fast', '-x',
        action='store_true',
        help='Stop on first failure'
    )
    
    parser.add_argument(
        '--smoke-test',
        action='store_true',
        help='Run quick smoke test only'
    )
    
    parser.add_argument(
        '--include-performance',
        action='store_true',
        help='Include performance benchmarks'
    )
    
    parser.add_argument(
        '--include-real-server',
        action='store_true',
        help='Include real server tests (requires MCP server)'
    )
    
    args = parser.parse_args()
    
    runner = MCPTestRunner()
    
    if args.smoke_test:
        success = runner.run_quick_smoke_test()
        sys.exit(0 if success else 1)
    
    # Determine categories to run
    categories = args.categories
    if 'all' in categories:
        categories = ['unit', 'integration', 'fallback', 'compatibility']
        if args.include_performance:
            categories.append('performance')
        if args.include_real_server:
            categories.append('real_server')
    else:
        if args.include_performance and 'performance' not in categories:
            categories.append('performance')
        if args.include_real_server and 'real_server' not in categories:
            categories.append('real_server')
    
    # Run tests
    results = runner.run_all_tests(categories, args.verbose, args.fail_fast)
    
    # Print summary and exit with appropriate code
    success = runner.print_summary(results)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()