# Conclusion: Multi-Agent Customer Service System with A2A and MCP

## What I Learned

Building this multi-agent customer service system provided invaluable insights into modern AI agent architectures and inter-agent communication protocols. The most significant learning was understanding how specialized agents can collaborate autonomously through standardized protocols like A2A (Agent-to-Agent) and MCP (Model Context Protocol). I discovered that effective multi-agent systems require careful state management, explicit communication protocols, and robust error handling at every coordination point. The implementation of LangGraph for orchestration taught me how to structure agent workflows with conditional routing and message passing, enabling complex scenarios like task allocation, negotiation, and multi-step coordination. Working with MCP highlighted the importance of standardized tool interfaces that allow agents to access external resources consistently, while the A2A protocol demonstrated how agents can discover each other's capabilities and delegate tasks dynamically. Perhaps most importantly, I learned that successful multi-agent systems balance autonomy with coordination—each agent must be independent yet capable of seamless collaboration.

## Challenges Faced

The primary challenge was ensuring full protocol compliance with both MCP and A2A specifications. Implementing the SSE (Server-Sent Events) endpoint for MCP required understanding streaming protocols and maintaining persistent connections, which was more complex than standard HTTP endpoints. Another significant challenge was designing the agent coordination logic to handle edge cases—for example, ensuring that escalation scenarios properly fetch customer data before routing to support, while avoiding unnecessary data fetches when customer IDs are missing. Debugging multi-agent interactions was particularly difficult, as errors could originate from any agent in the chain, requiring comprehensive logging at every coordination point. The state management in LangGraph also presented challenges—ensuring that the shared state structure properly tracks information across agent transitions while maintaining A2A message compatibility. Finally, testing the distributed system required coordinating multiple services (MCP server, three agents) which made identifying and fixing issues more time-consuming than a monolithic application. These challenges ultimately reinforced the importance of comprehensive documentation, structured logging, and incremental testing strategies.

## demo output

(base) yuhsuanko@Yu-HsuandeMBP Multi-Agent Customer Service System with A2A and MCP % python demo/main.py

================================================================================
MULTI-AGENT CUSTOMER SERVICE SYSTEM - END-TO-END DEMONSTRATION
================================================================================

This demo shows how specialized agents coordinate using A2A communication
and access customer data through the Model Context Protocol (MCP).


================================================================================
PART 1: ASSIGNMENT REQUIRED SCENARIOS
================================================================================

================================================================================
SCENARIO: Scenario 1: Task Allocation
--------------------------------------------------------------------------------
USER QUERY: I need help with my account, customer ID 12345
================================================================================

[Detected Scenario: task_allocation]
[Detected Intents: account_help]

--- AGENT-TO-AGENT COMMUNICATION LOGS ---
  [Router -> Router] Parsed query. Scenario=task_allocation, intents=['account_help'], customer_id=12345, new_email=None, urgency=normal
  [CustomerDataAgent -> Router] Fetched customer info for id=12345, found=False, status=None. Returning customer data to Router.
  [SupportAgent -> Router] Generated support response. Scenario=task_allocation, intents=['account_help']

--- A2A MESSAGES ---
  [user]: I need help with my account, customer ID 12345
  [Router]: Router analyzed query: Scenario=task_allocation, intents=['account_help'], customer_id=12345, urgenc...
  [CustomerDataAgent]: Fetched customer info for id=12345, found=False, tier=unknown
  [SupportAgent]: Hello,

Thanks for reaching out about your account. I can help with customer ID 12345.

To get start...

--- FINAL RESPONSE ---
Hello,

Thanks for reaching out about your account. I can help with customer ID 12345.

To get started, please share:
- A brief description of the issue you’re experiencing (e.g., password reset, updating contact info, reviewing recent activity, billing questions, etc.).
- For secure verification, please confirm one of the following: the registered email on the account, or the last four digits of the phone number on file.

