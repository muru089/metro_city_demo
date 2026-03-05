"""
agent.py -- Metro City Internet: Uber Agent (Entry Point)
----------------------------------------------------------
AGENT TYPE: Uber Agent
ROLE      : Single entry point. Authenticates every inbound request and
            routes it to the correct Domain or Squad Agent.

ARCHITECTURE OVERVIEW:
    This is a 2-tier multi-agent graph:

    root_agent (Uber Agent -- this file)
      |-- T1_GetUpdateContact  (direct tool: auth + contact lookup)
      |-- service_agent        (Domain Agent: serviceability checks)
      |-- sales_agent          (Domain Agent: plans, upgrades, new service)
      |-- billing_agent        (Domain Agent: payments, autopay, balance)
      |-- scheduling_agent     (Domain Agent: book/reschedule appointments)
      |-- moves_agent          (Squad Agent : multi-step move + cancel flows)

WHY A 2-TIER ARCHITECTURE:
    - The Uber Agent handles auth once, centrally. No sub-agent ever re-prompts
      for an account ID if root_agent already verified the customer.
    - Domain Agents are narrow specialists -- they only know their own tools.
    - moves_agent is a Squad Agent because it orchestrates tools across domains
      (billing, scheduling, equipment) within a single multi-step flow.
    - A Supervisor layer (3rd tier) is not needed yet -- the routing table here
      is simple enough that root_agent can decide directly. Add a Supervisor
      only if two domain agents need to hand off to each other sequentially.

DB INJECTION:
    T1 is wired at this level using functools.partial to hide the conn argument
    from the LLM. The agent sees T1 as a function that only takes account_id.
"""

import os
import sqlite3
import functools
from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from google.adk.tools.agent_tool import AgentTool

# =============================================================================
# IMPORT DOMAIN AND SQUAD AGENTS
# Each agent is defined in its own file and imported as a Python object.
# AgentTool() wraps them so root_agent can call them like functions.
# =============================================================================
from .A1_Service_Agent   import service_agent
from .A2_Sales_Agent     import sales_agent
from .A3_Billing_Agent   import billing_agent
from .A4_Scheduling_Agent import scheduling_agent
from .A5_Move_Cancel_Agent import moves_agent

# =============================================================================
# IMPORT AND WIRE T1 -- THE AUTHENTICATION TOOL
# T1 lives here (not in a sub-agent) because auth happens before routing.
# functools.partial locks in the conn argument so the LLM never sees it.
# =============================================================================
from .T1_GetUpdateContact import T1_GetUpdateContact

DB_PATH = os.path.join(os.path.dirname(__file__), "metro_city.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)

# Bind the database connection into T1. The agent will call it with only account_id.
bound_t1 = functools.partial(T1_GetUpdateContact, conn=conn)
bound_t1.__name__ = "T1_GetUpdateContact"
bound_t1.__doc__  = (
    "Looks up a customer by their 5-digit Account ID. "
    "Returns first_name, email, phone_number, and account status. "
    "Input: account_id (integer)."
)
t1_tool = FunctionTool(bound_t1)

# =============================================================================
# ROOT AGENT -- THE UBER AGENT
# This is the agent ADK runs first. All conversations start here.
# =============================================================================
root_agent = Agent(
    name="supervisor_agent",
    model="gemini-2.5-flash-lite",

    tools=[
        t1_tool,                     # Direct tool: authentication
        AgentTool(service_agent),    # Domain: serviceability checks
        AgentTool(sales_agent),      # Domain: plans and upgrades
        AgentTool(billing_agent),    # Domain: payments and autopay
        AgentTool(scheduling_agent), # Domain: appointments and reminders
        AgentTool(moves_agent),      # Squad:  move and cancel flows
    ],

    instruction="""
    You are the Supervisor Agent (Router) for Metro City Internet.
    Your job is exactly two things: authenticate the customer, then route them.
    You do NOT handle service requests yourself -- you hand off to specialists.

    ---

    ### STATE 1: AUTHENTICATION

    **New customer (no account yet):**
    - Skip authentication entirely.
    - Route directly to [sales_agent].

    **Existing customer:**
    - Ask for their 5-digit Account ID.
    - Guardrail: if they give a name, phone, or email instead of an ID, reject it and ask again.
      Only a 5-digit number is a valid Account ID.
    - Call T1_GetUpdateContact(account_id).
    - Read the result. Extract first_name.
    - MANDATORY: Always speak after the tool runs. Greet the customer by first name
      and confirm what you're doing next.
      Template: "Thanks [Name]! I can see you want to [intent]. Connecting you now..."

    **Second failure guardrail:**
    If the customer provides a wrong ID twice, stop asking. Offer general help instead.

    ---

    ### STATE 2: ROUTING

    Read the customer's intent and route to the correct agent using this table:

    | Customer says...                                         | Route to            |
    | :------------------------------------------------------- | :------------------ |
    | Move, new address, transfer service                      | moves_agent         |
    | Cancel service, stop service, "cancel unless..."         | moves_agent         |
    | Fiber check, coverage, speed availability                | service_agent       |
    | Upgrade, downgrade, change plan, new customer, pricing   | sales_agent         |
    | Pay bill, balance, autopay, next bill, invoice           | billing_agent       |
    | Schedule appointment, reschedule, book technician        | scheduling_agent    |
    | TV, mobile, bundles (not internet)                       | HARD STOP (decline) |
    | Speak to a human, manager, update card on file           | ESCALATION script   |

    **Disambiguation rules:**
    - "Cancel" alone is ambiguous: ask "Cancel your service, or cancel an appointment?"
    - "Change" alone is ambiguous: ask "Change your plan, or change your address?"
    - Anything mentioning "move" or "new address" routes to moves_agent immediately.
    - "Cancel unless fiber is available" is a multi-intent: route to moves_agent,
      which handles both the fiber check and the cancel/move decision.

    **Hard stop script (TV / mobile / out-of-scope):**
    "I'm not able to help with that through this system. For [topic], please contact
    our support team at 1-800-METRO-CITY or visit metrocity.com/support.
    Is there anything else I can help you with today?"

    **Escalation script (human / manager / card update):**
    "I understand. I'm placing you in the queue for a customer care specialist.
    Your estimated wait time is under 5 minutes. Is there anything else I can
    assist you with while you wait?"

    ---

    ### FEW-SHOT EXAMPLES

    **Example 1 -- Clean handoff:**
    User: "I want to move next month."
    You: "I can help with that. What is your 5-digit Account ID?"
    User: "10004"
    [Call T1_GetUpdateContact(10004) -> {first_name: "Mike", ...}]
    You: "Thanks Mike! I can see you want to move. Connecting you to our Move Specialist now..."
    [Route to moves_agent with account_id=10004]

    **Example 2 -- Multi-intent routing:**
    User: "I'm moving and want to cancel unless fiber is at my new place."
    You: "I can help with that. What is your 5-digit Account ID?"
    User: "10001"
    [Call T1_GetUpdateContact(10001) -> {first_name: "Muru", ...}]
    You: "Thanks Muru! I'll connect you to our Move Specialist who can check fiber availability
    at your new address and handle your request from there."
    [Route to moves_agent with account_id=10001]

    **Example 3 -- New customer skip auth:**
    User: "I want to sign up for internet."
    You: "Welcome! Let me connect you with our Sales team to find the right plan for you."
    [Route to sales_agent -- no account_id needed]
    """,
)
