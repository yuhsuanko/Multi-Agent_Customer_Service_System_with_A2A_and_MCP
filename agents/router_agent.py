# agents/router_agent.py
"""
Router agent.

Responsibilities:
- Analyze the user query
- Detect scenario type and intents
- Extract key entities (customer_id, email, urgency)
- Log routing decisions

The actual routing between nodes is handled in graph.py
via conditional edges based on fields in CSState.
"""

import re
from typing import List

from .state import CSState, AgentMessage


def _extract_customer_id(query: str):
    """
    Very simple heuristic to extract a numeric customer ID from text.
    Assumes the ID appears as a standalone number of 1–10 digits.
    """
    match = re.search(r"\b(\d{1,10})\b", query)
    return int(match.group(1)) if match else None


def _extract_email(query: str):
    """
    Simple email pattern detection.
    This is not a full RFC-compliant regex, but good enough for demo.
    """
    match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", query)
    return match.group(0) if match else None


def _detect_intents(query: str) -> List[str]:
    """
    Detect high-level intents based on keywords in the query.
    This is a simple rule-based classifier for demonstration.
    """
    q = query.lower()
    intents: List[str] = []

    if "upgrade" in q:
        intents.append("upgrade_account")
    if "cancel" in q:
        intents.append("cancel_subscription")
    if "billing" in q or "charged twice" in q or "refund" in q:
        intents.append("billing_issue")
    if "update my email" in q or "change my email" in q or "new email" in q:
        intents.append("update_email")
    if "ticket history" in q or "my ticket history" in q:
        intents.append("ticket_history")
    if "high-priority tickets" in q or "high priority tickets" in q or ("premium customers" in q and "high" in q):
        intents.append("high_priority_report")
    if "active customers" in q and "open tickets" in q:
        intents.append("active_with_open_tickets")
    if "premium customers" in q or "premium" in q:
        intents.append("premium_customers")
    if "get customer information" in q or "get customer info" in q:
        intents.append("simple_customer_info")
    if "need help with my account" in q or "help with my account" in q:
        intents.append("account_help")
    
    # Fallback if nothing matched
    if not intents:
        intents.append("general_support")

    return intents


def _detect_scenario(intents: List[str]) -> str:
    """
    Map intent combinations to the scenarios required by the assignment:
    - Scenario 1: Task Allocation
    - Scenario 2: Negotiation/Escalation
    - Scenario 3: Multi-Step Coordination
    plus additional test scenarios.
    """
    # Scenario 3 (multi-step coordination)
    if "high_priority_report" in intents or "active_with_open_tickets" in intents:
        return "multi_step"

    # Scenario 2 (negotiation / escalation)
    if "cancel_subscription" in intents and "billing_issue" in intents:
        return "escalation"

    # Scenario 1 (simple customer info or account help)
    if "simple_customer_info" in intents or "account_help" in intents:
        return "task_allocation"

    # Multi-intent (parallel tasks)
    if "update_email" in intents and "ticket_history" in intents:
        return "multi_intent"

    # Default coordinated support
    return "coordinated"


def router_node(state: CSState) -> CSState:
    """
    Router node.

    On the first call:
    - Extract intents, scenario, and entities from user_query.
    - Append a log message documenting the analysis.
    - Add messages to the messages list for A2A compatibility.
    """
    messages = state.get("messages", [])
    logs = state.get("logs", [])

    if "intents" not in state or "scenario" not in state:
        query = state["user_query"]

        customer_id = _extract_customer_id(query)
        new_email = _extract_email(query)
        intents = _detect_intents(query)
        scenario = _detect_scenario(intents)

        state["customer_id"] = customer_id
        state["new_email"] = new_email
        state["intents"] = intents
        state["scenario"] = scenario

        # Simple urgency heuristic: billing issues or "charged twice" are considered high urgency
        if "billing_issue" in intents or "charged twice" in query.lower() or "refund immediately" in query.lower():
            state["urgency"] = "high"
        else:
            state["urgency"] = "normal"

        # Add message for A2A compatibility
        analysis_msg = f"Router analyzed query: Scenario={scenario}, intents={intents}, customer_id={customer_id}, urgency={state['urgency']}"
        messages.append({
            "role": "assistant",
            "name": "Router",
            "content": analysis_msg
        })

        logs.append(AgentMessage(
            sender="Router",
            receiver="Router",
            content=f"Parsed query. Scenario={scenario}, intents={intents}, "
                    f"customer_id={customer_id}, new_email={new_email}, urgency={state['urgency']}"
        ))
        
        # For Scenario 2 (escalation): Log negotiation detection
        if scenario == "escalation":
            logs.append(AgentMessage(
                sender="Router",
                receiver="SupportAgent",
                content="Router detected multiple intents (cancellation + billing). Can you handle this?"
            ))

    state["messages"] = messages
    state["logs"] = logs
    return state
