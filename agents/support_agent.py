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
    if scenario == "multi_step":
        # For multi-step, always include ticket information (even if empty)
        if tickets and len(tickets) > 0:
            # Determine ticket type from intents or context
            intents_str = str(intents).lower()
            if "open" in intents_str or "open_tickets" in intents_str or "list_open" in intents_str:
                ticket_type = "open tickets"
            else:
                ticket_type = "high-priority tickets"
            
            context_parts.append(f"DATA ALREADY FETCHED: Retrieved {len(tickets)} {ticket_type} for active customers:")
            # Include ALL tickets to ensure IDs are available (don't limit)
            for t in tickets:
                customer_id = t.get('customer_id', 'Unknown')
                customer_name = t.get('customer_name', f'Customer {customer_id}')
                ticket_id = t.get('ticket_id') or t.get('id', 'Unknown')
                context_parts.append(
                    f"  - Ticket ID: {ticket_id} | Customer: {customer_name} (ID: {customer_id}) | "
                    f"Status: {t.get('status', 'unknown')} | Priority: {t.get('priority', 'unknown')} | Issue: {t.get('issue', 'No description')}"
                )
            context_parts.append(f"\nCRITICAL: The above {len(tickets)} tickets MUST be listed in your response with their exact Ticket IDs and Customer IDs.")
        else:
            # Determine what was checked based on intents
            intents_str = str(intents).lower()
            if "open" in intents_str or "open_tickets" in intents_str or "list_open" in intents_str:
                ticket_type = "open tickets"
            else:
                ticket_type = "high-priority tickets"
            context_parts.append(f"DATA ALREADY FETCHED: Checked all active customers via MCP, but found 0 {ticket_type}.")
    elif tickets:
        context_parts.append(f"Customer has {len(tickets)} tickets in history")
    if customer_list:
        if scenario == "multi_step":
            context_parts.append(f"DATA ALREADY FETCHED: Retrieved {len(customer_list)} premium customers (status=active) for multi-step query:")
            # Include customer names and IDs for all customers
            for c in customer_list[:12]:
                context_parts.append(f"  - Customer: {c.get('name', 'Unknown')} (ID: {c.get('id')})")
            if len(customer_list) > 12:
                context_parts.append(f"  ... and {len(customer_list) - 12} more customers")
        else:
            context_parts.append(f"Retrieved {len(customer_list)} customers for query")
    
    context = "\n".join(context_parts) if context_parts else "No additional context available."
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a Support Agent in a multi-agent customer service system.
Your job is to generate helpful, natural responses to customer queries based on the context provided.

Guidelines:
- Be friendly, professional, and empathetic
- Use the customer's name when available
- For premium customers, acknowledge their status appropriately
- For escalation scenarios, create tickets and provide ticket IDs
- For multi-step queries, format reports clearly using the data provided
- IMPORTANT: If context mentions tickets or customer_list, that data is ALREADY available - use it directly in your response
- If customer data is missing, politely ask for it

