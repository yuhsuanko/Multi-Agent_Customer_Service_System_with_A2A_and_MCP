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
USER QUERY: I need help with my account, customer ID 1
================================================================================

[Detected Scenario: task_allocation]
[Detected Intents: account_help]

--- AGENT-TO-AGENT COMMUNICATION LOGS ---
  [Router -> Router] Parsed query. Scenario=task_allocation, intents=['account_help'], customer_id=1, new_email=None, urgency=normal
  [CustomerDataAgent -> Router] Fetched customer info for id=1, found=True, status=active. Returning customer data to Router.
  [Router -> Router] Analyzed customer tier/status: tier=premium, status=active
  [SupportAgent -> Router] Generated support response. Scenario=task_allocation, intents=['account_help']

--- A2A MESSAGES ---
  [user]: I need help with my account, customer ID 1
  [Router]: Router analyzed query: Scenario=task_allocation, intents=['account_help'], customer_id=1, urgency=no...
  [CustomerDataAgent]: Fetched customer info for id=1, found=True, tier=premium
  [SupportAgent]: Here is the information we have on file for customer #1:
- Name: John Doe
- Email: new.email@example...

--- FINAL RESPONSE ---
Here is the information we have on file for customer #1:
- Name: John Doe
- Email: new.email@example.com
- Phone: +1-555-0101
- Status: active

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
  [SupportAgent -> Router] I can help with this escalation, but I need the customer ID to proceed.
  [SupportAgent -> Router] Generated support response. Scenario=escalation, intents=['cancel_subscription', 'billing_issue']

--- A2A MESSAGES ---
  [user]: I want to cancel my subscription but I'm having billing issues
  [Router]: Router analyzed query: Scenario=escalation, intents=['cancel_subscription', 'billing_issue'], custom...
  [SupportAgent]: I can help with your billing issue, but I first need your customer ID to locate your account.

--- FINAL RESPONSE ---
I can help with your billing issue, but I first need your customer ID to locate your account.

================================================================================


================================================================================
SCENARIO: Scenario 3: Multi-Step Coordination
--------------------------------------------------------------------------------
USER QUERY: What's the status of all high-priority tickets for premium customers?
================================================================================

[Detected Scenario: multi_step]
[Detected Intents: high_priority_report, premium_customers]

--- AGENT-TO-AGENT COMMUNICATION LOGS ---
  [Router -> Router] Parsed query. Scenario=multi_step, intents=['high_priority_report', 'premium_customers'], customer_id=None, new_email=None, urgency=normal
  [CustomerDataAgent -> Router] Fetched 12 active customers for multi-step report.
  [SupportAgent -> Router] Compiled multi-step ticket report.
  [SupportAgent -> Router] Generated support response. Scenario=multi_step, intents=['high_priority_report', 'premium_customers']

--- A2A MESSAGES ---
  [user]: What's the status of all high-priority tickets for premium customers?
  [Router]: Router analyzed query: Scenario=multi_step, intents=['high_priority_report', 'premium_customers'], c...
  [CustomerDataAgent]: Fetched 12 active customers for multi-step report.
  [SupportAgent]: Here is the status of high-priority tickets for active customers:

Customer 1 (John Doe):
  - Ticket...

--- FINAL RESPONSE ---
Here is the status of high-priority tickets for active customers:

Customer 1 (John Doe):
  - Ticket 26 (open): Test issue created by MCP tool
  - Ticket 1 (open): Cannot login to account

Customer 2 (Jane Smith):
  - Ticket 30 (open): Billing issue with possible double charge and/or cancellation request
  - Ticket 29 (open): Billing issue with possible double charge and/or cancellation request
  - Ticket 28 (open): Billing problem with possible double charge and/or cancellation request
  - Ticket 27 (open): Billing issue with possible double charge and/or cancellation request

Customer 4 (Alice Williams):
  - Ticket 2 (in_progress): Database connection timeout errors

