# agents/state.py
"""
Shared state definition for the multi-agent customer support system.

This state is passed between LangGraph nodes (agents) and stores:
- messages: List of messages for A2A compatibility (required by LangGraph A2A)
- user query
- extracted intents and entities
- MCP query results
- intermediate and final agent outputs
- A2A communication logs
"""

from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict


class AgentMessage(TypedDict):
    """Represents a single agent-to-agent message in the log."""
    sender: str
    receiver: str
    content: str
    timestamp: Optional[str]


class CSState(TypedDict, total=False):
    """
    Shared state for the customer support workflow.
    Fields are optional and populated gradually as agents run.
    
    IMPORTANT: For LangGraph A2A compatibility, the state must include a 'messages' key
    that contains a list of message dictionaries.
    """

    # Required for A2A: messages list (each message is a dict with 'content' and optionally 'role', 'name')
    messages: List[Dict[str, Any]]  # A2A-compatible message list
    
    # Raw user input
    user_query: str

    # Scenario and high-level intent classification
    scenario: str                     # e.g., "task_allocation", "escalation", "multi_step", "multi_intent", "coordinated"
    intents: List[str]                # e.g., ["upgrade_account"], ["cancel_subscription", "billing_issue"]

    # Extracted entities
    customer_id: Optional[int]
    new_email: Optional[str]
    urgency: Optional[str]            # e.g., "normal", "high"

    # MCP data results
    customer_data: Optional[Dict[str, Any]]
    customer_list: Optional[List[Dict[str, Any]]]
    tickets: Optional[List[Dict[str, Any]]]

    # Support agent output
    support_response: Optional[str]

    # A2A logging (additional structured logs for debugging)
    logs: List[AgentMessage]

    # End-of-flow flag
    done: bool
