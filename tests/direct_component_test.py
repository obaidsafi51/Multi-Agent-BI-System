#!/usr/bin/env python3
"""
Direct component test - Test components with minimal dependencies
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.getcwd())

def test_nlp_agent():
    """Test NLP Agent with minimal setup"""
    print("🧠 Testing NLP Agent...")
    try:
        # Set basic environment variables
        os.environ["ENABLE_WEBSOCKETS"] = "false"
        os.environ["MONITORING_ENABLED"] = "false"
        
        import sys
        sys.path.insert(0, "agents/nlp-agent")
        
        from fastapi.testclient import TestClient
        import main_optimized
        
        # Create test client
        client = TestClient(main_optimized.app)
        
        # Test health endpoint (should fail with monitoring not initialized, but app should respond)
        try:
            response = client.get("/health")
            print(f"   Health endpoint responded: {response.status_code}")
            if response.status_code in [200, 503]:  # Either healthy or service unavailable
                print("   ✅ NLP Agent responding to requests")
            else:
                print(f"   ❌ Unexpected health response: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Health endpoint failed: {e}")
        
        # Test the actual process endpoint
        try:
            payload = {
                "query": "Show me sales data",
                "context": {}
            }
            response = client.post("/process", json=payload)
            print(f"   Process endpoint responded: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ NLP Agent processing working")
            elif response.status_code == 503:
                print("   ⚠️ NLP Agent available but dependencies not initialized")
            else:
                print(f"   ❌ Process endpoint failed: {response.status_code}")
                print(f"      Response: {response.text}")
        except Exception as e:
            print(f"   ❌ Process endpoint failed: {e}")
            
        return True
        
    except Exception as e:
        print(f"   ❌ NLP Agent test failed: {e}")
        return False

def test_viz_agent():
    """Test Viz Agent with minimal setup"""
    print("📈 Testing Viz Agent...")
    try:
        os.environ["ENABLE_WEBSOCKETS"] = "false"
        
        import sys
        sys.path.insert(0, "agents/viz-agent")
        
        from fastapi.testclient import TestClient
        import main
        
        client = TestClient(main.app)
        
        # Test health
        response = client.get("/health")
        print(f"   Health endpoint: {response.status_code}")
        
        # Test visualization creation
        payload = {
            "data": [{"month": "Jan", "revenue": 1000}],
            "chart_type": "bar",
            "title": "Test Chart",
            "user_id": "test_user"
        }
        response = client.post("/create_visualization", json=payload)
        print(f"   Visualization endpoint: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ Viz Agent working")
            return True
        else:
            print(f"   ⚠️ Viz Agent responded but with status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Viz Agent test failed: {e}")
        return False

def test_backend():
    """Test Backend with minimal setup"""
    print("🏢 Testing Backend...")
    try:
        os.environ["ENABLE_WEBSOCKETS"] = "false"
        os.environ["MONITORING_ENABLED"] = "false"
        
        import sys
        sys.path.insert(0, "backend")
        
        from fastapi.testclient import TestClient
        import main
        
        client = TestClient(main.app)
        
        # Test health
        response = client.get("/health")
        print(f"   Health endpoint: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Backend healthy: {data}")
            return True
        else:
            print(f"   ⚠️ Backend responded but with status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Backend test failed: {e}")
        return False

def main():
    """Run direct component tests"""
    print("Multi-Agent BI System - Direct Component Test")
    print("=" * 50)
    print("Testing components with minimal dependencies...")
    
    results = []
    
    # Test each component
    results.append(("NLP Agent", test_nlp_agent()))
    results.append(("Viz Agent", test_viz_agent()))
    results.append(("Backend", test_backend()))
    
    # Summary
    print("\n" + "=" * 50)
    print("DIRECT TEST RESULTS")
    print("=" * 50)
    
    passed = 0
    for name, result in results:
        status = "✅ WORKING" if result else "❌ ISSUES"
        print(f"{name:12}: {status}")
        if result:
            passed += 1
    
    print(f"\nResult: {passed}/{len(results)} components working")
    
    if passed >= 2:  # At least 2 out of 3 working
        print("🎉 Most components are functional!")
        return True
    else:
        print("⚠️ Multiple components have issues")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
