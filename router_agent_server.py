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
        if "high_priority_report" in intents or "active_with_open_tickets" in intents:
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
        # first: update email
        if customer_id is not None and state.get("new_email"):
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

        # second: fetch history
        if customer_id is not None:
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

    if scenario == "escalation" or "billing_issue" in intents:
        action = "billing_escalation"
        payload["customer_id"] = customer_id
        payload["issue"] = "Billing problem with possible double charge and/or cancellation request"
        payload["priority"] = "high"

    elif scenario == "task_allocation":
        if customer and customer.get("found"):
            support_response = (
                f"Here is the information we have on file for customer #{customer['id']}:\n"
                f"- Name: {customer['name']}\n"
                f"- Email: {customer['email']}\n"
                f"- Phone: {customer['phone']}\n"
                f"- Status: {customer['status']}"
            )

    elif scenario == "coordinated" and "upgrade_account" in intents:
        if customer and customer.get("found"):
            support_response = (
                f"Hi {customer['name']}, I can help you upgrade your account.\n"
                "Based on your current status, you are eligible for our premium tier.\n"
                "Would you like me to proceed with the upgrade now?"
            )
        else:
            support_response = (
                "I can help you upgrade your account, but I could not find your customer record. "
                "Please provide your customer ID."
            )

    elif scenario == "multi_intent":
        # Router already got history & updated email via Data Agent
        parts: List[str] = []
        if state.get("new_email"):
            parts.append(f"I have updated your email address to: {state['new_email']}.")
        tickets = state.get("tickets", [])
        if tickets is not None:
            # Call Support Agent to format history text
            action = "ticket_history_summary"
            payload["customer_id"] = customer_id
        else:
            parts.append("No ticket history was found for this account.")
        if parts:
            support_response = "\n".join(parts)

    elif scenario == "multi_step":
        customers = state.get("customer_list", [])
        if "high_priority_report" in intents:
            action = "high_priority_report"
            payload["high_priority_report_customers"] = customers
        elif "active_with_open_tickets" in intents:
            action = "active_open_report"
            payload["active_open_report_customers"] = customers

    # If we already have a full support_response, no need to call Support Agent
    if support_response:
        logs.append({
            "sender": "Router",
            "receiver": "SupportAgent",
            "content": f"Generated support response locally for scenario={scenario}."
        })
        state["support_response"] = support_response
        state["done"] = True
        state["logs"] = logs
        return state

    if action is None:
        # Fallback
        support_response = "I am here to help. Could you please provide more details about your issue?"
        state["support_response"] = support_response
        state["done"] = True
        logs.append({
            "sender": "Router",
            "receiver": "SupportAgent",
            "content": f"No specific support action required, returned fallback response."
        })
        state["logs"] = logs
        return state

    # Call Support Agent
    req_body = {"input": {"action": action, **payload}}
    resp = requests.post(f"{SUPPORT_AGENT_URL}/agent/tasks", json=req_body, timeout=20)
    data = resp.json()
    if data.get("status") == "completed":
        result = data.get("result", {})
        support_response = result.get("support_response", "")
    else:
        support_response = f"Support agent error: {data}"

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
        scenario = state.get("scenario", "coordinated")
        if scenario == "escalation":
            return "support_agent"
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
