# Multi-Agent Customer Service System with A2A and MCP

## Overview

This project implements a multi-agent customer-service automation system that demonstrates:

- **Agent-to-Agent (A2A) coordination** using LangGraph's message-based communication
- **Model Context Protocol (MCP)** integration for structured data access
- **Multi-agent task allocation, negotiation, and multi-step coordination**
- **Practical customer service automation** with specialized agent roles

The system demonstrates how specialized agents collaborate to analyze customer queries, retrieve structured data, escalate issues, and generate user-facing responses.

---

## System Architecture

### Three Specialized Agents (LLM-Powered)

All agents use LLM backends for intelligent reasoning and decision-making:

| Agent | Responsibilities | LLM Usage |
|-------|------------------|-----------|
| **Router Agent (Orchestrator)** | Receives customer queries, analyzes query intent, routes to appropriate specialist agents, coordinates responses from multiple agents | Uses LLM to detect intents, classify scenarios, and extract entities from natural language queries |
| **Customer Data Agent (Specialist)** | Accesses customer database via MCP, retrieves customer information, updates customer records, handles data validation | Uses LLM to reason about what data operations are needed based on context |
| **Support Agent (Specialist)** | Handles general customer support queries, can escalate complex issues, requests customer context from Data Agent, provides solutions and recommendations | Uses LLM to generate natural, context-aware responses based on customer data and scenario |

**Note:** Agents can work with rule-based fallback logic if no LLM API key is configured, but LLM reasoning is recommended for full functionality.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      User Query                              │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        v
            ┌───────────────────────┐
            │   Router Agent        │
            │   (Orchestrator)      │
            │  - Intent Detection   │
            │  - Scenario Analysis  │
            │  - Entity Extraction  │
            └───────┬───────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
        v           v           v
┌─────────────┐ ┌──────────────┐ ┌─────────────┐
│ Data Agent  │ │ Support Agent│ │   Direct    │
│   (MCP)     │ │   (MCP)      │ │   Path      │
└──────┬──────┘ └──────┬───────┘ └─────────────┘
       │                │
       └────────┬───────┘
                │
                v
        ┌───────────────┐
        │ Final Response│
        └───────────────┘
```

---

## Protocol Compliance

This implementation is designed to comply with both **MCP (Model Context Protocol)** and **A2A (Agent-to-Agent)** specifications as required by the assignment.

### MCP Protocol Compliance ✓

The MCP server (`db_mcp_server.py`) implements:
- **SSE (Server-Sent Events)** endpoint (`/sse`) for streaming communication
- **`/tools/list`** endpoint returning full tool schemas with JSON Schema definitions
- **`/tools/call`** endpoint for tool execution
- Compatible with **MCP Inspector** and standard MCP clients

**Test with MCP Inspector:**
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

### A2A Protocol Compliance ✓

Each agent implements the full A2A specification:
- **`/agent/card`** endpoint for agent discovery (GET)
- **`/agent/tasks`** endpoint for task execution (POST)
- **`/health`** endpoint for service monitoring
- Independent agent services that communicate via A2A protocol
- Agents discover and communicate with each other using standardized endpoints

**Agent Endpoints:**
- Router Agent: `http://localhost:8001/agent/card`, `/agent/tasks`
- Data Agent: `http://localhost:8002/agent/card`, `/agent/tasks`
- Support Agent: `http://localhost:8003/agent/card`, `/agent/tasks`

See `PROTOCOLS.md` for detailed protocol specifications and testing procedures.

---

## MCP Integration

The system includes a complete MCP server implementation with the following tools:

### Required Tools

1. **`get_customer(customer_id)`** - Retrieves a single customer record by ID
2. **`list_customers(status, limit)`** - Lists customers filtered by status (active/disabled)
3. **`update_customer(customer_id, data)`** - Updates customer fields (name, email, phone, status)
4. **`create_ticket(customer_id, issue, priority)`** - Creates a new support ticket
5. **`get_customer_history(customer_id)`** - Retrieves all tickets for a customer

### Database Schema

**Customers Table:**
- `id` (INTEGER PRIMARY KEY)
- `name` (TEXT NOT NULL)
- `email` (TEXT)
- `phone` (TEXT)
- `status` (TEXT: 'active' or 'disabled')
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

**Tickets Table:**
- `id` (INTEGER PRIMARY KEY)
- `customer_id` (INTEGER, FK to customers.id)
- `issue` (TEXT NOT NULL)
- `status` (TEXT: 'open', 'in_progress', 'resolved')
- `priority` (TEXT: 'low', 'medium', 'high')
- `created_at` (DATETIME)

---

## A2A Coordination Scenarios

The system implements three core coordination patterns:

### Scenario 1: Task Allocation

**Query:** "I need help with my account, customer ID 12345."

**A2A Flow:**
1. Router Agent receives query and extracts customer ID
2. Router Agent → Customer Data Agent: "Get customer info for ID 12345"
3. Customer Data Agent fetches via MCP
4. Customer Data Agent → Router Agent: Returns customer data
5. Router Agent → Support Agent: "Handle support for customer"
6. Support Agent generates response
7. Router Agent returns final response

