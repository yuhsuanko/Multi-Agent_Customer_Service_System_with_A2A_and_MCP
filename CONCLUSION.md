# Conclusion: Multi-Agent Customer Service System with A2A and MCP

## What I Learned

Building this multi-agent customer service system provided insights into AI agent architectures and inter-agent communication protocols. The most significant learning was understanding how specialized agents can collaborate autonomously through standardized protocols like A2A and MCP. I discovered that effective multi-agent systems require careful state management, explicit communication protocols, and robust error handling at every coordination point. The implementation of LangGraph for orchestration taught me how to structure agent workflows with conditional routing and message passing, enabling complex scenarios like task allocation, negotiation, and multi-step coordination. Working with MCP highlighted the importance of standardized tool interfaces that allow agents to access external resources consistently, while the A2A protocol demonstrated how agents can discover each other's capabilities and delegate tasks dynamically. Perhaps most importantly, I learned that successful multi-agent systems balance autonomy with coordination—each agent must be independent yet capable of seamless collaboration.

## Challenges Faced

The primary challenge was ensuring full protocol compliance with both MCP and A2A specifications. Implementing the SSE endpoint for MCP required understanding streaming protocols and maintaining persistent connections, which was more complex than standard HTTP endpoints. Another significant challenge was designing the agent coordination logic to handle edge cases—for example, ensuring that escalation scenarios properly fetch customer data before routing to support, while avoiding unnecessary data fetches when customer IDs are missing. Debugging multi-agent interactions was particularly difficult, as errors could originate from any agent in the chain, requiring comprehensive logging at every coordination point. The state management in LangGraph also presented challenges—ensuring that the shared state structure properly tracks information across agent transitions while maintaining A2A message compatibility. Finally, testing the distributed system required coordinating multiple services (MCP server, three agents) which made identifying and fixing issues more time-consuming than a monolithic application. These challenges ultimately reinforced the importance of comprehensive documentation, structured logging, and incremental testing strategies.

## demo output

(base) yuhsuanko@Yu-HsuandeMBP Multi-Agent Customer Service System with A2A and MCP % python demo/main.py

================================================================================
MULTI-AGENT CUSTOMER SERVICE SYSTEM - END-TO-END DEMONSTRATION
================================================================================

This demo uses LangGraph SDK directly to execute the multi-agent workflow.
The workflow orchestrates agents that communicate via A2A protocol:
1. LangGraph SDK builds and executes workflow
2. Router Agent (in workflow) → Customer Data Agent (A2A)
3. Router Agent (in workflow) → Support Agent (A2A)
4. Workflow returns final response

NOTE: This demo uses LangGraph SDK (StateGraph) as required.
Agents are independent services with A2A endpoints.
LangGraph SDK is available
[Building LangGraph workflow using SDK...]
LangGraph workflow built successfully


================================================================================
PART 1: ASSIGNMENT REQUIRED SCENARIOS
================================================================================

================================================================================
SCENARIO: Scenario 1: Task Allocation
--------------------------------------------------------------------------------
USER QUERY: I need help with my account, customer ID 12345
================================================================================

[Building LangGraph workflow using SDK...]
[Executing LangGraph workflow...]

[Detected Scenario: unknown]
[Detected Intents: get_customer_info]

--- AGENT-TO-AGENT COMMUNICATION LOGS ---
  [Router -> Router] Parsed query. intents=['get_customer_info'], customer_id=12345, new_email=None, urgency=normal
  [Router -> data_agent] Routing decision: To address the user's account question for customer 12345, we need to retrieve the customer's stored data and ticket history before responding.
  [CustomerDataAgent -> Router] Fetched customer info for id=12345, found=False, status=None. Returning customer data to Router.
  [SupportAgent -> Router] Generated support response. Scenario=coordinated, intents=['get_customer_info']

--- FINAL RESPONSE ---
Hello! I can help with your account for Customer ID 12345.