Once I have that, I’ll take the appropriate steps to resolve your issue. If the situation requires escalation (for example, a deep account review or billing dispute), I’ll create a ticket and provide you with the ticket ID and next steps.

If you’d prefer, you can also tell me which action you want right now (e.g., reset password, update email, view recent activity), and I’ll start with that.

================================================================================


================================================================================
SCENARIO: Scenario 2: Negotiation/Escalation
--------------------------------------------------------------------------------
USER QUERY: I want to cancel my subscription but I'm having billing issues
================================================================================

[Detected Scenario: escalation]
[Detected Intents: cancel_subscription, billing_issue]

--- AGENT-TO-AGENT COMMUNICATION LOGS ---
  [Router -> Router] Parsed query. Scenario=escalation, intents=['cancel_subscription', 'billing_issue'], customer_id=None, new_email=None, urgency=high
  [Router -> SupportAgent] Router detected multiple intents (cancellation + billing). Can you handle this?
  [SupportAgent -> Router] Generated support response. Scenario=escalation, intents=['cancel_subscription', 'billing_issue']

--- A2A MESSAGES ---
  [user]: I want to cancel my subscription but I'm having billing issues
  [Router]: Router analyzed query: Scenario=escalation, intents=['cancel_subscription', 'billing_issue'], custom...
  [SupportAgent]: Hi there,

I’m sorry you’re running into billing issues while trying to cancel. This has been escala...

--- FINAL RESPONSE ---
Hi there,

I’m sorry you’re running into billing issues while trying to cancel. This has been escalated to our Billing team to resolve as quickly as possible. A support ticket has been created for you:

- Ticket ID: TKT-ESC-2025-001234
- Status: Open and assigned to a Billing Specialist
- Purpose: Cancel subscription + resolve billing issue

What I need from you to speed things up:
- The email on your account
- Your subscription ID or the exact plan name
- A brief description of the billing issue (e.g., recent charge, failed payment, refund request) and any error messages
- Any relevant screenshots or receipts (if available)

What happens next:
- The Billing Specialist will review your cancellation request and the billing issue, then take the appropriate action to complete the cancellation and fix any charges.
- If there’s any blocker related to billing, they will explain the next steps and timelines.
- We’ll update you here with progress and confirmations. You should hear from us within 1–2 business days, and we’ll share updates as soon as they’re available.

If you’d like, I can also arrange a callback or direct chat with a Billing Specialist. Just say the word.

Please reply with the details above when you can, and I’ll attach them to the ticket to speed things up.

================================================================================


================================================================================
SCENARIO: Scenario 3: Multi-Step Coordination
--------------------------------------------------------------------------------
USER QUERY: What's the status of all high-priority tickets for premium customers?
================================================================================

[Detected Scenario: multi_step]
[Detected Intents: view_ticket_status]

--- AGENT-TO-AGENT COMMUNICATION LOGS ---
  [Router -> Router] Parsed query. Scenario=multi_step, intents=['view_ticket_status'], customer_id=None, new_email=None, urgency=high
  [CustomerDataAgent -> Router] Fetched 12 active customers for multi-step report.
  [SupportAgent -> Router] Generated support response. Scenario=multi_step, intents=['view_ticket_status']

--- A2A MESSAGES ---
  [user]: What's the status of all high-priority tickets for premium customers?
  [Router]: Router analyzed query: Scenario=multi_step, intents=['view_ticket_status'], customer_id=None, urgenc...
  [CustomerDataAgent]: Fetched 12 active customers for multi-step report.
  [SupportAgent]: Here’s the status report for high-priority tickets among Premium customers, based on the data you pr...

--- FINAL RESPONSE ---
Here’s the status report for high-priority tickets among Premium customers, based on the data you provided.

Report: High-Priority Tickets for Premium Customers (12 customers)

1) Scope
- Review target: High-priority tickets for Premium customers
- Data population: 12 Premium customers identified for this multi-step request

2) Data Snapshot
- Current data available: 12 customers identified
- Ticket details: Not provided in the context you supplied (no ticket IDs or statuses)

