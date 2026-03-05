import os
import sqlite3
import functools
from google.adk.agents import Agent
from google.adk.tools import FunctionTool

# --- IMPORT TOOLS ---
from .T9_BookAppt import T9_BookAppt
from .T10_ReschedAppt import T10_ReschedAppt
from .T11_SetReminder import T11_SetReminder

# --- DATABASE HELPER ---
DB_PATH = os.path.join(os.path.dirname(__file__), 'metro_city.db')

def db_wrapper(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        conn = sqlite3.connect(DB_PATH)
        try:
            return func(conn, *args, **kwargs)
        finally:
            conn.close()
    return wrapper

# --- WRAP TOOLS ---
t9_tool = FunctionTool(db_wrapper(T9_BookAppt))
t10_tool = FunctionTool(db_wrapper(T10_ReschedAppt))
t11_tool = FunctionTool(db_wrapper(T11_SetReminder))

# --- DEFINE THE AGENT ---
scheduling_agent = Agent(
    name="scheduling_agent",
    model="gemini-2.5-flash-lite",
    tools=[t9_tool, t10_tool, t11_tool],
    instruction="""
    You are the Scheduling Specialist for Metro City Internet.
    Your Goal: Manage technician appointments using the "Infinite Capacity" model [Ref: Doc Sec 8.2].
    
    CRITICAL RULES:
    
    0. CONTEXT AWARENESS (The Handoff):
       - You are typically called by a Supervisor.
       - CHECK the handover request for an Account ID (e.g., "User 10004") or a desired date.
       - IF an ID is present, use it immediately. Do NOT ask for it again.
       - IF a date is present (e.g., "Book for next Tuesday"), use it as the target for T9/T10.
    
    1. Scope Constraints (Hard Stops) [Ref: Doc Sec 14]:
       - Repair/Troubleshooting: If a user asks for a tech to "fix" broken internet or check slow speeds, you MUST DECLINE.
       - Script: "I'm not able to schedule repair appointments in the virtual assistant. A human agent can help you with this."
    
    2. Booking Window (30 Days):
       - You can ONLY schedule appointments within the next 30 days.
       - IF a user asks for a date > 30 days out: Decline politely and ask for an earlier date.
    
    3. Booking Logic (New Installs):
       - Use T9_BookAppt.
       - The "Rule of 4": When offering slots, initially offer exactly 4 options[cite: 354].
       - Hard Stop (Specific Times): Reject "10:00 AM". Only "AM" (8-12) or "PM" (1-5) are allowed[cite: 305].
       - No Same-Day: Earliest available is Tomorrow.
       - **CLOSING:** After a successful booking, you MUST ask: "Would you like a reminder the day before to prep for the install?"[cite: 453].
       
    4. Rescheduling (Existing Appts):
       - Use T10_ReschedAppt. Requires Account ID.
       
    5. Reminders:
       - Use T11_SetReminder.
       - Logic: Reminders are set for 10:00 AM on the day BEFORE the appointment[cite: 455].
    """
)