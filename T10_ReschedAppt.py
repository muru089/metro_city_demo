"""
T10_ReschedAppt
Function: The "Calendar Update." Moves an existing appointment to a new slot.
Business Logic: 
    1. Validates the new date is in the future.
    2. Enforces a 30-Day Scheduling Window (cannot move to a date > 30 days out).
Customer Use Case:
    Primary: "I need to reschedule my appointment." 
    Secondary: "Can I move my install to a different day?"
    Constraint: Logic prevents moving to "Today", the past, or too far in the future. 

Logic Specification
	Input:
		account_id (Required).
		new_date (Required, format "YYYY-MM-DD").
		new_slot (Required, "AM" or "PM").
	Logic:
		1. Validate Date: 
            - Must be in the future (tomorrow or later).
            - Must be within the next 30 days.
		2. Validate Slot: The slot must strictly be "AM" or "PM".
		3. Update Database: Update the install_date and install_slot columns for that customer.
	Output: A success message confirming the new appointment details.
"""

import sqlite3
from datetime import datetime, timedelta

def T10_ReschedAppt(conn, account_id, new_date_str, new_slot):
    """
    T_Resched: Updates the appointment date and time for a customer.
    
    Args:
        conn: The active database connection.
        account_id (int or str): The customer's ID.
        new_date_str (str): The desired date (Format: 'YYYY-MM-DD').
        new_slot (str): The desired window ('AM' or 'PM').
    
    Returns:
        dict: Status of the reschedule attempt.
    """
    
    cursor = conn.cursor()
    
    # --- STEP 1: VALIDATE THE DATE ---
    try:
        # Convert string to a Date object
        requested_date = datetime.strptime(new_date_str, "%Y-%m-%d")
        today = datetime.now()
        
        # NEW RULE: Calculate the 30-Day Horizon
        max_date = today + timedelta(days=30)
        
        # Rule A: Date must be in the future (Tomorrow or later)
        if requested_date.date() <= today.date():
            return {
                "status": "error", 
                "message": "Appointments can only be scheduled for future dates (tomorrow or later)."
            }

        # Rule B: Max 30 Days (NEW RULE)
        if requested_date.date() > max_date.date():
            return {
                "status": "error", 
                "message": f"I can only reschedule within the next 30 days (before {max_date.strftime('%Y-%m-%d')}). Please choose an earlier date."
            }
            
    except ValueError:
        return {"status": "error", "message": "Invalid date format. Please use YYYY-MM-DD."}

    # --- STEP 2: VALIDATE THE SLOT ---
    # Normalize input to uppercase
    slot_clean = new_slot.upper().strip()
    
    # Rule: Slot must be AM or PM
    if slot_clean not in ["AM", "PM"]:
        return {
            "status": "error", 
            "message": "Invalid time slot. Please choose 'AM' (8-12) or 'PM' (1-5)."
        }

    # --- STEP 3: UPDATE THE DATABASE ---
    try:
        cursor.execute(
            "UPDATE customer_accounts SET install_date = ?, install_slot = ? WHERE account_id = ?",
            (new_date_str, slot_clean, account_id)
        )
        conn.commit()
        
        # Check if the account actually exists
        if cursor.rowcount == 0:
            return {"status": "error", "message": "Account ID not found."}
            
        return {
            "status": "success",
            "message": f"Appointment successfully rescheduled to {new_date_str} in the {slot_clean}.",
            "details": {"date": new_date_str, "slot": slot_clean}
        }

    except sqlite3.Error as e:
        return {"status": "error", "message": str(e)}

# --- TEST SNIPPET ---
if __name__ == "__main__":
    conn = sqlite3.connect(":memory:")
    # Setup dummy table with the new columns
    conn.execute("CREATE TABLE customer_accounts (account_id INTEGER, install_date TEXT, install_slot TEXT)")
    conn.execute("INSERT INTO customer_accounts VALUES (10001, '2026-05-12', 'AM')")
    
    print("--- Test 1: Reschedule Valid Future Date (Tomorrow) ---")
    # We use a dynamic date so this test always works
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    print(T10_ReschedAppt(conn, 10001, tomorrow, "pm"))
    
    print("\n--- Test 2: Try to Reschedule to the Past ---")
    print(T10_ReschedAppt(conn, 10001, "2020-01-01", "AM"))

    print("\n--- Test 3: Try to Reschedule TOO FAR in Future (>30 Days) ---")
    future_far = (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d")
    print(T10_ReschedAppt(conn, 10001, future_far, "AM"))
    
    conn.close()