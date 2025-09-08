"""
Validation script for MCP Schema Management test suite.

This script validates that all MCP tests are properly structured,
have correct imports, and follow testing best practices.
"""

import os
import ast
import sys
import importlib.util
from typing import List, Dict, Any, Set
from pathlib import Path


class MCPTestValidator:
    """Validator for MCP test suite structure and quality."""
    
    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.mcp_test_files = []
        self.validation_results = {}
        
        # Expected test patterns
        self.required_imports = {
            'pytest',
            'asyncio',
            'unittest.mock'
        }
        
        self.expected_test_categories = {
            'unit', 'integration', 'e2e', 'real_server', 
            'benchmark', 'compatibility'
        }
        
        self.required_test_methods = {
            'test_mcp_schema_manager.py': [
                'test_connect_success',
                'test_discover_databases_success',
                'test_get_table_schema_success',
                'test_cache_stats'
            ],
            'test_dynamic_data_validator.py': [
                'test_validate_against_schema_success',
                'test_validate_data_types_integer_validation',
                'test_validate_constraints_primary_key_missing'
            ],
            'test_mcp_cache_layer.py': [
                'test_cache_key_generation_consistency',
                'test_cache_validity_fresh_entry',
                'test_set_cache_enabled'
            ]
        }
    
    def discover_mcp_test_files(self) -> List[Path]:
        """Discover all MCP-related test files."""
        mcp_patterns = [
            'test_mcp_*.py',
            'test_dynamic_*.py'
        ]
        
        test_files = []
        for pattern in mcp_patterns:
            test_files.extend(self.test_dir.glob(pattern))
        
        # Filter out this validation script
        test_files = [f for f in test_files if f.name != 'validate_mcp_tests.py']
        
        return sorted(test_files)
    
    def validate_file_structure(self, file_path: Path) -> Dict[str, Any]:
        """Validate the structure of a test file."""
        result = {
            'file': file_path.name,
            'exists': file_path.exists(),
            'has_docstring': False,
            'has_imports': False,
            'has_test_classes': False,
            'has_test_methods': False,
            'has_fixtures': False,
            'has_async_tests': False,
            'imports': set(),
            'test_classes': [],
            'test_methods': [],
            'fixtures': [],
            'markers': set(),
            'issues': []
        }
        
        if not file_path.exists():
            result['issues'].append('File does not exist')
            return result
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            tree = ast.parse(content)
            
            # Check for module docstring
            if (tree.body and isinstance(tree.body[0], ast.Expr) and 
                isinstance(tree.body[0].value, ast.Constant) and 
                isinstance(tree.body[0].value.value, str)):
                result['has_docstring'] = True
            
            # Analyze AST nodes
            for node in ast.walk(tree):
                # Check imports
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    result['has_imports'] = True
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            result['imports'].add(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            result['imports'].add(node.module)
                
                # Check classes
                elif isinstance(node, ast.ClassDef):
                    if node.name.startswith('Test'):
                        result['has_test_classes'] = True
                        result['test_classes'].append(node.name)
                
                # Check functions/methods
                elif isinstance(node, ast.FunctionDef):
                    if node.name.startswith('test_'):
                        result['has_test_methods'] = True
                        result['test_methods'].append(node.name)
                        
                        # Check if async
                        if isinstance(node, ast.AsyncFunctionDef):
                            result['has_async_tests'] = True
                    
                    # Check for fixtures
                    for decorator in node.decorator_list:
                        if (isinstance(decorator, ast.Attribute) and 
                            decorator.attr == 'fixture'):
                            result['has_fixtures'] = True
                            result['fixtures'].append(node.name)
                        elif (isinstance(decorator, ast.Name) and 
                              decorator.id == 'fixture'):
                            result['has_fixtures'] = True
                            result['fixtures'].append(node.name)
                
                # Check for pytest markers
                elif isinstance(node, ast.Attribute):
                    if (hasattr(node, 'attr') and 
                        node.attr in self.expected_test_categories):
                        result['markers'].add(node.attr)
            
            # Check for required imports
            missing_imports = self.required_imports - result['imports']
            if missing_imports:
                result['issues'].append(f"Missing imports: {missing_imports}")
            
            # Check for required test methods (if specified)
            if file_path.name in self.required_test_methods:
                required_methods = set(self.required_test_methods[file_path.name])
                actual_methods = set(result['test_methods'])
                missing_methods = required_methods - actual_methods
                if missing_methods:
                    result['issues'].append(f"Missing required test methods: {missing_methods}")
            
            # Basic structure checks
            if not result['has_test_classes'] and not result['test_methods']:
                result['issues'].append("No test classes or test methods found")
            
            if not result['has_docstring']:
                result['issues'].append("Missing module docstring")
            
        except Exception as e:
            result['issues'].append(f"Error parsing file: {str(e)}")
        
        return result
    
    def validate_test_coverage(self) -> Dict[str, Any]:
        """Validate test coverage across the MCP system."""
        coverage_result = {
            'components_covered': set(),
            'missing_coverage': [],
            'test_distribution': {},
            'issues': []
        }
        
        # Expected components to be tested
        expected_components = {
            'MCPSchemaManager',
            'EnhancedMCPClient', 
            'DynamicDataValidator',
            'MCPSchemaConfig',
            'ValidationResult',
            'CacheLayer',
            'FallbackMechanisms',
            'PerformanceBenchmarks',
            'BackwardCompatibility',
            'EndToEndValidation'
        }
        
        # Analyze test files to determine coverage
        for file_path in self.mcp_test_files:
            file_result = self.validation_results.get(file_path.name, {})
            
            # Determine what components are covered based on file name and content
            if 'schema_manager' in file_path.name:
                coverage_result['components_covered'].add('MCPSchemaManager')
            if 'client' in file_path.name:
                coverage_result['components_covered'].add('EnhancedMCPClient')
            if 'validator' in file_path.name:
                coverage_result['components_covered'].add('DynamicDataValidator')
            if 'cache' in file_path.name:
                coverage_result['components_covered'].add('CacheLayer')
            if 'fallback' in file_path.name:
                coverage_result['components_covered'].add('FallbackMechanisms')
            if 'performance' in file_path.name or 'benchmark' in file_path.name:
                coverage_result['components_covered'].add('PerformanceBenchmarks')
            if 'compatibility' in file_path.name:
                coverage_result['components_covered'].add('BackwardCompatibility')
            if 'end_to_end' in file_path.name or 'e2e' in file_path.name:
                coverage_result['components_covered'].add('EndToEndValidation')
            
            # Count test methods per file
            test_count = len(file_result.get('test_methods', []))
            coverage_result['test_distribution'][file_path.name] = test_count
        
        # Check for missing coverage
        missing_coverage = expected_components - coverage_result['components_covered']
        coverage_result['missing_coverage'] = list(missing_coverage)
        
        if missing_coverage:
            coverage_result['issues'].append(f"Missing test coverage for: {missing_coverage}")
        
        return coverage_result
    
    def validate_test_quality(self) -> Dict[str, Any]:
        """Validate test quality metrics."""
        quality_result = {
            'total_test_files': 0,
            'total_test_methods': 0,
            'files_with_fixtures': 0,
            'files_with_async_tests': 0,
            'files_with_markers': 0,
            'average_tests_per_file': 0,
            'quality_score': 0,
            'recommendations': []
        }
        
        total_methods = 0
        files_with_issues = 0
        
        for file_path in self.mcp_test_files:
            file_result = self.validation_results.get(file_path.name, {})
            
            quality_result['total_test_files'] += 1
            
            method_count = len(file_result.get('test_methods', []))
            total_methods += method_count
            
            if file_result.get('has_fixtures'):
                quality_result['files_with_fixtures'] += 1
            
            if file_result.get('has_async_tests'):
                quality_result['files_with_async_tests'] += 1
            
            if file_result.get('markers'):
                quality_result['files_with_markers'] += 1
            
            if file_result.get('issues'):
                files_with_issues += 1
        
        quality_result['total_test_methods'] = total_methods
        
        if quality_result['total_test_files'] > 0:
            quality_result['average_tests_per_file'] = total_methods / quality_result['total_test_files']
        
        # Calculate quality score (0-100)
        score_factors = [
            (files_with_issues == 0, 30),  # No structural issues
            (quality_result['files_with_fixtures'] / quality_result['total_test_files'] > 0.8, 20),  # Good fixture usage
            (quality_result['files_with_async_tests'] / quality_result['total_test_files'] > 0.7, 20),  # Async test coverage
            (quality_result['average_tests_per_file'] >= 10, 15),  # Adequate test density
            (quality_result['files_with_markers'] / quality_result['total_test_files'] > 0.5, 15)  # Good marker usage
        ]
        
        quality_result['quality_score'] = sum(points for condition, points in score_factors if condition)
        
        # Generate recommendations
        if files_with_issues > 0:
            quality_result['recommendations'].append(f"Fix structural issues in {files_with_issues} test files")
        
        if quality_result['average_tests_per_file'] < 10:
            quality_result['recommendations'].append("Consider adding more test methods per file")
        
        if quality_result['files_with_fixtures'] / quality_result['total_test_files'] < 0.8:
            quality_result['recommendations'].append("Add more pytest fixtures for better test setup")
        
        return quality_result
    
    def run_validation(self) -> Dict[str, Any]:
        """Run complete validation of MCP test suite."""
        print("Validating MCP Schema Management Test Suite...")
        print("=" * 60)
        
        # Discover test files
        self.mcp_test_files = self.discover_mcp_test_files()
        print(f"Found {len(self.mcp_test_files)} MCP test files")
        
        # Validate each file
        print("\nValidating individual test files...")
        for file_path in self.mcp_test_files:
            print(f"  Validating {file_path.name}...")
            self.validation_results[file_path.name] = self.validate_file_structure(file_path)
        
        # Validate coverage
        print("\nValidating test coverage...")
        coverage_result = self.validate_test_coverage()
        
        # Validate quality
        print("Validating test quality...")
        quality_result = self.validate_test_quality()
        
        # Compile final results
        final_result = {
            'file_validations': self.validation_results,
            'coverage': coverage_result,
            'quality': quality_result,
            'summary': {
                'total_files': len(self.mcp_test_files),
                'files_with_issues': sum(1 for r in self.validation_results.values() if r.get('issues')),
                'total_test_methods': quality_result['total_test_methods'],
                'overall_score': quality_result['quality_score']
            }
        }
        
        return final_result
    
    def print_validation_report(self, results: Dict[str, Any]):
        """Print detailed validation report."""
        print(f"\n{'='*60}")
        print("MCP TEST SUITE VALIDATION REPORT")
        print(f"{'='*60}")
        
        summary = results['summary']
        print(f"Total test files: {summary['total_files']}")
        print(f"Total test methods: {summary['total_test_methods']}")
        print(f"Files with issues: {summary['files_with_issues']}")
        print(f"Overall quality score: {summary['overall_score']}/100")
        
        # File-level issues
        print(f"\n{'='*40}")
        print("FILE VALIDATION RESULTS")
        print(f"{'='*40}")
        
        for file_name, file_result in results['file_validations'].items():
            status = "✅ PASS" if not file_result.get('issues') else "❌ ISSUES"
            print(f"{status} {file_name}")
            
            if file_result.get('issues'):
                for issue in file_result['issues']:
                    print(f"    - {issue}")
            
            print(f"    Tests: {len(file_result.get('test_methods', []))}, "
                  f"Fixtures: {len(file_result.get('fixtures', []))}, "
                  f"Classes: {len(file_result.get('test_classes', []))}")
        
        # Coverage results
        print(f"\n{'='*40}")
        print("COVERAGE ANALYSIS")
        print(f"{'='*40}")
        
        coverage = results['coverage']
        print(f"Components covered: {len(coverage['components_covered'])}")
        print(f"Missing coverage: {coverage['missing_coverage']}")
        
        if coverage['missing_coverage']:
            print("⚠️  Consider adding tests for missing components")
        
        # Quality results
        print(f"\n{'='*40}")
        print("QUALITY METRICS")
        print(f"{'='*40}")
        
        quality = results['quality']
        print(f"Average tests per file: {quality['average_tests_per_file']:.1f}")
        print(f"Files with fixtures: {quality['files_with_fixtures']}/{quality['total_test_files']}")
        print(f"Files with async tests: {quality['files_with_async_tests']}/{quality['total_test_files']}")
        print(f"Files with markers: {quality['files_with_markers']}/{quality['total_test_files']}")
        
        if quality['recommendations']:
            print("\n📋 RECOMMENDATIONS:")
            for rec in quality['recommendations']:
                print(f"  - {rec}")
        
        # Overall assessment
        print(f"\n{'='*60}")
        if summary['overall_score'] >= 80:
            print("🎉 EXCELLENT: Test suite meets high quality standards!")
        elif summary['overall_score'] >= 60:
            print("✅ GOOD: Test suite is well-structured with minor improvements needed")
        elif summary['overall_score'] >= 40:
            print("⚠️  FAIR: Test suite needs improvement in several areas")
        else:
            print("❌ POOR: Test suite requires significant improvements")
        
        return summary['files_with_issues'] == 0 and summary['overall_score'] >= 60


def main():
    """Main entry point for test validation."""
    validator = MCPTestValidator()
    
    try:
        results = validator.run_validation()
        success = validator.print_validation_report(results)
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"Error during validation: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()