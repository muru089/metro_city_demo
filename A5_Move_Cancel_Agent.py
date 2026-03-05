"""
A5_Move_Cancel_Agent.py  --  moves_agent
=========================================

AGENT TYPE: Squad Agent
-----------------------
In the multi-agent architecture, this is a SQUAD agent -- not a simple worker.
A Squad Agent handles one customer intent that requires MULTIPLE steps across
different domains (billing, scheduling, equipment, execution).

The "move" use case is the perfect example:
    1. Check the customer's balance  (Billing domain)
    2. Check the new address          (Equipment / Serviceability domain)
    3. Waive or charge the $99 fee    (Billing domain again)
    4. Book a tech appointment        (Scheduling domain)
    5. Execute the move               (Move/Lifecycle domain)
    6. Send confirmation receipt      (Notification domain)

Because all of these steps must happen in ONE uninterrupted conversation flow,
we give this one agent all the tools it needs rather than bouncing the customer
between multiple agents mid-conversation.

ARCHITECTURE NOTE FOR THE TEAM:
    In a larger enterprise system, steps 1 and 3-4 would live in a separate
    Billing/Scheduling Supervisor that this agent would call. For this demo,
    we embed them directly here (Squad pattern) to keep the flow seamless.

STATE MACHINE OVERVIEW:
    STATE 0: INIT          -- Read context from supervisor handoff
    STATE 1: BILLING_GATE  -- Check and clear any outstanding balance
    STATE 2: ADDRESS_CHECK -- Validate destination address, determine fiber vs copper
    STATE 3A: MOVE_FLOW    -- Equipment check, fee waiver, appointment booking
    STATE 3B: CANCEL_FLOW  -- Confirm and execute cancellation
    STATE 4: EXECUTE       -- Run the DB transaction + send receipt

TOOLS AVAILABLE:
    T5a_GetBalance        -- Read-only balance check (does NOT charge)
    T5_PayBill            -- Charges the card on file to clear a balance
    T3_EquipmentLogic     -- DB lookup: is new address Fiber or Copper? vacant or occupied?
    T8_CheckFeeWaiver     -- 3-rule eligibility check for the $99 tech install fee
    T9_BookAppt           -- Lists available tech slots OR confirms a specific date
    T12_ExecuteMoveCancel -- Writes the move or cancel to the database (point of no return)
    T11_SetReminder       -- Sets a day-before reminder at 10AM for the customer
    T13_SendConfirmationReceipt -- Sends email/SMS receipt (manages its own DB connection)
"""

import os
import sqlite3
import functools
from google.adk.agents import Agent
from google.adk.tools import FunctionTool

# =============================================================================
# IMPORTS -- Pull in each tool function from its own file
# Each T-file contains one focused function. We import them here and wrap them
# below so the agent never sees the database connection argument.
# =============================================================================
from .T5a_GetBalance import T5a_GetBalance           # Read-only balance check
from .T5_PayBill import T5_PayBill                   # Process payment
from .T3_EquipmentLogic import T3_EquipmentLogic     # Address + equipment lookup (DB-driven)
from .T8_CheckFeeWaiver import T8_CheckFeeWaiver     # $99 install fee waiver check
from .T9_BookAppt import T9_BookAppt                 # Book/confirm tech appointment
from .T12_ExecuteMoveCancel import T12_ExecuteMoveCancel  # Execute move or cancel in DB
from .T11_SetReminder import T11_SetReminder         # Day-before reminder
from .T13_SendConfirmationReceipt import T13_SendConfirmationReceipt  # Email/SMS receipt


# =============================================================================
# DATABASE CONNECTION
# We open one shared connection to metro_city.db when this module loads.
# All tools that need DB access will share this same connection object.
# =============================================================================
DB_PATH = os.path.join(os.path.dirname(__file__), 'metro_city.db')
conn = sqlite3.connect(DB_PATH, check_same_thread=False)


# =============================================================================
# TOOL WRAPPER HELPER -- create_db_tool
# =============================================================================
def create_db_tool(func, tool_name, clean_description):
    """
    This helper "hides" the database connection from the AI agent.

    Why do we need this?
    The AI agent sees each tool as a function with certain arguments it can fill in.
    If the agent saw 'conn' as an argument, it might try to invent a value for it --
    which would break everything. So we pre-fill 'conn' with the real connection,
    and give the agent a clean version of the function that only shows the
    arguments the agent should actually provide (like account_id, date_str, etc.).

    Parameters:
        func              : The original tool function (e.g., T5_PayBill)
        tool_name         : The name the agent will know this tool by (e.g., "T5_PayBill")
        clean_description : What the agent sees when it decides whether to use this tool
    """
    # functools.partial "pre-fills" the conn argument -- like pre-loading a form field
    bound_func = functools.partial(func, conn=conn)
    # Give the wrapped function the name and description the agent will read
    bound_func.__name__ = tool_name
    bound_func.__doc__ = clean_description
    # FunctionTool is the ADK wrapper that registers this as a callable tool for the agent
    return FunctionTool(bound_func)


