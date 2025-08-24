"""
Integration example demonstrating comprehensive error handling and user-friendly messaging.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any

from intelligent_chat.error_handler import ErrorHandler, RecoveryResult, RecoveryStrategy
from intelligent_chat.user_friendly_errors import UserFriendlyErrorGenerator, ErrorRecoveryHandler
from intelligent_chat.models import ContextEntry, ToolResult
from intelligent_chat.exceptions import ToolExecutionError, TimeoutError, ResourceLimitError


async def demonstrate_error_handling_integration():
    """
    Demonstrate the complete error handling and recovery flow.
    """
    print("=== Error Handling and Recovery Integration Demo ===\n")
    
    # Initialize components
    error_handler = ErrorHandler(enable_fallback_tools=True)
    error_generator = UserFriendlyErrorGenerator(enable_technical_details=True)
    recovery_handler = ErrorRecoveryHandler()
    
    # Simulate different error scenarios
    scenarios = [
        {
            "name": "Tool Execution Failure",
            "error": ToolExecutionError("Database connection failed", "CreateSupportTicket"),
            "context": {
                "query": "Create a support ticket for my billing issue",
                "user_id": "user123",
                "session_id": "session456"
            }
        },
        {
            "name": "Timeout Error",
            "error": TimeoutError("Request processing timeout", "complex_analysis", 45.0),
            "context": {
                "query": "Please analyze all my data and provide comprehensive insights with detailed charts and graphs",
                "user_id": "user456"
            }
        },
        {
            "name": "Resource Limit Error",
            "error": ResourceLimitError("Memory limit exceeded", "memory", 100.0, 80.0),
            "context": {
                "query": "Process large dataset",
                "user_id": "user789"
            }
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"{i}. {scenario['name']}")
        print("-" * 50)
        
        # Step 1: Handle the error with comprehensive error handler
        print("Step 1: Comprehensive Error Handling")
        context_entries = [
            ContextEntry(
                content="Previous conversation context",
                source="conversation",
                relevance_score=0.8,
                timestamp=datetime.now(),
                context_type="conversation"
            )
        ]
        
        recovery_result = error_handler.handle_tool_failure(
            scenario["context"].get("tool_name", "unknown_tool"),
            scenario["error"],
            scenario["context"]["query"],
            context_entries,
            scenario["context"]
        )
        
        print(f"  Recovery Strategy: {recovery_result.strategy_used.value}")
        print(f"  Success: {recovery_result.success}")
        if recovery_result.user_message:
            print(f"  Message: {recovery_result.user_message}")
        
        # Step 2: Generate user-friendly error message
        print("\nStep 2: User-Friendly Error Generation")
        user_friendly_error = error_generator.generate_user_friendly_error(
            scenario["error"], 
            scenario["context"]
        )
        
        print(f"  Title: {user_friendly_error.title}")
        print(f"  Message: {user_friendly_error.message}")
        print(f"  Category: {user_friendly_error.category.value}")
        print(f"  Severity: {user_friendly_error.severity.value}")
        print(f"  Suggested Actions: {user_friendly_error.suggested_actions[:2]}")
        
        # Step 3: Create UI component
        print("\nStep 3: UI Component Creation")
        ui_component = error_generator.create_error_ui_component(user_friendly_error)
        
        print(f"  Component Type: {ui_component.component_type}")
        print(f"  Icon: {ui_component.icon}")
        print(f"  Color Scheme: {ui_component.color_scheme}")
        print(f"  Recovery Actions: {len(ui_component.actions)}")
        
        # Step 4: Demonstrate recovery action handling
        print("\nStep 4: Recovery Action Handling")
        if user_friendly_error.recovery_buttons:
            first_action = user_friendly_error.recovery_buttons[0]
            print(f"  Simulating: {first_action['label']}")
            
            recovery_action_result = await recovery_handler.handle_recovery_action(
                first_action["action_id"],
                scenario["context"]
            )
            
            print(f"  Action Result: {recovery_action_result['success']}")
            print(f"  Action Message: {recovery_action_result['message']}")
        
        # Step 5: Show error statistics
        print("\nStep 5: Error Statistics")
        stats = error_handler.get_error_statistics()
        print(f"  Total Errors Recorded: {stats['total_errors']}")
        
        print("\n" + "="*70 + "\n")
    
    # Demonstrate partial results handling
    print("Bonus: Partial Results Handling")
    print("-" * 50)
    
    successful_results = [
        ToolResult(
            tool_name="BTWebsiteSearch",
            success=True,
            result="Found information about BT services",
            execution_time=2.5
        ),
        ToolResult(
            tool_name="BTSupportHours",
            success=True,
            result="Support hours: 9 AM - 5 PM",
            execution_time=1.0
        )
    ]
    
    failed_tools = ["CreateSupportTicket", "DatabaseQuery"]
    
    partial_response = error_handler.create_partial_result(
        successful_results,
        failed_tools,
        "Help me with BT services and create a support ticket"
    )
    
    print(f"Partial Response Content: {partial_response.content[:100]}...")
    print(f"Confidence Score: {partial_response.confidence_score:.2f}")
    print(f"Tools Used: {partial_response.tools_used}")
    print(f"UI Hints: {list(partial_response.ui_hints.keys())}")
    
    print("\n=== Demo Complete ===")


def demonstrate_error_pattern_detection():
    """
    Demonstrate error pattern detection and adaptive recovery strategies.
    """
    print("\n=== Error Pattern Detection Demo ===\n")
    
    error_handler = ErrorHandler()
    
    # Simulate repeated timeout errors for the same tool
    print("Simulating repeated timeout errors...")
    
    for i in range(4):
        error = TimeoutError(f"Timeout {i+1}", "problematic_tool", 30.0)
        context_entries = []
        execution_context = {"attempt": i+1}
        
        result = error_handler.handle_tool_failure(
            "problematic_tool",
            error,
            "test query",
            context_entries,
            execution_context
        )
        
        print(f"Attempt {i+1}: Strategy = {result.strategy_used.value}")
        
        # After multiple failures, should eventually switch to fallback strategy
        if i >= 2 and result.strategy_used == RecoveryStrategy.FALLBACK_TOOL:
            print("  ✓ Switched to fallback tool strategy after repeated failures")
        elif i >= 2:
            print(f"  → Still using {result.strategy_used.value} strategy")
    
    # Show error statistics
    stats = error_handler.get_error_statistics()
    print(f"\nError Statistics:")
    print(f"  Total Errors: {stats['total_errors']}")
    print(f"  Component Stats: {list(stats['component_stats'].keys())}")
    
    print("\n=== Pattern Detection Demo Complete ===")


if __name__ == "__main__":
    # Run the integration demonstration
    asyncio.run(demonstrate_error_handling_integration())
    
    # Run the pattern detection demonstration
    demonstrate_error_pattern_detection()