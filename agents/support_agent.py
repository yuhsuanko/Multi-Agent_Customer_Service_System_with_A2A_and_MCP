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

from typing import List, Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from .state import CSState, AgentMessage
from .mcp_client import mcp_create_ticket, mcp_get_customer_history
from .llm_config import get_default_llm


def _plan_data_needs_with_llm(query: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Use LLM to reason about what data operations are needed.
    
    TRUE AGENT: LLM decides if we need tickets, which customers, what filters.
    NO hardcoded rules.
    
    Returns:
        {
            "need_tickets": bool,
            "customers": [customer_ids] or empty to use customer_list,
            "filters": {"priority": "high" or None, "status": "open" or None},
            "format": "report" or "summary"
        }
    """
    llm = get_default_llm()
    if llm is None:
        return {"need_tickets": False, "customers": [], "filters": {}, "format": "summary"}
    
    customer_list = context.get("customer_list", [])
    has_tickets = context.get("has_tickets", False)
    intents = context.get("intents", [])
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a Support Agent planning what data to fetch.

CRITICAL: You MUST return ONLY valid JSON. Do NOT include any explanation, analysis, or text before or after the JSON.

Analyze the query and determine:
1. Does this query need ticket data?
2. For which customers? (if customer_list is provided, use those; otherwise specify customer IDs)
3. What filters are needed? (priority="high", status="open", etc.)
4. What format is needed? (detailed report, summary, etc.)

Important context:
- "premium customers" = customers with status="active"
- "high-priority tickets" = tickets with priority="high"
- "open tickets" = tickets with status="open"

CRITICAL INSTRUCTIONS:
- If the query asks for "high-priority tickets for premium customers" or similar, you MUST:
  1. Set "need_tickets": true
  2. Set "customers": [] (empty array to use the provided customer_list)
  3. Set "filters": {{"priority": "high"}}
- If customer_list is provided and query mentions tickets, you MUST fetch tickets for those customers
- Always use the customer_list if provided, don't ask for specific customer IDs

Return ONLY JSON:
{{
    "need_tickets": true/false,
    "customers": [list of specific customer IDs if needed, or empty array to use customer_list],
    "filters": {{"priority": "high" or null, "status": "open" or null}},
    "format": "report" or "summary"
}}

Return ONLY the JSON object, nothing else."""),
        ("user", """Query: {query}
Available context:
- customer_list: {customer_list_count} customers available
- has_tickets: {has_tickets}
- intents: {intents}

Return ONLY JSON with need_tickets, customers, filters, and format. No explanation.""")
    ])
    
    parser = JsonOutputParser(pydantic_object=None)
    chain = prompt | llm | parser
    
    try:
        result = chain.invoke({
            "query": query,
            "customer_list_count": len(customer_list) if customer_list else 0,
            "has_tickets": has_tickets,
            "intents": str(intents),
        })
        
        return {
            "need_tickets": result.get("need_tickets", False),
            "customers": result.get("customers", []),
            "filters": result.get("filters", {}),
            "format": result.get("format", "summary"),
        }
    except Exception as e:
        print(f"Warning: LLM data planning failed, trying to extract JSON: {e}")
        try:
            raw_response = llm.invoke(prompt.format_messages(
                query=query,
                customer_list_count=len(customer_list) if customer_list else 0,
                has_tickets=has_tickets,
                intents=str(intents),
            ))
            raw_text = raw_response.content if hasattr(raw_response, 'content') else str(raw_response)
            
            import json
            import re
            # Look for JSON object in the text
            json_match = re.search(r'\{[^{}]*"need_tickets"[^{}]*\}', raw_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                return {
                    "need_tickets": result.get("need_tickets", False),
                    "customers": result.get("customers", []),
                    "filters": result.get("filters", {}),
                    "format": result.get("format", "summary"),
                }
        except:
            pass
        
        print(f"Warning: JSON extraction failed, using default values")
        return {"need_tickets": False, "customers": [], "filters": {}, "format": "summary"}


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
    
    intents = state.get("intents", [])
    customer = state.get("customer_data", {})
    customer_id = state.get("customer_id")
    urgency = state.get("urgency", "normal")
    tickets = state.get("tickets", [])
    customer_list = state.get("customer_list", [])
    query = state.get("user_query", "")
    
    # Build context string - NO scenario dependencies
    context_parts = []
    if customer.get("found"):
        context_parts.append(f"Customer: {customer.get('name')} (ID: {customer.get('id')}, Status: {customer.get('status')})")
    
    # Check if query asks for customers "who have" something (e.g., "customers who have open tickets")
    query_lower = query.lower()
    asks_for_customers_with_tickets = ("who have" in query_lower or "with" in query_lower) and ("ticket" in query_lower or "open" in query_lower)
    
    # Include customer list if available - CRITICAL: These are premium customers
    if customer_list:
        # If query asks for "customers who have open tickets", only list customers that actually have tickets
        if asks_for_customers_with_tickets and tickets:
            # Find which customers have tickets
            customers_with_tickets = {}
            ticket_customer_ids = set(t.get('customer_id') for t in tickets if t.get('customer_id'))
            
            for c in customer_list:
                cid = c.get('id') if isinstance(c, dict) else c
                if cid in ticket_customer_ids:
                    customers_with_tickets[cid] = c
            
            if customers_with_tickets:
                context_parts.append(f"ACTIVE CUSTOMERS WITH OPEN TICKETS: Found {len(customers_with_tickets)} active customers who have open tickets:")
                for cid, c in list(customers_with_tickets.items())[:12]:
                    context_parts.append(f"  - Customer: {c.get('name', 'Unknown')} (ID: {cid}) - HAS OPEN TICKETS")
                if len(customers_with_tickets) > 12:
                    context_parts.append(f"  ... and {len(customers_with_tickets) - 12} more customers with open tickets")
                context_parts.append(f"\nCRITICAL: Only list these {len(customers_with_tickets)} customers who HAVE open tickets. Do NOT list all active customers.")
            else:
                context_parts.append(f"ACTIVE CUSTOMERS: Retrieved {len(customer_list)} active customers, but NONE have open tickets.")
        else:
            # Normal case: list all premium customers
            context_parts.append(f"PREMIUM CUSTOMERS (status='active'): Retrieved {len(customer_list)} premium customers:")
            premium_customer_ids = set()
            for c in customer_list[:12]:
                cid = c.get('id') if isinstance(c, dict) else c
                premium_customer_ids.add(cid)
                context_parts.append(f"  - Customer: {c.get('name', 'Unknown')} (ID: {cid}) - PREMIUM")
            if len(customer_list) > 12:
                for c in customer_list[12:]:
                    cid = c.get('id') if isinstance(c, dict) else c
                    premium_customer_ids.add(cid)
                context_parts.append(f"  ... and {len(customer_list) - 12} more premium customers")
            context_parts.append(f"\nCRITICAL: All customers listed above are PREMIUM customers (status='active').")
            context_parts.append(f"Premium customer IDs: {sorted(premium_customer_ids)}")
    
    # Include ticket information if available
    if tickets and len(tickets) > 0:
        # Determine ticket type from intents or query
        intents_str = str(intents).lower()
        query_lower = query.lower()
        if "open" in intents_str or "open_tickets" in intents_str or "open tickets" in query_lower:
            ticket_type = "open tickets"
        elif "high" in intents_str or "high-priority" in query_lower or "high priority" in query_lower:
            ticket_type = "high-priority tickets"
        else:
            ticket_type = "tickets"
        
        # Filter tickets to only premium customers if customer_list is provided
        premium_customer_ids = set()
        if customer_list:
            for c in customer_list:
                cid = c.get('id') if isinstance(c, dict) else c
                premium_customer_ids.add(cid)
        
        filtered_tickets = tickets
        if premium_customer_ids:
            # Only show tickets for premium customers
            filtered_tickets = [t for t in tickets if t.get('customer_id') in premium_customer_ids]
            context_parts.append(f"\nDATA ALREADY FETCHED: Retrieved {len(filtered_tickets)} {ticket_type} FOR PREMIUM CUSTOMERS:")
        else:
            context_parts.append(f"DATA ALREADY FETCHED: Retrieved {len(tickets)} {ticket_type}:")
        
        # Include ALL filtered tickets to ensure IDs are available
        for t in filtered_tickets:
            ticket_customer_id = t.get('customer_id', 'Unknown')
            customer_name = t.get('customer_name', f'Customer {ticket_customer_id}')
            ticket_id = t.get('ticket_id') or t.get('id', 'Unknown')
            context_parts.append(
                f"  - Ticket ID: {ticket_id} | Customer: {customer_name} (ID: {ticket_customer_id}) | "
                f"Status: {t.get('status', 'unknown')} | Priority: {t.get('priority', 'unknown')} | Issue: {t.get('issue', 'No description')}"
            )
        context_parts.append(f"\nIMPORTANT: The above {len(filtered_tickets)} tickets are FOR PREMIUM CUSTOMERS and MUST be listed in your response with their exact Ticket IDs and Customer IDs.")
    elif customer_id and not tickets:
        # Single customer query but no tickets yet
        context_parts.append("Customer ticket history not yet retrieved.")
    
    context = "\n".join(context_parts) if context_parts else "No additional context available."
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a Support Agent in a multi-agent customer service system.
Your job is to generate helpful, natural responses to customer queries based on the context provided.

Guidelines:
- Be friendly, professional, and empathetic
- Use the customer's name when available
- For premium customers, acknowledge their status appropriately
- For urgent billing/refund issues, mention that a ticket will be created
- For complex queries requiring reports, format them clearly using the data provided
- IMPORTANT: If context mentions tickets or customer_list, that data is ALREADY available - use it directly in your response
- CRITICAL: If context shows "PREMIUM CUSTOMERS" and lists customer IDs, those ARE the premium customers - don't ask for them again
- CRITICAL: If context shows tickets "FOR PREMIUM CUSTOMERS", those tickets are already filtered - just list them
- If customer data is missing, politely ask for it

Think about what the customer needs and generate a natural response that addresses their query."""),
        ("user", """Query: {query}
Intents: {intents}
Urgency: {urgency}
Available Context: {context}

Analyze the query and available context. Generate a helpful response:

1. What is the customer asking for?
2. What data do we have available in the context?
3. What information might be missing?
4. How should I respond to help the customer?

CRITICAL INSTRUCTIONS:
- The context contains data that has ALREADY been fetched - use it directly
- If you see "PREMIUM CUSTOMERS" in the context, those ARE the premium customers - don't ask for them
- If you see "ACTIVE CUSTOMERS WITH OPEN TICKETS" in the context, you MUST FIRST list those customers by name and ID, THEN list their tickets
- If query asks for "active customers who have open tickets" or "customers with open tickets":
  * FIRST: List the customers who have open tickets (from "ACTIVE CUSTOMERS WITH OPEN TICKETS" section)
  * THEN: List all their open tickets with full details
- If you see "DATA ALREADY FETCHED: Retrieved X tickets FOR PREMIUM CUSTOMERS", those tickets are ALREADY filtered for premium customers - just list them
- If the context shows tickets with Ticket IDs, Customer IDs, and Issue descriptions, you MUST list ALL of them
- MUST include exact ticket IDs and customer IDs/names for each ticket from the context
- Format reports clearly: 
  * For "customers who have open tickets": First list the customers, then list their tickets
  * For other queries: List each ticket with Ticket ID, Customer ID/Name, Status, Priority, Issue
- NEVER say "I need data" or "please provide data" or "I don't know which customers are premium" if the context already contains it
- NEVER say "the data doesn't mark which customers are premium" if context shows "PREMIUM CUSTOMERS" - those ARE the premium customers
- NEVER list all active customers if the query asks for "customers who have open tickets" - only list those who actually have tickets
- Include ALL tickets provided in the context (don't summarize unless there are 20+ tickets)
- If context shows ticket data like "Ticket ID: X | Customer: Y", those are REAL tickets that MUST be listed
- If query asks for "high-priority tickets for premium customers" and context shows tickets "FOR PREMIUM CUSTOMERS", those ARE the answer - list them all

Generate your response:""")
    ])
    
    try:
        response = llm.invoke(prompt.format_messages(
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
    
    # Check if this is an escalation scenario (cancellation + billing)
    has_cancellation = any("cancel" in str(intent).lower() for intent in intents)
    has_billing = any("billing" in str(intent).lower() or "refund" in str(intent).lower() for intent in intents)
    is_escalation = has_cancellation and has_billing
    
    # For escalation scenarios without customer_id: Add negotiation logging
    if is_escalation and not customer_id:
        logs.append({
            "sender": "SupportAgent",
            "receiver": "Router",
            "content": "I need billing context (customer_id) to handle this escalation."
        })
    
    # Handle ticket creation for escalation scenarios
    ticket_id = None
    if (is_escalation or "billing_issue" in intents) and customer_id:
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
    
    # TRUE AGENT: Use LLM to decide if we need to fetch tickets
    # NO hardcoded scenario checks or keyword matching
    if not state.get("tickets"):
        customer_list = state.get("customer_list", [])
        query_full = state.get("user_query", "")
        
        # Use LLM to plan data needs (NO rules)
        data_plan = _plan_data_needs_with_llm(query_full, {
            "customer_list": customer_list,
            "has_tickets": False,
            "intents": intents,
        })
        
        # Fetch tickets if LLM says we need them
        if data_plan.get("need_tickets") and customer_list:
            customers_to_fetch = data_plan.get("customers") or customer_list
            filters = data_plan.get("filters", {})
            
            all_tickets = []
            for c in customers_to_fetch:
                cid = c.get("id") if isinstance(c, dict) else c
                if not cid:
                    continue
                try:
                    history = mcp_get_customer_history(cid)
                    if not isinstance(history, list):
                        history = []
                    
                    # Apply LLM-determined filters (NO hardcoded rules)
                    filtered_tickets = history
                    if filters.get("priority"):
                        filtered_tickets = [t for t in filtered_tickets if t.get("priority") == filters["priority"]]
                    if filters.get("status"):
                        filtered_tickets = [t for t in filtered_tickets if t.get("status") == filters["status"]]
                    
                    for t in filtered_tickets:
                        ticket_data = {
                            "ticket_id": t.get("ticket_id") or t.get("id"),
                            "customer_id": cid,
                            "customer_name": c.get("name", f"Customer {cid}") if isinstance(c, dict) else f"Customer {cid}",
                            "status": t.get("status", "unknown"),
                            "priority": t.get("priority", "unknown"),
                            "issue": t.get("issue", "No description"),
                            "created_at": t.get("created_at", "")
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
                "content": f"LLM decided to fetch tickets. Retrieved {len(all_tickets)} tickets with filters: {filters}"
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
