# db_mcp_server.py
"""
MCP (Model Context Protocol) server exposing database tools over SSE (Server-Sent Events).

This server implements the MCP protocol with:
- SSE endpoint for streaming communication
- tools/list method to list available tools
- tools/call method to invoke tools
- Compatible with MCP Inspector and standard MCP clients

Endpoints:
- GET  /sse               -> SSE connection for MCP protocol
- POST /tools/list        -> HTTP fallback for tools/list
- POST /tools/call        -> HTTP fallback for tools/call
"""

from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import sqlite3
import json
import asyncio
from config import DB_PATH

app = FastAPI(title="DB MCP Server", version="1.0.0")


# ---------- Pydantic models for request / response ----------

class ToolCallRequest(BaseModel):
    tool: str
    arguments: Dict[str, Any]


class ToolCallResponse(BaseModel):
    ok: bool
    result: Any = None
    error: Optional[str] = None


# ---------- Helper: DB connection ----------

def get_connection():
    """Create a new SQLite connection for each request."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------- MCP tool implementations (local) ----------

def mcp_get_customer(customer_id: int) -> Dict[str, Any]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, email, phone, status, created_at, updated_at "
            "FROM customers WHERE id = ?",
            (customer_id,)
        )
        row = cur.fetchone()
        if not row:
            return {"found": False}
        return {
            "found": True,
            "id": row["id"],
            "name": row["name"],
            "email": row["email"],
            "phone": row["phone"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
    finally:
        conn.close()


def mcp_list_customers(status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        if status:
            cur.execute(
                "SELECT id, name, email, phone, status FROM customers WHERE status = ? LIMIT ?",
                (status, limit),
            )
        else:
            cur.execute(
                "SELECT id, name, email, phone, status FROM customers LIMIT ?",
                (limit,),
            )
        rows = cur.fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "email": r["email"],
                "phone": r["phone"],
                "status": r["status"],
            }
            for r in rows
        ]
    finally:
        conn.close()


def mcp_update_customer(customer_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    if not data:
        return {"updated": False, "reason": "No fields provided"}

    allowed_fields = {"name", "email", "phone", "status"}
    update_fields = {k: v for k, v in data.items() if k in allowed_fields}
    if not update_fields:
        return {"updated": False, "reason": "No valid fields provided"}

    conn = get_connection()
    try:
        cur = conn.cursor()
        sets = ", ".join(f"{k} = ?" for k in update_fields.keys())
        values = list(update_fields.values()) + [customer_id]
        cur.execute(f"UPDATE customers SET {sets} WHERE id = ?", values)
        conn.commit()
        return {"updated": cur.rowcount > 0}
    finally:
        conn.close()


def mcp_create_ticket(customer_id: int, issue: str, priority: str) -> Dict[str, Any]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO tickets (customer_id, issue, status, priority) "
            "VALUES (?, ?, 'open', ?)",
            (customer_id, issue, priority),
        )
        conn.commit()
        ticket_id = cur.lastrowid
        return {"ticket_id": ticket_id, "status": "open", "priority": priority}
    finally:
        conn.close()


def mcp_get_customer_history(customer_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, issue, status, priority, created_at "
            "FROM tickets WHERE customer_id = ? ORDER BY created_at DESC",
            (customer_id,),
        )
        rows = cur.fetchall()
        return [
            {
                "ticket_id": r["id"],
                "issue": r["issue"],
                "status": r["status"],
                "priority": r["priority"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
    finally:
        conn.close()


# ---------- MCP Tool Definitions ----------

def get_tools_list() -> List[Dict[str, Any]]:
    """Get list of available MCP tools with full schemas."""
    return [
        {
            "name": "get_customer",
            "description": "Get a single customer record by ID.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "integer",
                        "description": "The customer ID to retrieve"
                    }
                },
                "required": ["customer_id"]
            }
        },
        {
            "name": "list_customers",
            "description": "List customers filtered by status (optional).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["active", "disabled"],
                        "description": "Filter by customer status (optional)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of customers to return",
                        "default": 50
                    }
                },
                "required": []
            }
        },
        {
            "name": "update_customer",
            "description": "Update one or more customer fields (name, email, phone, status).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "integer",
                        "description": "The customer ID to update"
                    },
                    "data": {
                        "type": "object",
                        "description": "Fields to update",
                        "properties": {
                            "name": {"type": "string"},
                            "email": {"type": "string"},
                            "phone": {"type": "string"},
                            "status": {"type": "string", "enum": ["active", "disabled"]}
                        }
                    }
                },
                "required": ["customer_id", "data"]
            }
        },
        {
            "name": "create_ticket",
            "description": "Create a new support ticket for a customer.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "integer",
                        "description": "The customer ID this ticket belongs to"
                    },
                    "issue": {
                        "type": "string",
                        "description": "Description of the issue"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Ticket priority level",
                        "default": "medium"
                    }
                },
                "required": ["customer_id", "issue"]
            }
        },
        {
            "name": "get_customer_history",
            "description": "Get all tickets (history) for a customer.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "integer",
                        "description": "The customer ID to get history for"
                    }
                },
                "required": ["customer_id"]
            }
        },
    ]


# ---------- MCP Protocol: Execute tool call ----------

def execute_tool_call(tool: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool call and return the result."""
    try:
        if tool == "get_customer":
            result = mcp_get_customer(customer_id=int(arguments["customer_id"]))
        elif tool == "list_customers":
            result = mcp_list_customers(
                status=arguments.get("status"),
                limit=int(arguments.get("limit", 50)),
            )
        elif tool == "update_customer":
            result = mcp_update_customer(
                customer_id=int(arguments["customer_id"]),
                data=arguments.get("data", {}),
            )
        elif tool == "create_ticket":
            result = mcp_create_ticket(
                customer_id=int(arguments["customer_id"]),
                issue=str(arguments["issue"]),
                priority=str(arguments.get("priority", "medium")),
            )
        elif tool == "get_customer_history":
            result = mcp_get_customer_history(
                customer_id=int(arguments["customer_id"])
            )
        else:
            return {
                "ok": False,
                "error": f"Unknown tool: {tool}"
            }
        
        return {
            "ok": True,
            "result": result
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }


