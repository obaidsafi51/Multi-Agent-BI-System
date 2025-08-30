#!/usr/bin/env python3
"""
Demo script to showcase FastAPI backend functionality
"""

import asyncio
import json
from fastapi.testclient import TestClient
from main import app

def demo_api_endpoints():
    """Demonstrate API endpoints functionality"""
    print("🚀 AI CFO Backend Demo")
    print("=" * 50)
    
    client = TestClient(app)
    
    # Test health endpoint
    print("\n1. Health Check:")
    response = client.get("/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}")
    
    # Test root endpoint
    print("\n2. Root Endpoint:")
    response = client.get("/")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}")
    
    # Test authentication
    print("\n3. Authentication:")
    login_data = {"username": "cfo", "password": "demo"}
    response = client.post("/api/auth/login", json=login_data)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        token_data = response.json()
        print(f"   Token received: {token_data['access_token'][:50]}...")
        
        # Use token for authenticated request
        headers = {"Authorization": f"Bearer {token_data['access_token']}"}
        
        print("\n4. Query Processing:")
        query_data = {"query": "Show me quarterly revenue trends"}
        response = client.post("/api/query", json=query_data, headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   Query ID: {result['query_id']}")
            print(f"   Intent: {result['intent']['metric_type']} for {result['intent']['time_period']}")
            print(f"   Data rows: {result['result']['row_count']}")
        
        print("\n5. Get Suggestions:")
        response = client.get("/api/suggestions", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            suggestions = response.json()
            print(f"   Suggestions: {len(suggestions)} items")
            for i, suggestion in enumerate(suggestions[:3], 1):
                print(f"   {i}. {suggestion}")
        
        print("\n6. User Profile:")
        response = client.get("/api/profile", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            profile = response.json()
            print(f"   User: {profile['user_id']}")
            print(f"   Expertise: {profile['expertise_level']}")
            print(f"   Color scheme: {profile['color_scheme']}")

def demo_websocket():
    """Demonstrate WebSocket functionality"""
    print("\n7. WebSocket Communication:")
    client = TestClient(app)
    
    try:
        with client.websocket_connect("/ws/chat/demo_user") as websocket:
            # Receive welcome message
            welcome = websocket.receive_json()
            print(f"   Welcome: {welcome['message']}")
            
            # Send query
            query = {"type": "query", "message": "Show revenue trends"}
            websocket.send_json(query)
            
            # Receive response
            response = websocket.receive_json()
            print(f"   Query response: {response['type']}")
            print(f"   Query ID: {response['query_id']}")
            print(f"   Data: {response['data']['chart_type']} with {len(response['data']['values'])} values")
            
            # Test ping/pong
            websocket.send_json({"type": "ping"})
            pong = websocket.receive_json()
            print(f"   Ping/Pong: {pong['type']}")
            
    except Exception as e:
        print(f"   WebSocket error: {e}")

def demo_error_handling():
    """Demonstrate error handling"""
    print("\n8. Error Handling:")
    client = TestClient(app)
    
    # Test invalid login
    response = client.post("/api/auth/login", json={"username": "invalid", "password": "wrong"})
    print(f"   Invalid login: {response.status_code}")
    
    # Test unauthorized access
    response = client.get("/api/profile")
    print(f"   Unauthorized access: {response.status_code}")
    
    # Test invalid endpoint
    response = client.get("/api/nonexistent")
    print(f"   Invalid endpoint: {response.status_code}")

if __name__ == "__main__":
    demo_api_endpoints()
    demo_websocket()
    demo_error_handling()
    
    print("\n" + "=" * 50)
    print("✅ Demo completed successfully!")
    print("\nTo start the server manually:")
    print("   uvicorn main:app --host 0.0.0.0 --port 8000 --reload")
    print("\nAPI Documentation available at:")
    print("   http://localhost:8000/docs")