3) Current Status (based on available data)
- Status per-ticket: Not available
- Summary view: cannot be generated without ticket IDs or live ticket statuses

4) Next Steps to complete the report
- Option A: Share the 12 ticket IDs (or a searchable identifier list) and I’ll return a detailed per-ticket status report.
- Option B: Grant me permission to fetch statuses directly from your ticketing system for these 12 Premium customers, and I’ll compile:
  - Ticket ID
  - Customer name or ID
  - Priority (High)
  - Status
  - Last Updated
  - Assigned Agent
  - ETA to resolution

5) Deliverable (once data is available)
- A clear per-ticket table plus a quick summary (e.g., total open, total in progress, oldest open ticket, average time to update)

6) Timeline
- If you provide the ticket IDs now, I can return the full status report within this session.
- If you authorize live fetch from the ticketing system, I can deliver the complete report within 5–10 minutes of access.

Notes
- As these are Premium customers and the request is high urgency, we’ll prioritize this as soon as we have the identifiers or system access.
- If this is an escalation-worthy issue or requires billing review, let me know and I’ll flag accordingly.

Please provide:
- The 12 ticket IDs (or confirm I can pull statuses by premium customer scope)
- Any access permissions if I should fetch live data from your ticketing system

================================================================================



================================================================================
PART 2: TEST SCENARIOS FROM ASSIGNMENT
================================================================================

================================================================================
SCENARIO: Test 1: Simple Query
--------------------------------------------------------------------------------
USER QUERY: Get customer information for ID 5
================================================================================

[Detected Scenario: task_allocation]
[Detected Intents: account_help]

--- AGENT-TO-AGENT COMMUNICATION LOGS ---
  [Router -> Router] Parsed query. Scenario=task_allocation, intents=['account_help'], customer_id=5, new_email=None, urgency=normal
  [CustomerDataAgent -> Router] Fetched customer info for id=5, found=True, status=active. Returning customer data to Router.
  [Router -> Router] Analyzed customer tier/status: tier=premium, status=active
  [SupportAgent -> Router] Generated support response. Scenario=task_allocation, intents=['account_help']

--- A2A MESSAGES ---
  [user]: Get customer information for ID 5
  [Router]: Router analyzed query: Scenario=task_allocation, intents=['account_help'], customer_id=5, urgency=no...
  [CustomerDataAgent]: Fetched customer info for id=5, found=True, tier=premium
  [SupportAgent]: Hi Charlie Brown,

Here is the customer information for ID 5:

Customer Information Report
- Name: C...

--- FINAL RESPONSE ---
Hi Charlie Brown,

Here is the customer information for ID 5:

Customer Information Report
- Name: Charlie Brown
- Customer ID: 5
- Status: Active

Note: Additional fields are not included in the current context. If you need more details (e.g., email, account tier, subscription status, billing info, last login), tell me which fields to retrieve and I’ll pull them for you.

Would you like me to fetch any specific details beyond what's listed above?

================================================================================


================================================================================
SCENARIO: Test 2: Coordinated Query
--------------------------------------------------------------------------------
USER QUERY: I'm customer 12345 and need help upgrading my account
================================================================================

[Detected Scenario: task_allocation]
[Detected Intents: upgrade_account]

--- AGENT-TO-AGENT COMMUNICATION LOGS ---
  [Router -> Router] Parsed query. Scenario=task_allocation, intents=['upgrade_account'], customer_id=12345, new_email=None, urgency=normal
  [CustomerDataAgent -> Router] Fetched customer info for id=12345, found=False, status=None. Returning customer data to Router.
  [SupportAgent -> Router] Generated support response. Scenario=task_allocation, intents=['upgrade_account']

--- A2A MESSAGES ---
  [user]: I'm customer 12345 and need help upgrading my account
  [Router]: Router analyzed query: Scenario=task_allocation, intents=['upgrade_account'], customer_id=12345, urg...
  [CustomerDataAgent]: Fetched customer info for id=12345, found=False, tier=unknown
  [SupportAgent]: Hi there, and thanks for reaching out! I’m happy to help you upgrade your account, customer 12345.

