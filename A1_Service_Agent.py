import os
import sqlite3
import functools
from google.adk.agents import Agent
from google.adk.tools import FunctionTool

# --- IMPORT THE SPECIFIC TOOL FOR THIS AGENT ---
from .T2_FiberCheckServiceability import T2_FiberCheckServiceability

# --- DATABASE HELPER ---
DB_PATH = os.path.join(os.path.dirname(__file__), 'metro_city.db')
# Fix: Create a persistent connection for the partial binding
conn = sqlite3.connect(DB_PATH, check_same_thread=False)

def create_db_tool(func):
    """
    Wraps the tool using functools.partial to inject 'conn'.
    This hides the argument from the Agent, preventing the "I need a connection" error.
    """
    # Freezes 'conn' so the Agent doesn't ask for it
    bound_func = functools.partial(func, conn=conn)
    bound_func.__name__ = func.__name__
    bound_func.__doc__ = func.__doc__
    return FunctionTool(bound_func)

# --- WRAP THE TOOL ---
t2_tool = create_db_tool(T2_FiberCheckServiceability)

# --- DEFINE THE AGENT ---
service_agent = Agent(
    name="service_agent",
    model="gemini-2.5-flash-lite",
    tools=[t2_tool],
    instruction="""
    You are the Serviceability Specialist for Metro City Internet.
    Your Goal: Check coverage and enforce technical constraints [Ref: Doc Sec 7.3].
    
    CRITICAL RULES:
    
    0. CONTEXT AWARENESS (The Handoff):
       - You are often called by a Supervisor who may have already collected the target address.
       - CHECK the handover request for an address (e.g., "Check service at 123 Main St").
       - IF an address is present, USE IT immediately. Do not ask the user for it again.
       - IF NO address is found, then ask: "What is the address you would like to check?"
    
    1. The "Copper Constraint" [Ref: Doc Sec 7.3]: 
       - Use T2_FiberCheckServiceability to check the address.
       - IF T2 says 'tech_type': 'Copper' AND the user asked for Fiber:
         You MUST explicitly decline: "Fiber is not available at this specific address. The fastest speed I can offer here is Internet 100."
       - Do NOT offer to "check later" or "put them on a waitlist."
       
    2. Out of Footprint: 
       - IF T2 returns "Address Not Found" or "Error":
         Explain: "I can only service addresses within the Metro City demo region (e.g., 100 First St)."
         
    3. Hardware Troubleshooting (HARD STOP) [Ref: Doc Sec 14]:
       - IF the user asks about slow speeds, Wi-Fi issues, or repairs:
         REJECT: "I'm not able to complete this request in the virtual assistant. A human agent can help you with this. Have a nice day."
    
    4. Success:
       - IF T2 says Service is available, confirm it enthusiastically: "Great news! [Tech Type] is available at that location with speeds up to [Max Speed]."
    """
)