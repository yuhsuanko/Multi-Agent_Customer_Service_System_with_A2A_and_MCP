# demo/main.py
"""
End-to-end demo for the multi-agent customer support system (LangGraph version).

This script:
- Builds the LangGraph workflow
- Runs several test queries that match the assignment scenarios
- Prints agent-to-agent logs and final responses

Run this from the project root directory:
    python demo/main.py
"""

import sys
from pathlib import Path

# Add project root to Python path to allow imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from agents.graph import build_workflow
from agents.state import CSState


def run_query(app, query: str, scenario_name: str = ""):
    """
    Helper to run a single query through the workflow and print logs + response.
    """
    print("\n" + "=" * 80)
    if scenario_name:
        print(f"SCENARIO: {scenario_name}")
        print("-" * 80)
    print(f"USER QUERY: {query}")
    print("=" * 80)

    # Initial state for this query (must include messages for A2A compatibility)
    initial_state: CSState = {
        "messages": [
            {
                "role": "user",
                "content": query
            }
        ],
        "user_query": query,
        "logs": [],
    }

    final_state = app.invoke(initial_state)

    # Print detected scenario and intents
    scenario = final_state.get("scenario", "unknown")
    intents = final_state.get("intents", [])
    print(f"\n[Detected Scenario: {scenario}]")
    print(f"[Detected Intents: {', '.join(intents)}]")

    # Print A2A logs
    print("\n--- AGENT-TO-AGENT COMMUNICATION LOGS ---")
    for msg in final_state.get("logs", []):
        print(f"  [{msg['sender']} -> {msg['receiver']}] {msg['content']}")
    if not final_state.get("logs"):
        print("  (No inter-agent logs)")

    # Print A2A messages
    messages = final_state.get("messages", [])
    if messages:
        print("\n--- A2A MESSAGES ---")
        for msg in messages:
            name = msg.get("name", msg.get("role", "unknown"))
            content = msg.get("content", "")
            print(f"  [{name}]: {content[:100]}{'...' if len(content) > 100 else ''}")

    # Print final response
    print("\n--- FINAL RESPONSE ---")
    response = final_state.get("support_response", "(No response generated)")
    print(response)
    print("\n" + "=" * 80 + "\n")


def main():
    print("\n" + "=" * 80)
    print("MULTI-AGENT CUSTOMER SERVICE SYSTEM - END-TO-END DEMONSTRATION")
    print("=" * 80)
    print("\nThis demo shows how specialized agents coordinate using A2A communication")
    print("and access customer data through the Model Context Protocol (MCP).")
    
    # Build the workflow
    app = build_workflow()

    print("\n\n" + "=" * 80)
    print("PART 1: ASSIGNMENT REQUIRED SCENARIOS")
    print("=" * 80)

    # Scenario 1: Task Allocation
    run_query(
        app, 
        "I need help with my account, customer ID 1",
        "Scenario 1: Task Allocation"
    )

    # Scenario 2: Negotiation/Escalation
    run_query(
        app,
        "I want to cancel my subscription but I'm having billing issues",
        "Scenario 2: Negotiation/Escalation"
    )

    # Scenario 3: Multi-Step Coordination
    run_query(
        app,
        "What's the status of all high-priority tickets for premium customers?",
        "Scenario 3: Multi-Step Coordination"
    )

    print("\n\n" + "=" * 80)
    print("PART 2: TEST SCENARIOS FROM ASSIGNMENT")
    print("=" * 80)

    # Test 1: Simple Query
    run_query(
        app, 
        "Get customer information for ID 5",
        "Test 1: Simple Query"
    )

    # Test 2: Coordinated Query
    run_query(
        app, 
        "I'm customer 12345 and need help upgrading my account",
        "Test 2: Coordinated Query"
    )

    # Test 3: Complex Query
    run_query(
        app, 
        "Show me all active customers who have open tickets",
        "Test 3: Complex Query"
    )

    # Test 4: Escalation
    run_query(
        app, 
        "I've been charged twice, please refund immediately!",
        "Test 4: Escalation"
    )

    # Test 5: Multi-Intent
    run_query(
        app, 
        "Update my email to new.email@example.com and show my ticket history.",
        "Test 5: Multi-Intent"
    )

    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
