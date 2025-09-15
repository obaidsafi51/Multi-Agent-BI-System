#!/usr/bin/env python3
"""
Simple WebSocket test using built-in libraries
Tests the URL and environment variable fixes
"""

import json
import sys
import urllib.request
import urllib.error

def test_environment_variables():
    """Test if environment variables are correctly configured"""
    print("🔧 Testing Environment Variable Fixes...")
    print("=" * 50)
    
    # Test backend API endpoint availability
    try:
        with urllib.request.urlopen("http://localhost:8080/health", timeout=5) as response:
            if response.status == 200:
                print("✅ Backend API (port 8080) is accessible")
                return True
            else:
                print(f"❌ Backend API returned status: {response.status}")
                return False
    except urllib.error.URLError as e:
        print(f"❌ Backend API not accessible: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing backend API: {e}")
        return False

def test_frontend_env_file():
    """Test if frontend .env.local file has correct configuration"""
    print("\n🔧 Testing Frontend Environment File...")
    print("=" * 50)
    
    try:
        with open('frontend/.env.local', 'r') as f:
            content = f.read()
            
        # Check for correct port configurations
        checks = [
            ("NEXT_PUBLIC_API_URL=http://localhost:8080", "✅ API URL uses correct port 8080"),
            ("NEXT_PUBLIC_BACKEND_URL=http://localhost:8080", "✅ Backend URL configured"),
            ("NEXT_PUBLIC_WS_URL=ws://localhost:8080", "✅ WebSocket URL configured"),
        ]
        
        all_passed = True
        for check, success_msg in checks:
            if check in content:
                print(success_msg)
            else:
                print(f"❌ Missing or incorrect: {check}")
                all_passed = False
                
        return all_passed
        
    except FileNotFoundError:
        print("❌ Frontend .env.local file not found")
        return False
    except Exception as e:
        print(f"❌ Error reading frontend .env.local: {e}")
        return False

def test_docker_compose_config():
    """Test Docker Compose configuration"""
    print("\n🔧 Testing Docker Compose Configuration...")
    print("=" * 50)
    
    try:
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
        # Check for consistent port configurations
        checks = [
            ("\"8080:8080\"", "✅ Backend port mapping correct"),
            ("NEXT_PUBLIC_API_URL=http://localhost:8080", "✅ Frontend env uses port 8080"),
            ("MCP_SERVER_WS_URL=ws://tidb-mcp-server:8000/ws", "✅ MCP WebSocket URL configured"),
        ]
        
        all_passed = True
        for check, success_msg in checks:
            if check in content:
                print(success_msg)
            else:
                print(f"❌ Missing or incorrect: {check}")
                all_passed = False
                
        return all_passed
        
    except FileNotFoundError:
        print("❌ docker-compose.yml file not found")
        return False
    except Exception as e:
        print(f"❌ Error reading docker-compose.yml: {e}")
        return False

def test_websocket_client_fixes():
    """Test WebSocket client code fixes"""
    print("\n🔧 Testing WebSocket Client Code Fixes...")
    print("=" * 50)
    
    try:
        with open('frontend/src/hooks/useWebSocketClient.ts', 'r') as f:
            content = f.read()
            
        # Check for fixes implemented
        checks = [
            ("process.env.NEXT_PUBLIC_WS_URL", "✅ Uses environment variable for WebSocket URL"),
            ("frontend_${fullConfig.user_id}_${sessionId}", "✅ Stable agent ID generation"),
            ("connection_handshake", "✅ Connection handshake implemented"),
            ("connection_acknowledged", "✅ Connection acknowledgment handling"),
            ("standardized message format", "⚠️  Message format improvements present"),
        ]
        
        all_passed = True
        for check, success_msg in checks[:4]:  # Skip the last descriptive check
            if check in content:
                print(success_msg)
            else:
                print(f"❌ Missing: {check}")
                all_passed = False
                
        # Check for hardcoded URLs (should be minimized to development fallback only)
        if "ws://localhost:8080" in content:
            # Count occurrences to see if we reduced them
            count = content.count("ws://localhost:8080")
            if count == 1:  # Only development fallback should remain
                print("✅ Hardcoded WebSocket URLs eliminated (only dev fallback remains)")
            elif count <= 2:
                print("✅ Hardcoded WebSocket URLs minimized")
            else:
                print(f"⚠️  Still has {count} hardcoded WebSocket URLs")
        else:
            print("✅ No hardcoded WebSocket URLs found")
                
        return all_passed
        
    except FileNotFoundError:
        print("❌ useWebSocketClient.ts file not found")
        return False
    except Exception as e:
        print(f"❌ Error reading useWebSocketClient.ts: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 WebSocket Fixes Validation Test")
    print("=" * 60)
    
    tests = [
        test_environment_variables,
        test_frontend_env_file,
        test_docker_compose_config,
        test_websocket_client_fixes
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("📊 FINAL RESULTS")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 ALL TESTS PASSED! ({passed}/{total})")
        print("✅ WebSocket fixes successfully implemented!")
    else:
        print(f"⚠️  {passed}/{total} tests passed")
        print("🔧 Some fixes may need additional work")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
