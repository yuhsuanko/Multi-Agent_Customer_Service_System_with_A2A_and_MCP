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

    # Conditional routing after router
    def router_to_next(state: CSState) -> str:
        """
        Decide which node to go to after the router based on the scenario.
        """
        scenario = state.get("scenario", "coordinated")
        customer_id = state.get("customer_id")

        # Scenario 1: Task allocation (simple customer info)
        if scenario == "task_allocation":
            return "data_agent"

        # Scenario 2: Escalation / billing issue
        # Router first checks with Support Agent, then gets billing context if needed
        if scenario == "escalation":
            # Router negotiates: first route to Support Agent to check if it can handle
            # Support Agent will indicate it needs billing context
            # Then Router will route to Data Agent if customer_id exists
            if customer_id is not None:
                # For negotiation flow: Router → Support checks → Data Agent → Support
                # We'll route to Support first to show negotiation, then to Data
                # In LangGraph, we implement this as: Router → Support (implicit check) → Data → Support
                # For simplicity, we route to Data first to get context, then Support
                return "data_agent"  # Fetch customer/billing data first for context
            return "support_agent"   # Skip data fetch if no customer_id

        # Scenario 3: Multi-step coordination (reports)
        if scenario == "multi_step":
            return "data_agent"

        # Multi-intent: update email + ticket history
        if scenario == "multi_intent":
            return "data_agent"

        # Default: coordinated query (Router -> Data -> Support)
        return "data_agent"

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
