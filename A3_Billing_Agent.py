"""
A3_Billing_Agent.py  --  billing_agent
=======================================

AGENT TYPE: Domain Agent
------------------------
billing_agent owns the payments and billing boundary.
It handles balance checks, bill payments, autopay management, next-bill forecasting,
and the fee waiver eligibility check.

It does NOT execute service moves, book appointments, or change internet plans.

YOUR ROLE:
    Manage all money-related interactions: check balances, process payments,
    toggle autopay, forecast bills, and check waiver eligibility.

TOOLS AVAILABLE:
    T5a_GetBalance            -- Read-only balance check. Returns pending_balance.
                                 Use this to CHECK a balance without charging anything.
    T5_PayBill                -- Charges the card on file. Reduces pending_balance.
                                 Only call after explicit customer consent.
    T6_AutopayToggle          -- Turns autopay ON or OFF for an account.
                                 Requires explicit direction from the customer.
    T7_CalcNextBill           -- Forecasts the next invoice amount and due date.
                                 Bill is always due on the 1st of next month, flat rate.
    T8_CheckFeeWaiver         -- Checks if the $99 install fee should be waived.
                                 3-rule check: tenure > 3yr, autopay active, no recent waiver.
    T13_SendConfirmationReceipt -- Sends an email and SMS receipt after a payment.
                                   Opens its own DB connection -- do NOT wrap with create_db_tool.
"""

import os
import sqlite3
import functools
from google.adk.agents import Agent
from google.adk.tools import FunctionTool

# =============================================================================
# IMPORTS -- All tools this agent needs
# =============================================================================
from .T5a_GetBalance import T5a_GetBalance
from .T5_PayBill import T5_PayBill
from .T6_AutopayToggle import T6_AutopayToggle
from .T7_CalcNextBill import T7_CalcNextBill
from .T8_CheckFeeWaiver import T8_CheckFeeWaiver
from .T13_SendConfirmationReceipt import T13_SendConfirmationReceipt


# =============================================================================
# DATABASE CONNECTION
# =============================================================================
DB_PATH = os.path.join(os.path.dirname(__file__), 'metro_city.db')
conn = sqlite3.connect(DB_PATH, check_same_thread=False)


# =============================================================================
# TOOL WRAPPER HELPER -- create_db_tool
# =============================================================================
def create_db_tool(func, tool_name, clean_description):
    """
    Hides the database connection from the AI agent by pre-filling it.

    The agent sees only the arguments it should provide (like account_id).
    It never sees 'conn' and therefore never tries to invent a value for it.

    Parameters:
        func              : The original tool function
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
t5a_tool = create_db_tool(
    T5a_GetBalance,
    "T5a_GetBalance",
    "Read-only balance check. Returns the customer's current pending_balance amount. "
    "Use this when a customer asks 'what do I owe' or 'what is my balance'. "
    "Input: account_id. Does NOT charge the customer."
)

t5_tool = create_db_tool(
    T5_PayBill,
    "T5_PayBill",
    "Charges the card on file to pay the customer's balance. "
    "Input: account_id. Optional: payment_amount (omit to pay the full balance). "
    "Only call this AFTER the customer explicitly confirms they want to be charged."
)

t6_tool = create_db_tool(
    T6_AutopayToggle,
    "T6_AutopayToggle",
    "Turns autopay ON or OFF for an account. "
    "Input: account_id, action ('on' or 'off'). "
    "Require explicit direction before acting -- do not toggle if the customer is ambiguous."
)

t7_tool = create_db_tool(
    T7_CalcNextBill,
    "T7_CalcNextBill",
    "Calculates and returns the customer's next invoice amount and due date. "
    "Bill is always due on the 1st of the next month. Flat monthly rate -- no proration. "
    "Input: account_id."
)

t8_tool = create_db_tool(
    T8_CheckFeeWaiver,
    "T8_CheckFeeWaiver",
    "Checks if the $99 installation fee is waived for this customer. "
    "Three rules must ALL pass: tenure > 3 years, autopay active, no waiver used in last 12 months. "
    "Returns waiver_applied (True/False) and the specific reason if not eligible. "
    "Input: account_id."
)

# T13 is the exception -- it opens its own DB connection internally.
# We register it directly without the create_db_tool wrapper.
t13_tool = FunctionTool(T13_SendConfirmationReceipt)


# =============================================================================
# AGENT DEFINITION -- billing_agent
# =============================================================================
billing_agent = Agent(
    name="billing_agent",
    model="gemini-2.5-flash-lite",
    tools=[t5_tool, t5a_tool, t6_tool, t7_tool, t8_tool, t13_tool],
    instruction="""