To securely pull up your information, please confirm:
- The full name on the account
- The email address on file

Once you verify, I’ll fetch:
- Account status and current plan
- Billing summary (balance, upcoming charges, next due date)
- Recent activity
- Your ticket history (and any open tickets, if applicable)

If there are specific details you want included (e.g., last login, recent charges, or open tickets), let me know and I’ll include them.

================================================================================


================================================================================
SCENARIO: Scenario 2: Negotiation/Escalation
--------------------------------------------------------------------------------
USER QUERY: I want to cancel my subscription but I'm having billing issues
================================================================================

[Building LangGraph workflow using SDK...]
[Executing LangGraph workflow...]

[Detected Scenario: unknown]
[Detected Intents: cancel_subscription, billing_issue]

--- AGENT-TO-AGENT COMMUNICATION LOGS ---
  [Router -> Router] Parsed query. intents=['cancel_subscription', 'billing_issue'], customer_id=None, new_email=None, urgency=normal
  [Router -> SupportAgent] Router detected multiple intents (cancellation + billing). Can you handle this?
  [Router -> data_agent] Routing decision: The user wants to cancel a subscription and has billing issues, but we have no customer identifiers or account data. We must fetch the customer's account, subscription status, and billing history before proceeding.
  [SupportAgent -> Router] I need billing context (customer_id) to handle this escalation.
  [SupportAgent -> Router] Generated support response. Scenario=coordinated, intents=['cancel_subscription', 'billing_issue']

--- FINAL RESPONSE ---
I’m sorry you’re hitting billing issues while trying to cancel. I can help with both canceling your subscription and investigating the charges.

What I can do for you
- Cancel your subscription now or specify end of the current billing period.
- Open a billing issue ticket to investigate the charge(s) and ensure any due adjustments are handled.

What I need from you to proceed
- Account email or username (the one tied to the subscription)
- Subscription ID or the exact plan name
- Do you want the cancellation effective immediately or at the end of the current billing cycle?
- A brief note on the billing issue (e.g., unexpected charge, duplicate charge, failed payment, etc.)
- Optional: any relevant invoices or screenshots

Would you like me to:
- Cancel now and simultaneously open a billing issue ticket for you? If you say yes, I’ll generate a reference number and keep you updated, or
- Cancel at the end of the current period and then start the billing investigation after that?

Please reply with the details above and your preferred option, and I’ll get everything processed right away.

================================================================================


================================================================================
SCENARIO: Scenario 3: Multi-Step Coordination
--------------------------------------------------------------------------------
USER QUERY: What's the status of all high-priority tickets for premium customers?
================================================================================

[Building LangGraph workflow using SDK...]
[Executing LangGraph workflow...]

[Detected Scenario: unknown]
[Detected Intents: get_ticket_status, filter_tickets_by_priority_and_customer_type]

--- AGENT-TO-AGENT COMMUNICATION LOGS ---
  [Router -> Router] Parsed query. intents=['get_ticket_status', 'filter_tickets_by_priority_and_customer_type'], customer_id=None, new_email=None, urgency=normal
  [Router -> data_agent] Routing decision: The request requires identifying premium customers and their tickets; current state lacks customer data, customer list, and ticket data.
  [CustomerDataAgent -> Router] Fetched 12 active customers for multi-step report.
  [SupportAgent -> Router] LLM decided to fetch tickets. Retrieved 10 tickets with filters: {'priority': 'high'}
  [SupportAgent -> Router] Generated support response. Scenario=coordinated, intents=['get_ticket_status', 'filter_tickets_by_priority_and_customer_type']

--- FINAL RESPONSE ---
Here are the high-priority tickets for premium customers, as retrieved:

- Ticket ID: 26 | Customer: John Doe (ID: 1) | Status: open | Priority: high | Issue: Test issue created by MCP tool
- Ticket ID: 1 | Customer: John Doe (ID: 1) | Status: open | Priority: high | Issue: Cannot login to account
- Ticket ID: 30 | Customer: Jane Smith (ID: 2) | Status: open | Priority: high | Issue: Billing issue with possible double charge and/or cancellation request
- Ticket ID: 29 | Customer: Jane Smith (ID: 2) | Status: open | Priority: high | Issue: Billing issue with possible double charge and/or cancellation request
- Ticket ID: 28 | Customer: Jane Smith (ID: 2) | Status: open | Priority: high | Issue: Billing problem with possible double charge and/or cancellation request
- Ticket ID: 27 | Customer: Jane Smith (ID: 2) | Status: open | Priority: high | Issue: Billing issue with possible double charge and/or cancellation request
- Ticket ID: 2 | Customer: Alice Williams (ID: 4) | Status: in_progress | Priority: high | Issue: Database connection timeout errors
- Ticket ID: 3 | Customer: Edward Norton (ID: 7) | Status: open | Priority: high | Issue: Payment processing failing for all transactions
- Ticket ID: 4 | Customer: Hannah Lee (ID: 10) | Status: in_progress | Priority: high | Issue: Critical security vulnerability found
- Ticket ID: 5 | Customer: Laura Martinez (ID: 14) | Status: resolved | Priority: high | Issue: Website completely down

If you’d like, I can also summarize how many are open vs in progress vs resolved, or pull any additional details for specific tickets.

================================================================================



================================================================================
PART 2: TEST SCENARIOS FROM ASSIGNMENT
================================================================================

================================================================================
SCENARIO: Test 1: Simple Query
--------------------------------------------------------------------------------
USER QUERY: Get customer information for ID 5
================================================================================

[Building LangGraph workflow using SDK...]
[Executing LangGraph workflow...]

[Detected Scenario: unknown]
[Detected Intents: get_customer_info]

--- AGENT-TO-AGENT COMMUNICATION LOGS ---
  [Router -> Router] Parsed query. intents=['get_customer_info'], customer_id=5, new_email=None, urgency=normal
  [Router -> data_agent] Routing decision: Customer data for ID 5 is not loaded; retrieve the full customer record using data_agent.
  [CustomerDataAgent -> Router] Fetched customer info for id=5, found=True, status=active. Returning customer data to Router.
  [Router -> Router] Analyzed customer tier/status: tier=premium, status=active
  [SupportAgent -> Router] Generated support response. Scenario=coordinated, intents=['get_customer_info']

--- FINAL RESPONSE ---
Hi there,

Here’s the information I have for Charlie Brown (ID: 5):
- Name: Charlie Brown
- ID: 5
- Status: Active
- Ticket history: not retrieved yet

Would you like me to pull Charlie’s full profile details (email, phone, address, account plan, billing cycle) and their ticket history? I can fetch and present a structured summary, for example:
- Profile: Email, Phone, Address, Plan, Billing Cycle
- Tickets: List of all tickets with Ticket ID, Status, Priority, and Issue

Please tell me which details you’d like included, and I’ll fetch them right away.

================================================================================


================================================================================
SCENARIO: Test 2: Coordinated Query
--------------------------------------------------------------------------------
USER QUERY: I'm customer 12345 and need help upgrading my account
================================================================================

[Building LangGraph workflow using SDK...]
[Executing LangGraph workflow...]

[Detected Scenario: unknown]
[Detected Intents: upgrade_account]

--- AGENT-TO-AGENT COMMUNICATION LOGS ---
  [Router -> Router] Parsed query. intents=['upgrade_account'], customer_id=12345, new_email=None, urgency=normal
  [Router -> data_agent] Routing decision: We need to retrieve the customer's existing account information and eligibility before processing an upgrade.
  [CustomerDataAgent -> Router] Fetched customer info for id=12345, found=False, status=None. Returning customer data to Router.
  [SupportAgent -> Router] Generated support response. Scenario=coordinated, intents=['upgrade_account']

--- FINAL RESPONSE ---
Hi there! I can help you upgrade your account.

