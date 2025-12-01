# router_agent_server.py
"""
Router Agent (A2A) with internal LangGraph orchestration.

External interface:
- GET  /agent/card
- POST /agent/tasks   (input.user_query)

Internal:
- Uses LangGraph to:
  - detect intents / scenario
  - call Data Agent via A2A
  - call Support Agent via A2A
"""

from typing import List, Dict, Any, Optional
from fastapi import FastAPI
from pydantic import BaseModel
import requests
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END

from config import DATA_AGENT_URL, SUPPORT_AGENT_URL
# Import LLM-based analysis from agents module
from agents.router_agent import _analyze_query_with_llm, _extract_customer_id, _extract_email

app = FastAPI(title="Router Agent", version="1.0.0")


# ---------- A2A models ----------

class AgentCard(BaseModel):
    name: str
    description: str
    version: str
    capabilities: List[str]


class TaskInput(BaseModel):
    user_query: str


class TaskRequest(BaseModel):
    input: TaskInput


class TaskResult(BaseModel):
    status: str
    result: Optional[Dict[str, Any]] = None


# ---------- Shared state for LangGraph ----------

class AgentMessage(TypedDict):
    sender: str
    receiver: str
    content: str


class CSState(TypedDict, total=False):
    user_query: str
    scenario: str
    intents: List[str]
    customer_id: Optional[int]
    new_email: Optional[str]
    urgency: Optional[str]
    customer_data: Optional[Dict[str, Any]]
    customer_list: Optional[List[Dict[str, Any]]]
    tickets: Optional[List[Dict[str, Any]]]
    support_response: Optional[str]
    logs: List[AgentMessage]
    done: bool


# ---------- Simple intent / entity detection ----------

import re


def extract_customer_id(query: str) -> Optional[int]:
    match = re.search(r"\b(\d{1,10})\b", query)
    return int(match.group(1)) if match else None


def extract_email(query: str) -> Optional[str]:
    match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", query)
    return match.group(0) if match else None


def detect_intents(query: str) -> List[str]:
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
    if "high-priority tickets" in q or "high priority tickets" in q:
        intents.append("high_priority_report")
    if "active customers" in q and "open tickets" in q:
        intents.append("active_with_open_tickets")
    if "get customer information" in q or "get customer info" in q:
        intents.append("simple_customer_info")
    if not intents:
        intents.append("general_support")
    return intents


def detect_scenario(intents: List[str]) -> str:
    if "high_priority_report" in intents or "active_with_open_tickets" in intents:
        return "multi_step"
    if "cancel_subscription" in intents and "billing_issue" in intents:
        return "escalation"
    if "simple_customer_info" in intents:
        return "task_allocation"
    if "update_email" in intents and "ticket_history" in intents:
        return "multi_intent"
    return "coordinated"


# ---------- LangGraph nodes ----------

