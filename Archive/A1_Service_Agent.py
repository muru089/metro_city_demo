"""
A1_Service_Agent.py  --  service_agent
=======================================

AGENT TYPE: Domain Agent
------------------------
A Domain Agent owns one system boundary and does not share tools with other agents.
service_agent is the single authority on "Is service available at this address?"
It does not process payments, book appointments, or change plans -- it only checks coverage.

YOUR ROLE:
    Answer the question: "Can Metro City Internet serve this address, and at what technology level?"
    This is typically called when a customer asks about availability before signing up,
    or when move_cancel_loop needs to verify a new address is in our footprint.

TOOLS AVAILABLE:
    T2_FiberCheckServiceability -- Looks up an address by addr_id and returns the
                                   technology type (Fiber or Copper) and maximum speed.
                                   Input: address_id (e.g., "A11"), NOT a street string.
"""

import os
import sqlite3
import functools
from google.adk.agents import Agent
from google.adk.tools import FunctionTool

# =============================================================================
# IMPORT -- Pull in the one tool this agent uses
# =============================================================================
from .T2_FiberCheckServiceability import T2_FiberCheckServiceability


# =============================================================================
# DATABASE CONNECTION
# A single persistent connection shared by all tool calls for this agent.
# =============================================================================
DB_PATH = os.path.join(os.path.dirname(__file__), 'metro_city.db')
conn = sqlite3.connect(DB_PATH, check_same_thread=False)


# =============================================================================
# TOOL WRAPPER HELPER -- create_db_tool
# =============================================================================
def create_db_tool(func, tool_name, clean_description):
    """
    Hides the database connection from the AI agent by pre-filling it.

    The agent sees only the arguments it should provide (like address_id).
    It never sees 'conn' and therefore never tries to invent a value for it.

    Parameters:
        func              : The original tool function (e.g., T2_FiberCheckServiceability)
        tool_name         : The name the agent will call this tool by
        clean_description : What the agent reads to decide when and how to use this tool
    """
    bound_func = functools.partial(func, conn=conn)
    bound_func.__name__ = tool_name
    bound_func.__doc__ = clean_description
    return FunctionTool(bound_func)


# =============================================================================
# TOOL REGISTRATION
# =============================================================================
t2_tool = create_db_tool(
    T2_FiberCheckServiceability,
    "T2_FiberCheckServiceability",
    "Checks service availability at a specific address. "
    "Returns technology type (Fiber or Copper), maximum speed, and equipment type. "
    "Input: address_id (e.g., 'A11'). NOTE: This takes an address ID, not a street string."
)


# =============================================================================
# AGENT DEFINITION -- service_agent
# =============================================================================
service_agent = Agent(
    name="service_agent",
    model="gemini-2.5-flash-lite",
    tools=[t2_tool],
    instruction="""
You are the Serviceability Specialist for Metro City Internet.

YOUR ROLE:
    Determine whether Metro City Internet can serve a given address, and at what
    technology level (Fiber or Copper). You are the single source of truth for coverage.

YOUR OPERATING PRINCIPLE:
    Always check the address first using T2, then respond based on what it returns.
    Never promise service that the tool does not confirm.

================================================================================
STATE 0: INIT -- Read the Handoff Context
================================================================================
ENTRY: Always first.

WHAT TO DO:
    - Check the supervisor's handoff message for an address or address ID.
    - If an address IS present: use it immediately. Do not ask again.
    - If no address is found: ask exactly: "What is the address you would like to check?"

NOTE -- Input Format for T2:
    T2 requires an address ID (e.g., "A11"), not a street string.
    If the customer gives a street address, match it to the correct addr_id from context
    or ask for clarification. The address IDs follow the format A01-A20.

================================================================================
STATE 1: CHECK SERVICE -- Run T2 and Respond
================================================================================
ENTRY: After STATE 0 confirms a valid address or address ID.

WHAT TO DO:
    Call T2_FiberCheckServiceability(address_id).

    IF T2 returns service available:
        Confirm enthusiastically with the technology type and maximum speed:
        "Great news! [Fiber/Copper] service is available at that address with speeds up to [X] Mbps."

    IF T2 returns "Copper" AND the customer specifically asked for Fiber:
        Be direct and clear -- do NOT hedge or offer a waitlist:
        "Fiber is not available at this specific address. The fastest speed available here
         is Internet 100 at 100 Mbps."

    IF T2 returns address not found:
        "I was unable to find that address in our service area. We may not serve that location yet.
         Please verify the address or try a nearby street."

================================================================================
GLOBAL GUARDRAILS (apply at all times)
================================================================================
    1. Copper Constraint: If the address is Copper-only, never offer or imply Fiber is an option.
       Do not say "check back later" or offer a waitlist. Be honest and direct.

    2. Out of Footprint: If T2 does not find the address, do not guess. Report it as out of area.

    3. Repair Hard Stop: If the customer asks about slow speeds, Wi-Fi problems, outages,
       or any form of troubleshooting -- this is out of scope. Use the standard script:
       "I'm not able to help with that through this system. For technical issues, please
        contact our support team at 1-800-METRO-CITY or visit metrocity.com/support.
        Is there anything else I can help you with today?"
"""
)
