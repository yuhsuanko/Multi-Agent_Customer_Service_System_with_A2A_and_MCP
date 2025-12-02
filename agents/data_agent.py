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
from langchain_core.output_parsers import JsonOutputParser

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
    
    TRUE AGENT implementation: LLM reasons directly from the query,
    not from predefined scenarios.
    
    Returns:
        Dict with operation details (action, customer_id, filters, etc.)
    """
    llm = get_default_llm()
    
    if llm is None:
        # Fallback: simple rule-based logic
        return {"operations": _determine_operations_rule_based(state)}
    
    intents = state.get("intents", [])
    customer_id = state.get("customer_id")
    query = state.get("user_query", "")
    new_email = state.get("new_email")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a Customer Data Agent. Your job is to determine what database operations are needed based on the user's query.

Available MCP operations:
1. get_customer(customer_id) - Fetch a single customer by ID
2. list_customers(status, limit) - List customers with optional status filter (e.g., "active", "inactive")
3. get_customer_history(customer_id) - Get all tickets for a customer
4. update_customer(customer_id, data) - Update customer fields (email, name, phone, status)

IMPORTANT CONTEXT MAPPINGS:
- "premium customers" = customers with status="active"
- "active customers" = customers with status="active"
- "inactive customers" = customers with status="inactive" or "disabled"
- When query asks for "premium customers" or "active customers", you MUST use list_customers with filters: {{"status": "active"}}

CRITICAL: You MUST return ONLY valid JSON. Do NOT include any explanation, analysis, or text before or after the JSON.

Return a JSON object with:
- operations: array of operation objects, each with:
  - action: one of "get_customer", "list_customers", "get_customer_history", "update_customer"
  - customer_id: if needed (integer or None)
  - filters: dict with filters (e.g., {{"status": "active"}}) if needed
  - update_data: dict with fields to update (e.g., {{"email": "new@email.com"}}) if needed

CRITICAL: If the query asks for "premium customers" or "active customers", you MUST include a list_customers operation with filters: {{"status": "active"}}

Return ONLY the JSON object, nothing else."""),
        ("user", """Query: {query}
Intents: {intents}
Customer ID from context: {customer_id}
New email from context: {new_email}

Return ONLY a JSON object with the operations array. No explanation, no analysis, just JSON.""")
    ])
    
    parser = JsonOutputParser(pydantic_object=None)
    chain = prompt | llm | parser
    
    try:
        result = chain.invoke({
            "query": query,
            "intents": intents,
            "customer_id": customer_id,
            "new_email": new_email,
        })
        
        operations = result.get("operations", [])
        if not operations:
            # Fallback if LLM returns no operations
            return {"operations": _determine_operations_rule_based(state)}
        
        return {"operations": operations}
    except Exception as e:
        # Try to extract JSON from the error message or raw LLM output
        print(f"Warning: LLM reasoning failed, trying to extract JSON: {e}")
        try:
            # Try calling LLM directly and extract JSON from response
            raw_response = llm.invoke(prompt.format_messages(
                query=query,
                intents=intents,
                customer_id=customer_id,
                new_email=new_email,
            ))
            raw_text = raw_response.content if hasattr(raw_response, 'content') else str(raw_response)
            
            # Try to extract JSON from the text
            import json
            import re
            # Look for JSON object in the text
            json_match = re.search(r'\{[^{}]*"operations"[^{}]*\[[^\]]*\][^{}]*\}', raw_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                operations = result.get("operations", [])
                if operations:
                    return {"operations": operations}
        except:
            pass
        
        # Final fallback
        print(f"Warning: JSON extraction failed, using rule-based fallback")
        return {"operations": _determine_operations_rule_based(state)}


def _determine_operations_rule_based(state: CSState) -> list:
    """Rule-based operation determination (fallback when LLM unavailable)."""
    operations = []
    query = state.get("user_query", "").lower()
    intents = state.get("intents", [])
    customer_id = state.get("customer_id")
    new_email = state.get("new_email")
    
    # Simple heuristics (fallback only)
    if customer_id and ("get customer" in query or "customer info" in query or "account" in query):
        operations.append({"action": "get_customer", "customer_id": customer_id})
    
    if "premium" in query or "active customers" in query:
        operations.append({"action": "list_customers", "filters": {"status": "active"}})
    
    if "ticket history" in query or "ticket" in query and customer_id:
        operations.append({"action": "get_customer_history", "customer_id": customer_id})
    
    if "update" in query and "email" in query and customer_id and new_email:
        operations.append({"action": "update_customer", "customer_id": customer_id, "update_data": {"email": new_email}})
    
    if not operations and customer_id:
        # Default: get customer if we have an ID
        operations.append({"action": "get_customer", "customer_id": customer_id})
    
    return operations


def data_agent_node(state: CSState) -> CSState:
    """
    Data agent node with LLM-powered reasoning about data needs.
    
    TRUE AGENT implementation: Uses LLM to reason about what data operations
    are needed from the query, then executes them.
    """
    messages = state.get("messages", [])
    logs = state.get("logs", [])
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
    
    # All operations are now handled by LLM reasoning above
    # No legacy scenario-based logic needed
    
    state["messages"] = messages
    state["logs"] = logs
    return state
