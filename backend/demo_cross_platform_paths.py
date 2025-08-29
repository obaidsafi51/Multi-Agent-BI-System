#!/usr/bin/env python3
"""
Demonstration of cross-platform path handling improvements.
"""

import tempfile
import os
from pathlib import Path


def demo_cross_platform_paths():
    """Demonstrate cross-platform path handling"""
    
    print("=== Cross-Platform Path Handling Demo ===\n")
    
    # Show the difference between hard-coded and cross-platform approaches
    print("1. Hard-coded approach (NOT recommended):")
    hardcoded_path = "/tmp/test_file.txt"
    print(f"   Path: {hardcoded_path}")
    print(f"   Issues: Only works on Unix-like systems, fails on Windows")
    print()
    
    print("2. Cross-platform approach (RECOMMENDED):")
    temp_dir = Path(tempfile.gettempdir())
    cross_platform_path = temp_dir / "test_file.txt"
    print(f"   Path: {cross_platform_path}")
    print(f"   Benefits: Works on all operating systems")
    print()
    
    print("3. System information:")
    print(f"   Operating System: {os.name}")
    print(f"   Platform temp directory: {tempfile.gettempdir()}")
    print()
    
    print("4. Alternative cross-platform approaches:")
    
    # Using tempfile.NamedTemporaryFile
    with tempfile.NamedTemporaryFile(suffix='.env', delete=False) as temp_file:
        temp_file_path = Path(temp_file.name)
        print(f"   NamedTemporaryFile: {temp_file_path}")
    
    # Clean up
    temp_file_path.unlink()
    
    # Using tempfile.TemporaryDirectory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir) / "test_file.env"
        print(f"   TemporaryDirectory: {temp_dir_path}")
    
    print()
    print("5. Best practices for cross-platform file paths:")
    print("   ✓ Use tempfile.gettempdir() for temporary directories")
    print("   ✓ Use tempfile.NamedTemporaryFile() for temporary files")
    print("   ✓ Use tempfile.TemporaryDirectory() for temporary directories")
    print("   ✓ Use pathlib.Path for path manipulation")
    print("   ❌ Avoid hard-coded paths like '/tmp/' or 'C:\\temp\\'")
    print()
    
    print("=== Demo Complete ===")


if __name__ == "__main__":
    demo_cross_platform_paths()