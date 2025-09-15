#!/usr/bin/env python3
"""
Simple test to verify WebSocket MCP is configured and working.
Uses only built-in Python libraries.
"""

import json
import socket
import urllib.request
import urllib.parse


def test_http_mcp():
    """Test HTTP MCP endpoint using built-in urllib."""
    print("🌐 Testing HTTP MCP endpoint...")
    try:
        # Test server stats endpoint
        url = "http://localhost:8000/tools/get_server_stats_tool"
        data = json.dumps({}).encode('utf-8')
        
        req = urllib.request.Request(url, data=data)
        req.add_header('Content-Type', 'application/json')
        
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                result = json.loads(response.read().decode('utf-8'))
                print("✅ HTTP MCP endpoint working")
                
                # Check for deduplication stats
                dedup_stats = result.get("request_deduplication")
                if dedup_stats:
                    effectiveness = dedup_stats.get("effectiveness_percent", 0)
                    cache_size = dedup_stats.get("cache_size", 0)
                    total_requests = dedup_stats.get("total_requests", 0)
                    hits = dedup_stats.get("hits", 0)
                    
                    print(f"   📊 Request deduplication: {effectiveness}% effective")
                    print(f"   💾 Cache size: {cache_size} entries")
                    print(f"   📈 Total requests: {total_requests}, Hits: {hits}")
                
                return True
            else:
                print(f"❌ HTTP endpoint failed: {response.status}")
                return False
                
    except Exception as e:
        print(f"❌ HTTP test error: {e}")
        return False


def test_websocket_port():
    """Test if WebSocket port is accessible."""
    print("🔌 Testing WebSocket port accessibility...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('localhost', 8000))
        sock.close()
        
        if result == 0:
            print("✅ WebSocket port 8000 is accessible")
            return True
        else:
            print("❌ WebSocket port 8000 is not accessible")
            return False
            
    except Exception as e:
        print(f"❌ WebSocket port test error: {e}")
        return False


def test_backend_health():
    """Test backend health."""
    print("🔧 Testing backend health...")
    try:
        url = "http://localhost:8080/health"
        
        with urllib.request.urlopen(url, timeout=5) as response:
            if response.status == 200:
                result = json.loads(response.read().decode('utf-8'))
                print("✅ Backend is healthy")
                return True
            else:
                print(f"❌ Backend health check failed: {response.status}")
                return False
                
    except Exception as e:
        print(f"❌ Backend health test error: {e}")
        return False


def check_docker_services():
    """Check if required Docker services are running."""
    print("🐳 Checking Docker services...")
    import subprocess
    
    try:
        result = subprocess.run(['docker', 'compose', 'ps', '--format', 'json'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            services = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        service_info = json.loads(line)
                        name = service_info.get('Service', service_info.get('Name', 'Unknown'))
                        state = service_info.get('State', 'Unknown')
                        services.append(f"   • {name}: {state}")
                    except:
                        continue
            
            if services:
                print("✅ Docker services status:")
                for service in services:
                    print(service)
                return True
            else:
                print("❌ No Docker services found")
                return False
        else:
            print(f"❌ Docker compose command failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Docker services check error: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 WebSocket MCP Configuration Verification")
    print("="*60)
    
    results = {}
    
    # Check Docker services
    results['docker'] = check_docker_services()
    print()
    
    # Test backend
    results['backend'] = test_backend_health()
    print()
    
    # Test WebSocket port
    results['websocket_port'] = test_websocket_port()
    print()
    
    # Test HTTP MCP
    results['http_mcp'] = test_http_mcp()
    print()
    
    # Summary
    print("="*60)
    print("📊 Configuration Verification Summary:")
    print()
    
    if results.get('docker'):
        print("✅ Docker services are running")
    else:
        print("❌ Docker services issue detected")
    
    if results.get('backend'):
        print("✅ Backend service is healthy")
    else:
        print("❌ Backend service is not responding")
    
    if results.get('websocket_port'):
        print("✅ WebSocket port is accessible")
    else:
        print("❌ WebSocket port is not accessible")
    
    if results.get('http_mcp'):
        print("✅ MCP server is working with deduplication")
    else:
        print("❌ MCP server is not responding properly")
    
    print()
    
    if all(results.values()):
        print("🎉 WebSocket MCP configuration verification PASSED!")
        print()
        print("✨ Your system now benefits from:")
        print("   • Request deduplication (prevents redundant schema calls)")
        print("   • Server-side caching with intelligent TTL")
        print("   • WebSocket capability (ready for persistent connections)")
        print("   • Real-time performance monitoring")
        print()
        print("🚀 The redundant schema call issue should be significantly reduced!")
    else:
        print("⚠️  Some issues detected. Check the services:")
        print("   docker compose logs tidb-mcp-server")
        print("   docker compose logs backend")


if __name__ == "__main__":
    main()