To get you set up, could you please share:
- Which plan you want to upgrade to (or the features you need, e.g., more storage, more users, premium support)?
- Your preferred billing frequency (monthly or yearly)?
- Do you want me to proceed using the payment method on file, or would you like to review options first?

If you’re not sure which plan is best, I can outline the differences once you tell me the features you need.

Once you confirm, I’ll take care of the upgrade right away and send you a confirmation.

================================================================================


================================================================================
SCENARIO: Test 3: Complex Query
--------------------------------------------------------------------------------
USER QUERY: Show me all active customers who have open tickets
================================================================================

[Building LangGraph workflow using SDK...]
[Executing LangGraph workflow...]

[Detected Scenario: unknown]
[Detected Intents: retrieve_active_customers_with_open_tickets]

--- AGENT-TO-AGENT COMMUNICATION LOGS ---
  [Router -> Router] Parsed query. intents=['retrieve_active_customers_with_open_tickets'], customer_id=None, new_email=None, urgency=normal
  [Router -> data_agent] Routing decision: To identify all active customers with open tickets, we must fetch the customer list and their ticket histories/status via MCP tools.
  [CustomerDataAgent -> Router] Fetched 12 active customers for multi-step report.
  [SupportAgent -> Router] LLM decided to fetch tickets. Retrieved 16 tickets with filters: {'status': 'open'}
  [SupportAgent -> Router] Generated support response. Scenario=coordinated, intents=['retrieve_active_customers_with_open_tickets']

--- FINAL RESPONSE ---
Hello,

Here’s what you requested.

Active customers who have open tickets:
- John Doe (ID: 1)
- Jane Smith (ID: 2)
- Alice Williams (ID: 4)
- Charlie Brown (ID: 5)
- Diana Prince (ID: 6)
- Edward Norton (ID: 7)
- George Miller (ID: 9)
- Hannah Lee (ID: 10)
- Isaac Newton (ID: 11)
- Julia Roberts (ID: 12)
- Michael Scott (ID: 15)

Open tickets for premium customers (listed with exact IDs and details):
- Ticket ID: 26 | Customer: John Doe (ID: 1) | Status: open | Priority: high | Issue: Test issue created by MCP tool
- Ticket ID: 1 | Customer: John Doe (ID: 1) | Status: open | Priority: high | Issue: Cannot login to account
- Ticket ID: 30 | Customer: Jane Smith (ID: 2) | Status: open | Priority: high | Issue: Billing issue with possible double charge and/or cancellation request
- Ticket ID: 29 | Customer: Jane Smith (ID: 2) | Status: open | Priority: high | Issue: Billing issue with possible double charge and/or cancellation request
- Ticket ID: 28 | Customer: Jane Smith (ID: 2) | Status: open | Priority: high | Issue: Billing problem with possible double charge and/or cancellation request
- Ticket ID: 27 | Customer: Jane Smith (ID: 2) | Status: open | Priority: high | Issue: Billing issue with possible double charge and/or cancellation request
- Ticket ID: 15 | Customer: Jane Smith (ID: 2) | Status: open | Priority: low | Issue: Feature request: dark mode
- Ticket ID: 24 | Customer: Alice Williams (ID: 4) | Status: open | Priority: low | Issue: Feature request: integration with Slack
- Ticket ID: 8 | Customer: Charlie Brown (ID: 5) | Status: open | Priority: medium | Issue: Email notifications not being received
- Ticket ID: 18 | Customer: Diana Prince (ID: 6) | Status: open | Priority: low | Issue: Request for additional language support
- Ticket ID: 3 | Customer: Edward Norton (ID: 7) | Status: open | Priority: high | Issue: Payment processing failing for all transactions
- Ticket ID: 10 | Customer: George Miller (ID: 9) | Status: open | Priority: medium | Issue: Export to CSV feature broken
- Ticket ID: 25 | Customer: Hannah Lee (ID: 10) | Status: open | Priority: low | Issue: Suggestion: add keyboard shortcuts
- Ticket ID: 20 | Customer: Isaac Newton (ID: 11) | Status: open | Priority: low | Issue: Feature request: export to PDF
- Ticket ID: 21 | Customer: Julia Roberts (ID: 12) | Status: open | Priority: low | Issue: Color scheme suggestion for better contrast
- Ticket ID: 13 | Customer: Michael Scott (ID: 15) | Status: open | Priority: medium | Issue: API rate limiting too restrictive

