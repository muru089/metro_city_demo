"""
T9_BookAppt
Function: The "Calendar." Books a new installation slot (AM or PM).
Business Logic: 
    1. Only allows booking for future dates (tomorrow or later).
    2. Enforces a 30-Day Booking Window (cannot book more than 30 days out).
    3. Used when T3 says a technician is required.
Customer Use Case:
    Primary: "Schedule the tech for next Tuesday AM" 
    Secondary: "I want a morning appointment." / "Do you have anything in the PM?"
    Constraint: This tool is ONLY used if T3 returns "Technician Install.
    
Logic Specification
    Goal: To simulate a real technician's calendar.
    Scenario A (No Date Provided): The user asks "When can you come?"
        Action: The tool calculates "today" and automatically generates 4 available slots starting 2 days from now.
    Scenario B (Specific Date Provided): The user asks "Can you come on 2026-05-20?"
        Action: The tool checks if that date is:
            a) In the future (Valid).
            b) Within the next 30 days (Valid).
            c) Returns "Confirmed" or "Error" based on these checks.
"""

import sqlite3
from datetime import datetime, timedelta

def T9_BookAppt(conn, date_str=None):
    """
    T_Book: Checks for appointment availability or confirms a specific date.
    
    Args:
        conn: The database connection (not used here, but kept for consistency).
        date_str (str, optional): A specific date the user wants (Format: 'YYYY-MM-DD').
                                  If empty, we return the next 4 available slots.
    
    Returns:
        dict: Contains the 'status' and either a list of 'slots' or a 'confirmation'.
    """
    
    # 1. GET "TODAY" AND "MAX DATE"
    today = datetime.now()
    
    # NEW RULE: Calculate the 30-Day Horizon
    max_date = today + timedelta(days=30)
    
    # --- SCENARIO A: User did NOT provide a date (They want options) ---
    if not date_str:
        # We need to generate the "Rule of 4" (4 slots starting 2 days from now)
        
        slots = []
        
        # Loop 2 times (for 2 days)
        for i in range(2):
            # Calculate the date: Today + 2 days + i (extra days)
            future_date = today + timedelta(days=2 + i)
            
            # Format the date to look nice (e.g., "2026-05-15")
            formatted_date = future_date.strftime("%Y-%m-%d")
            
            # Add a Morning slot (8:00 AM - 12:00 PM)
            slots.append(f"{formatted_date} (8:00 AM - 12:00 PM)")
            
            # Add an Afternoon slot (1:00 PM - 5:00 PM)
            slots.append(f"{formatted_date} (1:00 PM - 5:00 PM)")
            
        # Return the list of 4 generated slots
        return {
            "status": "success",
            "message": "Here are the next available appointments:",
            "available_slots": slots
        }

    # --- SCENARIO B: User PROVIDED a specific date (They want to confirm) ---
    else:
        try:
            # Convert the text string "2026-05-20" into a real Date object
            requested_date = datetime.strptime(date_str, "%Y-%m-%d")
            
            # CHECK 1: Past Date
            if requested_date.date() < today.date():
                return {
                    "status": "error", 
                    "message": "That date is in the past. Please choose a future date."
                }
            
            # CHECK 2: Max Lead Time (NEW 30-DAY RULE)
            if requested_date.date() > max_date.date():
                 return {
                    "status": "error", 
                    "message": f"I can only book appointments within the next 30 days (before {max_date.strftime('%Y-%m-%d')}). Please choose an earlier date."
                }
            
            # If it passes both checks, we "fake" confirm it (assume we are always available)
            return {
                "status": "success",
                "message": f"Appointment confirmed for {date_str}.",
                "booked_date": date_str
            }
            
        except ValueError:
            # This happens if the user types a date we don't understand (like "next tuesday")
            return {
                "status": "error", 
                "message": "Invalid date format. Please use YYYY-MM-DD."
            }

# --- TEST SNIPPET ---
# This block only runs if you play this file directly.
if __name__ == "__main__":
    # We don't need a real DB connection for this tool, so we pass None
    dummy_conn = None
    
    print("--- Test 1: User asks for options ---")
    result_options = T9_BookAppt(dummy_conn)
    # This prints the 4 slots logic
    print(result_options)
    
    print("\n--- Test 2: User picks a specific VALID date (Tomorrow) ---")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    result_confirm = T9_BookAppt(dummy_conn, tomorrow)
    print(result_confirm)
    
    print("\n--- Test 3: User picks a PAST date ---")
    result_fail_past = T9_BookAppt(dummy_conn, "1990-01-01")
    print(result_fail_past)

    print("\n--- Test 4: User picks a date TOO FAR in future (>30 Days) ---")
    future_far = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
    result_fail_far = T9_BookAppt(dummy_conn, future_far)
    print(result_fail_far)