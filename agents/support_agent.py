# agents/support_agent.py
"""
Support Agent with LLM-powered response generation.

Responsibilities:
- Use LLM to generate intelligent, context-aware responses
- Interpret intents + structured data in CSState
- Create tickets via MCP when needed (e.g., escalation / billing issues)
- Add A2A log entries describing actions

The agent uses LLM to craft natural, helpful responses based on customer context.
"""

from typing import List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate

from .state import CSState, AgentMessage
from .mcp_client import mcp_create_ticket, mcp_get_customer_history
from .llm_config import get_default_llm


def _generate_response_with_llm(state: CSState) -> str:
    """
    Use LLM to generate a natural, helpful response based on context.
    
    Returns:
        Generated response string
    """
    llm = get_default_llm()
    
    # If no LLM is available, use fallback
    if llm is None:
        return _generate_fallback_response(state)
    
    scenario = state.get("scenario", "coordinated")
    intents = state.get("intents", [])
    customer = state.get("customer_data", {})
    customer_id = state.get("customer_id")
    urgency = state.get("urgency", "normal")
    tickets = state.get("tickets", [])
    customer_list = state.get("customer_list", [])
    query = state.get("user_query", "")
    
    # Build context string
    context_parts = []
    if customer.get("found"):
        context_parts.append(f"Customer: {customer.get('name')} (ID: {customer.get('id')}, Status: {customer.get('status')})")
    if tickets:
        context_parts.append(f"Customer has {len(tickets)} tickets in history")
    if customer_list:
        context_parts.append(f"Retrieved {len(customer_list)} customers for multi-step query")
    
    context = "\n".join(context_parts) if context_parts else "No additional context available."
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a Support Agent in a multi-agent customer service system.
Your job is to generate helpful, natural responses to customer queries based on the context provided.

Guidelines:
- Be friendly, professional, and empathetic
- Use the customer's name when available
- For premium customers, acknowledge their status appropriately
- For escalation scenarios, create tickets and provide ticket IDs
- For multi-step queries, format reports clearly
- If customer data is missing, politely ask for it

Generate a natural response that addresses the customer's query using the context provided."""),
        ("user", """Scenario: {scenario}
Intents: {intents}
Urgency: {urgency}
Context: {context}
Customer Query: {query}

Generate a helpful response to the customer. If this is an escalation or billing issue, mention that a ticket has been created (include ticket creation in your reasoning, but the system will create it separately).

For multi-step queries, format the response as a clear report based on the data provided.

Response:""")
    ])
    
    try:
        response = llm.invoke(prompt.format_messages(
            scenario=scenario,
            intents=str(intents),
            urgency=urgency,
            context=context,
            query=query
        ))
        
        return response.content if hasattr(response, 'content') else str(response)
    except Exception as e:
        print(f"Warning: LLM response generation failed, using fallback: {e}")
        return _generate_fallback_response(state)


def _generate_fallback_response(state: CSState) -> str:
    """Fallback rule-based response generation if LLM fails."""
    scenario = state.get("scenario", "coordinated")
    intents = state.get("intents", [])
    customer = state.get("customer_data", {})
    customer_id = state.get("customer_id")
    urgency = state.get("urgency", "normal")
    tickets = state.get("tickets", [])
    
    response_parts = []
    
    if scenario == "task_allocation" and customer.get("found"):
        response_parts.append(
            f"Here is the information we have on file for customer #{customer['id']}:\n"
            f"- Name: {customer['name']}\n"
            f"- Email: {customer['email']}\n"
            f"- Phone: {customer['phone']}\n"
            f"- Status: {customer['status']}"
        )
    
    elif scenario == "escalation" or "billing_issue" in intents:
        if customer_id:
            response_parts.append(
                "I understand you're experiencing billing issues. "
                "I've created a high-priority ticket for our billing team to review your charges "
                "and process any necessary refund."
            )
        else:
            response_parts.append(
                "I can help with your billing issue, but I first need your customer ID "
                "to locate your account."
            )
    
    elif scenario == "multi_intent":
        if "update_email" in intents and state.get("new_email"):
            response_parts.append(f"I have updated your email address to: {state['new_email']}.")
        if "ticket_history" in intents:
            if tickets:
                response_parts.append("Here is your recent ticket history:")
                for t in tickets:
                    response_parts.append(f"- Ticket {t.get('ticket_id')}: {t.get('issue')} ({t.get('status')})")
            else:
                response_parts.append("You currently have no tickets on file.")
    
    else:
        response_parts.append("I am here to help. Could you please provide more details about your issue?")
    
    return "\n\n".join(response_parts)