If you’d like, I can filter or export these into a report, or open a support ticket to follow up on any specific item.

================================================================================


================================================================================
SCENARIO: Test 4: Escalation
--------------------------------------------------------------------------------
USER QUERY: I've been charged twice, please refund immediately!
================================================================================

[Building LangGraph workflow using SDK...]
[Executing LangGraph workflow...]

[Detected Scenario: unknown]
[Detected Intents: refund, billing_dispute]

--- AGENT-TO-AGENT COMMUNICATION LOGS ---
  [Router -> Router] Parsed query. intents=['refund', 'billing_dispute'], customer_id=None, new_email=None, urgency=high
  [Router -> data_agent] Routing decision: Cannot process refund without identifying the customer and locating the duplicate charge. No customer_id or billing data is available yet.
  [SupportAgent -> Router] Generated support response. Scenario=coordinated, intents=['refund', 'billing_dispute']

--- FINAL RESPONSE ---
I’m really sorry about the double charge—that’s not what you should experience. I’ve created a high-priority refund ticket so our Billing team can investigate and issue a refund as quickly as possible.

To help us process this faster, please reply with:
- The transaction/order ID or invoice number for each charge
- The date of each charge and the amounts (the two charges)
- The last four digits of the card used (or the payment method)
- The email on your account and the billing address on file
- A screenshot or copy of the charges if you have it
- Confirm that you want the refunds issued to the original payment method

What happens next:
- You’ll receive updates on the ticket status via email.
- If we need any more information, we’ll reach out right away.
- Refunds typically appear on your original payment method within 5–10 business days, depending on your bank. We’ll do our best to expedite the process.

If you’d like, you can send the above details here and I’ll attach them to the ticket for you. Again, I’m sorry for the hassle—we’ll get this sorted as soon as possible.

================================================================================


================================================================================
SCENARIO: Test 5: Multi-Intent
--------------------------------------------------------------------------------
USER QUERY: Update my email to new.email@example.com and show my ticket history.
================================================================================

[Building LangGraph workflow using SDK...]
[Executing LangGraph workflow...]

[Detected Scenario: unknown]
[Detected Intents: update_email, view_ticket_history]

--- AGENT-TO-AGENT COMMUNICATION LOGS ---
  [Router -> Router] Parsed query. intents=['update_email', 'view_ticket_history'], customer_id=None, new_email=new.email@example.com, urgency=normal
  [Router -> data_agent] Routing decision: No customer_id or customer data available. To update the email and fetch ticket history, we must identify the customer and retrieve their ticket history using the data_agent.
  [SupportAgent -> Router] Generated support response. Scenario=coordinated, intents=['update_email', 'view_ticket_history']

--- FINAL RESPONSE ---
Hi there! I can help with updating your email to new.email@example.com and pulling up your ticket history.

To proceed, I’ll need to verify your account. Could you please confirm or provide:
- Your full name as it appears on the account
- The current email on file (if you know it)
- Your Customer ID (if you have it)
- Confirm the new email address: new.email@example.com

What happens next after verification:
- I will update your email to the new address and send a verification to new.email@example.com (if required by our system).
- I will then retrieve your ticket history and present it clearly, including:
  - Ticket ID
  - Customer ID / Name
  - Status
  - Priority
  - Issue description

If you prefer, you can share just what you’re comfortable with, and I’ll guide you through the rest.

================================================================================


================================================================================
DEMO COMPLETE
================================================================================