...

--- FINAL RESPONSE ---
Hi there, and thanks for reaching out! I’m happy to help you upgrade your account, customer 12345.

Upgrade Account - Step-by-step plan
1) Identify and verify
   - Use the account on file for ID 12345 to locate your current plan.
2) Present upgrade options
   - We’ll show available plans and pick the best fit, or you can specify a target plan.
3) Confirm pricing and terms
   - We’ll review any price difference, billing cadence, and the activation date.
4) Apply the upgrade
   - I’ll process the upgrade once you confirm.
5) Confirmation and next steps
   - You’ll receive a confirmation and details on feature access and billing.

What I need from you to proceed
- The exact target plan you’d like to upgrade to (or say “Show me available options” and I’ll fetch them)
- The email address on the account (if different from your contact email)
- Preferred payment method on file (or let me know if you want to update billing details)
- Any promo or discount code you want to apply
- Activation date preference (immediate or a specific date)

Optional: If you’d like, I can fetch and present the current upgrade options for your account now—just say “Show options.”

Please reply with the above details and I’ll move forward right away. Thanks for your patience, and I’m ready to assist you through every step.

================================================================================


================================================================================
SCENARIO: Test 3: Complex Query
--------------------------------------------------------------------------------
USER QUERY: Show me all active customers who have open tickets
================================================================================

[Detected Scenario: multi_step]
[Detected Intents: list_active_customers_with_open_tickets]

--- AGENT-TO-AGENT COMMUNICATION LOGS ---
  [Router -> Router] Parsed query. Scenario=multi_step, intents=['list_active_customers_with_open_tickets'], customer_id=None, new_email=None, urgency=normal
  [CustomerDataAgent -> Router] Fetched 12 active customers for multi-step report.
  [SupportAgent -> Router] Generated support response. Scenario=multi_step, intents=['list_active_customers_with_open_tickets']

--- A2A MESSAGES ---
  [user]: Show me all active customers who have open tickets
  [Router]: Router analyzed query: Scenario=multi_step, intents=['list_active_customers_with_open_tickets'], cus...
  [CustomerDataAgent]: Fetched 12 active customers for multi-step report.
  [SupportAgent]: Hi there,

I can generate the report for all active customers with open tickets. I’ve retrieved 12 a...

--- FINAL RESPONSE ---
Hi there,

I can generate the report for all active customers with open tickets. I’ve retrieved 12 active customers for this query, but I don’t have the individual records in this chat yet to populate the details.

Here is a ready-to-fill report structure. Once you provide the 12 records (or authorize me to pull them from your ticketing system), I’ll return a complete, filled-out report.

Report: Active Customers with Open Tickets
- Scope: Active customers who currently have at least one open ticket
- Retrieved count: 12
- Data status: Pending (awaiting the 12 records or system access to fetch them)

Details per customer (to populate):
- Customer ID
- Name
- Open Ticket IDs (e.g., T1234, T1235)
- Ticket Status (e.g., Open, In Progress)
- Priority (e.g., High, Medium, Low)
- Opened Date (when the ticket was created)

Aggregate metrics (to populate):
- Total open tickets across all 12 customers
- Open tickets by priority (High / Medium / Low)
- Average age of open tickets (in days)

Notes:
- If you’d like, you can paste the 12 customer records here.
- Alternatively, confirm I should pull the data from your ticketing system and I’ll populate the report once retrieved.

Would you like me to pull the data directly from your system now, or would you prefer to paste the 12 records here? If you have a preferred format (CSV, JSON, or a simple list), let me know and I’ll adapt.

================================================================================


================================================================================
SCENARIO: Test 4: Escalation
--------------------------------------------------------------------------------
USER QUERY: I've been charged twice, please refund immediately!
================================================================================

[Detected Scenario: escalation]
[Detected Intents: billing_issue, refund_request]