### Scenario 2: Negotiation/Escalation

**Query:** "I want to cancel my subscription but I'm having billing issues"

**A2A Flow:**
1. Router detects multiple intents (cancellation + billing)
2. Router → Support Agent: "Can you handle this?"
3. Support Agent → Router: "I need billing context"
4. Router negotiates between agents to formulate response
5. Support Agent creates high-priority ticket via MCP
6. Coordinated response sent to customer

### Scenario 3: Multi-Step Coordination

**Query:** "What's the status of all high-priority tickets for premium customers?"

**A2A Flow:**
1. Router decomposes into sub-tasks
2. Router → Customer Data Agent: "Get all active customers"
3. Customer Data Agent → Router: Returns customer list
4. Router → Support Agent: "Get high-priority tickets for these IDs"
5. Support Agent queries tickets via MCP for each customer
6. Agents coordinate to format the report
7. Router synthesizes final answer

---

## Installation and Setup

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Step 1: Create a Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure LLM (Required for Agent Reasoning)

The agents use LLM backends for intelligent reasoning. You need to configure an API key:

**Option 1: Using OpenAI**
```bash
export OPENAI_API_KEY="your_openai_api_key_here"
export LLM_PROVIDER="openai"
export LLM_MODEL="gpt-3.5-turbo"  # or "gpt-4"
```

**Option 2: Using Anthropic**
```bash
export ANTHROPIC_API_KEY="your_anthropic_api_key_here"
export LLM_PROVIDER="anthropic"
export LLM_MODEL="claude-3-haiku-20240307"
```

**Option 3: Using .env file (Recommended)**
1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your API key:
   ```bash
   OPENAI_API_KEY=your_openai_api_key_here
   LLM_PROVIDER=openai
   LLM_MODEL=gpt-3.5-turbo
   ```

3. Install python-dotenv (if not already installed):
   ```bash
   pip install python-dotenv
   ```

The system will automatically load environment variables from `.env` file.

**Note:** If no API key is configured, the system will use rule-based fallback logic (useful for testing, but agents won't have LLM reasoning capabilities).

### Step 4: Set Up the Database

```bash
python database_setup.py
```

When prompted:
- Enter `y` to insert sample data
- Optionally enter `y` to run sample queries

This will create `support.db` with sample customers and tickets.

### Step 5: Verify Installation

Run a quick test to ensure everything is set up correctly:

```bash
python -c "from agents.graph import build_workflow; print('Setup successful!')"
```

---

## Usage

### Option 1: Local LangGraph Demo (Recommended for Testing)

Run the end-to-end demo that uses a local LangGraph workflow:

```bash
python demo/main.py
```

This will execute all test scenarios and display:
- User queries
- Detected scenarios and intents
- Agent-to-agent communication logs
- A2A messages
- Final responses

### Option 2: Distributed A2A Services (Production-like)

For a production-like setup with separate services using **proper MCP and A2A protocols**:

#### Terminal 1: Start MCP Server
```bash
python db_mcp_server.py
```
- Server runs on `http://localhost:8000`
- MCP endpoints: `/sse`, `/tools/list`, `/tools/call`
- **Test with MCP Inspector:** Connect to `http://localhost:8000/sse`

#### Terminal 2: Start Data Agent (A2A)
```bash
python data_agent_server.py
```
- Server runs on `http://localhost:8002`
- A2A endpoints: `/agent/card`, `/agent/tasks`, `/health`

#### Terminal 3: Start Support Agent (A2A)
```bash
python support_agent_server.py
```
- Server runs on `http://localhost:8003`
- A2A endpoints: `/agent/card`, `/agent/tasks`, `/health`

#### Terminal 4: Start Router Agent (A2A)
```bash
python router_agent_server.py
```
- Server runs on `http://localhost:8001`
- A2A endpoints: `/agent/card`, `/agent/tasks`, `/health`
- Orchestrates other agents via A2A protocol

#### Verify Protocol Compliance

**Test MCP Server:**
```bash
# Test tools/list (should return full tool schemas)
curl http://localhost:8000/tools/list

# Test tools/call
curl -X POST http://localhost:8000/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool": "get_customer", "arguments": {"customer_id": 1}}'
```

**Test A2A Agents:**
```bash
# Get agent cards (discovery)
curl http://localhost:8001/agent/card  # Router
curl http://localhost:8002/agent/card  # Data Agent
curl http://localhost:8003/agent/card  # Support Agent

# Check health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

#### Execute Query via A2A

```bash
curl -X POST http://localhost:8001/agent/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "user_query": "Get customer information for ID 5"
    }
  }'
