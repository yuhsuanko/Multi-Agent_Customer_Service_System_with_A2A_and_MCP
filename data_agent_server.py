# data_agent_server.py
"""
Customer Data Agent (A2A).

Responsibilities:
- Provide an A2A interface for data-related tasks.
- Internally calls the MCP DB server via HTTP to:
  - get_customer
  - list_customers
  - get_customer_history
  - update_customer
"""

from typing import Dict, Any, Optional, List
from fastapi import FastAPI
from pydantic import BaseModel
import requests
from config import MCP_SERVER_URL

app = FastAPI(title="Customer Data Agent", version="1.0.0")


# ---------- A2A models ----------

class AgentCard(BaseModel):
    name: str
    description: str
    version: str
    capabilities: List[str]


class TaskInput(BaseModel):
    action: str
    customer_id: Optional[int] = None
    status: Optional[str] = None
    limit: Optional[int] = 50
    update_data: Optional[Dict[str, Any]] = None


class TaskRequest(BaseModel):
    input: TaskInput


class TaskResult(BaseModel):
    status: str
    result: Optional[Dict[str, Any]] = None


# ---------- Helper: call MCP server ----------

def call_mcp(tool: str, arguments: Dict[str, Any]) -> Any:
    """Call the MCP DB server using /tools/call."""
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


# ---------- A2A endpoints ----------

@app.get("/agent/card", response_model=AgentCard)
def get_agent_card():
    """
    A2A endpoint: Return the agent card with metadata and capabilities.
    This allows other agents to discover this agent's capabilities.
    """
    return AgentCard(
        name="customer-data-agent",
        description="Specialized agent for customer and ticket data via MCP. Handles data retrieval, updates, and validation.",
        version="1.0.0",
        capabilities=["get_customer", "list_customers", "get_history", "update_customer"],
    )


@app.get("/a2a/customer-data-agent", response_model=AgentCard)
@app.get("/a2a/{assistant_id}", response_model=AgentCard)
def get_a2a_agent_card(assistant_id: str = "customer-data-agent"):
    """
    LangGraph A2A endpoint: Return the agent card at /a2a/{assistant_id}.
    This endpoint is for LangGraph's native A2A compatibility.
    """
    if assistant_id not in ["customer-data-agent"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Assistant {assistant_id} not found")
    
    return AgentCard(
        name="customer-data-agent",
        description="Specialized agent for customer and ticket data via MCP. Handles data retrieval, updates, and validation.",
        version="1.0.0",
        capabilities=["get_customer", "list_customers", "get_history", "update_customer"],
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
        "service": "customer-data-agent",
        "mcp_server": mcp_status
    }


@app.post("/agent/tasks", response_model=TaskResult)
def create_task(request: TaskRequest):
    """
    Handle a data-related task.

    Supported actions:
    - get_customer
    - list_customers
    - get_customer_history
    - update_customer
    """
    inp = request.input
    action = inp.action

    result: Dict[str, Any] = {}

    if action == "get_customer":
        if inp.customer_id is None:
            return TaskResult(status="error", result={"error": "customer_id is required"})
        result["customer"] = call_mcp("get_customer", {"customer_id": inp.customer_id})

    elif action == "list_customers":
        result["customers"] = call_mcp(
            "list_customers",
            {"status": inp.status, "limit": inp.limit or 50},
        )

    elif action == "get_customer_history":
        if inp.customer_id is None:
            return TaskResult(status="error", result={"error": "customer_id is required"})
        result["history"] = call_mcp(
            "get_customer_history",
            {"customer_id": inp.customer_id},
        )

    elif action == "update_customer":
        if inp.customer_id is None or not inp.update_data:
            return TaskResult(status="error", result={"error": "customer_id and update_data are required"})
        update_result = call_mcp(
            "update_customer",
            {"customer_id": inp.customer_id, "data": inp.update_data},
        )
        result["update_result"] = update_result

    else:
        return TaskResult(status="error", result={"error": f"Unsupported action: {action}"})

    return TaskResult(status="completed", result=result)


if __name__ == "__main__":
    import uvicorn
    from config import DATA_AGENT_URL

    uvicorn.run(app, host="0.0.0.0", port=8002)
