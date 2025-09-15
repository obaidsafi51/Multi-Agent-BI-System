#!/usr/bin/env python3
"""
Test WebSocket connection status and debugging
"""

import subprocess
import time
import json

def check_websocket_status():
    """Check WebSocket connection status from multiple perspectives"""
    print("🔍 Debugging WebSocket Connection Status...")
    
    # Test 1: Check backend logs for WebSocket connections
    print("\n1️⃣ Backend WebSocket connections:")
    try:
        result = subprocess.run(
            'docker compose logs --tail=10 backend | grep -i "websocket.*established\\|connection open"',
            shell=True, capture_output=True, text=True, 
            cwd="/home/obaidsafi31/Desktop/Agentic BI "
        )
        if result.returncode == 0 and result.stdout.strip():
            connections = result.stdout.strip().split('\n')
            print(f"   ✅ Found {len(connections)} WebSocket connection entries")
            for conn in connections[-3:]:  # Show last 3
                if "established for user:" in conn:
                    user_id = conn.split("established for user: ")[-1]
                    print(f"   📡 User: {user_id}")
        else:
            print("   ⚠️  No recent WebSocket connections found in backend logs")
    except Exception as e:
        print(f"   ❌ Error checking backend: {e}")
    
    # Test 2: Check if frontend is making WebSocket connection attempts
    print("\n2️⃣ Frontend WebSocket activity:")
    try:
        # Check for recent compilation which might affect WebSocket
        result = subprocess.run(
            'docker compose logs --tail=20 frontend | grep -E "Compiled|Ready|WebSocket"',
            shell=True, capture_output=True, text=True, 
            cwd="/home/obaidsafi31/Desktop/Agentic BI "
        )
        if result.returncode == 0 and result.stdout.strip():
            print("   📋 Recent frontend activity:")
            for line in result.stdout.strip().split('\n')[-5:]:
                print(f"     {line}")
        else:
            print("   📝 No recent frontend activity found")
    except Exception as e:
        print(f"   ❌ Error checking frontend: {e}")
    
    # Test 3: Check WebSocket endpoint directly
    print("\n3️⃣ Direct WebSocket endpoint test:")
    user_id = f"debug_user_{int(time.time())}"
    print(f"   🧪 Testing with user ID: {user_id}")
    
    # We can't easily test WebSocket from Python without additional libraries,
    # but we can check if the endpoint is accessible by looking at the network
    
    # Test 4: Check environment variables that affect WebSocket
    print("\n4️⃣ WebSocket configuration check:")
    try:
        result = subprocess.run(
            'docker compose exec frontend printenv | grep -E "NEXT_PUBLIC.*URL"',
            shell=True, capture_output=True, text=True, 
            cwd="/home/obaidsafi31/Desktop/Agentic BI "
        )
        if result.returncode == 0 and result.stdout.strip():
            print("   🔧 Environment variables:")
            for line in result.stdout.strip().split('\n'):
                print(f"     {line}")
        else:
            print("   ⚠️  Could not read environment variables from container")
    except Exception as e:
        print(f"   ❌ Error checking environment: {e}")
    
    print("\n✅ WebSocket debugging completed!")

def suggest_fixes():
    """Suggest potential fixes based on the findings"""
    print("\n💡 Potential Issues and Fixes:")
    
    print("\n🔧 Issue 1: WebSocket URL mismatch")
    print("   Problem: Frontend might be using wrong WebSocket URL")
    print("   Solution: Ensure NEXT_PUBLIC_WS_URL is correctly set to ws://localhost:8080")
    
    print("\n🔧 Issue 2: Connection state not updating")
    print("   Problem: WebSocket connects but frontend state doesn't update")
    print("   Solution: Check if onopen event is firing and state is being set")
    
    print("\n🔧 Issue 3: Container networking")
    print("   Problem: Frontend container can't reach backend WebSocket")
    print("   Solution: Verify network connectivity between containers")
    
    print("\n🔧 Issue 4: Browser WebSocket restrictions")
    print("   Problem: Browser security might be blocking WebSocket connections")
    print("   Solution: Check browser console for WebSocket errors")

if __name__ == "__main__":
    print("🚀 WebSocket Connection Status Debugger")
    print("=" * 50)
    
    check_websocket_status()
    suggest_fixes()
    
    print("\n" + "=" * 50)
    print("🎯 Debug completed!")
    print("\n🔍 Next steps:")
    print("   1. Check browser console for WebSocket errors")
    print("   2. Verify WebSocket URL in frontend network tab")
    print("   3. Test WebSocket connection manually")