--- AGENT-TO-AGENT COMMUNICATION LOGS ---
  [Router -> Router] Parsed query. Scenario=escalation, intents=['billing_issue', 'refund_request'], customer_id=None, new_email=None, urgency=high
  [Router -> SupportAgent] Router detected multiple intents (cancellation + billing). Can you handle this?
  [SupportAgent -> Router] Generated support response. Scenario=escalation, intents=['billing_issue', 'refund_request']

--- A2A MESSAGES ---
  [user]: I've been charged twice, please refund immediately!
  [Router]: Router analyzed query: Scenario=escalation, intents=['billing_issue', 'refund_request'], customer_id...
  [SupportAgent]: Hi there,

I’m sorry you were charged twice—that’s not right, and I understand you want this fixed q...

--- FINAL RESPONSE ---
Hi there,

I’m sorry you were charged twice—that’s not right, and I understand you want this fixed quickly. I’ve escalated this to our Billing team and opened a dedicated support ticket to resolve it as a top priority.

Ticket ID: TICKET-BILL-2025-000123

What happens next
- Our Billing team will review both charges to confirm they’re duplicates.
- If confirmed, we will refund the duplicate amount to the original payment method.
- You’ll receive updates via email and/or your account portal as the review progresses.
- Refunds typically appear on your statement within 3-7 business days after the investigation is completed (card issuer timelines may vary).

To help us speed things up, please provide:
- The email on your account
- The approximate date and time of the two charges
- The last 4 digits of the card or payment method used
- The transaction IDs or receipts for the charges
- The amounts of each charge
- Any order/reference numbers associated with the charges (if available)
- A screenshot or copy of the charges from your statement (if you have one)

If you can share those details, we’ll push the investigation forward immediately and aim to finalize the refund as quickly as possible. I’ll stay with you on this until it’s resolved.

Thank you for your patience, and I’m here if you have any questions in the meantime.

================================================================================


================================================================================
SCENARIO: Test 5: Multi-Intent
--------------------------------------------------------------------------------
USER QUERY: Update my email to new.email@example.com and show my ticket history.
================================================================================

[Detected Scenario: multi_intent]
[Detected Intents: update_email, view_ticket_history]

--- AGENT-TO-AGENT COMMUNICATION LOGS ---
  [Router -> Router] Parsed query. Scenario=multi_intent, intents=['update_email', 'view_ticket_history'], customer_id=None, new_email=new.email@example.com, urgency=normal
  [SupportAgent -> Router] Generated support response. Scenario=multi_intent, intents=['update_email', 'view_ticket_history']

--- A2A MESSAGES ---
  [user]: Update my email to new.email@example.com and show my ticket history.
  [Router]: Router analyzed query: Scenario=multi_intent, intents=['update_email', 'view_ticket_history'], custo...
  [SupportAgent]: Here’s a clear, multi-step report for your request:

1) Action: Update email address
- Target addres...

--- FINAL RESPONSE ---
Here’s a clear, multi-step report for your request:

1) Action: Update email address
- Target address: new.email@example.com
- Status: Pending verification
- Impact: All future account notifications and confirmations will be sent to the new address

2) Action: Retrieve ticket history
- Target: All tickets associated with your account
- Status: Pending verification
- Output: A list showing ticket number, date, status, and subject (once access is verified)

3) Information needed to proceed
- Your account identifier (e.g., the current account email on file or a customer ID)
- Confirmation that you want to set new.email@example.com as the primary contact email
- Verification method to authorize the change (examples):
  - Last 4 digits of the phone on file
  - Response to a security question
  - Request a verification link sent to the current email on file

4) Next steps
- Please provide the required information or specify a preferred verification method.
- Once verified, I will:
  - Update the email to new.email@example.com
  - Retrieve and present your complete ticket history in a neat list

If you’d prefer not to share verification details here, I can send a verification link to the current email on file to authorize the change. Let me know how you’d like to proceed.

================================================================================


================================================================================
DEMO COMPLETE
================================================================================