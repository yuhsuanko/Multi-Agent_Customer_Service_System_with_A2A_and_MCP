# agents/support_agent.py
"""
Support Agent.

Responsibilities:
- Interpret intents + structured data in CSState
- Optionally create tickets via MCP (e.g., escalation / billing issues)
- Generate a user-facing response
- Add A2A log entries describing what it did

For simplicity, the response is rule-based text.
In a real system, this is where you might call an LLM.
"""

from typing import List, Dict, Any

from .state import CSState, AgentMessage
from .mcp_client import mcp_create_ticket, mcp_get_customer_history


def _summarize_ticket_history(tickets: List[Dict[str, Any]]) -> str:
    """
    Build a human-readable summary of past tickets.
    """
    if not tickets:
        return "You currently have no tickets on file."

    lines = []
    for t in tickets:
        lines.append(
            f"- Ticket {t['ticket_id']}: {t['issue']} "
            f"({t['status']}, priority={t['priority']})"
        )
    return "\n".join(lines)


def support_agent_node(state: CSState) -> CSState:
    """
    Support agent node.

    Uses scenario + intents to decide what actions to take and what
    response to generate. Also creates tickets for escalation cases.
    """
    messages = state.get("messages", [])
    logs = state.get("logs", [])
    scenario = state.get("scenario", "coordinated")
    intents = state.get("intents", [])
    customer_id = state.get("customer_id")
    customer = state.get("customer_data")
    urgency = state.get("urgency", "normal")

    response_parts: List[str] = []

    # Scenario 2: Negotiation/Escalation (cancel + billing issue, or urgent billing)
    if scenario == "escalation" or "billing_issue" in intents:
        # Negotiation flow: Support Agent needs billing context
        if customer_id is not None:
            # Check if we have customer data (billing context)
            if not customer:
                # Support Agent → Router: "I need billing context"
                logs.append(AgentMessage(
                    sender="SupportAgent",
                    receiver="Router",
                    content="I need billing context to handle this escalation properly. Requesting customer data."
                ))
                # Response will be generated after data is fetched in next pass
                response_parts.append(
                    "I can handle this escalation, but I need billing context first. "
                    "Let me request your customer information."
                )
            else:
                # We have billing context, can proceed
                ticket_result = mcp_create_ticket(
                    customer_id=customer_id,
                    issue="Billing issue with possible double charge and/or cancellation request",
                    priority="high",
                )
                
                # Personalize response if customer data is available
                greeting = ""
                if customer and customer.get("found"):
                    greeting = f"Hi {customer.get('name', 'there')}, "
                
                logs.append(AgentMessage(
                    sender="SupportAgent",
                    receiver="Router",
                    content=f"Created high-priority ticket for escalation. Result={ticket_result}"
                ))
                response_parts.append(
                    f"{greeting}I see that you are having billing issues. "
                    "I have created a high-priority ticket so our billing team can review your charges "
                    "and process any necessary refund.\n"
                    f"Your ticket ID is {ticket_result.get('ticket_id')}."
                )
        else:
            logs.append(AgentMessage(
                sender="SupportAgent",
                receiver="Router",
                content="I can help with this escalation, but I need the customer ID to proceed."
            ))
            response_parts.append(
                "I can help with your billing issue, but I first need your customer ID "
                "to locate your account."
            )

    # Scenario 1: Task allocation / simple customer info
    if scenario == "task_allocation":
        customer_tier = state.get("customer_tier", "unknown")
        if customer and customer.get("found"):
            # Router has analyzed customer tier, Support Agent handles accordingly
            tier_message = ""
            if customer_tier == "premium":
                tier_message = "\n\nI see you are a premium customer. "
                logs.append(AgentMessage(
                    sender="SupportAgent",
                    receiver="Router",
                    content=f"Handling support for premium customer (ID: {customer.get('id')})"
                ))
            elif customer_tier == "standard":
                logs.append(AgentMessage(
                    sender="SupportAgent",
                    receiver="Router",
                    content=f"Handling support for standard customer (ID: {customer.get('id')})"
                ))
            
            response_parts.append(
                f"{tier_message}Here is the information we have on file for customer #{customer['id']}:\n"
                f"- Name: {customer['name']}\n"
                f"- Email: {customer['email']}\n"
                f"- Phone: {customer['phone']}\n"
                f"- Status: {customer['status']}"
            )
        else:
            response_parts.append(
                "I was not able to find a customer with that ID. "
                "Please check the number and try again."
            )

    # Coordinated scenario: upgrading an account
    if scenario == "coordinated" and "upgrade_account" in intents:
        if customer and customer.get("found"):
            response_parts.append(
                f"Hi {customer['name']}, I can help you upgrade your account.\n"
                "Based on your current status, you are eligible for our premium tier.\n"
                "Would you like me to proceed with the upgrade now?"
            )
        else:
            response_parts.append(
                "I can help you upgrade your account, but I could not find your customer record. "
                "Please provide your customer ID."
            )

    # Multi-intent scenario: update email + ticket history
    if scenario == "multi_intent":
        if "update_email" in intents and state.get("new_email"):
            response_parts.append(
                f"I have updated your email address to: {state['new_email']}."
            )
        if "ticket_history" in intents:
            tickets = state.get("tickets", [])
            response_parts.append("Here is your recent ticket history:")
            response_parts.append(_summarize_ticket_history(tickets))

    # Scenario 3: Multi-step coordination
    if scenario == "multi_step":
        customers = state.get("customer_list", [])
        entries: List[str] = []

        # If the intent is "high_priority_report": high-priority tickets for active/premium customers
        if "high_priority_report" in intents:
            for c in customers:
                cid = c["id"]
                history = mcp_get_customer_history(cid)
                high_tickets = [t for t in history if t["priority"] == "high"]
                if high_tickets:
                    entry = f"Customer {cid} ({c['name']}):"
                    for ht in high_tickets:
                        entry += f"\n  - Ticket {ht['ticket_id']} ({ht['status']}): {ht['issue']}"
                    entries.append(entry)

            if entries:
                response_parts.append(
                    "Here is the status of high-priority tickets for active customers:\n\n"
                    + "\n\n".join(entries)
                )
            else:
                response_parts.append(
                    "There are currently no high-priority tickets for active customers."
                )

        # If the intent is "active_with_open_tickets": active customers who have open tickets
        if "active_with_open_tickets" in intents:
            for c in customers:
                cid = c["id"]
                history = mcp_get_customer_history(cid)
                open_tickets = [t for t in history if t["status"] == "open"]
                if open_tickets:
                    entry = f"Customer {cid} ({c['name']}):"
                    for ot in open_tickets:
                        entry += f"\n  - Ticket {ot['ticket_id']} (priority={ot['priority']}): {ot['issue']}"
                    entries.append(entry)

            if entries:
                response_parts.append(
                    "Here are all active customers who currently have open tickets:\n\n"
                    + "\n\n".join(entries)
                )
            else:
                response_parts.append(
                    "There are no active customers with open tickets at the moment."
                )

        logs.append(AgentMessage(
            sender="SupportAgent",
            receiver="Router",
            content="Compiled multi-step ticket report."
        ))

    # Fallback: general support (if nothing else matched)
    if not response_parts:
        if urgency == "high":
            response_parts.append(
                "I understand this is urgent. I will create a high-priority ticket "
                "for our support team to review your issue as quickly as possible."
            )
            if customer_id is not None:
                ticket_result = mcp_create_ticket(
                    customer_id=customer_id,
                    issue="Urgent issue reported by customer",
                    priority="high",
                )
                response_parts.append(f"Your ticket ID is {ticket_result.get('ticket_id')}.")
        else:
            response_parts.append(
                "I am here to help. Could you please provide more details about your issue?"
            )

    final_response = "\n\n".join(response_parts)
    state["support_response"] = final_response
    state["done"] = True

    # Add final response to messages
    messages.append({
        "role": "assistant",
        "name": "SupportAgent",
        "content": final_response
    })

    logs.append(AgentMessage(
        sender="SupportAgent",
        receiver="Router",
        content=f"Generated support response. Scenario={scenario}, intents={intents}"
    ))
    state["messages"] = messages
    state["logs"] = logs

    return state