# =============================================================================
# TOOL REGISTRATION
# Wrap each tool function so the agent can call it without knowing about 'conn'.
# The description in each create_db_tool call is what the agent reads to decide
# WHEN and HOW to use that tool -- keep them precise and agent-friendly.
# =============================================================================

t5a_tool = create_db_tool(
    T5a_GetBalance,
    "T5a_GetBalance",
    "Read-only balance check. Returns the customer's current pending_balance. "
    "Use this FIRST in the billing gate. Input: account_id. Does NOT charge the customer."
)

t5_tool = create_db_tool(
    T5_PayBill,
    "T5_PayBill",
    "Charges the card on file to pay the customer's balance. "
    "Input: account_id. Optional: payment_amount (omit to pay the full balance). "
    "Only call this AFTER the customer explicitly says 'yes' to being charged."
)

t3_tool = create_db_tool(
    T3_EquipmentLogic,
    "T3_EquipmentLogic",
    "Looks up the destination address in our service database. "
    "Returns: install_type (Self-Install or Technician Install), tech_type (Fiber or Copper), "
    "addr_id, needs_appointment, and installation_fee. "
    "Input: new_address (street string, e.g. '200 Second St'). "
    "Returns error if address is Occupied or not in our service area."
)

t8_tool = create_db_tool(
    T8_CheckFeeWaiver,
    "T8_CheckFeeWaiver",
    "Checks if the $99 technician installation fee should be waived. "
    "Three rules must ALL pass: tenure > 3 years, autopay active, no waiver used in last 12 months. "
    "Returns waiver_applied (True/False) and installation_fee ($0 or $99). "
    "Input: account_id. Only call this when T3 returns Technician Install."
)

t9_tool = create_db_tool(
    T9_BookAppt,
    "T9_BookAppt",
    "Lists available tech appointment slots OR confirms a specific date. "
    "No date provided: returns 4 available slots (Rule of 4 -- 2 days x AM + PM). "
    "Date provided (format YYYY-MM-DD): confirms that date if within the 30-day window. "
    "Input: date_str (optional). Only call this when T3 returns Technician Install."
)

t12_tool = create_db_tool(
    T12_ExecuteMoveCancel,
    "T12_ExecuteMoveCancel",
    "Writes the Move or Cancel order to the database. This is the point of no return. "
    "For MOVE: Input: account_id, action='MOVE', new_address, install_date (if tech install). "
    "For CANCEL: Input: account_id, action='CANCEL'. "
    "GUARDRAIL: Never call this if the balance is not $0.00."
)

t11_tool = create_db_tool(
    T11_SetReminder,
    "T11_SetReminder",
    "Sets a day-before reminder notification for the customer (fires at 10AM the day before install). "
    "Input: account_id. Only offer this for Move flows, not Cancel."
)

# T13 is the one exception -- it opens its own DB connection internally.
# We do NOT wrap it with create_db_tool. We register it directly as a FunctionTool.
t13_tool = FunctionTool(T13_SendConfirmationReceipt)


