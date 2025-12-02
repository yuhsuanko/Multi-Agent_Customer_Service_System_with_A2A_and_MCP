# agents/router_agent.py
"""
Router Agent with LLM-powered reasoning.

Responsibilities:
- Analyze the user query using LLM
- Detect scenario type and intents with LLM reasoning
- Extract key entities (customer_id, email, urgency)
- Log routing decisions

The agent uses LLM for intelligent intent detection and scenario classification
rather than simple keyword matching.
"""

import re
import json
from typing import List, Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from .state import CSState, AgentMessage
from .llm_config import get_default_llm


def _extract_customer_id(query: str) -> Optional[int]:
    """Extract numeric customer ID from text using regex.
    
    Looks for patterns like:
    - "customer ID 12345"
    - "customer 12345"
    - "I'm customer 12345"
    - "ID 12345"
    - Any standalone number if context suggests it's a customer ID
    """
    query_lower = query.lower()
    
    # Try explicit patterns first
    patterns = [
        r"customer\s+id\s+(\d{1,10})",
        r"customer\s+(\d{1,10})",
        r"i'?m\s+customer\s+(\d{1,10})",
        r"id\s+(\d{1,10})",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, query_lower)
        if match:
            return int(match.group(1))
    
    # Fallback: look for standalone numbers (but be more careful)
    # Only extract if query mentions "customer" or "ID" somewhere
    if "customer" in query_lower or " id " in query_lower:
        match = re.search(r"\b(\d{1,10})\b", query)
        if match:
            return int(match.group(1))
    
    return None


def _extract_email(query: str) -> str:
    """Extract email address from text using regex."""
    match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", query)
    return match.group(0) if match else None


def _analyze_query_with_llm(query: str) -> Dict[str, Any]:
    """
    Use LLM to analyze the query and extract key information.
    
    This is a TRUE AGENT implementation - LLM reasons about the query
    without forcing it into predefined scenario categories.
    
    Returns:
        Dict with keys: intents (list), urgency (str), reasoning (str)
    """
    llm = get_default_llm()
    
    # If no LLM is available, use fallback
    if llm is None:
        return _fallback_analysis(query)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a Router Agent in a multi-agent customer service system.
Your job is to analyze customer queries and extract key information for routing decisions.

You should NOT classify queries into predefined scenarios.
Instead, reason about:
1. What the customer is asking for
2. What information or actions are needed
3. The urgency level

CRITICAL: You MUST return ONLY valid JSON. Do NOT include any explanation, analysis, or text before or after the JSON.

Return a JSON object with:
- intents: array of what the customer wants (e.g., ["get_customer_info"], ["cancel_subscription", "refund"])
- urgency: "normal" or "high" (high if words like "immediately", "urgent", "charged twice", "refund now")
- reasoning: Brief explanation of what the query needs

Return ONLY the JSON object, nothing else."""),
        ("user", "Analyze this customer query and return ONLY JSON: {query}")
    ])
    
    parser = JsonOutputParser(pydantic_object=None)
    chain = prompt | llm | parser
    
    try:
        result = chain.invoke({"query": query})
        
        # Ensure required fields exist
        if not isinstance(result, dict):
            result = {"intents": [], "urgency": "normal", "reasoning": ""}
        
        return {
            "intents": result.get("intents", []),
            "urgency": result.get("urgency", "normal"),
            "reasoning": result.get("reasoning", ""),
        }
    except Exception as e:
        # Try to extract JSON from raw LLM output
        print(f"Warning: LLM analysis failed, trying to extract JSON: {e}")
        try:
            raw_response = llm.invoke(prompt.format_messages(query=query))
            raw_text = raw_response.content if hasattr(raw_response, 'content') else str(raw_response)
            
            import json
            import re
            # Look for JSON object in the text
            json_match = re.search(r'\{[^{}]*"intents"[^{}]*\[[^\]]*\][^{}]*\}', raw_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                return {
                    "intents": result.get("intents", []),
                    "urgency": result.get("urgency", "normal"),
                    "reasoning": result.get("reasoning", ""),
                }
        except:
            pass
        
        # Fallback to simple heuristics if LLM fails
        print(f"Warning: JSON extraction failed, using rule-based fallback")
        return _fallback_analysis(query)


def _decide_routing_with_llm(query: str, current_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Use LLM to decide which agent to call next based on reasoning.
    
    This is TRUE AGENT behavior - LLM reasons about what's needed
    and decides routing dynamically, without hardcoded scenarios.
    
    Args:
        query: The user's query
        current_state: Current state including customer_id, customer_data, customer_list, tickets
    
    Returns:
        Dict with: next_agent (str), reason (str), needed_data (list)
    """
    llm = get_default_llm()
    
    if llm is None:
        # Fallback: simple heuristics
        if current_state.get("customer_id") and not current_state.get("customer_data"):
            return {"next_agent": "data_agent", "reason": "Need customer data", "needed_data": ["customer_data"]}
        return {"next_agent": "data_agent", "reason": "Default routing", "needed_data": []}
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a Router Agent deciding which agent to call next.

