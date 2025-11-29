# support_agent_server.py
"""
Support Agent (A2A).

Responsibilities:
- Provide an A2A interface for support-related tasks.
- Create tickets via MCP (escalation).
- Summarize ticket history for reporting.
"""

from typing import Dict, Any, List, Optional
from fastapi import FastAPI
from pydantic import BaseModel
import requests
from config import MCP_SERVER_URL

app = FastAPI(title="Support Agent", version="1.0.0")


class AgentCard(BaseModel):
    name: str
    description: str
    version: str
    capabilities: List[str]


class TaskInput(BaseModel):
    action: str
    customer_id: Optional[int] = None
    issue: Optional[str] = None
    priority: Optional[str] = "medium"
    high_priority_report_customers: Optional[List[Dict[str, Any]]] = None
    active_open_report_customers: Optional[List[Dict[str, Any]]] = None


class TaskRequest(BaseModel):
    input: TaskInput


class TaskResult(BaseModel):
    status: str
    result: Optional[Dict[str, Any]] = None


def call_mcp(tool: str, arguments: Dict[str, Any]) -> Any:
    resp = requests.post(
        f"{MCP_SERVER_URL}/tools/call",
        json={"tool": tool, "arguments": arguments},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"MCP error: {data.get('error')}")
    return data.get("result")


def summarize_history(tickets: List[Dict[str, Any]]) -> str:
    if not tickets:
        return "You currently have no tickets on file."
    lines = []
    for t in tickets:
        lines.append(
            f"- Ticket {t['ticket_id']}: {t['issue']} "
            f"({t['status']}, priority={t['priority']})"
        )
    return "\n".join(lines)


@app.get("/agent/card", response_model=AgentCard)
def get_agent_card():
    """
    A2A endpoint: Return the agent card with metadata and capabilities.
    This allows other agents to discover this agent's capabilities.
    """
    return AgentCard(
        name="support-agent",
        description="Specialized agent for customer support flows and ticket escalation. Handles support queries, escalations, and generates user-facing responses.",
        version="1.0.0",
        capabilities=["billing_escalation", "ticket_history_summary", "multi_customer_report"],
    )


@app.get("/a2a/support-agent", response_model=AgentCard)
@app.get("/a2a/{assistant_id}", response_model=AgentCard)
def get_a2a_agent_card(assistant_id: str = "support-agent"):
    """
    LangGraph A2A endpoint: Return the agent card at /a2a/{assistant_id}.
    This endpoint is for LangGraph's native A2A compatibility.
    """
    if assistant_id not in ["support-agent"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Assistant {assistant_id} not found")
    
    return AgentCard(
        name="support-agent",
        description="Specialized agent for customer support flows and ticket escalation. Handles support queries, escalations, and generates user-facing responses.",
        version="1.0.0",
        capabilities=["billing_escalation", "ticket_history_summary", "multi_customer_report"],
    )


@app.get("/health")
async def health_check():
    """Health check endpoint for service monitoring."""
    try:
        # Quick connectivity check to MCP server
        resp = requests.get(f"{MCP_SERVER_URL}/health", timeout=2)
        mcp_status = "connected" if resp.status_code == 200 else "disconnected"
    except:
        mcp_status = "disconnected"
    
    return {
        "status": "ok",
        "service": "support-agent",
        "mcp_server": mcp_status
    }


@app.post("/agent/tasks", response_model=TaskResult)
def create_task(request: TaskRequest):
    inp = request.input
    action = inp.action
    result: Dict[str, Any] = {}

    # 1) Billing / escalation: create high-priority ticket
    if action == "billing_escalation":
        if inp.customer_id is None or not inp.issue:
            return TaskResult(status="error", result={"error": "customer_id and issue are required"})
        ticket = call_mcp(
            "create_ticket",
            {"customer_id": inp.customer_id, "issue": inp.issue, "priority": inp.priority or "high"},
        )
        response_text = (
            "I see that you are having billing issues. "
            "I have created a high-priority ticket so our billing team can review your charges "
            "and process any necessary refund.\n"
            f"Your ticket ID is {ticket.get('ticket_id')}."
        )
        result["support_response"] = response_text
        result["ticket"] = ticket

    # 2) Single-customer history summary
    elif action == "ticket_history_summary":
        if inp.customer_id is None:
            return TaskResult(status="error", result={"error": "customer_id is required"})
        history = call_mcp(
            "get_customer_history",
            {"customer_id": inp.customer_id},
        )
        result["support_response"] = "Here is your recent ticket history:\n" + summarize_history(history)
        result["history"] = history

    # 3) Multi-customer high-priority report
    elif action == "high_priority_report":
        customers = inp.high_priority_report_customers or []
        entries: List[str] = []
        for c in customers:
            cid = c["id"]
            history = call_mcp("get_customer_history", {"customer_id": cid})
            high_tickets = [t for t in history if t["priority"] == "high"]
            if high_tickets:
                entry = f"Customer {cid} ({c['name']}):"
                for ht in high_tickets:
                    entry += f"\n  - Ticket {ht['ticket_id']} ({ht['status']}): {ht['issue']}"
                entries.append(entry)
        if entries:
            text = "Here is the status of high-priority tickets for active customers:\n\n" + "\n\n".join(entries)
        else:
            text = "There are currently no high-priority tickets for active customers."
        result["support_response"] = text

    # 4) Multi-customer active-with-open-tickets report
    elif action == "active_open_report":
        customers = inp.active_open_report_customers or []
        entries: List[str] = []
        for c in customers:
            cid = c["id"]
            history = call_mcp("get_customer_history", {"customer_id": cid})
            open_tickets = [t for t in history if t["status"] == "open"]
            if open_tickets:
                entry = f"Customer {cid} ({c['name']}):"
                for ot in open_tickets:
                    entry += f"\n  - Ticket {ot['ticket_id']} (priority={ot['priority']}): {ot['issue']}"
                entries.append(entry)
        if entries:
            text = "Here are all active customers who currently have open tickets:\n\n" + "\n\n".join(entries)
        else:
            text = "There are no active customers with open tickets at the moment."
        result["support_response"] = text

    else:
        return TaskResult(status="error", result={"error": f"Unsupported action: {action}"})

    return TaskResult(status="completed", result=result)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
