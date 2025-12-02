# agents/graph.py
"""
LangGraph workflow definition.

Nodes:
- router         (Router Agent)
- data_agent     (Customer Data Agent)
- support_agent  (Support Agent)

Routing logic:
- Entry point: router
- Router analyzes the query and sets scenario + intents
- Conditional edges decide whether to route through Data Agent
- Support Agent always produces the final user-facing response
"""

from langgraph.graph import StateGraph, END

from .state import CSState
from .router_agent import router_node
from .data_agent import data_agent_node
from .support_agent import support_agent_node


def build_workflow():
    """
    Build and compile the LangGraph workflow.

    Returns:
        A compiled LangGraph app that can be invoked with an initial CSState.
    """
    workflow = StateGraph(CSState)

    # Register nodes
    workflow.add_node("router", router_node)
    workflow.add_node("data_agent", data_agent_node)
    workflow.add_node("support_agent", support_agent_node)

    # Entry point is the router
    workflow.set_entry_point("router")

    # Conditional routing after router - LLM-driven decision making
    def router_to_next(state: CSState) -> str:
        """
        Use LLM to decide which agent to call next.
        
        TRUE AGENT implementation: LLM reasons about what's needed
        and decides routing dynamically, without hardcoded scenarios.
        """
        from .router_agent import _decide_routing_with_llm
        
        query = state.get("user_query", "")
        current_state = {
            "customer_id": state.get("customer_id"),
            "customer_data": state.get("customer_data"),
            "customer_list": state.get("customer_list"),
            "tickets": state.get("tickets"),
            "intents": state.get("intents", []),
        }
        
        # Use LLM to decide routing
        routing_decision = _decide_routing_with_llm(query, current_state)
        next_agent = routing_decision.get("next_agent", "data_agent")
        
        # Log the routing decision
        logs = state.get("logs", [])
        logs.append({
            "sender": "Router",
            "receiver": next_agent,
            "content": f"Routing decision: {routing_decision.get('reason', '')}"
        })
        state["logs"] = logs
        
        return next_agent

    workflow.add_conditional_edges(
        "router",
        router_to_next,
        {
            "data_agent": "data_agent",
            "support_agent": "support_agent",
        },
    )

    # After Data Agent finishes, go to Support Agent
    # (Router analysis of customer tier happens implicitly via state passed from Data Agent)
    workflow.add_edge("data_agent", "support_agent")

    # Support Agent produces the final response
    workflow.add_edge("support_agent", END)

    # Compile the graph into a runnable app
    app = workflow.compile()
    return app
