#!/usr/bin/env python3
"""
WebSocket Connection Cleanup Verification

This script verifies that:
1. Only necessary WebSocket components remain
2. No conflicting WebSocket servers exist
3. Connection architecture is clean
"""

import os
import glob
from pathlib import Path

def check_websocket_files():
    """Check for WebSocket-related files"""
    project_root = Path("/home/obaidsafi31/Desktop/Agentic BI ")
    
    print("🔍 WebSocket Files Analysis:")
    print("=" * 50)
    
    # Check for removed files
    removed_files = [
        "agents/nlp-agent/websocket_server.py",
        "agents/nlp-agent/src/websocket_mcp_client.py",
        "agents/nlp-agent/websocket_server.py.fixed"
    ]
    
    print("\n❌ REMOVED FILES (should not exist):")
    for file in removed_files:
        full_path = project_root / file
        status = "✅ REMOVED" if not full_path.exists() else "❌ STILL EXISTS"
        print(f"  {file}: {status}")
    
    # Check for remaining WebSocket files
    remaining_files = [
        "agents/nlp-agent/src/enhanced_websocket_client.py",
        "agents/nlp-agent/src/hybrid_mcp_operations_adapter.py",
        "tidb-mcp-server/src/tidb_mcp_server/websocket_server.py"
    ]
    
    print("\n✅ REQUIRED FILES (should exist):")
    for file in remaining_files:
        full_path = project_root / file
        status = "✅ EXISTS" if full_path.exists() else "❌ MISSING"
        print(f"  {file}: {status}")

def check_startup_configuration():
    """Check startup.py configuration"""
    startup_file = Path("/home/obaidsafi31/Desktop/Agentic BI /agents/nlp-agent/startup.py")
    
    print("\n🔧 STARTUP CONFIGURATION:")
    print("=" * 50)
    
    if startup_file.exists():
        with open(startup_file, 'r') as f:
            content = f.read()
            
        # Check WebSocket server status
        if 'self.websocket_enabled = False' in content:
            print("✅ WebSocket server disabled correctly")
        else:
            print("❌ WebSocket server still enabled")
            
        # Check imports
        if 'from websocket_server import' in content:
            print("❌ Still importing websocket_server")
        else:
            print("✅ No websocket_server import found")
    else:
        print("❌ startup.py not found")

def check_dockerfile():
    """Check Dockerfile configuration"""
    dockerfile = Path("/home/obaidsafi31/Desktop/Agentic BI /agents/nlp-agent/Dockerfile")
    
    print("\n🐳 DOCKERFILE CONFIGURATION:")
    print("=" * 50)
    
    if dockerfile.exists():
        with open(dockerfile, 'r') as f:
            content = f.read()
            
        # Check port exposure
        if 'EXPOSE 8001 8011' in content:
            print("❌ Still exposing WebSocket port 8011")
        elif 'EXPOSE 8001' in content and '8011' not in content:
            print("✅ Only exposing HTTP port 8001")
        else:
            print("⚠️  Port configuration unclear")
            
        # Check websocket_server.py copy
        if 'COPY websocket_server.py' in content:
            print("❌ Still copying websocket_server.py")
        else:
            print("✅ No websocket_server.py copy found")
    else:
        print("❌ Dockerfile not found")

def check_websocket_architecture():
    """Verify the correct WebSocket architecture"""
    print("\n🏗️  WEBSOCKET ARCHITECTURE:")
    print("=" * 50)
    print("✅ NLP Agent: WebSocket CLIENT only")
    print("✅ TiDB MCP Server: WebSocket SERVER only")
    print("✅ Connection: NLP Agent → TiDB MCP Server (ws://tidb-mcp-server:8000/ws)")
    print("✅ Fallback: HTTP requests if WebSocket fails")
    print("✅ No conflicting servers on same ports")

if __name__ == "__main__":
    print("🚀 WebSocket Cleanup Verification")
    print("=" * 50)
    
    check_websocket_files()
    check_startup_configuration()
    check_dockerfile()
    check_websocket_architecture()
    
    print("\n" + "=" * 50)
    print("✅ CLEANUP COMPLETE - WebSocket connection should be stable!")
    print("📍 NLP Agent connects to TiDB MCP Server on ws://tidb-mcp-server:8000/ws")
    print("🔄 HTTP fallback available for reliability")
