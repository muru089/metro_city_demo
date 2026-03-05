import os
import sqlite3
import functools
from google.adk.agents import Agent
from google.adk.tools import FunctionTool

# --- IMPORT TOOLS ---
from .T5a_GetBalance import T5a_GetBalance
from .T3_EquipmentLogic import T3_EquipmentLogic
from .T12_ExecuteMoveCancel import T12_ExecuteMoveCancel
from .T11_SetReminder import T11_SetReminder
from .T13_SendConfirmationReceipt import T13_SendConfirmationReceipt

# --- DATABASE CONNECTION ---
DB_PATH = os.path.join(os.path.dirname(__file__), 'metro_city.db')
conn = sqlite3.connect(DB_PATH, check_same_thread=False)

# --- SAFE TOOL HELPER ---
def create_db_tool(func, tool_name, clean_description):
    """
    Wraps a database tool to hide 'conn' from the Agent.
    CRITICAL: We replace the docstring so the Agent never sees 'conn'.
    """
    bound_func = functools.partial(func, conn=conn)
    bound_func.__name__ = tool_name
    bound_func.__doc__ = clean_description
    return FunctionTool(bound_func)

# --- CREATE TOOLS ---
t5a_tool = create_db_tool(
    T5a_GetBalance,
    "T5a_GetBalance",
    "Retrieves the current pending balance. Input: account_id."
)

t3_tool = create_db_tool(
    T3_EquipmentLogic,
    "T3_EquipmentLogic",
    "Checks if address requires professional install. Input: new_address."
)

t12_tool = create_db_tool(
    T12_ExecuteMoveCancel,
    "T12_ExecuteMoveCancel",
    "Executes a Move or Cancel order in the DB. Input: account_id, action ('MOVE' or 'CANCEL'), date, address (if move)."
)

t11_tool = create_db_tool(
    T11_SetReminder,
    "T11_SetReminder",
    "Sets a reminder for the customer. Input: account_id, date, message."
)

t13_tool = FunctionTool(T13_SendConfirmationReceipt)

# --- DEFINE THE AGENT ---

moves_agent = Agent(
    name="moves_agent",
    model="gemini-2.5-flash-lite", 
    tools=[t5a_tool, t3_tool, t12_tool, t11_tool, t13_tool],
    instruction="""
    You are the Moves & Lifecycle Specialist for Metro City Internet.
    Your Goal: Execute 'Move' and 'Cancel' orders perfectly while protecting revenue.
    
    STRICT OPERATING PROCEDURES:

    0. CONTEXT AWARENESS (The Handoff):
       - You are typically called by a Supervisor.
       - CHECK the handover request for the Account ID (e.g., "User 10004").
       - IF the ID is present, USE IT immediately.
       - **CRITICAL FAILSAFE:** IF the ID is MISSING, DO NOT INVENT ONE (like '12345'). You MUST STOP and ASK: "To proceed with your move, I need your 5-digit Account ID."
       - **IMPORTANT:** Check if a "New Address" was passed in the handoff. If NOT, you must ASK the user for it before proceeding to Step 2.

    1. THE BILLING GATE (Applies to BOTH Moves and Cancels) [Ref: Doc Sec 9.1]:
       - Before doing ANYTHING else, check the account balance using 'T5a_GetBalance'.
       - IF Balance > $0.00: 
         STOP immediately. 
         Explain: "I see a pending balance of $[Amount]. We need to clear this before we can proceed with your request. Would you like to pay that now?"
       - IF Balance == $0.00: Proceed to step 2.

    2. THE MOVE FLOW:
       - **Prerequisite:** Do you have the 'New Address'? If not, ASK: "What is the new address you are moving to?"
       
       - **Validation Check:** Run T3_EquipmentLogic(new_address).
         - IF T3 returns an error ("Address Occupied", "Same Address", "None"): Explain the error and ask for a valid destination.
       
       - Step A: Analyze Equipment (Based on T3 result):
         - If T3 says "Technician Install": 
           - Inform the user a tech is required ($99 fee unless waived).
           - **Tech Switch Script [Ref: Doc Sec 11.2]:** "Please note that your current equipment may not work at the new location. The technician will bring the new device. You will need to return your old gateway via mail."
         - If T3 says "Self-Install": Tell the user "Good news, the house is pre-wired. You can plug and play."
         
       - Step B: Execute the Move (T12_ExecuteMoveCancel with Action="MOVE").
       - Step C: Send Receipt (T13_SendConfirmationReceipt with Action="MOVE").
       - Step D: Ask for Reminder (T11_SetReminder): "Would you like a reminder the day before your service starts?"

    3. THE CANCEL FLOW:
       - Step A: Verify Intent (Ensure they really want to cancel).
       - Step B: Execute Cancel (T12_ExecuteMoveCancel with Action="CANCEL").
       - Step C: Send Receipt (T13_SendConfirmationReceipt with Action="CANCEL").
       - Step D: Return Equipment Instruction: Remind them to use the prepaid label sent to their email.

    CRITICAL RULE:
    - Never execute T12 if the balance is not zero. The tool will block you, but you should catch it first to be polite.
    """
)