Customer 7 (Edward Norton):
  - Ticket 3 (open): Payment processing failing for all transactions

Customer 10 (Hannah Lee):
  - Ticket 4 (in_progress): Critical security vulnerability found

Customer 14 (Laura Martinez):
  - Ticket 5 (resolved): Website completely down

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
[Detected Intents: simple_customer_info]

--- AGENT-TO-AGENT COMMUNICATION LOGS ---
  [Router -> Router] Parsed query. Scenario=task_allocation, intents=['simple_customer_info'], customer_id=5, new_email=None, urgency=normal
  [CustomerDataAgent -> Router] Fetched customer info for id=5, found=True, status=active. Returning customer data to Router.
  [Router -> Router] Analyzed customer tier/status: tier=premium, status=active
  [SupportAgent -> Router] Generated support response. Scenario=task_allocation, intents=['simple_customer_info']

--- A2A MESSAGES ---
  [user]: Get customer information for ID 5
  [Router]: Router analyzed query: Scenario=task_allocation, intents=['simple_customer_info'], customer_id=5, ur...
  [CustomerDataAgent]: Fetched customer info for id=5, found=True, tier=premium
  [SupportAgent]: Here is the information we have on file for customer #5:
- Name: Charlie Brown
- Email: charlie.brow...

--- FINAL RESPONSE ---
Here is the information we have on file for customer #5:
- Name: Charlie Brown
- Email: charlie.brown@email.com
- Phone: +1-555-0105
- Status: active

================================================================================


================================================================================
SCENARIO: Test 2: Coordinated Query
--------------------------------------------------------------------------------
USER QUERY: I'm customer 12345 and need help upgrading my account
================================================================================

[Detected Scenario: coordinated]
[Detected Intents: general_support]

--- AGENT-TO-AGENT COMMUNICATION LOGS ---
  [Router -> Router] Parsed query. Scenario=coordinated, intents=['general_support'], customer_id=12345, new_email=None, urgency=normal
  [CustomerDataAgent -> Router] Fetched customer info for coordinated scenario, id=12345.
  [SupportAgent -> Router] Generated support response. Scenario=coordinated, intents=['general_support']

--- A2A MESSAGES ---
  [user]: I'm customer 12345 and need help upgrading my account
  [Router]: Router analyzed query: Scenario=coordinated, intents=['general_support'], customer_id=12345, urgency...
  [CustomerDataAgent]: Fetched customer info for coordinated scenario, id=12345.
  [SupportAgent]: I am here to help. Could you please provide more details about your issue?

--- FINAL RESPONSE ---
I am here to help. Could you please provide more details about your issue?

================================================================================


================================================================================
SCENARIO: Test 3: Complex Query
--------------------------------------------------------------------------------
USER QUERY: Show me all active customers who have open tickets
================================================================================

[Detected Scenario: multi_step]
[Detected Intents: active_with_open_tickets]

--- AGENT-TO-AGENT COMMUNICATION LOGS ---
  [Router -> Router] Parsed query. Scenario=multi_step, intents=['active_with_open_tickets'], customer_id=None, new_email=None, urgency=normal
  [CustomerDataAgent -> Router] Fetched 12 active customers for multi-step report.
  [SupportAgent -> Router] Compiled multi-step ticket report.
  [SupportAgent -> Router] Generated support response. Scenario=multi_step, intents=['active_with_open_tickets']

--- A2A MESSAGES ---
  [user]: Show me all active customers who have open tickets
  [Router]: Router analyzed query: Scenario=multi_step, intents=['active_with_open_tickets'], customer_id=None, ...
  [CustomerDataAgent]: Fetched 12 active customers for multi-step report.
  [SupportAgent]: Here are all active customers who currently have open tickets:

Customer 1 (John Doe):
  - Ticket 26...

--- FINAL RESPONSE ---
Here are all active customers who currently have open tickets:

