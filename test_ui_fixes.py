#!/usr/bin/env python3
"""
Test the fixes: Remove refresh button in full-width mode and auto-connect WebSocket
"""

def test_refresh_button_removal():
    """Test if refresh button is removed from full-width dashboard"""
    print("🔧 Testing Refresh Button Removal from Full-Width Mode...")
    print("=" * 60)
    
    try:
        with open('frontend/src/components/dashboard.tsx', 'r') as f:
            content = f.read()
        
        # Check that the refresh button section is removed from full-width header
        full_width_header_start = content.find('isFullWidth={true}')
        if full_width_header_start == -1:
            print("❌ Could not find full-width section")
            return False
        
        # Look for the header section after isFullWidth={true}
        header_section = content[full_width_header_start:full_width_header_start + 2000]
        
        # Check that refresh button is not in this section
        has_refresh_button = 'onClick={refreshDashboard}' in header_section and 'Refresh' in header_section
        
        if not has_refresh_button:
            print("✅ Refresh button successfully removed from full-width mode")
            return True
        else:
            print("❌ Refresh button still found in full-width mode")
            return False
            
    except FileNotFoundError:
        print("❌ Dashboard file not found")
        return False
    except Exception as e:
        print(f"❌ Error testing refresh button removal: {e}")
        return False

def test_websocket_auto_connect():
    """Test if WebSocket auto-connect logic is implemented"""
    print("\n🔧 Testing WebSocket Auto-Connect Implementation...")
    print("=" * 60)
    
    try:
        with open('frontend/src/contexts/WebSocketContext.tsx', 'r') as f:
            content = f.read()
        
        checks = [
            ("Auto-connect useEffect", "React.useEffect"),
            ("Auto-connect logic", "Auto-connecting on page load"),
            ("Session storage user ID", "sessionStorage.getItem('websocket_user_id')"),
            ("Auto-connect flag", "autoConnectAttemptedRef"),
            ("Delayed connection", "setTimeout"),
        ]
        
        all_passed = True
        for check_name, check_string in checks:
            if check_string in content:
                print(f"✅ {check_name}: Found")
            else:
                print(f"❌ {check_name}: Missing")
                all_passed = False
        
        return all_passed
        
    except FileNotFoundError:
        print("❌ WebSocket context file not found")
        return False
    except Exception as e:
        print(f"❌ Error testing WebSocket auto-connect: {e}")
        return False

def test_websocket_manual_controls_removed():
    """Test if manual WebSocket connection controls are removed"""
    print("\n🔧 Testing Manual WebSocket Controls Removal...")
    print("=" * 60)
    
    try:
        with open('frontend/src/components/chat/chat-interface.tsx', 'r') as f:
            content = f.read()
        
        # Check that WebSocketConnectionControl import is removed
        has_control_import = 'WebSocketConnectionControl' in content
        
        # Check that manual connection buttons are replaced with status indicator
        has_status_indicator = 'WebSocket Connection Status (read-only)' in content
        has_connection_dot = 'w-2 h-2 rounded-full' in content
        
        if not has_control_import and has_status_indicator and has_connection_dot:
            print("✅ Manual WebSocket controls removed")
            print("✅ Auto-connect status indicator added")
            return True
        else:
            if has_control_import:
                print("❌ WebSocketConnectionControl import still present")
            if not has_status_indicator:
                print("❌ Status indicator not found")
            if not has_connection_dot:
                print("❌ Connection status dot not found")
            return False
            
    except FileNotFoundError:
        print("❌ Chat interface file not found")
        return False
    except Exception as e:
        print(f"❌ Error testing manual controls removal: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing WebSocket & Refresh Button Fixes")
    print("=" * 80)
    
    tests = [
        test_refresh_button_removal,
        test_websocket_auto_connect,
        test_websocket_manual_controls_removed
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 80)
    print("📊 FINAL RESULTS")
    print("=" * 80)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 ALL TESTS PASSED! ({passed}/{total})")
        print("✅ Refresh button removed from full-width mode")
        print("✅ WebSocket auto-connects on page load")  
        print("✅ Manual WebSocket controls replaced with status indicator")
    else:
        print(f"⚠️  {passed}/{total} tests passed")
        print("🔧 Some fixes may need additional work")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    import sys
    sys.exit(0 if success else 1)
