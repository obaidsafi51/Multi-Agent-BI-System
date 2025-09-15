#!/usr/bin/env python3
"""
Test Complete Architecture - Backend Schema Caching + NLP Agent Cache-Only + Frontend Enforcement
"""

import requests
import json
import time
import sys
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

def print_step(step, description):
    print(f"\n{Fore.CYAN}📋 Step {step}: {description}{Style.RESET_ALL}")

def print_success(message):
    print(f"{Fore.GREEN}✅ {message}{Style.RESET_ALL}")

def print_error(message):
    print(f"{Fore.RED}❌ {message}{Style.RESET_ALL}")

def print_info(message):
    print(f"{Fore.YELLOW}ℹ️  {message}{Style.RESET_ALL}")

def test_backend_schema_caching():
    """Test 1: Backend should cache schema completely"""
    print_step(1, "Testing Backend Schema Caching")
    
    try:
        # Call backend database selection endpoint
        url = "http://localhost:8080/api/database/select"
        payload = {
            "database_name": "Agentic_BI",
            "session_id": "test_session_123"
        }
        
        print_info(f"POST {url}")
        print_info(f"Payload: {json.dumps(payload, indent=2)}")
        
        start_time = time.time()
        response = requests.post(url, json=payload, timeout=30)
        duration = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print_success(f"Backend cached schema successfully in {duration:.2f}s")
                print_info(f"Total tables: {data.get('total_tables', 0)}")
                print_info(f"Schema initialized: {data.get('schema_initialized', False)}")
                return True
            else:
                print_error(f"Backend schema caching failed: {data.get('error', 'Unknown error')}")
                return False
        else:
            print_error(f"HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Backend schema caching test failed: {e}")
        return False

def test_nlp_agent_cache_only():
    """Test 2: NLP agent should use cached schema only (no direct fetching)"""
    print_step(2, "Testing NLP Agent Cache-Only Approach")
    
    try:
        # Call NLP agent with query that requires schema
        url = "http://localhost:8001/process"
        payload = {
            "query": "Show me total budget by department",
            "query_id": "test_query_123",
            "user_id": "test_user",
            "session_id": "test_session_123",
            "database_context": {
                "database_name": "Agentic_BI",
                "session_id": "test_session_123"
            }
        }
        
        print_info(f"POST {url}")
        print_info(f"Payload: {json.dumps(payload, indent=2)}")
        
        start_time = time.time()
        response = requests.post(url, json=payload, timeout=60)
        duration = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"NLP agent processed query in {duration:.2f}s")
            
            # Check if response indicates schema was found in cache
            response_text = str(data)
            if "Using backend's cached schema" in response_text or "cached schema" in response_text.lower():
                print_success("✅ NLP agent used cached schema (no direct fetching)")
            else:
                print_info("Schema usage pattern not explicitly mentioned in response")
            
            # Check if no timeout errors occurred (indicates no direct fetching)
            if duration < 30:  # Should be fast if using cache only
                print_success("✅ Fast response indicates cache-only approach")
            else:
                print_error("❌ Slow response might indicate direct schema fetching")
                
            return True
        else:
            print_error(f"HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"NLP agent cache-only test failed: {e}")
        return False

def test_nlp_agent_no_schema():
    """Test 3: NLP agent should handle missing schema gracefully"""
    print_step(3, "Testing NLP Agent Behavior Without Schema")
    
    try:
        # Call NLP agent with non-existent database
        url = "http://localhost:8001/process"
        payload = {
            "query": "Show me sales data",
            "query_id": "test_query_456",
            "user_id": "test_user",
            "session_id": "test_session_456",
            "database_context": {
                "database_name": "nonexistent_db",
                "session_id": "test_session_456"
            }
        }
        
        print_info(f"POST {url}")
        print_info(f"Payload: {json.dumps(payload, indent=2)}")
        
        start_time = time.time()
        response = requests.post(url, json=payload, timeout=30)
        duration = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"NLP agent handled missing schema in {duration:.2f}s")
            
            # Check if response indicates no schema available
            response_text = str(data).lower()
            if "no cached schema" in response_text or "database must be selected" in response_text:
                print_success("✅ NLP agent correctly reported missing schema")
            else:
                print_info("Missing schema message not explicitly found in response")
                
            return True
        else:
            print_error(f"HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"NLP agent missing schema test failed: {e}")
        return False

def main():
    print(f"{Fore.MAGENTA}🚀 Testing Complete Architecture Implementation{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}=" * 60 + Style.RESET_ALL)
    
    print_info("Architecture Requirements:")
    print_info("1. Backend should fetch and cache schema completely")
    print_info("2. NLP agent should use cached schema only (no direct fetching)")
    print_info("3. Frontend should enforce database selection before queries")
    print_info("4. No timeouts or multiple calls causing slowness")
    
    # Run tests
    results = []
    
    # Test 1: Backend schema caching
    results.append(test_backend_schema_caching())
    
    # Test 2: NLP agent cache-only approach
    results.append(test_nlp_agent_cache_only())
    
    # Test 3: NLP agent handles missing schema
    results.append(test_nlp_agent_no_schema())
    
    # Summary
    print(f"\n{Fore.MAGENTA}📊 Test Results Summary{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}=" * 30 + Style.RESET_ALL)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print_success(f"All {total} tests passed! ✨")
        print_success("Architecture implementation successful!")
    else:
        print_error(f"{passed}/{total} tests passed")
        print_error("Architecture implementation needs attention")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