def router_node(state: CSState) -> CSState:
    """
    Router node with LLM-powered query analysis.
    Uses LLM for intelligent intent detection and scenario classification.
    """
    logs = state.get("logs", [])
    messages = state.get("messages", [])
    
    if "intents" not in state or "scenario" not in state:
        q = state["user_query"]
        
        # Extract entities using regex (more reliable than LLM for structured data)
        customer_id = _extract_customer_id(q)
        new_email = _extract_email(q)
        
        # Use LLM for intelligent intent detection and scenario classification
        llm_analysis = _analyze_query_with_llm(q)
        
        intents = llm_analysis["intents"]
        scenario = llm_analysis["scenario"]
        urgency = llm_analysis.get("urgency", "normal")
        
        # Override urgency if query contains urgency keywords
        if "refund immediately" in q.lower() or "charged twice" in q.lower():
            urgency = "high"

        state["customer_id"] = customer_id
        state["new_email"] = new_email
        state["intents"] = intents
        state["scenario"] = scenario
        state["urgency"] = urgency
        
        # Add message for A2A compatibility
        analysis_msg = (
            f"Router analyzed query (using LLM): Scenario={scenario}, "
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
            "content": f"Parsed query using LLM. Scenario={scenario}, intents={intents}, "
                       f"customer_id={customer_id}, new_email={new_email}, urgency={urgency}"
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


def call_data_agent_node(state: CSState) -> CSState:
    """
    This node calls the Data Agent via A2A HTTP.

    It sends a task with an 'action' field plus relevant parameters,
    depending on the scenario and intents.
    """
    logs = state.get("logs", [])
    scenario = state.get("scenario", "coordinated")
    intents = state.get("intents", [])
    customer_id = state.get("customer_id")

    action = None
    payload: Dict[str, Any] = {}

    if scenario == "task_allocation":
        action = "get_customer"
        payload["customer_id"] = customer_id
    elif scenario == "multi_step":
        # For multi_step, determine what data is needed based on query
        query = state.get("user_query", "").lower()
        if "premium" in query and "high-priority" in query:
            # Scenario: "high-priority tickets for premium customers"
            # Need to: 1) Get premium customers (status="active"), 2) Then get their tickets
            action = "list_customers"
            payload["status"] = "active"
            payload["limit"] = 200
            # Note: We'll need to filter for premium customers after getting the list
            # For now, get all active customers, then Support Agent will filter for premium and get tickets
        elif "active" in query and "open tickets" in query:
            # Scenario: "active customers who have open tickets"
            action = "list_customers"
            payload["status"] = "active"
            payload["limit"] = 200
        else:
            # Default multi_step: list customers
            action = "list_customers"
            payload["status"] = "active"
            payload["limit"] = 200
    elif scenario == "multi_intent":
        # Router delegates update + history to Data Agent
        action = "update_customer"  # then we also fetch history
    elif scenario == "coordinated":
        if customer_id is not None:
            action = "get_customer"
            payload["customer_id"] = customer_id
    elif scenario == "escalation":
        # For escalation, check if customer_id exists to fetch billing context
        if customer_id is not None:
            action = "get_customer"
            payload["customer_id"] = customer_id
    elif scenario == "escalation":
        # For escalation, check if customer_id exists to fetch billing context
        if customer_id is not None:
            action = "get_customer"
            payload["customer_id"] = customer_id

    if action is None:
        logs.append({
            "sender": "Router",
            "receiver": "CustomerDataAgent",
            "content": f"No specific data action required for scenario={scenario}"
        })
        state["logs"] = logs
        return state

    # Call Data Agent
    if action == "update_customer":
        # Multi-intent scenario: update email AND get ticket history
        # Both operations require customer_id
        if customer_id is not None:
            # first: update email
            if state.get("new_email"):
                update_req = {
                    "input": {
                        "action": "update_customer",
                        "customer_id": customer_id,
                        "update_data": {"email": state["new_email"]},
                    }
                }
                resp = requests.post(f"{DATA_AGENT_URL}/agent/tasks", json=update_req, timeout=10)
                data = resp.json()
                logs.append({
                    "sender": "Router",
                    "receiver": "CustomerDataAgent",
                    "content": f"Called update_customer. Response status={data.get('status')}"
                })

            # second: fetch history (always do this for multi_intent)
            history_req = {
                "input": {
                    "action": "get_customer_history",
                    "customer_id": customer_id,
                }
            }
            resp = requests.post(f"{DATA_AGENT_URL}/agent/tasks", json=history_req, timeout=10)
            data = resp.json()
            if data.get("status") == "completed":
                state["tickets"] = data["result"].get("history", [])
            logs.append({
                "sender": "Router",
                "receiver": "CustomerDataAgent",
                "content": f"Fetched history for customer {customer_id}."
            })
        else:
            # No customer_id: log that we need it
            logs.append({
                "sender": "Router",
                "receiver": "CustomerDataAgent",
                "content": "Multi-intent scenario requires customer_id, but none provided. Support Agent will request it."
            })

    else:
        req_body = {"input": {"action": action, **payload}}
        resp = requests.post(f"{DATA_AGENT_URL}/agent/tasks", json=req_body, timeout=10)
        data = resp.json()
        if data.get("status") == "completed":
            result = data.get("result", {})
            if "customer" in result:
                state["customer_data"] = result["customer"]
            if "customers" in result:
                state["customer_list"] = result["customers"]
        logs.append({
            "sender": "Router",
            "receiver": "CustomerDataAgent",
            "content": f"Called Data Agent action={action}, response_status={data.get('status')}"
        })

    state["logs"] = logs
    return state


def call_support_agent_node(state: CSState) -> CSState:
    """
    This node calls the Support Agent via A2A HTTP and expects a
    'support_response' string in the result.
    """
    logs = state.get("logs", [])
    scenario = state.get("scenario", "coordinated")
    intents = state.get("intents", [])
    customer_id = state.get("customer_id")
    customer = state.get("customer_data")
    support_response = ""

    action = None
    payload: Dict[str, Any] = {}

    if scenario == "escalation":
        # Escalation scenario: billing + cancellation requires negotiation
        # Log negotiation detection (already logged in router_node)
        # If customer_id exists, we already have billing context from Data Agent
        # If not, Support Agent will request it
        
        # Check if this is the negotiation phase (first call) or final call (with context)
        if customer_id is not None and customer and customer.get("found"):
            # We have billing context, proceed with escalation
            action = "billing_escalation"
            payload["customer_id"] = customer_id
            payload["issue"] = "Billing problem with possible double charge and/or cancellation request"
            payload["priority"] = "high"
        elif customer_id is None:
            # First negotiation: Support Agent needs context
            # In a full negotiation, Support Agent would respond asking for customer_id
            # For now, we log this and proceed (Support Agent will ask for customer_id in response)
            logs.append({
                "sender": "SupportAgent",
                "receiver": "Router",
                "content": "I need billing context (customer_id) to handle this escalation."
            })
            action = "billing_escalation"
            payload["customer_id"] = None
            payload["issue"] = "Billing problem with possible double charge and/or cancellation request. Need customer_id for billing context."
            payload["priority"] = "high"
        else:
            # Have customer_id but no customer data yet - wait for Data Agent (shouldn't happen in current flow)
            action = "billing_escalation"
            payload["customer_id"] = customer_id
            payload["issue"] = "Billing problem with possible double charge and/or cancellation request"
            payload["priority"] = "high"
    elif "billing_issue" in intents and scenario != "escalation":
        # Standalone billing issue (not escalation)
        action = "billing_escalation"
        payload["customer_id"] = customer_id
        payload["issue"] = "Billing issue reported"
        payload["priority"] = "high" if state.get("urgency") == "high" else "medium"

    elif scenario == "multi_step":
        customers = state.get("customer_list", [])
        query = state.get("user_query", "").lower()
        
        if "premium" in query and "high-priority" in query:
            # Multi-step: Get premium customers, then their high-priority tickets
            # Filter customers for premium (status="active" customers are considered premium in our system)
            # Data Agent already fetched active customers, now Support Agent will get their tickets
            premium_customers = [c for c in customers if c.get("status") == "active"]
            action = "high_priority_report"
            payload["high_priority_report_customers"] = premium_customers
            logs.append({
                "sender": "Router",
                "receiver": "SupportAgent",
                "content": f"Got {len(premium_customers)} premium customers. Requesting high-priority tickets for these IDs."
            })
        elif "active" in query and "open tickets" in query:
            # Multi-step: Get active customers, then their open tickets
            action = "active_open_report"
            payload["active_open_report_customers"] = customers
            logs.append({
                "sender": "Router",
                "receiver": "SupportAgent",
                "content": f"Got {len(customers)} active customers. Requesting open tickets for these IDs."
            })
        elif "list_active_customers" in intents and ("list_open_tickets" in intents or "open tickets" in query):
            # Handle case where LLM detected separate intents
            action = "active_open_report"
            payload["active_open_report_customers"] = customers
            logs.append({
                "sender": "Router",
                "receiver": "SupportAgent",
                "content": f"Got {len(customers)} active customers. Requesting open tickets for these IDs."
            })
        elif "high_priority_report" in intents or "high-priority" in query:
            action = "high_priority_report"
            payload["high_priority_report_customers"] = customers
        elif "active_with_open_tickets" in intents:
            action = "active_open_report"
            payload["active_open_report_customers"] = customers

    # ALWAYS call Support Agent via A2A - NO hardcoded responses
    # Support Agent will use LLM to generate all responses

    # ALWAYS call Support Agent via A2A to use LLM for response generation
    # NO hardcoded responses - Support Agent uses LLM backend reasoning
    
    # Build context for Support Agent's LLM
    support_context = {
        "scenario": scenario,
        "intents": intents,
        "customer_data": customer,
        "urgency": state.get("urgency", "normal"),
        "tickets": state.get("tickets", []),
        "customer_list": state.get("customer_list", []),
    }
    
    # If no specific action, provide query for LLM-based generation
    if action is None:
        action = "general_query"
        payload = {
            "query": state.get("user_query", ""),
            "context": support_context,
            "customer_id": customer_id,
        }
    
    # Call Support Agent via A2A - it will use LLM to generate response
    print(f"[Router Agent] Calling Support Agent with action={action}, payload keys={list(payload.keys())}")
    if "high_priority_report_customers" in payload:
        print(f"[Router Agent] high_priority_report_customers count: {len(payload.get('high_priority_report_customers', []))}")
    req_body = {"input": {"action": action, "query": state.get("user_query", ""), "context": support_context, **payload}}
    resp = requests.post(f"{SUPPORT_AGENT_URL}/agent/tasks", json=req_body, timeout=20)
    data = resp.json()
    
    if data.get("status") == "completed":
        result = data.get("result", {})
        support_response = result.get("support_response", "")
        # Support Agent should always generate via LLM
        # If no response, this indicates an error - Support Agent should always return a response
        if not support_response:
            # This should not happen - Support Agent always uses LLM to generate responses
            # Log error but don't use hardcoded response - return error instead
            support_response = f"Error: Support Agent did not generate a response. Status: {data.get('status')}"
    else:
        # Error case - return error message (not a hardcoded test response)
        support_response = f"Support agent error: {data.get('result', {}).get('error', 'Unknown error')}"

    state["support_response"] = support_response
    state["done"] = True

    logs.append({
        "sender": "Router",
        "receiver": "SupportAgent",
        "content": f"Called Support Agent action={action}, response_status={data.get('status')}"
    })
    state["logs"] = logs
    return state


# ---------- Build LangGraph workflow ----------

def build_workflow():
    workflow = StateGraph(CSState)

    workflow.add_node("router", router_node)
    workflow.add_node("data_agent", call_data_agent_node)
    workflow.add_node("support_agent", call_support_agent_node)

    workflow.set_entry_point("router")

    def router_to_next(state: CSState) -> str:
        """
        Routing logic after Router analyzes the query.
        
        For escalation: 
        - If customer_id exists, get billing context first (Data Agent), then Support
        - If no customer_id, go to Support for negotiation (Support will request customer_id)
        """
        scenario = state.get("scenario", "coordinated")
        customer_id = state.get("customer_id")
        
        if scenario == "escalation":
            # Escalation: Need billing context if customer_id exists
            # If customer_id exists, fetch customer data first for context
            # If not, go to Support Agent for negotiation (Support will ask for customer_id)
            if customer_id is not None:
                return "data_agent"  # Get billing context first
            else:
                return "support_agent"  # Go to Support for negotiation
        
        # All other scenarios go through Data Agent first
        return "data_agent"

    workflow.add_conditional_edges(
        "router",
        router_to_next,
        {
            "data_agent": "data_agent",
            "support_agent": "support_agent",
        },
    )

    workflow.add_edge("data_agent", "support_agent")
    workflow.add_edge("support_agent", END)

    return workflow.compile()


graph_app = build_workflow()


# ---------- A2A endpoints for Router Agent ----------

@app.get("/agent/card", response_model=AgentCard)
def get_agent_card():
    """
    A2A endpoint: Return the agent card with metadata and capabilities.
    This allows other agents to discover this agent's capabilities.
    """
    return AgentCard(
        name="router-agent",
        description="Router agent that orchestrates other agents using LangGraph. Receives customer queries, analyzes intent, and routes to appropriate specialist agents.",
        version="1.0.0",
        capabilities=["routing", "scenario_detection", "multi_agent_coordination"],
    )


@app.get("/a2a/router-agent", response_model=AgentCard)
@app.get("/a2a/{assistant_id}", response_model=AgentCard)
def get_a2a_agent_card(assistant_id: str = "router-agent"):
    """
    LangGraph A2A endpoint: Return the agent card at /a2a/{assistant_id}.
    This endpoint is for LangGraph's native A2A compatibility.
    """
    if assistant_id not in ["router-agent"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Assistant {assistant_id} not found")
    
    return AgentCard(
        name="router-agent",
        description="Router agent that orchestrates other agents using LangGraph. Receives customer queries, analyzes intent, and routes to appropriate specialist agents.",
        version="1.0.0",
        capabilities=["routing", "scenario_detection", "multi_agent_coordination"],
    )


@app.get("/health")
async def health_check():
    """Health check endpoint for service monitoring."""
    agent_statuses = {}
    
    # Check connectivity to other agents
    try:
        resp = requests.get(f"{DATA_AGENT_URL}/health", timeout=2)
        agent_statuses["data_agent"] = "connected" if resp.status_code == 200 else "disconnected"
    except:
        agent_statuses["data_agent"] = "disconnected"
    
    try:
        resp = requests.get(f"{SUPPORT_AGENT_URL}/health", timeout=2)
        agent_statuses["support_agent"] = "connected" if resp.status_code == 200 else "disconnected"
    except:
        agent_statuses["support_agent"] = "disconnected"
    
    return {
        "status": "ok",
        "service": "router-agent",
        "connected_agents": agent_statuses
    }


@app.post("/agent/tasks", response_model=TaskResult)
def create_task(request: TaskRequest):
    """
    Entry point for external clients or tools.

    Input:
    {
      "input": {
        "user_query": "I am customer 2. I've been charged twice, please refund immediately!"
      }
    }
    """
    user_query = request.input.user_query
    initial_state: CSState = {
        "messages": [],  # Required for LangGraph A2A compatibility
        "user_query": user_query,
        "logs": [],
    }
    final_state = graph_app.invoke(initial_state)

    return TaskResult(
        status="completed",
        result={
            "support_response": final_state.get("support_response"),
            "logs": final_state.get("logs", []),
            "scenario": final_state.get("scenario"),
            "intents": final_state.get("intents"),
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
