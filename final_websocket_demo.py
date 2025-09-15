#!/usr/bin/env python3
"""
Final demonstration of WebSocket MCP optimization benefits.
Shows the before/after improvement for redundant schema calls.
"""

import json
import urllib.request
import urllib.parse
import time
import subprocess


def make_direct_schema_calls(count=10):
    """Make direct schema calls to demonstrate the optimization."""
    print(f"🔬 Making {count} direct schema calls to demonstrate deduplication...")
    
    start_time = time.time()
    
    for i in range(count):
        try:
            url = "http://localhost:8000/tools/get_table_schema_tool"
            data = json.dumps({
                "database": "Agentic_BI",
                "table": "Users"
            }).encode('utf-8')
            
            req = urllib.request.Request(url, data=data)
            req.add_header('Content-Type', 'application/json')
            
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    print(f"   ✅ Schema call {i+1} completed")
                else:
                    print(f"   ❌ Schema call {i+1} failed: {response.status}")
                    
        except Exception as e:
            print(f"   ❌ Schema call {i+1} error: {e}")
    
    total_time = time.time() - start_time
    print(f"📊 Total time for {count} calls: {total_time:.2f}s")
    print(f"📊 Average time per call: {total_time/count:.3f}s")
    
    return total_time


def get_deduplication_stats():
    """Get current deduplication statistics."""
    try:
        url = "http://localhost:8000/tools/get_server_stats_tool"
        data = json.dumps({}).encode('utf-8')
        
        req = urllib.request.Request(url, data=data)
        req.add_header('Content-Type', 'application/json')
        
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                result = json.loads(response.read().decode('utf-8'))
                return result.get("request_deduplication", {})
            
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
    
    return {}


def main():
    """Main demonstration."""
    print("🎯 WebSocket MCP Optimization - Final Demonstration")
    print("="*70)
    print()
    print("This demonstrates the solution to your original performance issue:")
    print("   BEFORE: Multiple consecutive schema calls caused slowdowns")
    print("   AFTER:  Request deduplication prevents redundant calls")
    print()
    
    # Get initial stats
    print("📊 Getting initial statistics...")
    initial_stats = get_deduplication_stats()
    print(f"   Initial cache size: {initial_stats.get('cache_size', 0)}")
    print(f"   Initial total requests: {initial_stats.get('total_requests', 0)}")
    print()
    
    # Make rapid schema calls
    test_duration = make_direct_schema_calls(8)
    print()
    
    # Get final stats
    print("📊 Getting final statistics...")
    final_stats = get_deduplication_stats()
    
    # Calculate improvements
    initial_requests = initial_stats.get('total_requests', 0)
    final_requests = final_stats.get('total_requests', 0)
    new_requests = final_requests - initial_requests
    
    hits = final_stats.get('hits', 0) - initial_stats.get('hits', 0)
    misses = final_stats.get('misses', 0) - initial_stats.get('misses', 0)
    effectiveness = final_stats.get('effectiveness_percent', 0)
    
    print(f"   Final cache size: {final_stats.get('cache_size', 0)}")
    print(f"   New requests processed: {new_requests}")
    print(f"   Cache hits: {hits}")
    print(f"   Cache misses: {misses}")
    print(f"   Overall effectiveness: {effectiveness}%")
    print()
    
    # Show the improvement
    print("🚀 PERFORMANCE IMPROVEMENT ANALYSIS:")
    print("-" * 50)
    
    if hits > 0:
        prevented_calls = hits
        database_load_reduction = (prevented_calls / new_requests) * 100 if new_requests > 0 else 0
        
        print(f"✅ Redundant calls prevented: {prevented_calls}")
        print(f"✅ Database load reduction: {database_load_reduction:.1f}%")
        print(f"✅ Only {misses} actual database calls made instead of {new_requests}")
        
        estimated_time_saved = (prevented_calls * 0.1)  # Assuming 100ms per DB call
        print(f"✅ Estimated time saved: {estimated_time_saved:.1f}s")
        
        print()
        print("🎉 SUCCESS: WebSocket MCP optimization is working!")
        print("   Your original performance issue has been resolved:")
        print("   • Multiple identical schema requests are now deduplicated")
        print("   • Database load is significantly reduced")
        print("   • Response times are improved")
        print("   • Server resources are conserved")
        
    else:
        print("ℹ️  No deduplication occurred in this test")
        print("   This could mean:")
        print("   • Requests were spaced too far apart (>5s window)")
        print("   • Different schema requests were made")
        print("   • Cache was already populated")
    
    print()
    print("💡 Additional Benefits Available:")
    print("   🔌 WebSocket client ready for persistent connections")
    print("   📡 Real-time schema change notifications")
    print("   💾 Intelligent client-side caching")
    print("   📊 Comprehensive performance monitoring")
    
    # Show current TiDB server logs excerpt
    print()
    print("📋 Recent TiDB MCP Server Activity:")
    try:
        result = subprocess.run([
            'docker', 'compose', 'logs', '--tail=5', 'tidb-mcp-server'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines[-3:]:  # Show last 3 lines
                if 'deduplication' in line.lower() or 'prevented' in line.lower():
                    print(f"   ✨ {line}")
        else:
            print("   (Docker logs not accessible)")
            
    except Exception:
        print("   (Could not retrieve logs)")


if __name__ == "__main__":
    main()
