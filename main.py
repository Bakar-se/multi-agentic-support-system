"""
Main entry point for multi-agent customer support system.

Provides CLI interface to test the LangGraph workflow with all required scenarios.
"""

import os
import sys
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from graph import graph
from state import ConversationState


def print_separator():
    """Print a visual separator."""
    print("\n" + "=" * 80 + "\n")


def print_state_info(state: ConversationState, step_name: str = ""):
    """
    Print current state information for observability.
    
    Args:
        state: Current conversation state
        step_name: Name of the current step/agent
    """
    print_separator()
    if step_name:
        print(f"📍 Current Agent: {step_name}")
        print_separator()
    
    print("📊 State Information:")
    print(f"  Intent: {state.get('intent', 'Not classified')}")
    print(f"  Customer Email: {state.get('customer_email', 'Not provided')}")
    
    if state.get('cancellation_reason'):
        print(f"  Cancellation Reason: {state.get('cancellation_reason')}")
    
    if state.get('customer_data'):
        customer_data = state['customer_data']
        print(f"  Customer: {customer_data.get('name', 'N/A')} ({customer_data.get('tier', 'N/A')} tier)")
        print(f"  Plan: {customer_data.get('plan_type', 'N/A')}")
    
    if state.get('retention_offer'):
        offer = state['retention_offer']
        print(f"\n  💰 Retention Offer:")
        print(f"    Type: {offer.get('type', 'N/A')}")
        print(f"    Description: {offer.get('description', 'N/A')}")
        if 'new_cost' in offer:
            print(f"    New Cost: ${offer.get('new_cost', 'N/A')}")
        if 'duration_months' in offer:
            print(f"    Duration: {offer.get('duration_months', 'N/A')} months")
    
    if state.get('retrieved_context'):
        print(f"\n  📚 Retrieved RAG Context ({len(state['retrieved_context'])} chunks):")
        for idx, context in enumerate(state['retrieved_context'][:3], 1):  # Show first 3
            source = context.split(']')[0].replace('[', '') if ']' in context else 'unknown'
            preview = context[:150] + "..." if len(context) > 150 else context
            print(f"    {idx}. [{source}] {preview}")
    
    if state.get('final_action'):
        print(f"\n  ✅ Final Action: {state.get('final_action')}")
    
    print_separator()


def run_conversation(user_message: str, customer_email: Optional[str] = None) -> ConversationState:
    """
    Run a single conversation through the LangGraph workflow.
    
    Args:
        user_message: User's input message
        customer_email: Optional customer email (if not in message)
        
    Returns:
        Final conversation state
    """
    # Initialize state
    initial_state: ConversationState = {
        "user_message": user_message,
        "customer_email": customer_email,
        "customer_data": None,
        "intent": None,
        "cancellation_reason": None,
        "retrieved_context": [],
        "retention_offer": None,
        "final_action": None,
    }
    
    print(f"\n💬 User Message: {user_message}")
    if customer_email:
        print(f"📧 Customer Email: {customer_email}")
    
    # Invoke the graph workflow
    # The graph will execute: orchestrator -> (conditional) -> retention -> (conditional) -> processor
    try:
        final_state = graph.invoke(initial_state)
        return final_state
    except Exception as e:
        print(f"\n❌ Error executing workflow: {e}")
        import traceback
        traceback.print_exc()
        return initial_state


def test_scenario(scenario_name: str, user_message: str, customer_email: Optional[str] = None):
    """
    Test a specific scenario.
    
    Args:
        scenario_name: Name of the test scenario
        user_message: User message for the scenario
        customer_email: Optional customer email
    """
    print_separator()
    print(f"🧪 TEST SCENARIO: {scenario_name}")
    print_separator()
    
    final_state = run_conversation(user_message, customer_email)
    
    # Print final state summary
    print_state_info(final_state, "Final State")
    
    # Print summary
    print("📋 Summary:")
    print(f"  Intent Classified: {final_state.get('intent', 'None')}")
    print(f"  Customer Data Retrieved: {'Yes' if final_state.get('customer_data') else 'No'}")
    print(f"  RAG Context Retrieved: {len(final_state.get('retrieved_context', []))} chunks")
    print(f"  Retention Offer Generated: {'Yes' if final_state.get('retention_offer') else 'No'}")
    print(f"  Final Action: {final_state.get('final_action', 'None')}")
    print_separator()


