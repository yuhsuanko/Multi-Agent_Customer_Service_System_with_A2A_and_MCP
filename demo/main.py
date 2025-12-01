# demo/main.py
"""
End-to-end demo for the multi-agent customer support system.

This script uses LangGraph SDK directly to execute the multi-agent workflow.
The LangGraph workflow orchestrates agents that communicate via A2A protocol:
- Router Agent (using LangGraph SDK) orchestrates other agents
- Router Agent → Customer Data Agent (A2A)
- Router Agent → Support Agent (A2A)
- Router Agent returns final response

Run this from the project root directory:
    python demo/main.py

Prerequisites:
- All servers must be running:
  - MCP Server (port 8000): python db_mcp_server.py
  - Data Agent (port 8002): python data_agent_server.py
  - Support Agent (port 8003): python support_agent_server.py
Note: Router Agent server is NOT required as we use LangGraph SDK directly.
"""

import sys
from pathlib import Path

# Add project root to Python path to allow imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import LangGraph SDK and workflow
from agents.graph import build_workflow
from agents.state import CSState


def run_query(query: str, scenario_name: str = ""):
    """
    Helper to run a single query using LangGraph SDK directly.
    
    This uses LangGraph SDK to execute the workflow:
    1. Build LangGraph workflow using SDK
    2. Create initial state with messages key (required for LangGraph A2A)
    3. Execute workflow using graph_app.invoke()
    4. Router Agent (in workflow) → Customer Data Agent (A2A)
    5. Router Agent (in workflow) → Support Agent (A2A)
    6. Return final response
    """
    print("\n" + "=" * 80)
    if scenario_name:
        print(f"SCENARIO: {scenario_name}")
        print("-" * 80)
    print(f"USER QUERY: {query}")
    print("=" * 80)

    # Build LangGraph workflow using SDK
    try:
        print("\n[Building LangGraph workflow using SDK...]")
        graph_app = build_workflow()
    except Exception as e:
        print(f"\nERROR: Failed to build LangGraph workflow: {e}")
        print("Please ensure all dependencies are installed and agents modules are available.")
        return

    # Create initial state for LangGraph (with messages key for A2A compatibility)
    initial_state: CSState = {
        "messages": [],  # Required for LangGraph A2A compatibility
        "user_query": query,
        "logs": [],
    }

    # Execute workflow using LangGraph SDK
    try:
        print("[Executing LangGraph workflow...]")
        final_state = graph_app.invoke(initial_state)
    except Exception as e:
        print(f"\nERROR: Failed to execute LangGraph workflow: {e}")
        print("Please ensure all agent servers are running:")
        print(f"  - MCP Server (port 8000): python db_mcp_server.py")
        print(f"  - Data Agent (port 8002): python data_agent_server.py")
        print(f"  - Support Agent (port 8003): python support_agent_server.py")
        return

    # Extract results from final state
    final_state = {
        "scenario": final_state.get("scenario", "unknown"),
        "intents": final_state.get("intents", []),
        "logs": final_state.get("logs", []),
        "support_response": final_state.get("support_response", ""),
    }

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
    print("\nThis demo uses LangGraph SDK directly to execute the multi-agent workflow.")
    print("The workflow orchestrates agents that communicate via A2A protocol:")
    print("1. LangGraph SDK builds and executes workflow")
    print("2. Router Agent (in workflow) → Customer Data Agent (A2A)")
    print("3. Router Agent (in workflow) → Support Agent (A2A)")
    print("4. Workflow returns final response")
    print("\nNOTE: This demo uses LangGraph SDK (StateGraph) as required.")
    print("Agents are independent services with A2A endpoints.")
    
    # Verify LangGraph SDK is available
    try:
        from langgraph.graph import StateGraph, END
        print("LangGraph SDK is available")
    except ImportError as e:
        print(f"\nERROR: LangGraph SDK not available: {e}")
        print("Please install LangGraph: pip install langgraph")
        return
    
    # Build workflow to verify it works
    try:
        print("[Building LangGraph workflow using SDK...]")
        graph_app = build_workflow()
        print("LangGraph workflow built successfully")
    except Exception as e:
        print(f"\nERROR: Failed to build LangGraph workflow: {e}")
        return

    print("\n\n" + "=" * 80)
    print("PART 1: ASSIGNMENT REQUIRED SCENARIOS")
    print("=" * 80)

    # Scenario 1: Task Allocation
    run_query(
        "I need help with my account, customer ID 12345",
        "Scenario 1: Task Allocation"
    )

    # Scenario 2: Negotiation/Escalation
    run_query(
        "I want to cancel my subscription but I'm having billing issues",
        "Scenario 2: Negotiation/Escalation"
    )

    # Scenario 3: Multi-Step Coordination
    run_query(
        "What's the status of all high-priority tickets for premium customers?",
        "Scenario 3: Multi-Step Coordination"
    )

    print("\n\n" + "=" * 80)
    print("PART 2: TEST SCENARIOS FROM ASSIGNMENT")
    print("=" * 80)

    # Test 1: Simple Query
    run_query(
        "Get customer information for ID 5",
        "Test 1: Simple Query"
    )

    # Test 2: Coordinated Query
    run_query(
        "I'm customer 12345 and need help upgrading my account",
        "Test 2: Coordinated Query"
    )

    # Test 3: Complex Query
    run_query(
        "Show me all active customers who have open tickets",
        "Test 3: Complex Query"
    )

    # Test 4: Escalation
    run_query(
        "I've been charged twice, please refund immediately!",
        "Test 4: Escalation"
    )

    # Test 5: Multi-Intent
    run_query(
        "Update my email to new.email@example.com and show my ticket history.",
        "Test 5: Multi-Intent"
    )

    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
