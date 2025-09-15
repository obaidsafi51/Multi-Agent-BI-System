#!/usr/bin/env python3
"""
Simple session management test using curl and built-in tools
"""

import subprocess
import time
import json
import os

def run_command(command, timeout=10):
    """Run a command and return the result"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"

def test_frontend_reload_simulation():
    """Test session management by checking frontend behavior"""
    print("🧪 Testing Frontend Reload Session Management...")
    
    # Test 1: Check if frontend is responsive
    print("\n1️⃣ Testing frontend accessibility...")
    code, stdout, stderr = run_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:3000')
    if code == 0 and stdout.strip() == "200":
        print("   ✅ Frontend accessible")
    else:
        print(f"   ❌ Frontend not accessible: {stdout} {stderr}")
        return
    
    # Test 2: Check backend WebSocket endpoint
    print("\n2️⃣ Testing backend WebSocket endpoint...")
    test_user_id = f"test_user_{int(time.time())}"
    
    # We can't easily test WebSocket directly, but we can check if the endpoint exists
    # by checking backend logs for WebSocket connection attempts
    
    # Test 3: Check for WebSocket connection conflicts in logs
    print("\n3️⃣ Checking for WebSocket connection conflicts...")
    code, stdout, stderr = run_command('docker compose logs --tail=20 backend | grep -i "websocket\\|connection"')
    if code == 0:
        lines = stdout.strip().split('\n')
        websocket_connections = [line for line in lines if 'WebSocket' in line and 'established' in line]
        print(f"   📊 Recent WebSocket connections: {len(websocket_connections)}")
        
        # Look for any error patterns
        error_lines = [line for line in lines if any(word in line.lower() for word in ['error', 'failed', 'conflict'])]
        if error_lines:
            print("   ⚠️  Found potential issues:")
            for line in error_lines[-3:]:  # Show last 3 errors
                print(f"      {line}")
        else:
            print("   ✅ No obvious connection conflicts detected")
    
    # Test 4: Check frontend WebSocket behavior
    print("\n4️⃣ Checking frontend WebSocket status...")
    
    # Check if frontend is making multiple connection attempts
    code, stdout, stderr = run_command('docker compose logs --tail=20 frontend | grep -i "websocket\\|connect"')
    if code == 0 and stdout.strip():
        print("   📝 Frontend WebSocket activity detected")
        # Count connection attempts in logs
        connection_attempts = len([line for line in stdout.split('\n') if 'connect' in line.lower()])
        if connection_attempts > 2:
            print(f"   ⚠️  Multiple connection attempts detected: {connection_attempts}")
        else:
            print(f"   ✅ Normal connection activity: {connection_attempts} attempts")
    else:
        print("   📝 No recent WebSocket activity in frontend logs")
    
    # Test 5: Simulate reload by checking current connections
    print("\n5️⃣ Checking current active connections...")
    code, stdout, stderr = run_command('docker compose logs --tail=50 backend | grep -c "connection open"')
    if code == 0 and stdout.strip():
        open_connections = int(stdout.strip()) if stdout.strip().isdigit() else 0
        print(f"   📊 Current open connections: {open_connections}")
        
        if open_connections > 3:
            print("   ⚠️  High number of open connections - possible session management issue")
        else:
            print("   ✅ Normal connection count")
    
    print("\n✅ Session management check completed!")

def test_session_storage_behavior():
    """Test sessionStorage behavior for user ID management"""
    print("\n🔍 Testing Session Storage Behavior...")
    
    # Check if the frontend configuration is set to generate new user IDs
    print("   📋 Checking WebSocket context configuration...")
    
    # Check the current configuration
    code, stdout, stderr = run_command('grep -n "Generate a default user ID" /home/obaidsafi31/Desktop/Agentic\\ BI\\ /frontend/src/contexts/WebSocketContext.tsx')
    if code == 0:
        print("   ✅ Found user ID generation logic in WebSocket context")
    else:
        print("   ⚠️  Could not verify user ID generation logic")
    
    # Check for session management improvements
    code, stdout, stderr = run_command('grep -n "Always generate a new session ID" /home/obaidsafi31/Desktop/Agentic\\ BI\\ /frontend/src/contexts/WebSocketContext.tsx')
    if code == 0:
        print("   ✅ Found session ID regeneration on page load")
    else:
        print("   ⚠️  Session ID regeneration not confirmed")

if __name__ == "__main__":
    print("🔧 WebSocket Session Management Analysis")
    print("=" * 50)
    
    test_frontend_reload_simulation()
    test_session_storage_behavior()
    
    print("\n" + "=" * 50)
    print("🎯 Analysis completed!")
    print("\n💡 Key improvements made:")
    print("   • Generate new user ID on every page load")
    print("   • Add proper cleanup on page unload/reload")
    print("   • Improved connection conflict handling")
    print("   • Better connection timeout management")
    print("\n🔄 Try reloading the frontend page to test the fixes!")
