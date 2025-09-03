#!/usr/bin/env python3
"""
Quick System Health Check for Multi-Agent BI System
Fast connectivity test for all services (excluding personal-agent)
"""

import urllib.request
import urllib.parse
import json
import sys

def quick_health_check():
    """Quick health check of all services"""
    print("🏥 Quick Health Check - Multi-Agent BI System")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    # Test 1: Backend Health
    try:
        req = urllib.request.Request(f"{base_url}/health")
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                print(f"✅ Backend: {data.get('status', 'unknown')}")
            else:
                print(f"❌ Backend: HTTP {response.status}")
    except Exception as e:
        print(f"❌ Backend: Connection failed - {e}")
    
    # Test 2: Main Query API (which should integrate with NLP Agent)
    try:
        test_query = {"query": "Show me revenue for Q1 2024"}
        data = json.dumps(test_query).encode('utf-8')
        req = urllib.request.Request(f"{base_url}/api/query", data=data)
        req.add_header('Content-Type', 'application/json')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                result = json.loads(response.read().decode())
                print(f"✅ Query API: Connected - Intent: {result.get('intent', {}).get('metric_type', 'unknown')}")
            else:
                print(f"❌ Query API: HTTP {response.status}")
    except Exception as e:
        print(f"❌ Query API: {e}")
    
    # Test 3: Database Test Endpoint
    try:
        req = urllib.request.Request(f"{base_url}/api/database/test")
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                print("✅ Database Connection: Connected")
            else:
                print(f"❌ Database Connection: HTTP {response.status}")
    except Exception as e:
        print(f"❌ Database Connection: {e}")
    
    # Test 4: Sample Data Endpoint
    try:
        req = urllib.request.Request(f"{base_url}/api/database/sample-data")
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                print(f"✅ Sample Data: {len(data.get('data', []))} records available")
            else:
                print(f"❌ Sample Data: HTTP {response.status}")
    except Exception as e:
        print(f"⚠️  Sample Data: {e}")
    
    print("=" * 50)
    print("🏁 Health check complete!")

if __name__ == "__main__":
    quick_health_check()