def _summarize_ticket_history(tickets: List[Dict[str, Any]]) -> str:
    """Build a human-readable summary of past tickets."""
    if not tickets:
        return "You currently have no tickets on file."
    
    lines = []
    for t in tickets:
        lines.append(
            f"- Ticket {t.get('ticket_id', 'N/A')}: {t.get('issue', 'N/A')} "
            f"({t.get('status', 'N/A')}, priority={t.get('priority', 'N/A')})"
        )
    return "\n".join(lines)


def support_agent_node(state: CSState) -> CSState:
    """
    Support agent node with LLM-powered response generation.
    
    Uses LLM to craft natural responses, creates tickets when needed,
    and handles multi-step report formatting.
    """
    messages = state.get("messages", [])
    logs = state.get("logs", [])
    scenario = state.get("scenario", "coordinated")
    intents = state.get("intents", [])
    customer_id = state.get("customer_id")
    customer = state.get("customer_data", {})
    urgency = state.get("urgency", "normal")
    
    # Handle ticket creation for escalation scenarios
    ticket_id = None
    if (scenario == "escalation" or "billing_issue" in intents) and customer_id:
        if customer.get("found"):
            ticket_result = mcp_create_ticket(
                customer_id=customer_id,
                issue="Billing issue with possible double charge and/or cancellation request",
                priority="high",
            )
            ticket_id = ticket_result.get("ticket_id")
            logs.append({
                "sender": "SupportAgent",
                "receiver": "Router",
                "content": f"Created high-priority ticket for escalation. Ticket ID: {ticket_id}"
            })
    
    # Handle multi-step coordination scenarios
    if scenario == "multi_step":
        customers = state.get("customer_list", [])
        report_lines = []
        
        if "high_priority_report" in intents:
            report_lines.append("Here is the status of high-priority tickets for active customers:\n")
            for c in customers:
                cid = c["id"]
                history = mcp_get_customer_history(cid)
                high_tickets = [t for t in history if t.get("priority") == "high"]
                if high_tickets:
                    entry = f"Customer {cid} ({c['name']}):"
                    for ht in high_tickets:
                        entry += f"\n  - Ticket {ht.get('ticket_id')} ({ht.get('status')}): {ht.get('issue')}"
                    report_lines.append(entry)
        
        elif "active_with_open_tickets" in intents:
            report_lines.append("Here are all active customers who currently have open tickets:\n")
            for c in customers:
                cid = c["id"]
                history = mcp_get_customer_history(cid)
                open_tickets = [t for t in history if t.get("status") == "open"]
                if open_tickets:
                    entry = f"Customer {cid} ({c['name']}):"
                    for ot in open_tickets:
                        entry += f"\n  - Ticket {ot.get('ticket_id')} (priority={ot.get('priority')}): {ot.get('issue')}"
                    report_lines.append(entry)
        
        if report_lines:
            state["support_response"] = "\n\n".join(report_lines)
            logs.append({
                "sender": "SupportAgent",
                "receiver": "Router",
                "content": "Compiled multi-step ticket report."
            })
            state["done"] = True
            state["messages"] = messages
            state["logs"] = logs
            return state
    
    # Generate response using LLM
    response = _generate_response_with_llm(state)
    
    # Add ticket ID to response if created
    if ticket_id:
        response += f"\n\nYour ticket ID is {ticket_id}."
    
    state["support_response"] = response
    state["done"] = True
    
    # Add final response to messages
    messages.append({
        "role": "assistant",
        "name": "SupportAgent",
        "content": response
    })
    
    logs.append({
        "sender": "SupportAgent",
        "receiver": "Router",
        "content": f"Generated support response. Scenario={scenario}, intents={intents}"
    })
    
    state["messages"] = messages
    state["logs"] = logs
    
    return state
