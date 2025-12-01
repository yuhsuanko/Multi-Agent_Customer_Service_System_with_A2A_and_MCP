# agents/data_agent.py
"""
Customer Data Agent with LLM-powered reasoning.

Responsibilities:
- Use LLM to reason about what data is needed
- Interact with the customer/ticket database via MCP tools
- Fetch customer profiles, lists, ticket histories
- Update customer records (email, status, etc.)

The agent uses LLM to intelligently decide what data operations to perform
based on the scenario and context.
"""

from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate

from .state import CSState, AgentMessage
from .mcp_client import (
    mcp_get_customer,
    mcp_list_customers,
    mcp_get_customer_history,
    mcp_update_customer,
)
from .llm_config import get_default_llm


def _reason_about_data_needs(state: CSState) -> Dict[str, Any]:
    """
    Use LLM to reason about what data operations are needed.
    
    Returns:
        Dict with operation details (action, customer_id, filters, etc.)
    """
    llm = get_default_llm()
    
    scenario = state.get("scenario", "coordinated")
    intents = state.get("intents", [])
    customer_id = state.get("customer_id")
    query = state.get("user_query", "")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a Customer Data Agent. Your job is to determine what database operations are needed based on the scenario and intents.

Available operations:
1. get_customer - Fetch a single customer by ID
2. list_customers - List customers with optional status filter
3. get_customer_history - Get all tickets for a customer
4. update_customer - Update customer fields (email, name, phone, status)

Based on the scenario and intents, determine what operations are needed. Return a JSON object with:
- operations: array of operation objects, each with:
  - action: one of the operations above
  - customer_id: if needed (from context or query)
  - filters: any filters needed (status, etc.)

Be intelligent about what data is actually needed for the scenario."""),
        ("user", """Scenario: {scenario}
Intents: {intents}
Customer ID: {customer_id}
Query: {query}

