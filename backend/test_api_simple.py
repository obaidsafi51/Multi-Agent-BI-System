#!/usr/bin/env python3
"""
Simple API test script to verify /api/query endpoint functionality
"""

import asyncio
import json
import sys
from datetime import datetime
from fastapi.testclient import TestClient

# Import the FastAPI app
try:
    from main import app
    print("Successfully imported FastAPI app")
except ImportError as e:
    print(f"Failed to import app: {e}")
    sys.exit(1)

def test_root_endpoint():
    """Test the root endpoint"""
    print("\n=== Testing Root Endpoint ===")
    
    client = TestClient(app)
    response = client.get("/")
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.status_code == 200

def test_health_endpoint():
    """Test the health endpoint"""
    print("\n=== Testing Health Endpoint ===")
    
    client = TestClient(app)
    response = client.get("/health")
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.status_code == 200

def test_query_endpoint():
    """Test the /api/query endpoint"""
    print("\n=== Testing /api/query Endpoint ===")
    
    client = TestClient(app)
    
    # Test data that matches frontend format
    query_data = {
        "query": "Show me quarterly revenue",
        "context": {"user_preference": "detailed"},
        "metadata": {
            "user_id": "test_user",
            "session_id": "test_session_123",
            "timestamp": datetime.now().isoformat(),
            "source": "frontend"
        }
    }
    
    print(f"Request Data: {json.dumps(query_data, indent=2)}")
    
    try:
        response = client.post("/api/query", json=query_data)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            return True
        else:
            print(f"Error Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Exception during API call: {e}")
        return False

def test_query_endpoint_frontend_format():
    """Test with exact frontend format (no user_id, session_id in root)"""
    print("\n=== Testing /api/query Endpoint (Frontend Format) ===")
    
    client = TestClient(app)
    
    # Test data that exactly matches frontend format
    query_data = {
        "query": "Show me quarterly revenue",
        "context": {"user_preference": "detailed"}
    }
    
    print(f"Request Data: {json.dumps(query_data, indent=2)}")
    
    try:
        response = client.post("/api/query", json=query_data)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            return True
        else:
            print(f"Error Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Exception during API call: {e}")
        return False

def main():
    """Run all tests"""
    print("Starting API endpoint tests...")
    
    test_results = []
    
    # Test basic endpoints
    test_results.append(("Root Endpoint", test_root_endpoint()))
    test_results.append(("Health Endpoint", test_health_endpoint()))
    
    # Test query endpoint with different formats
    test_results.append(("Query Endpoint (Full)", test_query_endpoint()))
    test_results.append(("Query Endpoint (Frontend)", test_query_endpoint_frontend_format()))
    
    # Print summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<30} {status}")
    
    all_passed = all(result for _, result in test_results)
    
    if all_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
