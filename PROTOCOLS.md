# Protocol Specifications

This document describes how the system implements the MCP (Model Context Protocol) and A2A (Agent-to-Agent) protocols.

## MCP (Model Context Protocol) Implementation

The MCP server (`db_mcp_server.py`) implements the Model Context Protocol for tool access.

### Endpoints

1. **SSE Endpoint**: `GET /sse`
   - Server-Sent Events stream for MCP protocol communication
   - Maintains persistent connection for streaming tool results
   - Compatible with MCP Inspector and standard MCP clients

2. **Tools List**: `GET /tools/list` or `POST /tools/list`
   - Returns list of available tools with full JSON schemas
   - Each tool includes:
     - `name`: Tool identifier
     - `description`: Human-readable description
     - `inputSchema`: JSON schema defining required and optional parameters

3. **Tool Call**: `POST /tools/call`
   - Executes a tool with provided arguments
   - Request format:
     ```json
     {
       "tool": "tool_name",
       "arguments": {
         "param1": "value1",
         "param2": "value2"
       }
     }
     ```
   - Response format:
     ```json
     {
       "ok": true,
       "result": {...}
     }
     ```
     or
     ```json
     {
       "ok": false,
       "error": "error message"
     }
     ```

### Available Tools

1. **get_customer** - Get customer by ID
2. **list_customers** - List customers with optional status filter
3. **update_customer** - Update customer fields
4. **create_ticket** - Create a new support ticket
5. **get_customer_history** - Get all tickets for a customer

### Testing with MCP Inspector

To test the MCP server with MCP Inspector:

1. Start the MCP server:
   ```bash
   python db_mcp_server.py
   ```

2. The server will be available at `http://localhost:8000`

3. MCP Inspector can connect via:
   - SSE endpoint: `http://localhost:8000/sse`
   - HTTP endpoints: `http://localhost:8000/tools/list` and `http://localhost:8000/tools/call`

4. Test tools/list:
   ```bash
   curl http://localhost:8000/tools/list
   ```

5. Test tools/call:
   ```bash
   curl -X POST http://localhost:8000/tools/call \
     -H "Content-Type: application/json" \
     -d '{
       "tool": "get_customer",
       "arguments": {"customer_id": 1}
     }'
   ```

## A2A (Agent-to-Agent) Protocol Implementation

Each agent implements the A2A protocol specification for agent discovery and task execution.

### A2A Endpoints

Each agent exposes the following endpoints:

1. **Agent Card**: `GET /agent/card`
   - Returns agent metadata and capabilities
   - Response format:
     ```json
     {
       "name": "agent-name",
       "description": "Agent description",
       "version": "1.0.0",
       "capabilities": ["capability1", "capability2"]
     }
     ```

2. **Task Execution**: `POST /agent/tasks`
   - Executes a task delegated by another agent
   - Request format:
     ```json
     {
       "input": {
         "action": "action_name",
         "param1": "value1",
         "param2": "value2"
       }
     }
     ```
   - Response format:
     ```json
     {
       "status": "completed",
       "result": {...}
     }
     ```

3. **Health Check**: `GET /health`
   - Service health and connectivity status
   - Useful for monitoring and debugging

### Agent Roles

1. **Router Agent** (`router_agent_server.py`)
   - Port: 8001
   - A2A endpoints: `/agent/card`, `/agent/tasks`, `/health`
   - Discovers and coordinates with Data Agent and Support Agent

2. **Customer Data Agent** (`data_agent_server.py`)
   - Port: 8002
   - A2A endpoints: `/agent/card`, `/agent/tasks`, `/health`
   - Accesses MCP server for database operations

3. **Support Agent** (`support_agent_server.py`)
   - Port: 8003
   - A2A endpoints: `/agent/card`, `/agent/tasks`, `/health`
   - Accesses MCP server for ticket creation

### Agent-to-Agent Communication

Agents communicate via HTTP REST calls following A2A specifications:

1. **Discovery**: Agents can discover each other by calling `/agent/card`
   ```bash
   curl http://localhost:8002/agent/card
   ```

2. **Task Delegation**: Agents delegate tasks via `/agent/tasks`
   ```bash
   curl -X POST http://localhost:8002/agent/tasks \
     -H "Content-Type: application/json" \
     -d '{
       "input": {
         "action": "get_customer",
         "customer_id": 1
       }
     }'
   ```

### A2A Communication Flow

```
User Query
    ↓
Router Agent (receives via /agent/tasks)
    ↓
Router analyzes query
    ↓
Router → Data Agent (via A2A /agent/tasks)
    ↓
Data Agent → MCP Server (via /tools/call)
    ↓
Data Agent → Router (returns result)
    ↓
Router → Support Agent (via A2A /agent/tasks)
    ↓
Support Agent → MCP Server (if needed)
    ↓
Support Agent → Router (returns response)
    ↓
Router → User (final response)
```

## Protocol Compliance Checklist

### MCP Compliance ✓
- [x] SSE endpoint implemented (`/sse`)
- [x] `tools/list` endpoint with full tool schemas
- [x] `tools/call` endpoint for tool execution
- [x] Compatible with MCP Inspector
- [x] Proper error handling and response formats

### A2A Compliance ✓
- [x] Each agent has `/agent/card` endpoint
- [x] Each agent has `/agent/tasks` endpoint
- [x] Agents can discover each other
- [x] Agents communicate via HTTP REST (A2A protocol)
- [x] Proper task delegation and result passing
- [x] Health check endpoints for monitoring

## Testing Protocol Compliance

### Test MCP Server

```bash
# Start MCP server
python db_mcp_server.py

# Test tools/list
curl http://localhost:8000/tools/list

# Test tools/call
curl -X POST http://localhost:8000/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool": "get_customer", "arguments": {"customer_id": 1}}'
```

### Test A2A Agents

```bash
# Start all agents (in separate terminals)
python db_mcp_server.py        # Port 8000
python data_agent_server.py    # Port 8002
python support_agent_server.py # Port 8003
python router_agent_server.py  # Port 8001

# Test agent cards
curl http://localhost:8001/agent/card  # Router
curl http://localhost:8002/agent/card  # Data Agent
curl http://localhost:8003/agent/card  # Support Agent

# Test task execution via Router
curl -X POST http://localhost:8001/agent/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "user_query": "Get customer information for ID 5"
    }
  }'
```

