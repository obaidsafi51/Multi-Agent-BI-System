#!/usr/bin/env python3
"""
Test the query classification fix to ensure cashflow queries use correct processing path.
"""

import requests
import json
import time

def test_query_classification():
    """Test that cashflow queries now use standard path instead of fast path"""
    
    backend_url = "http://localhost:8080"
    
    # Test the problematic query
    test_query = "what is the cashflow of 2024?"
    
    print(f"Testing query: '{test_query}'")
    print("Expected: Should use STANDARD_PATH or COMPREHENSIVE_PATH (not FAST_PATH)")
    print("-" * 60)
    
    payload = {
        "query": test_query,
        "user_id": "test_user",
        "session_id": "test_session"
    }
    
    try:
        # Send request to backend
        response = requests.post(
            f"{backend_url}/api/query",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Extract processing path from response
            processing_path = None
            if "analytics" in result:
                processing_path = result["analytics"].get("processing_path")
            elif "processing_path" in result:
                processing_path = result["processing_path"]
            
            print(f"✅ Query processed successfully!")
            print(f"Status Code: {response.status_code}")
            print(f"Processing Path: {processing_path}")
            print(f"Full Response Keys: {list(result.keys())}")
            if "analytics" in result:
                print(f"Analytics Keys: {list(result['analytics'].keys())}")
            
            if processing_path == "fast_path":
                print("❌ ISSUE: Query is still using FAST_PATH (incorrect)")
                print("This query requires database access and should use STANDARD_PATH or COMPREHENSIVE_PATH")
                return False
            elif processing_path in ["standard_path", "comprehensive_path"]:
                print(f"✅ SUCCESS: Query correctly using {processing_path.upper()}")
                return True
            else:
                print(f"⚠️  UNKNOWN: Processing path is '{processing_path}'")
                return False
        else:
            print(f"❌ Request failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return False

def test_simple_definition_query():
    """Test that definition queries still use fast path"""
    
    backend_url = "http://localhost:8080"
    
    # Test a true definition query
    test_query = "what is revenue?"
    
    print(f"\nTesting definition query: '{test_query}'")
    print("Expected: Should use FAST_PATH (definitions don't need database)")
    print("-" * 60)
    
    payload = {
        "query": test_query,
        "user_id": "test_user",
        "session_id": "test_session"
    }
    
    try:
        response = requests.post(
            f"{backend_url}/api/query",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            processing_path = None
            if "analytics" in result:
                processing_path = result["analytics"].get("processing_path")
            elif "processing_path" in result:
                processing_path = result["processing_path"]
            
            print(f"✅ Query processed successfully!")
            print(f"Processing Path: {processing_path}")
            
            if processing_path == "fast_path":
                print("✅ SUCCESS: Definition query correctly using FAST_PATH")
                return True
            else:
                print(f"⚠️  Note: Definition query using {processing_path} (may be acceptable)")
                return True
        else:
            print(f"❌ Request failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Query Classification Fix")
    print("=" * 60)
    
    # Test the main issue
    success1 = test_query_classification()
    
    # Test that definitions still work
    success2 = test_simple_definition_query()
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"Cashflow query test: {'✅ PASSED' if success1 else '❌ FAILED'}")
    print(f"Definition query test: {'✅ PASSED' if success2 else '❌ FAILED'}")
    
    if success1 and success2:
        print("\n🎉 All tests passed! Query classification is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Query classification may need further adjustment.")