```

The Router Agent will:
1. Analyze the query
2. Call Data Agent via A2A (`/agent/tasks`)
3. Data Agent calls MCP Server (`/tools/call`)
4. Router calls Support Agent via A2A
5. Returns final response

---

## Test Scenarios

The system handles the following test scenarios:

### 1. Simple Query
**Query:** "Get customer information for ID 5"  
**Expected:** Single agent, straightforward MCP call

### 2. Coordinated Query
**Query:** "I'm customer 12345 and need help upgrading my account"  
**Expected:** Multiple agents coordinate: data fetch + support response

### 3. Complex Query
**Query:** "Show me all active customers who have open tickets"  
**Expected:** Requires negotiation between data and support agents

### 4. Escalation
**Query:** "I've been charged twice, please refund immediately!"  
**Expected:** Router identifies urgency and routes appropriately, creates high-priority ticket

### 5. Multi-Intent
**Query:** "Update my email to new@email.com and show my ticket history"  
**Expected:** Parallel task execution and coordination

---

## Project Structure

```
.
├── agents/                  # Agent implementations
│   ├── __init__.py
│   ├── router_agent.py     # Router/orchestrator agent
│   ├── data_agent.py       # Customer data specialist
│   ├── support_agent.py    # Support specialist
│   ├── graph.py            # LangGraph workflow definition
│   ├── state.py            # Shared state structure
│   ├── llm_config.py       # LLM configuration and initialization
│   └── mcp_client.py       # MCP tool client wrapper
├── demo/                   # Demo scripts
│   └── main.py            # End-to-end demonstration
├── .env.example            # Environment variables template
├── database_setup.py       # Database initialization script
├── db_mcp_server.py        # MCP server (FastAPI)
├── router_agent_server.py  # Router agent A2A server
├── data_agent_server.py    # Data agent A2A server
├── support_agent_server.py # Support agent A2A server
├── config.py               # Configuration (URLs, paths)
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── QUICKSTART.md          # Quick start guide
├── PROTOCOLS.md           # Protocol documentation
└── support.db             # SQLite database (created after setup)
```

---

## Technology Stack

- **LangGraph SDK**: Used for agent orchestration and workflow management
  - `StateGraph` from `langgraph.graph` for defining multi-agent workflows
  - Message-based state for A2A compatibility
  - Conditional routing and edge management
  - Native workflow compilation and execution
- **LangChain**: Used for LLM integration (OpenAI, Anthropic)
  - `ChatOpenAI` and `ChatAnthropic` for LLM backends
  - Prompt templating and output parsing
- **FastAPI**: Used for MCP and A2A server endpoints
- **SQLite**: Database backend for customer and ticket data

## Key Implementation Details

### LangGraph SDK Usage

This implementation uses **LangGraph SDK** for agent orchestration:

- **Workflow Definition**: Uses `StateGraph` to define the multi-agent workflow
- **Node Registration**: Each agent is registered as a LangGraph node
- **Conditional Routing**: Uses `add_conditional_edges()` for scenario-based routing
- **State Management**: Shared state (`CSState`) passed between agents
- **Workflow Compilation**: Workflow is compiled using `workflow.compile()`
- **Execution**: Workflow is invoked using `app.invoke(initial_state)`

### A2A Message Passing

The system uses LangGraph's message-based state structure for A2A compatibility:

- All states include a `messages` list (required for A2A)
- Messages are logged for debugging and transparency
- Agents communicate via structured messages with sender/receiver information

### MCP Integration

- MCP tools are accessible via HTTP endpoints (`/tools/call`)
- Agents can call tools directly (local demo) or via HTTP (distributed setup)
- All database operations go through MCP for consistency

### Error Handling

- Graceful handling of missing customer IDs
- Validation of customer status and ticket priorities
- Clear error messages for invalid inputs

---

## Troubleshooting

### Database Issues

**Problem:** `support.db` not found  
**Solution:** Run `python database_setup.py` to create the database

**Problem:** Database state corrupted  
**Solution:** Delete `support.db` and run `database_setup.py` again

### Port Conflicts

**Problem:** Port already in use  
**Solution:** Update URLs in `config.py` to use different ports

### Import Errors

**Problem:** Module not found errors  
**Solution:** Ensure virtual environment is activated and dependencies are installed:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

---

## Learning Outcomes

This project demonstrates:

1. **Multi-Agent Coordination:** How specialized agents collaborate to solve complex tasks
2. **A2A Communication:** Implementation of agent-to-agent protocols with explicit logging
3. **MCP Integration:** Structured access to external tools and data sources
4. **Task Decomposition:** Breaking complex queries into manageable sub-tasks
5. **State Management:** Sharing context between agents through structured state

---

## Future Enhancements

Potential improvements:

- Enhanced LLM prompts for better intent detection and response quality
- Implement persistent agent memory/context across sessions
- Add authentication and rate limiting for production use
- Support for additional MCP tools (email, notifications, etc.)
- Web interface for customer interactions
- Advanced routing based on customer tier/premium status
- Real-time streaming responses via SSE

---

## License

This project is created for educational purposes as part of the Applied Generative AI course assignment.
