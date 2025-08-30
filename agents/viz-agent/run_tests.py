#!/usr/bin/env python3
"""
Test runner for the Visualization Agent
"""

import sys
import subprocess
import os
from pathlib import Path

def run_tests():
    """Run all tests for the visualization agent"""
    
    # Change to the viz-agent directory
    viz_agent_dir = Path(__file__).parent
    os.chdir(viz_agent_dir)
    
    print("Running Visualization Agent Tests...")
    print("=" * 50)
    
    # Run pytest with coverage
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--disable-warnings"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)
        
        print(f"\nTest execution completed with return code: {result.returncode}")
        
        if result.returncode == 0:
            print("✅ All tests passed!")
        else:
            print("❌ Some tests failed!")
        
        return result.returncode
        
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)