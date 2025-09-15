#!/usr/bin/env python3
"""
Test script to verify frontend proxy is working correctly
"""

import requests
import time
import json

def test_frontend_proxy():
    """Test if frontend can proxy API requests correctly"""
    print("🧪 Testing Frontend Proxy Configuration...")
    
    # Test direct backend call
    try:
        print("\n1️⃣ Testing direct backend API call...")
        response = requests.get("http://localhost:8080/health", timeout=5)
        print(f"   ✅ Direct backend: {response.status_code} {response.json()}")
    except Exception as e:
        print(f"   ❌ Direct backend failed: {e}")
        return False
    
    # Test frontend proxy call
    try:
        print("\n2️⃣ Testing frontend proxy API call...")
        response = requests.get("http://localhost:3000/api/health", timeout=10)
        print(f"   ✅ Frontend proxy: {response.status_code} {response.json()}")
    except Exception as e:
        print(f"   ❌ Frontend proxy failed: {e}")
        return False
    
    # Test database endpoint through proxy
    try:
        print("\n3️⃣ Testing database endpoint through proxy...")
        response = requests.get("http://localhost:3000/api/database/status", timeout=10)
        if response.status_code == 200:
            print(f"   ✅ Database proxy: {response.status_code}")
        else:
            print(f"   ⚠️  Database proxy: {response.status_code} (might be expected)")
    except Exception as e:
        print(f"   ⚠️  Database proxy: {e} (might be expected)")
    
    print("\n✅ Frontend proxy configuration test completed!")
    return True

if __name__ == "__main__":
    test_frontend_proxy()