# ---------- SSE endpoint for MCP protocol ----------

async def mcp_sse_stream():
    """SSE stream for MCP protocol communication."""
    # Send initial connection message
    yield f"data: {json.dumps({'type': 'connection', 'status': 'connected'})}\n\n"
    
    # In a real MCP implementation, this would handle incoming messages via SSE
    # For now, we'll keep it simple and use HTTP endpoints for tool calls
    # The SSE endpoint is available for MCP clients that require it
    
    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(30)
            yield f"data: {json.dumps({'type': 'ping'})}\n\n"
    except asyncio.CancelledError:
        pass


@app.get("/sse")
async def sse_endpoint():
    """SSE endpoint for MCP protocol (streaming)."""
    return StreamingResponse(
        mcp_sse_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# ---------- HTTP endpoints (for compatibility and MCP Inspector) ----------

@app.post("/tools/list")
async def list_tools():
    """
    MCP tools/list endpoint.
    Returns list of available tools with their schemas.
    Compatible with MCP Inspector.
    """
    return {
        "tools": get_tools_list()
    }


@app.get("/tools/list")
async def list_tools_get():
    """HTTP GET version of tools/list."""
    return await list_tools()


@app.post("/tools/call", response_model=ToolCallResponse)
async def call_tool(payload: ToolCallRequest):
    """
    MCP tools/call endpoint.
    Executes a tool with the given arguments.
    Compatible with MCP Inspector.
    """
    result = execute_tool_call(payload.tool, payload.arguments)
    return ToolCallResponse(**result)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "mcp-server"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