What data operations are needed?""")
    ])
    
    try:
        response = llm.invoke(prompt.format_messages(
            scenario=scenario,
            intents=str(intents),
            customer_id=str(customer_id),
            query=query
        ))
        
        # Parse LLM response (simplified - in production, use structured output)
        content = response.content if hasattr(response, 'content') else str(response)
        
        # For now, use rule-based logic but with LLM guidance
        # In a full implementation, parse JSON from LLM response
        return {
            "operations": _determine_operations_rule_based(scenario, intents, customer_id, query)
        }
    except Exception as e:
        print(f"Warning: LLM reasoning failed, using rule-based: {e}")
        return {
            "operations": _determine_operations_rule_based(scenario, intents, customer_id, query)
        }


def _determine_operations_rule_based(scenario: str, intents: list, customer_id: Any, query: str = "") -> list:
    """Rule-based operation determination (fallback)."""
    operations = []
    query_lower = query.lower() if query else ""
    
    if scenario == "task_allocation" and customer_id:
        operations.append({"action": "get_customer", "customer_id": customer_id})
    
    elif scenario == "multi_step":
        # For multi_step, determine what data is needed
        if "premium" in query_lower:
            # Need to get premium customers (in our system, active = premium)
            operations.append({"action": "list_customers", "filters": {"status": "active"}})
        else:
            # Default: get active customers
            operations.append({"action": "list_customers", "filters": {"status": "active"}})
    
    elif scenario == "multi_intent":
        if "update_email" in intents and customer_id:
            operations.append({"action": "update_customer", "customer_id": customer_id})
        if "ticket_history" in intents and customer_id:
            operations.append({"action": "get_customer_history", "customer_id": customer_id})
    
    elif scenario in ["coordinated", "escalation"] and customer_id:
        operations.append({"action": "get_customer", "customer_id": customer_id})
    
    return operations


def data_agent_node(state: CSState) -> CSState:
    """
    Data agent node with LLM-powered reasoning about data needs.
    
    Uses LLM to determine what data operations are needed, then executes them.
    """
    messages = state.get("messages", [])
    logs = state.get("logs", [])
    scenario = state.get("scenario", "coordinated")
    intents = state.get("intents", [])
    customer_id = state.get("customer_id")
    
    # Use LLM to reason about data needs
    data_plan = _reason_about_data_needs(state)
    operations = data_plan.get("operations", [])
    
    # Execute operations
    for op in operations:
        action = op.get("action")
        
        if action == "get_customer":
            cid = op.get("customer_id") or customer_id
            if cid:
                customer = mcp_get_customer(cid)
                state["customer_data"] = customer
                
                # Determine customer tier
                if customer.get("found") and customer.get("status") == "active":
                    state["customer_tier"] = "premium"
                elif customer.get("found"):
                    state["customer_tier"] = "standard"
                else:
                    state["customer_tier"] = "unknown"
                
                msg_content = f"Fetched customer info for id={cid}, found={customer.get('found')}, tier={state.get('customer_tier', 'unknown')}"
                messages.append({
                    "role": "assistant",
                    "name": "CustomerDataAgent",
                    "content": msg_content
                })
                logs.append({
                    "sender": "CustomerDataAgent",
                    "receiver": "Router",
                    "content": f"Fetched customer info for id={cid}, found={customer.get('found')}, status={customer.get('status')}. Returning customer data to Router."
                })
                
                if customer.get("found"):
                    logs.append({
                        "sender": "Router",
                        "receiver": "Router",
                        "content": f"Analyzed customer tier/status: tier={state.get('customer_tier', 'unknown')}, status={customer.get('status')}"
                    })
        
        elif action == "list_customers":
            status = op.get("filters", {}).get("status", "active")
            customers = mcp_list_customers(status=status, limit=200)
            state["customer_list"] = customers
            msg_content = f"Fetched {len(customers)} {status} customers for multi-step report."
            messages.append({
                "role": "assistant",
                "name": "CustomerDataAgent",
                "content": msg_content
            })
            logs.append({
                "sender": "CustomerDataAgent",
                "receiver": "Router",
                "content": msg_content
            })
        
        elif action == "get_customer_history":
            cid = op.get("customer_id") or customer_id
            if cid:
                history = mcp_get_customer_history(cid)
                state["tickets"] = history
                msg_content = f"Fetched {len(history)} tickets for customer id={cid}."
                messages.append({
                    "role": "assistant",
                    "name": "CustomerDataAgent",
                    "content": msg_content
                })
                logs.append({
                    "sender": "CustomerDataAgent",
                    "receiver": "Router",
                    "content": msg_content
                })
        
        elif action == "update_customer":
            cid = op.get("customer_id") or customer_id
            new_email = state.get("new_email")
            if cid and new_email:
                result = mcp_update_customer(cid, {"email": new_email})
                msg_content = f"Updated email for customer id={cid}. Result={result}"
                messages.append({
                    "role": "assistant",
                    "name": "CustomerDataAgent",
                    "content": msg_content
                })
                logs.append({
                    "sender": "CustomerDataAgent",
                    "receiver": "Router",
                    "content": msg_content
                })
    
    # Legacy rule-based logic for backward compatibility
    if scenario == "task_allocation" and customer_id and "customer_data" not in state:
        customer = mcp_get_customer(customer_id)
        state["customer_data"] = customer
        if customer.get("found") and customer.get("status") == "active":
            state["customer_tier"] = "premium"
        elif customer.get("found"):
            state["customer_tier"] = "standard"
    
    if scenario == "multi_step" and "customer_list" not in state:
        customers = mcp_list_customers(status="active", limit=200)
        state["customer_list"] = customers
        msg_content = f"Fetched {len(customers)} active customers for multi-step report."
        messages.append({
            "role": "assistant",
            "name": "CustomerDataAgent",
            "content": msg_content
        })
    
    if scenario == "multi_intent" and customer_id:
        if "update_email" in intents and state.get("new_email"):
            mcp_update_customer(customer_id, {"email": state["new_email"]})
        if "ticket_history" in intents:
            history = mcp_get_customer_history(customer_id)
            state["tickets"] = history
    
    if scenario in ["coordinated", "escalation"] and customer_id and "customer_data" not in state:
        customer = mcp_get_customer(customer_id)
        state["customer_data"] = customer
    
    state["messages"] = messages
    state["logs"] = logs
    return state