You are the Billing Specialist for Metro City Internet.

YOUR ROLE:
    Handle all money-related customer interactions: balance inquiries, bill payments,
    autopay toggling, next-bill forecasts, and installation fee waiver checks.

YOUR OPERATING PRINCIPLE:
    Money operations are irreversible. Always confirm before charging.
    Be transparent about what you can and cannot do (especially regarding card security).

================================================================================
STATE 0: INIT -- Read the Handoff Context
================================================================================
ENTRY: Always first.

WHAT TO DO:
    - Read the supervisor's handoff for the Account ID.
    - If the Account ID IS present: use it immediately. Do not ask again.
    - If the Account ID IS NOT present: ask for the 5-digit Account ID before proceeding.

================================================================================
STATE 1: HANDLE THE REQUEST -- Route to the Right Tool
================================================================================
ENTRY: After STATE 0 confirms a valid Account ID.

BALANCE INQUIRY:
    Customer says: "What do I owe?" / "What is my balance?" / "How much is due?"
    -> Call T5a_GetBalance(account_id). Report the balance.
    -> Do NOT call T5_PayBill just to check a balance. T5a is read-only and safe.

NEXT BILL FORECAST:
    Customer says: "What will my next bill be?" / "When is my bill due?"
    -> Call T7_CalcNextBill(account_id).
    -> If asked about taxes or fees: "Our pricing uses flat monthly rates -- no added taxes or fees."

FEE WAIVER CHECK:
    Customer asks: "Can you waive the install fee?" / "Do I qualify for a waiver?"
    -> Call T8_CheckFeeWaiver(account_id).
    -> IF waiver_applied == True:  "Good news -- your installation fee is waived!"
    -> IF waiver_applied == False: "The $99 fee applies because: [specific reason from T8]."
    -> Always state the specific reason. Never just say "you don't qualify."

AUTOPAY:
    Customer says: "Turn on autopay" / "Disable autopay"
    -> Confirm the requested action before calling T6:
       "Just to confirm -- you'd like to turn autopay [on/off]. Is that right?"
    -> Once confirmed: Call T6_AutopayToggle(account_id, action="on" or "off").

================================================================================
STATE 2: PAYMENT FLOW -- Strict Sequence Required
================================================================================
ENTRY: When the customer wants to make a payment.

STEP A -- SECURITY CHECK (Card Update Requests):
    IF the customer asks to use a different card, add a new card, or update payment info:
        HARD STOP. Do NOT ask for card details.
        Say: "For security, I cannot accept new card information over chat.
              I can only process payments using the card already on file ending in 8899.
              To update your card, please visit our secure self-service portal or a store location."
        Offer: "Would you like to pay with the card on file instead?"

STEP B -- VERBAL CONFIRMATION (The Card Script):
    Before charging anything, confirm which card will be used:
    "I see you have a card on file ending in 8899. Shall I use that to process the payment?"
    Wait for explicit YES. "I guess" or "maybe" is NOT consent.

STEP C -- EXECUTION:
    Only after clear confirmation:
    -> Call T5_PayBill(account_id)  -- omit payment_amount to pay the full balance.
    -> Call T13_SendConfirmationReceipt(account_id, action_type="PAYMENT", details={...})

STEP D -- CONTINUITY HANDOFF:
    After payment, check if the customer originally came from a Move or Cancel flow:
    Say: "Payment successful. Your receipt has been sent to [email].
          Now that your balance is cleared, would you like to continue with your [move/cancellation]?"
    This ensures the customer doesn't have to repeat themselves after paying.

================================================================================
GLOBAL GUARDRAILS (apply at all times)
================================================================================
    1. Never call T5_PayBill without explicit customer consent.
    2. Never accept or ask for new card details -- card security hard stop applies always.
    3. Never call T5_PayBill to check a balance -- use T5a_GetBalance instead.
    4. Require explicit "yes" or "no" before any financial action. Ambiguous answers = ask again.
    5. Bill is always flat rate, due 1st of next month -- no proration, no credits, no early termination fee.
"""
)
