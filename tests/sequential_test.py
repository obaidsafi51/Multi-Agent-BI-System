#!/usr/bin/env python3
"""
Sequential component test - Start and test each component one by one
"""

import asyncio
import httpx
import subprocess
import time
import signal
import sys
from pathlib import Path

class ComponentTester:
    def __init__(self):
        self.processes = []
        
    def cleanup(self):
        """Clean up all started processes"""
        for process in self.processes:
            if process.poll() is None:  # Still running
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
        
    async def test_component(self, name, path, port, startup_cmd):
        """Test a single component"""
        print(f"🧪 Testing {name}...")
        print(f"   Starting {name} on port {port}...")
        
        # Start the component
        try:
            process = subprocess.Popen(
                startup_cmd,
                cwd=path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.processes.append(process)
            
            # Wait for startup
            print(f"   Waiting for {name} to initialize...")
            await asyncio.sleep(8)  # Give more time for startup
            
            # Test health endpoint
            health_url = f"http://localhost:{port}/health"
            print(f"   Testing health endpoint: {health_url}")
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(health_url, timeout=10.0)
                    
                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✅ {name} is healthy: {data}")
                    
                    # Try a functional test
                    await self.test_functionality(name, port, client)
                    
                    return True
                else:
                    print(f"   ❌ {name} health check failed: HTTP {response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"   ❌ {name} health check failed: {e}")
                return False
                
        except Exception as e:
            print(f"   ❌ {name} startup failed: {e}")
            return False
        finally:
            # Stop the component
            if process.poll() is None:
                print(f"   Stopping {name}...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    
    async def test_functionality(self, name, port, client):
        """Test basic functionality of each component"""
        try:
            if name == "Backend":
                # Test backend orchestration endpoint
                response = await client.get(f"http://localhost:{port}/api/health")
                if response.status_code == 200:
                    print(f"     ✅ {name} API endpoint working")
                
            elif name == "NLP Agent":
                # Test NLP processing
                payload = {
                    "query": "Show me revenue data", 
                    "user_id": "test_user"
                }
                response = await client.post(f"http://localhost:{port}/process_query", 
                                           json=payload, timeout=15.0)
                if response.status_code == 200:
                    print(f"     ✅ {name} query processing working")
                    
            elif name == "Viz Agent":
                # Test visualization creation
                payload = {
                    "data": [{"x": 1, "y": 2}],
                    "chart_type": "bar",
                    "title": "Test Chart",
                    "user_id": "test_user"
                }
                response = await client.post(f"http://localhost:{port}/create_visualization",
                                           json=payload, timeout=15.0)
                if response.status_code == 200:
                    print(f"     ✅ {name} visualization creation working")
                    
        except Exception as e:
            print(f"     ⚠️ {name} functionality test failed: {e}")

async def main():
    """Run sequential component tests"""
    print("Multi-Agent BI System - Sequential Component Test")
    print("=" * 50)
    
    tester = ComponentTester()
    
    # Component configurations
    components = [
        {
            "name": "NLP Agent",
            "path": Path("agents/nlp-agent").resolve(),
            "port": 8011,
            "cmd": ["python3", "main_optimized.py"]
        },
        {
            "name": "Viz Agent", 
            "path": Path("agents/viz-agent").resolve(),
            "port": 8013,
            "cmd": ["python3", "main.py"]
        },
        {
            "name": "Backend",
            "path": Path("backend").resolve(), 
            "port": 8000,
            "cmd": ["python3", "main.py"]
        }
    ]
    
    results = []
    
    try:
        for component in components:
            print(f"\n{'='*50}")
            result = await tester.test_component(
                component["name"],
                component["path"], 
                component["port"],
                component["cmd"]
            )
            results.append((component["name"], result))
            
            # Small delay between tests
            await asyncio.sleep(2)
            
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    finally:
        tester.cleanup()
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST RESULTS SUMMARY")
    print(f"{'='*50}")
    
    passed = 0
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name:12}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} components working")
    
    if passed == len(results):
        print("🎉 All tested components are working correctly!")
        return True
    else:
        print("⚠️ Some components have issues")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted")
        sys.exit(1)