Generate a natural response that addresses the customer's query using the context provided."""),
        ("user", """Scenario: {scenario}
Intents: {intents}
Urgency: {urgency}
Context: {context}
Customer Query: {query}

Generate a helpful response to the customer. If this is an escalation or billing issue, mention that a ticket has been created (include ticket creation in your reasoning, but the system will create it separately).

For multi-step queries (scenario="multi_step"):
- CRITICAL: The context contains customer_list and tickets data that has ALREADY been fetched via MCP
- The data is COMPLETE and READY - do NOT ask for more data
- IMPORTANT: Look at the context carefully - if you see "DATA ALREADY FETCHED: Retrieved X tickets", those tickets ARE available and MUST be included in your response
- If the context shows tickets with Ticket IDs, Customer IDs, and Issue descriptions, you MUST list ALL of them in your response
- If tickets list is empty (context says "found 0 tickets" or "Checked all active customers via MCP, but found 0"), then say "No high-priority tickets found for premium customers" and list the customers checked
- If tickets exist (context shows ticket data with "Ticket ID:", "Customer:", etc.), format a clear, detailed report using the ACTUAL ticket data from the context
- MUST include exact ticket IDs and customer IDs/names for each ticket from the context
- List each ticket with: Ticket ID, Customer ID/Name, Status, Priority, Issue description (use the exact values from context)
- Format as a structured report (table or list format)
- NEVER say "I need data" or "please provide data" - the data is already fetched and in the context
- Include ALL tickets provided in the context (don't summarize unless there are 20+ tickets)
- DO NOT say "No tickets found" if the context clearly shows ticket data with Ticket IDs
- CRITICAL: If you see lines like "  - Ticket ID: X | Customer: Y (ID: Z) | Status: ...", those are REAL tickets that MUST be listed in your response

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
    
    elif scenario == "multi_step":
        # Multi-step scenario: format report with exact IDs
        intents_str = str(intents).lower()
        if "open" in intents_str or "open_tickets" in intents_str or "list_open" in intents_str:
            report_title = "Active Customers with Open Tickets"
            ticket_type = "open tickets"
        else:
            report_title = "High-Priority Tickets for Premium Customers"
            ticket_type = "high-priority tickets"
        
        if tickets:
            response_parts.append(f"Report: {report_title}\n")
            response_parts.append(f"Found {len(tickets)} {ticket_type}:\n")
            for t in tickets:
                customer_id = t.get('customer_id', 'Unknown')
                customer_name = t.get('customer_name', f'Customer {customer_id}')
                response_parts.append(
                    f"- Ticket ID: {t.get('ticket_id')} | Customer: {customer_name} (ID: {customer_id}) | "
                    f"Status: {t.get('status')} | Priority: {t.get('priority')} | Issue: {t.get('issue')}"
                )
        else:
            customer_list = state.get("customer_list", [])
            response_parts.append(f"Report: {report_title}\n")
            response_parts.append(f"Checked {len(customer_list)} active customers via MCP, but found no {ticket_type}.")
            if customer_list:
                response_parts.append("\nCustomers checked:")
                for c in customer_list[:10]:
                    response_parts.append(f"  - {c.get('name', 'Unknown')} (ID: {c.get('id')})")
    
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
    query = state.get("user_query", "").lower()
    
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
    
    # CRITICAL: For multi_step scenarios, fetch tickets if not already in state
    if scenario == "multi_step" and not state.get("tickets"):
        customer_list = state.get("customer_list", [])
        query_lower = query
        
        # Check if this is a high-priority tickets query
        if customer_list and ("high-priority" in query_lower or "high priority" in query_lower) and ("premium" in query_lower):
            # Fetch high-priority tickets for all premium customers
            all_tickets = []
            for c in customer_list:
                cid = c.get("id") if isinstance(c, dict) else c
                if not cid:
                    continue
                try:
                    history = mcp_get_customer_history(cid)
                    if not isinstance(history, list):
                        history = []
                    # Filter for high-priority tickets only
                    high_tickets = [t for t in history if t.get("priority") == "high"]
                    for ht in high_tickets:
                        ticket_data = {
                            "ticket_id": ht.get("ticket_id") or ht.get("id"),
                            "customer_id": cid,
                            "customer_name": c.get("name", f"Customer {cid}") if isinstance(c, dict) else f"Customer {cid}",
                            "status": ht.get("status", "unknown"),
                            "priority": ht.get("priority", "unknown"),
                            "issue": ht.get("issue", "No description"),
                            "created_at": ht.get("created_at", "")
                        }
                        all_tickets.append(ticket_data)
                except Exception as e:
                    print(f"Warning: Failed to get history for customer {cid}: {e}")
                    continue
            
            # Update state with fetched tickets
            state["tickets"] = all_tickets
            logs.append({
                "sender": "SupportAgent",
                "receiver": "Router",
                "content": f"Fetched {len(all_tickets)} high-priority tickets from {len(customer_list)} premium customers via MCP."
            })
        
        # Check if this is an open tickets query
        elif customer_list and ("open tickets" in query_lower or "open_tickets" in str(intents).lower()):
            # Fetch open tickets for all active customers
            all_tickets = []
            for c in customer_list:
                cid = c.get("id") if isinstance(c, dict) else c
                if not cid:
                    continue
                try:
                    history = mcp_get_customer_history(cid)
                    if not isinstance(history, list):
                        history = []
                    # Filter for open tickets only
                    open_tickets = [t for t in history if t.get("status") == "open"]
                    for ot in open_tickets:
                        ticket_data = {
                            "ticket_id": ot.get("ticket_id") or ot.get("id"),
                            "customer_id": cid,
                            "customer_name": c.get("name", f"Customer {cid}") if isinstance(c, dict) else f"Customer {cid}",
                            "status": ot.get("status", "unknown"),
                            "priority": ot.get("priority", "unknown"),
                            "issue": ot.get("issue", "No description"),
                            "created_at": ot.get("created_at", "")
                        }
                        all_tickets.append(ticket_data)
                except Exception as e:
                    print(f"Warning: Failed to get history for customer {cid}: {e}")
                    continue
            
            # Update state with fetched tickets
            state["tickets"] = all_tickets
            logs.append({
                "sender": "SupportAgent",
                "receiver": "Router",
                "content": f"Fetched {len(all_tickets)} open tickets from {len(customer_list)} active customers via MCP."
            })
    
    # ALWAYS use LLM to generate responses - NO hardcoded responses
    # LLM will handle all scenarios including multi-step coordination
    # The LLM receives all context (customers, tickets, etc.) and generates natural responses
    
    # Generate response using LLM (handles all scenarios including multi-step)
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
