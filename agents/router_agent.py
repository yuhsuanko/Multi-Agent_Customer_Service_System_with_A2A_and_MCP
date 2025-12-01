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
from typing import List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from .state import CSState, AgentMessage
from .llm_config import get_default_llm


def _extract_customer_id(query: str) -> int:
    """Extract numeric customer ID from text using regex."""
    match = re.search(r"\b(\d{1,10})\b", query)
    return int(match.group(1)) if match else None


def _extract_email(query: str) -> str:
    """Extract email address from text using regex."""
    match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", query)
    return match.group(0) if match else None


def _analyze_query_with_llm(query: str) -> Dict[str, Any]:
    """
    Use LLM to analyze the query and detect intents, scenario, and entities.
    
    Returns:
        Dict with keys: intents (list), scenario (str), urgency (str)
    """
    llm = get_default_llm()
    
    # If no LLM is available, use fallback
    if llm is None:
        return _fallback_analysis(query)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a Router Agent in a multi-agent customer service system.
Your job is to analyze customer queries and determine:
1. The scenario type (task_allocation, escalation, multi_step, multi_intent, or coordinated)
2. The intents present in the query
3. The urgency level (normal or high)

Scenarios:
- task_allocation: Simple queries requesting customer info or account help with a specific customer ID
- escalation: Multiple intents like cancellation + billing issues, or urgent billing/refund requests
- multi_step: Complex queries requiring multiple data fetches (e.g., "show me all X with Y")
- multi_intent: Queries with multiple parallel tasks (e.g., "update email AND show history")
- coordinated: General support queries requiring data fetch + support response

Return a JSON object with:
- intents: array of detected intents (e.g., ["account_help"], ["cancel_subscription", "billing_issue"])
- scenario: one of the scenario types above
- urgency: "normal" or "high" (high for billing issues, refunds, "immediately", etc.)

Be intelligent about detecting the scenario based on query complexity and intent combinations."""),
        ("user", "Analyze this customer query: {query}")
    ])
    
    parser = JsonOutputParser(pydantic_object=None)
    chain = prompt | llm | parser
    
    try:
        result = chain.invoke({"query": query})
        
        # Ensure required fields exist
        if not isinstance(result, dict):
            result = {"intents": [], "scenario": "coordinated", "urgency": "normal"}
        
        return {
            "intents": result.get("intents", []),
            "scenario": result.get("scenario", "coordinated"),
            "urgency": result.get("urgency", "normal"),
        }
    except Exception as e:
        # Fallback to simple heuristics if LLM fails
        print(f"Warning: LLM analysis failed, using fallback: {e}")
        return _fallback_analysis(query)


def _fallback_analysis(query: str) -> Dict[str, Any]:
    """Fallback rule-based analysis if LLM fails."""
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
    
    # Scenario detection
    if "high_priority_report" in intents or "active_with_open_tickets" in intents:
        scenario = "multi_step"
    elif "cancel_subscription" in intents and "billing_issue" in intents:
        scenario = "escalation"
    elif "simple_customer_info" in intents or "account_help" in intents:
        scenario = "task_allocation"
    elif "update_email" in intents and "ticket_history" in intents:
        scenario = "multi_intent"
    else:
        scenario = "coordinated"
    
    urgency = "high" if ("billing_issue" in intents or "refund immediately" in q) else "normal"
    
    return {
        "intents": intents,
        "scenario": scenario,
        "urgency": urgency,
    }


def router_node(state: CSState) -> CSState:
    """
    Router node with LLM-powered query analysis.
    
    On the first call:
    - Use LLM to analyze the query and detect intents/scenario
    - Extract entities (customer_id, email)
    - Log routing decisions
    - Add messages for A2A compatibility
    """
    messages = state.get("messages", [])
    logs = state.get("logs", [])
    
    if "intents" not in state or "scenario" not in state:
        query = state["user_query"]
        
        # Extract entities using regex (more reliable than LLM for structured data)
        customer_id = _extract_customer_id(query)
        new_email = _extract_email(query)
        
        # Use LLM for intelligent intent detection and scenario classification
        llm_analysis = _analyze_query_with_llm(query)
        
        intents = llm_analysis["intents"]
        scenario = llm_analysis["scenario"]
        urgency = llm_analysis.get("urgency", "normal")
        
        # Override urgency if query contains urgency keywords
        if "refund immediately" in query.lower() or "charged twice" in query.lower():
            urgency = "high"
        
        state["customer_id"] = customer_id
        state["new_email"] = new_email
        state["intents"] = intents
        state["scenario"] = scenario
        state["urgency"] = urgency
        
        # Add message for A2A compatibility
        analysis_msg = (
            f"Router analyzed query: Scenario={scenario}, "
            f"intents={intents}, customer_id={customer_id}, urgency={urgency}"
        )
        messages.append({
            "role": "assistant",
            "name": "Router",
            "content": analysis_msg
        })
        
        logs.append({
            "sender": "Router",
            "receiver": "Router",
            "content": (
                f"Parsed query. Scenario={scenario}, intents={intents}, "
                f"customer_id={customer_id}, new_email={new_email}, urgency={urgency}"
            )
        })
        
        # For Scenario 2 (escalation): Log negotiation detection
        if scenario == "escalation":
            logs.append({
                "sender": "Router",
                "receiver": "SupportAgent",
                "content": "Router detected multiple intents (cancellation + billing). Can you handle this?"
            })
    
    state["messages"] = messages
    state["logs"] = logs
    return state