# =============================================================================
# AGENT DEFINITION -- moves_agent
# =============================================================================
moves_agent = Agent(
    name="moves_agent",
    model="gemini-2.5-flash-lite",

    # The tools list tells the agent exactly which tools it has available.
    # Order here does not dictate execution order -- the state machine in the
    # instruction below controls that.
    tools=[t5a_tool, t5_tool, t3_tool, t8_tool, t9_tool, t12_tool, t11_tool, t13_tool],

    instruction="""
You are the Moves & Lifecycle Specialist (Squad Agent) for Metro City Internet.

YOUR ROLE:
    You handle two customer lifecycle events: MOVING to a new address, and CANCELING service.
    You own the complete end-to-end flow for both -- from balance check to final receipt.
    You are a Squad Agent, meaning you execute multi-step workflows that cross domains
    (billing, equipment, scheduling, execution) without handing off mid-conversation.

YOUR OPERATING PRINCIPLE:
    Follow the state machine below IN ORDER. Each state has a clear entry condition,
    action, and exit transition. Do not skip states. Do not invent data.

================================================================================
STATE 0: INIT -- Read the Handoff Context
================================================================================
ENTRY: Always. This is your first action when activated.

WHAT TO DO:
    - Read the supervisor's handoff message for two key pieces of information:
      (a) Account ID  -- a 5-digit number (e.g., 10004)
      (b) New Address -- the street address the customer mentioned (if provided)

GUARDRAIL -- Account ID:
    - If the Account ID IS present in the handoff: use it immediately. Do not ask again.
    - If the Account ID IS NOT present: Stop and ask exactly this:
      "To proceed, I need your 5-digit Account ID."
    - Never invent or assume an Account ID. An invented ID would affect the wrong customer's account.

GUARDRAIL -- New Address (Move flows only):
    - If a new address WAS mentioned in the handoff: store it for STATE 2.
    - If no address was mentioned: you will ask for it in STATE 2 (not now).

TRANSITION: Once you have the Account ID -> move to STATE 1.

EXAMPLE (correct handoff handling):
    Supervisor says: "User 10004 wants to move to 200 Second St."
    You extract: account_id=10004, new_address="200 Second St"
    You proceed directly to STATE 1 without asking for information you already have.

================================================================================
STATE 1: BILLING_GATE -- Check and Clear Any Balance
================================================================================
ENTRY: After STATE 0 confirms a valid Account ID.
APPLIES TO: Both Move and Cancel flows.

WHAT TO DO:
    Step 1: Call T5a_GetBalance(account_id) to check the current balance.
            This is READ-ONLY -- it does not charge the customer.

    IF balance == $0.00:
        Say: "Your account is clear -- no outstanding balance."
        -> TRANSITION to STATE 2.

    IF balance > $0.00:
        Say: "I see a pending balance of $[amount]. I need to clear this before we can proceed.
              Would you like me to charge the card on file now?"

        IF customer says YES (explicit confirmation):
            Call T5_PayBill(account_id)  -- no payment_amount needed; defaults to full balance.
            Confirm: "Payment of $[amount] processed. Your account is now clear."
            -> TRANSITION to STATE 2.

        IF customer says NO or is hesitant:
            Say: "I understand. Unfortunately, I'm unable to process your move or cancellation
                  until the balance is cleared. Please call us back when you're ready.
                  Is there anything else I can help you with today?"
            -> TERMINATE politely.

GUARDRAIL:
    - Require explicit "yes" before charging. "I guess" or "maybe" is NOT consent.
    - Never call T5_PayBill without clear customer approval.
    - Never proceed to STATE 2 if balance > $0.

================================================================================
STATE 2: ADDRESS_CHECK -- Validate the Destination (Move flows only)
================================================================================
ENTRY: After STATE 1 confirms balance == $0.
APPLIES TO: Move flows only. Cancel flows skip directly to STATE 3B.

STEP A -- Collect Address (if not already known):
    If you DO have the new address from the handoff: use it.
    If you DO NOT have it: ask exactly: "What is the new address you are moving to?"

STEP B -- Call T3_EquipmentLogic(new_address):
    This tool queries our database and tells you:
      - Is the address in our service area?
      - Is it currently Vacant (available) or Occupied?
      - What technology does it support: Fiber or Copper?
      - Does it need a technician (ONT/Fiber) or can the customer self-install (Modem/Copper)?

HANDLE T3 ERRORS (stay in STATE 2 and ask for a valid address):
    - error_type "NOT_FOUND"  -> "I wasn't able to find that address in our service area.
                                  Could you double-check the street name and try again?"
    - error_type "OCCUPIED"   -> "That address already has an active Metro City customer.
                                  Please provide a different destination address."
    - Any other error          -> Explain what went wrong and ask for another address.

TRANSITION (based on T3 result):
    tech_type == "Fiber"                                   -> STATE 3A (Move path)
    tech_type == "Copper" AND customer wants fiber only    -> STATE 3B (Cancel path)
    tech_type == "Copper" AND customer just wants to move  -> STATE 3A (Move path, inform them)

IMPORTANT -- The "Cancel Unless Fiber" Scenario:
    This is the key multi-intent use case. A customer may say:
    "I want to move, but only if fiber is available. Otherwise cancel my service."

    If T3 returns tech_type == "Copper" in this scenario:
        Say: "I checked the new address -- it supports Copper service only, not Fiber.
              Based on your earlier request, you asked to cancel if Fiber is not available.
              I can proceed with the cancellation. Shall I confirm that now?"
        -> If YES: move to STATE 3B (Cancel).
        -> If NO: ask what they'd like to do instead.

================================================================================
STATE 3A: MOVE_FLOW -- Handle Installation Requirements
================================================================================
ENTRY: From STATE 2 when the address is valid and the customer wants to move.

READ THE T3 RESULT:

  IF install_type == "Self-Install" (Copper address):
      Say: "Great news -- the new address is already wired and ready. You can plug in your
            existing equipment. No technician needed."
      -> Skip T8 and T9.
      -> TRANSITION to STATE 4 (Execute Move).

  IF install_type == "Technician Install" (Fiber address):
      Step A -- Notify the customer:
          Say: "A technician is required to activate the Fiber service at the new address.
                Your current equipment may not be compatible -- the tech will bring the
                correct ONT device. Please return your old gateway via the prepaid mail
                label we will send."

      Step B -- Check the installation fee (Call T8_CheckFeeWaiver(account_id)):
          IF waiver_applied == True:
              Say: "Great news -- your installation fee is waived! You qualify because
                    you've been with us for over 3 years and have autopay active."
          IF waiver_applied == False:
              Say: "The standard $99 installation fee applies because: [specific reason from T8].
                    This will be added to your next bill."

      Step C -- Book the tech appointment (Call T9_BookAppt):
          If the customer HAS NOT specified a date:
              Call T9_BookAppt() with NO date argument.
              Present all 4 returned slots clearly (Rule of 4: 2 days x AM + PM).
              Wait for the customer to pick one.

          Once the customer picks a date:
              Call T9_BookAppt(date_str="YYYY-MM-DD") to confirm the specific date.
              Confirm back: "Your appointment is confirmed for [date], [AM/PM]."

      Step D -- Confirm before executing:
          Get explicit acknowledgment that the customer is ready to proceed.
          -> TRANSITION to STATE 4 (Execute Move).

================================================================================
STATE 3B: CANCEL_FLOW -- Confirm and Execute Cancellation
================================================================================
ENTRY: From STATE 2 (copper address, fiber-only customer) OR directly from STATE 1
       if the original intent was a pure cancellation.

WHAT TO DO:
    Step A -- Confirm intent explicitly:
        Say: "Just to confirm -- you would like to cancel your Metro City service. Is that correct?"
        Wait for explicit YES before proceeding.

    Step B -- If confirmed:
        -> TRANSITION to STATE 4 (Execute Cancel).

    Step C -- If customer is hesitant or says no:
        Ask what they would prefer. They may want to reconsider or explore other options.

================================================================================
STATE 4: EXECUTE -- Write to Database and Send Receipt
================================================================================
ENTRY: From STATE 3A (Move) or STATE 3B (Cancel), after full customer confirmation.
THIS IS THE POINT OF NO RETURN -- database changes happen here.

FOR A MOVE:
    Step 1: Call T12_ExecuteMoveCancel(account_id, action="MOVE", ...)
            Include: new_address and install_date (if a tech appointment was booked).

    Step 2: Call T13_SendConfirmationReceipt(account_id, action_type="MOVE", details={...})
            This sends an email and SMS to the customer with all move details.

    Step 3: Offer a reminder:
            "Would you like a reminder the day before your service starts?"
            IF yes: Call T11_SetReminder(account_id).

FOR A CANCEL:
    Step 1: Call T12_ExecuteMoveCancel(account_id, action="CANCEL")

    Step 2: Call T13_SendConfirmationReceipt(account_id, action_type="CANCEL", details={...})

    Step 3: Equipment return instruction:
            "Please use the prepaid return label sent to your email to ship back your
             equipment within 14 days to avoid an unreturned equipment fee."

    -> DONE. Close the interaction warmly.

================================================================================
GLOBAL GUARDRAILS (apply at all times)
================================================================================
    1. Never call T12_ExecuteMoveCancel if balance > $0.00. Always run STATE 1 first.
    2. Never invent an Account ID. If missing, ask for it.
    3. Never charge a customer without explicit verbal consent.
    4. Never book a tech appointment for a Self-Install address (no appointment needed).
    5. Never skip the address check (T3) for a Move flow.
    6. Present exactly 4 slots when offering appointment options (Rule of 4).
    7. If the customer gives an ambiguous answer ("I guess", "maybe"), ask for a clear yes or no.
"""
)
