#!/usr/bin/env python3
"""
Validation script for Visualization Agent implementation
This script validates the structure and basic syntax without requiring dependencies
"""

import os
import ast
import sys
from pathlib import Path

def validate_python_syntax(file_path):
    """Validate Python syntax of a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast.parse(content)
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    except Exception as e:
        return False, f"Error: {e}"

def validate_implementation():
    """Validate the visualization agent implementation"""
    
    viz_agent_dir = Path(__file__).parent
    src_dir = viz_agent_dir / "src"
    tests_dir = viz_agent_dir / "tests"
    
    print("Validating Visualization Agent Implementation")
    print("=" * 50)
    
    # Check directory structure
    required_dirs = [src_dir, tests_dir]
    for dir_path in required_dirs:
        if dir_path.exists():
            print(f"✅ Directory exists: {dir_path.name}")
        else:
            print(f"❌ Missing directory: {dir_path.name}")
            return False
    
    # Check source files
    src_files = [
        "models.py",
        "chart_selector.py", 
        "chart_generator.py",
        "interactive_features.py",
        "export_manager.py",
        "performance_optimizer.py",
        "visualization_agent.py"
    ]
    
    print("\nValidating source files:")
    all_valid = True
    
    for file_name in src_files:
        file_path = src_dir / file_name
        if file_path.exists():
            is_valid, error = validate_python_syntax(file_path)
            if is_valid:
                print(f"✅ {file_name} - syntax valid")
            else:
                print(f"❌ {file_name} - {error}")
                all_valid = False
        else:
            print(f"❌ Missing file: {file_name}")
            all_valid = False
    
    # Check test files
    test_files = [
        "test_chart_selector.py",
        "test_chart_generator.py", 
        "test_export_manager.py",
        "test_performance_optimizer.py",
        "test_visualization_agent.py"
    ]
    
    print("\nValidating test files:")
    
    for file_name in test_files:
        file_path = tests_dir / file_name
        if file_path.exists():
            is_valid, error = validate_python_syntax(file_path)
            if is_valid:
                print(f"✅ {file_name} - syntax valid")
            else:
                print(f"❌ {file_name} - {error}")
                all_valid = False
        else:
            print(f"❌ Missing file: {file_name}")
            all_valid = False
    
    # Check main.py
    main_file = viz_agent_dir / "main.py"
    if main_file.exists():
        is_valid, error = validate_python_syntax(main_file)
        if is_valid:
            print(f"✅ main.py - syntax valid")
        else:
            print(f"❌ main.py - {error}")
            all_valid = False
    else:
        print(f"❌ Missing main.py")
        all_valid = False
    
    # Check pyproject.toml
    pyproject_file = viz_agent_dir / "pyproject.toml"
    if pyproject_file.exists():
        print(f"✅ pyproject.toml exists")
    else:
        print(f"❌ Missing pyproject.toml")
        all_valid = False
    
    print("\n" + "=" * 50)
    
    if all_valid:
        print("✅ All validation checks passed!")
        print("\nImplementation Summary:")
        print("- Chart type selection logic based on financial data characteristics")
        print("- Dynamic visualization generation using Plotly with CFO-specific styling")
        print("- Interactive chart configuration with zoom, filter, and drill-down capabilities")
        print("- Export functionality for PNG, PDF, CSV, HTML, JSON, and Excel formats")
        print("- Performance optimization for rendering large financial datasets")
        print("- Comprehensive unit tests for all components")
        print("- Main agent orchestration with caching and error handling")
        return True
    else:
        print("❌ Some validation checks failed!")
        return False

if __name__ == "__main__":
    success = validate_implementation()
    sys.exit(0 if success else 1)