Available agents:
- data_agent: Fetches customer data, lists customers, updates records, gets ticket history via MCP tools
- support_agent: Generates responses, creates tickets, handles support queries

Your job: Analyze the query and current state, then decide which agent to call next.

CRITICAL: You MUST return ONLY valid JSON. Do NOT include any explanation, analysis, or text before or after the JSON.

Return JSON with these fields:
- next_agent: either "data_agent" or "support_agent"
- reason: clear explanation of why this agent should be called next
- needed_data: list of data we still need before we can answer
- has_sufficient_data: true or false

Be smart about dependencies - if we need customer data before generating a response, call data_agent first.

Return ONLY the JSON object, nothing else."""),
        ("user", """Query: {query}
Current state:
- customer_id: {customer_id}
- has_customer_data: {has_customer_data}
- has_customer_list: {has_customer_list}
- has_tickets: {has_tickets}
- intents: {intents}

Return ONLY JSON with next_agent, reason, needed_data, and has_sufficient_data. No explanation.""")
    ])
    
    parser = JsonOutputParser(pydantic_object=None)
    chain = prompt | llm | parser
    
    try:
        has_customer_data = bool(current_state.get("customer_data") and current_state["customer_data"].get("found"))
        has_customer_list = bool(current_state.get("customer_list") and len(current_state["customer_list"]) > 0)
        has_tickets = bool(current_state.get("tickets") and len(current_state["tickets"]) > 0)
        
        decision = chain.invoke({
            "query": query,
            "customer_id": current_state.get("customer_id"),
            "has_customer_data": has_customer_data,
            "has_customer_list": has_customer_list,
            "has_tickets": has_tickets,
            "intents": current_state.get("intents", []),
        })
        
        return {
            "next_agent": decision.get("next_agent", "data_agent"),
            "reason": decision.get("reason", ""),
            "needed_data": decision.get("needed_data", []),
            "has_sufficient_data": decision.get("has_sufficient_data", False),
        }
    except Exception as e:
        print(f"Warning: LLM routing decision failed, trying to extract JSON: {e}")
        try:
            has_customer_data = bool(current_state.get("customer_data") and current_state["customer_data"].get("found"))
            has_customer_list = bool(current_state.get("customer_list") and len(current_state["customer_list"]) > 0)
            has_tickets = bool(current_state.get("tickets") and len(current_state["tickets"]) > 0)
            
            raw_response = llm.invoke(prompt.format_messages(
                query=query,
                customer_id=current_state.get("customer_id"),
                has_customer_data=has_customer_data,
                has_customer_list=has_customer_list,
                has_tickets=has_tickets,
                intents=current_state.get("intents", []),
            ))
            raw_text = raw_response.content if hasattr(raw_response, 'content') else str(raw_response)
            
            import json
            import re
            # Look for JSON object in the text
            json_match = re.search(r'\{[^{}]*"next_agent"[^{}]*\}', raw_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                decision = json.loads(json_str)
                return {
                    "next_agent": decision.get("next_agent", "data_agent"),
                    "reason": decision.get("reason", ""),
                    "needed_data": decision.get("needed_data", []),
                    "has_sufficient_data": decision.get("has_sufficient_data", False),
                }
        except:
            pass
        
        # Fallback routing
        print(f"Warning: JSON extraction failed, using rule-based fallback")
        if current_state.get("customer_id") and not current_state.get("customer_data"):
            return {"next_agent": "data_agent", "reason": "Need customer data", "needed_data": ["customer_data"]}
        return {"next_agent": "data_agent", "reason": "Default routing", "needed_data": []}


def _fallback_analysis(query: str) -> Dict[str, Any]:
    """Fallback rule-based analysis if LLM fails.
    
    Note: This is still rule-based, but we don't classify into scenarios anymore.
    We just extract intents and urgency.
    """
    q = query.lower()
    intents = []
    
    if "upgrade" in q:
        intents.append("upgrade_account")
    if "cancel" in q:
        intents.append("cancel_subscription")
    if "billing" in q or "charged twice" in q or "refund" in q:
        intents.append("billing_issue")
    if "update my email" in q or "change my email" in q or "new email" in q:
        intents.append("update_email")
    if "ticket history" in q:
        intents.append("ticket_history")
    if "high-priority tickets" in q or ("premium customers" in q and "high" in q):
        intents.append("high_priority_report")
    if "active customers" in q and "open tickets" in q:
        intents.append("active_with_open_tickets")
    if "premium customers" in q:
        intents.append("premium_customers")
    if "get customer information" in q or "get customer info" in q:
        intents.append("simple_customer_info")
    if "need help with my account" in q or "help with my account" in q:
        intents.append("account_help")
    
    if not intents:
        intents.append("general_support")
    
    urgency = "high" if ("billing_issue" in intents or "refund immediately" in q or "charged twice" in q) else "normal"
    
    return {
        "intents": intents,
        "urgency": urgency,
        "reasoning": "Fallback rule-based analysis",
    }


def router_node(state: CSState) -> CSState:
    """
    Router node with LLM-powered query analysis.
    
    TRUE AGENT implementation: Uses LLM to reason about the query,
    not classify it into predefined scenarios.
    
    On the first call:
    - Use LLM to analyze the query and extract intents
    - Extract entities (customer_id, email)
    - Log routing decisions
    - Add messages for A2A compatibility
    """
    messages = state.get("messages", [])
    logs = state.get("logs", [])
    
    if "intents" not in state:
        query = state["user_query"]
        
        # Extract entities using regex (more reliable than LLM for structured data)
        customer_id = _extract_customer_id(query)
        new_email = _extract_email(query)
        
        # Use LLM for intelligent intent detection (no scenario classification)
        llm_analysis = _analyze_query_with_llm(query)
        
        intents = llm_analysis["intents"]
        urgency = llm_analysis.get("urgency", "normal")
        reasoning = llm_analysis.get("reasoning", "")
        
        # Override urgency if query contains urgency keywords
        if "refund immediately" in query.lower() or "charged twice" in query.lower():
            urgency = "high"
        
        state["customer_id"] = customer_id
        state["new_email"] = new_email
        state["intents"] = intents
        state["urgency"] = urgency
        
        # Add message for A2A compatibility
        analysis_msg = (
            f"Router analyzed query: intents={intents}, "
            f"customer_id={customer_id}, urgency={urgency}"
        )
        if reasoning:
            analysis_msg += f", reasoning={reasoning}"
        
        messages.append({
            "role": "assistant",
            "name": "Router",
            "content": analysis_msg
        })
        
        logs.append({
            "sender": "Router",
            "receiver": "Router",
            "content": (
                f"Parsed query. intents={intents}, "
                f"customer_id={customer_id}, new_email={new_email}, urgency={urgency}"
            )
        })
        
        # For escalation scenarios (cancellation + billing): Add initial negotiation detection
        has_cancellation = any("cancel" in str(intent).lower() for intent in intents)
        has_billing = any("billing" in str(intent).lower() or "refund" in str(intent).lower() for intent in intents)
        if has_cancellation and has_billing:
            # Scenario 2: Negotiation/Escalation - Router detects multiple intents
            logs.append({
                "sender": "Router",
                "receiver": "SupportAgent",
                "content": "Router detected multiple intents (cancellation + billing). Can you handle this?"
            })
    
    state["messages"] = messages
    state["logs"] = logs
    return state
