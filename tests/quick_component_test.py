#!/usr/bin/env python3
"""
Quick component verification test - tests basic import and health endpoint functionality
"""

import sys
import subprocess
import time
import requests
from pathlib import Path

def test_component_import(component_path, import_name, description):
    """Test if a component can import without errors"""
    print(f"🧪 Testing {description} import...")
    
    try:
        # Test import by running python with the import statement
        result = subprocess.run([
            'python3', '-c', f'import {import_name}; print("Import successful")'
        ], cwd=component_path, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"  ✅ {description} imports successfully")
            return True
        else:
            print(f"  ❌ {description} import failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"  ⏰ {description} import timed out")
        return False
    except Exception as e:
        print(f"  ❌ {description} import error: {e}")
        return False

def test_quick_startup(component_path, import_name, description, expected_port):
    """Test if component can start and respond to health checks"""
    print(f"🚀 Testing {description} quick startup...")
    
    try:
        # Start the component
        process = subprocess.Popen([
            'python3', '-c', f'''
import {import_name}
import threading
import time

# Start the service in a separate thread
def run_server():
    try:
        if hasattr({import_name}, "main"):
            {import_name}.main()
        else:
            # For uvicorn-based apps
            import uvicorn
            uvicorn.run({import_name}.app, host="127.0.0.1", port={expected_port}, log_level="error")
    except Exception as e:
        print(f"Server error: {{e}}")

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

# Give it time to start
time.sleep(5)

# Keep the process alive
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
'''
        ], cwd=component_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for startup
        time.sleep(6)
        
        # Test health endpoint
        try:
            response = requests.get(f"http://localhost:{expected_port}/health", timeout=5)
            if response.status_code == 200:
                print(f"  ✅ {description} started and responds to health checks")
                process.terminate()
                process.wait(timeout=5)
                return True
            else:
                print(f"  ❌ {description} health check failed: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"  ❌ {description} health check failed: {e}")
        
        # Clean up
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            
        return False
        
    except Exception as e:
        print(f"  ❌ {description} startup test error: {e}")
        return False

def main():
    """Run quick verification tests"""
    print("Multi-Agent BI System - Quick Component Verification")
    print("=" * 55)
    
    base_path = Path(__file__).parent
    
    # Test configurations
    tests = [
        {
            "path": base_path / "backend",
            "import": "main",
            "description": "Backend",
            "port": 8000
        },
        {
            "path": base_path / "agents" / "nlp-agent", 
            "import": "main_optimized",
            "description": "NLP Agent",
            "port": 8011
        },
        {
            "path": base_path / "agents" / "data-agent",
            "import": "main", 
            "description": "Data Agent",
            "port": 8012
        },
        {
            "path": base_path / "agents" / "viz-agent",
            "import": "main",
            "description": "Viz Agent", 
            "port": 8013
        }
    ]
    
    import_results = []
    startup_results = []
    
    # Test imports
    print("\n🧪 IMPORT TESTS")
    print("-" * 30)
    for test in tests:
        result = test_component_import(test["path"], test["import"], test["description"])
        import_results.append(result)
    
    # Test quick startups (only if imports work)
    print("\n🚀 QUICK STARTUP TESTS")
    print("-" * 30)
    for i, test in enumerate(tests):
        if import_results[i]:  # Only test startup if import worked
            result = test_quick_startup(test["path"], test["import"], test["description"], test["port"])
            startup_results.append(result)
        else:
            print(f"  ⏭️ Skipping {test['description']} startup test (import failed)")
            startup_results.append(False)
    
    # Summary
    print("\n" + "=" * 55)
    print("QUICK VERIFICATION SUMMARY")
    print("=" * 55)
    
    total_passed = 0
    total_tests = len(tests) * 2
    
    for i, test in enumerate(tests):
        component = test["description"]
        import_status = "✅ PASS" if import_results[i] else "❌ FAIL"
        startup_status = "✅ PASS" if startup_results[i] else "❌ FAIL"
        
        print(f"{component:12} - Import: {import_status}, Startup: {startup_status}")
        
        if import_results[i]:
            total_passed += 1
        if startup_results[i]:
            total_passed += 1
    
    print("-" * 55)
    print(f"RESULT: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("🎉 ALL COMPONENTS ARE WORKING!")
        return True
    else:
        print("❌ SOME COMPONENTS HAVE ISSUES")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Test failed with error: {e}")
        sys.exit(1)
