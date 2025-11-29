# agents/data_agent.py
"""
Customer Data Agent.

Responsibilities:
- Interact with the customer/ticket database via MCP tools
- Fetch customer profiles
- Fetch lists of customers
- Fetch ticket histories
- Update customer records (email, status, etc.)

The agent does not craft user-facing text; it prepares structured data
for the Router and Support Agent.
"""

from .state import CSState, AgentMessage
from .mcp_client import (
    mcp_get_customer,
    mcp_list_customers,
    mcp_get_customer_history,
    mcp_update_customer,
)


def data_agent_node(state: CSState) -> CSState:
    """
    Data agent node.

    Behavior depends on the scenario and intents:
    - Scenario 1 (task_allocation / simple):
        -> fetch a single customer record
    - Scenario 3 (multi_step):
        -> fetch active customers; Support Agent will derive open/high-priority tickets
    - Multi-intent:
        -> update email and fetch ticket history for a single customer
    - Coordinated:
        -> fetch a single customer record for support flows (e.g., upgrade)
    """
    messages = state.get("messages", [])
    logs = state.get("logs", [])
    scenario = state.get("scenario", "coordinated")
    intents = state.get("intents", [])
    customer_id = state.get("customer_id")

    # Scenario 1: Simple customer info lookup
    if scenario == "task_allocation":
        if customer_id is not None:
            customer = mcp_get_customer(customer_id)
            state["customer_data"] = customer
            
            # Determine customer tier based on status
            # Active customers are considered "premium" for this scenario
            if customer.get("found") and customer.get("status") == "active":
                state["customer_tier"] = "premium"
            elif customer.get("found"):
                state["customer_tier"] = "standard"
            else:
                state["customer_tier"] = "unknown"
            
            msg_content = f"Fetched customer info for id={customer_id}, found={customer.get('found')}, tier={state.get('customer_tier', 'unknown')}"
            messages.append({
                "role": "assistant",
                "name": "CustomerDataAgent",
                "content": msg_content
            })
            logs.append(AgentMessage(
                sender="CustomerDataAgent",
                receiver="Router",
                content=f"Fetched customer info for id={customer_id}, found={customer.get('found')}, status={customer.get('status')}. Returning customer data to Router."
            ))
            
            # Router analyzes customer tier/status (conceptual step - tier determined here)
            if customer.get("found"):
                logs.append(AgentMessage(
                    sender="Router",
                    receiver="Router",
                    content=f"Analyzed customer tier/status: tier={state.get('customer_tier', 'unknown')}, status={customer.get('status')}"
                ))

    # Scenario 3: Multi-step coordination
    if scenario == "multi_step":
        # We interpret "premium customers" as "active customers" in this dataset.
        customers = mcp_list_customers(status="active", limit=200)
        state["customer_list"] = customers
        msg_content = f"Fetched {len(customers)} active customers for multi-step report."
        messages.append({
            "role": "assistant",
            "name": "CustomerDataAgent",
            "content": msg_content
        })
        logs.append(AgentMessage(
            sender="CustomerDataAgent",
            receiver="Router",
            content=msg_content
        ))

    # Multi-intent: update email and fetch ticket history
    if scenario == "multi_intent":
        if customer_id is not None and "update_email" in intents:
            new_email = state.get("new_email")
            if new_email:
                result = mcp_update_customer(customer_id, {"email": new_email})
                msg_content = f"Updated email for customer id={customer_id}. Result={result}"
                messages.append({
                    "role": "assistant",
                    "name": "CustomerDataAgent",
                    "content": msg_content
                })
                logs.append(AgentMessage(
                    sender="CustomerDataAgent",
                    receiver="Router",
                    content=msg_content
                ))

        if customer_id is not None and "ticket_history" in intents:
            history = mcp_get_customer_history(customer_id)
            state["tickets"] = history
            msg_content = f"Fetched {len(history)} tickets for customer id={customer_id}."
            messages.append({
                "role": "assistant",
                "name": "CustomerDataAgent",
                "content": msg_content
            })
            logs.append(AgentMessage(
                sender="CustomerDataAgent",
                receiver="Router",
                content=msg_content
            ))

    # Coordinated scenario: typically upgrade account or other support flows
    if scenario == "coordinated":
        if customer_id is not None:
            customer = mcp_get_customer(customer_id)
            state["customer_data"] = customer
            msg_content = f"Fetched customer info for coordinated scenario, id={customer_id}."
            messages.append({
                "role": "assistant",
                "name": "CustomerDataAgent",
                "content": msg_content
            })
            logs.append(AgentMessage(
                sender="CustomerDataAgent",
                receiver="Router",
                content=msg_content
            ))

    # Escalation scenario: fetch customer/billing data for context if customer_id is available
    if scenario == "escalation":
        if customer_id is not None:
            customer = mcp_get_customer(customer_id)
            state["customer_data"] = customer
            msg_content = f"Fetched billing/customer info for escalation scenario, id={customer_id}."
            messages.append({
                "role": "assistant",
                "name": "CustomerDataAgent",
                "content": msg_content
            })
            logs.append(AgentMessage(
                sender="CustomerDataAgent",
                receiver="Router",
                content=f"Fetched billing info for customer id={customer_id} as requested by Router."
            ))

    state["messages"] = messages
    state["logs"] = logs
    return state
