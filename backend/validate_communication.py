#!/usr/bin/env python3
"""
Simple validation script for communication protocols implementation.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def validate_imports():
    """Validate that all communication modules can be imported"""
    print("🔍 Validating imports...")
    
    try:
        from communication import (
            MCPContextStore, A2AMessageBroker, ACPOrchestrator,
            CommunicationManager, MessageRouter, RetryManager,
            ContextData, AgentMessage, WorkflowTask,
            MessageType, TaskStatus, AgentType
        )
        print("✅ All communication modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def validate_models():
    """Validate that data models can be instantiated"""
    print("🔍 Validating data models...")
    
    try:
        from communication.models import (
            ContextData, AgentMessage, WorkflowTask,
            MessageType, TaskStatus, AgentType
        )
        
        # Test ContextData
        context = ContextData(
            session_id="test_session",
            data={"test": "data"}
        )
        print(f"✅ ContextData created: {context.context_id}")
        
        # Test AgentMessage
        message = AgentMessage(
            message_type=MessageType.QUERY_PROCESSING,
            sender=AgentType.BACKEND,
            recipient=AgentType.NLP,
            payload={"test": "payload"}
        )
        print(f"✅ AgentMessage created: {message.message_id}")
        
        # Test WorkflowTask
        task = WorkflowTask(
            workflow_id="test_workflow",
            task_name="test_task",
            agent_type=AgentType.NLP,
            payload={"test": "task"}
        )
        print(f"✅ WorkflowTask created: {task.task_id}")
        
        return True
    except Exception as e:
        print(f"❌ Model validation error: {e}")
        return False

def validate_protocol_classes():
    """Validate that protocol classes can be instantiated"""
    print("🔍 Validating protocol classes...")
    
    try:
        from communication import (
            MCPContextStore, A2AMessageBroker, ACPOrchestrator,
            CommunicationManager, MessageRouter, RetryManager
        )
        
        # Test MCP Context Store
        mcp_store = MCPContextStore("redis://localhost:6379")
        print("✅ MCPContextStore instantiated")
        
        # Test A2A Message Broker
        a2a_broker = A2AMessageBroker("amqp://guest:guest@localhost:5672/")
        print("✅ A2AMessageBroker instantiated")
        
        # Test ACP Orchestrator
        acp_orchestrator = ACPOrchestrator(
            "redis://localhost:6379/1",
            "redis://localhost:6379/2"
        )
        print("✅ ACPOrchestrator instantiated")
        
        # Test Communication Manager
        comm_manager = CommunicationManager()
        print("✅ CommunicationManager instantiated")
        
        # Test Message Router
        router = MessageRouter(mcp_store, a2a_broker, acp_orchestrator)
        print("✅ MessageRouter instantiated")
        
        # Test Retry Manager
        retry_manager = RetryManager()
        print("✅ RetryManager instantiated")
        
        return True
    except Exception as e:
        print(f"❌ Protocol class validation error: {e}")
        return False

def validate_file_structure():
    """Validate that all required files exist"""
    print("🔍 Validating file structure...")
    
    required_files = [
        "communication/__init__.py",
        "communication/models.py",
        "communication/mcp.py",
        "communication/a2a.py",
        "communication/acp.py",
        "communication/router.py",
        "communication/manager.py",
        "communication/example_usage.py",
        "tests/test_communication.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files exist")
        return True

def validate_dependencies():
    """Validate that required dependencies are specified"""
    print("🔍 Validating dependencies...")
    
    try:
        with open("pyproject.toml", "r") as f:
            content = f.read()
        
        required_deps = [
            "redis",
            "aio-pika",
            "celery",
            "kombu",
            "pydantic"
        ]
        
        missing_deps = []
        for dep in required_deps:
            if dep not in content:
                missing_deps.append(dep)
        
        if missing_deps:
            print(f"❌ Missing dependencies in pyproject.toml: {missing_deps}")
            return False
        else:
            print("✅ All required dependencies specified")
            return True
    except Exception as e:
        print(f"❌ Dependency validation error: {e}")
        return False

def main():
    """Run all validations"""
    print("🚀 Starting Communication Protocols Validation")
    print("=" * 50)
    
    validations = [
        ("File Structure", validate_file_structure),
        ("Dependencies", validate_dependencies),
        ("Imports", validate_imports),
        ("Data Models", validate_models),
        ("Protocol Classes", validate_protocol_classes)
    ]
    
    passed = 0
    failed = 0
    
    for name, validation_func in validations:
        print(f"\n{name}:")
        print("-" * 30)
        
        try:
            if validation_func():
                passed += 1
                print(f"✅ {name} validation PASSED")
            else:
                failed += 1
                print(f"❌ {name} validation FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {name} validation FAILED with exception: {e}")
    
    print("\n" + "=" * 50)
    print("Validation Summary:")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Total: {passed + failed}")
    print("=" * 50)
    
    if failed == 0:
        print("🎉 All validations passed! Communication protocols are ready.")
        return True
    else:
        print(f"💥 {failed} validations failed!")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nValidation interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"Validation failed with error: {e}")
        sys.exit(1)