def run_test_scenarios():
    """Run all 5 required test scenarios."""
    print("\n" + "=" * 80)
    print("🚀 RUNNING ALL TEST SCENARIOS")
    print("=" * 80)
    
    scenarios = [
        {
            "name": "1. Affordability-based cancellation",
            "message": "I want to cancel my Care+ plan. It's too expensive and I can't afford it anymore.",
            "email": "sarah.chen@email.com"
        },
        {
            "name": "2. Device malfunction + cancellation",
            "message": "My phone keeps overheating and I want to cancel my insurance because the device is defective.",
            "email": "mike.rodriguez@email.com"
        },
        {
            "name": "3. Value questioning",
            "message": "I'm thinking about canceling. I've had the plan for 8 months and haven't used it once. Is it really worth it?",
            "email": "lisa.kim@email.com"
        },
        {
            "name": "4. Technical support request",
            "message": "My phone battery is draining really fast. Can you help me fix this?",
            "email": "james.wilson@email.com"
        },
        {
            "name": "5. Billing discrepancy inquiry",
            "message": "I was charged $12.99 this month but I thought my plan was $6.99. Can you explain the charge?",
            "email": "maria.garcia@email.com"
        }
    ]
    
    for scenario in scenarios:
        test_scenario(scenario["name"], scenario["message"], scenario["email"])
        input("\nPress Enter to continue to next scenario...")
    
    print("\n✅ All test scenarios completed!")


def interactive_mode():
    """Run in interactive CLI mode."""
    print("\n" + "=" * 80)
    print("💬 INTERACTIVE MODE")
    print("=" * 80)
    print("Enter customer messages. Type 'quit' or 'exit' to stop.")
    print("You can optionally provide email in the format: email@example.com <message>")
    print_separator()
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if not user_input or user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            # Check if email is provided
            customer_email = None
            message = user_input
            
            # Simple email extraction (basic pattern)
            parts = user_input.split(' ', 1)
            if len(parts) == 2 and '@' in parts[0] and '.' in parts[0]:
                customer_email = parts[0]
                message = parts[1]
            
            final_state = run_conversation(message, customer_email)
            print_state_info(final_state, "Final State")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Main entry point."""
    print("\n" + "=" * 80)
    print("🤖 Multi-Agent Customer Support System")
    print("=" * 80)
    print("\nOptions:")
    print("  1. Run all test scenarios")
    print("  2. Interactive mode")
    print("  3. Single test scenario")
    print("  4. Exit")
    
    while True:
        try:
            choice = input("\nSelect option (1-4): ").strip()
            
            if choice == '1':
                run_test_scenarios()
                break
            elif choice == '2':
                interactive_mode()
                break
            elif choice == '3':
                print("\nEnter test scenario number (1-5):")
                print("  1. Affordability-based cancellation")
                print("  2. Device malfunction + cancellation")
                print("  3. Value questioning")
                print("  4. Technical support request")
                print("  5. Billing discrepancy inquiry")
                
                scenario_num = input("Scenario number: ").strip()
                scenarios = {
                    '1': ("1. Affordability-based cancellation", 
                          "I want to cancel my Care+ plan. It's too expensive and I can't afford it anymore.",
                          "sarah.chen@email.com"),
                    '2': ("2. Device malfunction + cancellation",
                          "My phone keeps overheating and I want to cancel my insurance because the device is defective.",
                          "mike.rodriguez@email.com"),
                    '3': ("3. Value questioning",
                          "I'm thinking about canceling. I've had the plan for 8 months and haven't used it once. Is it really worth it?",
                          "lisa.kim@email.com"),
                    '4': ("4. Technical support request",
                          "My phone battery is draining really fast. Can you help me fix this?",
                          "james.wilson@email.com"),
                    '5': ("5. Billing discrepancy inquiry",
                          "I was charged $12.99 this month but I thought my plan was $6.99. Can you explain the charge?",
                          "maria.garcia@email.com")
                }
                
                if scenario_num in scenarios:
                    name, message, email = scenarios[scenario_num]
                    test_scenario(name, message, email)
                else:
                    print("Invalid scenario number.")
                break
            elif choice == '4':
                print("\n👋 Goodbye!")
                sys.exit(0)
            else:
                print("Invalid choice. Please enter 1-4.")
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()

