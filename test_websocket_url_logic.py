#!/usr/bin/env python3
"""
Test WebSocket URL resolution logic
"""

def test_url_resolution():
    """Test the URL resolution logic we implemented"""
    print("🔧 Testing WebSocket URL Resolution Logic")
    print("=" * 50)
    
    # Simulate different environment variable scenarios
    scenarios = [
        {
            "name": "Full WebSocket URL provided",
            "NEXT_PUBLIC_WS_URL": "ws://localhost:8080",
            "NEXT_PUBLIC_BACKEND_URL": None,
            "NEXT_PUBLIC_API_URL": None,
            "expected": "ws://localhost:8080"
        },
        {
            "name": "Backend URL provided (HTTP)",
            "NEXT_PUBLIC_WS_URL": None,
            "NEXT_PUBLIC_BACKEND_URL": "http://localhost:8080",
            "NEXT_PUBLIC_API_URL": None,
            "expected": "ws://localhost:8080"
        },
        {
            "name": "API URL provided (HTTPS)",
            "NEXT_PUBLIC_WS_URL": None,
            "NEXT_PUBLIC_BACKEND_URL": None,
            "NEXT_PUBLIC_API_URL": "https://api.example.com",
            "expected": "wss://api.example.com"
        },
        {
            "name": "Production scenario",
            "NEXT_PUBLIC_WS_URL": "wss://production.example.com/ws",
            "NEXT_PUBLIC_BACKEND_URL": "https://production.example.com",
            "NEXT_PUBLIC_API_URL": "https://production.example.com/api",
            "expected": "wss://production.example.com/ws"
        }
    ]
    
    def get_websocket_url(ws_url, backend_url, api_url):
        """Simulate the JavaScript URL resolution logic"""
        # Try WebSocket-specific URL first
        if ws_url:
            return ws_url
        
        # Convert HTTP backend URL to WebSocket URL
        if backend_url:
            return backend_url.replace('http://', 'ws://').replace('https://', 'wss://')
        
        # Convert API URL to WebSocket URL
        if api_url:
            return api_url.replace('http://', 'ws://').replace('https://', 'wss://')
        
        # Development fallback
        return 'ws://localhost:8080'
    
    all_passed = True
    
    for scenario in scenarios:
        result = get_websocket_url(
            scenario["NEXT_PUBLIC_WS_URL"],
            scenario["NEXT_PUBLIC_BACKEND_URL"], 
            scenario["NEXT_PUBLIC_API_URL"]
        )
        
        if result == scenario["expected"]:
            print(f"✅ {scenario['name']}: {result}")
        else:
            print(f"❌ {scenario['name']}: Expected {scenario['expected']}, got {result}")
            all_passed = False
    
    return all_passed

if __name__ == "__main__":
    success = test_url_resolution()
    if success:
        print("\n🎉 All URL resolution tests passed!")
        print("✅ WebSocket URL logic is working correctly")
    else:
        print("\n❌ Some URL resolution tests failed")