Customer 1 (John Doe):
  - Ticket 26 (priority=high): Test issue created by MCP tool
  - Ticket 1 (priority=high): Cannot login to account

Customer 2 (Jane Smith):
  - Ticket 30 (priority=high): Billing issue with possible double charge and/or cancellation request
  - Ticket 29 (priority=high): Billing issue with possible double charge and/or cancellation request
  - Ticket 28 (priority=high): Billing problem with possible double charge and/or cancellation request
  - Ticket 27 (priority=high): Billing issue with possible double charge and/or cancellation request
  - Ticket 15 (priority=low): Feature request: dark mode

Customer 4 (Alice Williams):
  - Ticket 24 (priority=low): Feature request: integration with Slack

Customer 5 (Charlie Brown):
  - Ticket 8 (priority=medium): Email notifications not being received

Customer 6 (Diana Prince):
  - Ticket 18 (priority=low): Request for additional language support

Customer 7 (Edward Norton):
  - Ticket 3 (priority=high): Payment processing failing for all transactions

Customer 9 (George Miller):
  - Ticket 10 (priority=medium): Export to CSV feature broken

Customer 10 (Hannah Lee):
  - Ticket 25 (priority=low): Suggestion: add keyboard shortcuts

Customer 11 (Isaac Newton):
  - Ticket 20 (priority=low): Feature request: export to PDF

Customer 12 (Julia Roberts):
  - Ticket 21 (priority=low): Color scheme suggestion for better contrast

Customer 15 (Michael Scott):
  - Ticket 13 (priority=medium): API rate limiting too restrictive

================================================================================


================================================================================
SCENARIO: Test 4: Escalation
--------------------------------------------------------------------------------
USER QUERY: I've been charged twice, please refund immediately!
================================================================================

[Detected Scenario: coordinated]
[Detected Intents: billing_issue]

--- AGENT-TO-AGENT COMMUNICATION LOGS ---
  [Router -> Router] Parsed query. Scenario=coordinated, intents=['billing_issue'], customer_id=None, new_email=None, urgency=high
  [SupportAgent -> Router] I can help with this escalation, but I need the customer ID to proceed.
  [SupportAgent -> Router] Generated support response. Scenario=coordinated, intents=['billing_issue']

--- A2A MESSAGES ---
  [user]: I've been charged twice, please refund immediately!
  [Router]: Router analyzed query: Scenario=coordinated, intents=['billing_issue'], customer_id=None, urgency=hi...
  [SupportAgent]: I can help with your billing issue, but I first need your customer ID to locate your account.

--- FINAL RESPONSE ---
I can help with your billing issue, but I first need your customer ID to locate your account.

================================================================================


================================================================================
SCENARIO: Test 5: Multi-Intent
--------------------------------------------------------------------------------
USER QUERY: Update my email to new.email@example.com and show my ticket history.
================================================================================

[Detected Scenario: multi_intent]
[Detected Intents: update_email, ticket_history]

--- AGENT-TO-AGENT COMMUNICATION LOGS ---
  [Router -> Router] Parsed query. Scenario=multi_intent, intents=['update_email', 'ticket_history'], customer_id=None, new_email=new.email@example.com, urgency=normal
  [SupportAgent -> Router] Generated support response. Scenario=multi_intent, intents=['update_email', 'ticket_history']

--- A2A MESSAGES ---
  [user]: Update my email to new.email@example.com and show my ticket history.
  [Router]: Router analyzed query: Scenario=multi_intent, intents=['update_email', 'ticket_history'], customer_i...
  [SupportAgent]: I have updated your email address to: new.email@example.com.

Here is your recent ticket history:

Y...

--- FINAL RESPONSE ---
I have updated your email address to: new.email@example.com.

Here is your recent ticket history:

You currently have no tickets on file.

================================================================================


================================================================================
DEMO COMPLETE
================================================================================
