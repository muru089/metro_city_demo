"""
T11_SetReminder
Function: The "Assistant." Sets a notification flag for the day before service.
Business Logic: Proactive customer service to reduce failed installs.
Customer Use Case:
    Primary: "Remind me the day before the tech arrives.
    Secondary: "Send me a notification the day before."
    Implicit: The Agent asks "Would you like a reminder?" at the end of the call, triggering this tool if the user says "Yes."

Logic Specification
    Input: account_id (Required).
    Logic:
        1. Enable Flag: Update the customer's record to set a reminder_active flag to TRUE.
        2. Calculate Date: Retrieve the scheduled install_date from the database.
            Calculation: Subtract 1 day from the install date (e.g., Install May 13 $\rightarrow$ Reminder May 12)
            Fallback: If no date is found in the DB (e.g., in a testing scenario), default to a generic "day before service starts" message.
        3. Format Output: Confirm the reminder is set for 10:00 AM on that calculated date.
    Output: A success message confirming the specific date and time of the reminder.
"""


import sqlite3
from datetime import datetime, timedelta

def T11_SetReminder(conn, account_id):
    """
    T_SetReminder: Enables the 'Day Before' installation reminder.
    
    Args:
        conn: The active database connection.
        account_id (int or str): The customer's ID.
    
    Returns:
        dict: Confirmation details including the calculated reminder date.
    """
    
    cursor = conn.cursor()
    
    try:
        # --- STEP 1: ENABLE THE REMINDER FLAG ---
        # We update the database to remember the user wants this.
        cursor.execute(
            "UPDATE customer_accounts SET reminder_active = 1 WHERE account_id = ?",
            (account_id,)
        )
        conn.commit()
        
        # Check if account exists
        if cursor.rowcount == 0:
            return {"status": "error", "message": "Account ID not found."}

        # --- STEP 2: CALCULATE THE REMINDER DATE ---
        # We need to know WHEN the install is to calculate "The Day Before".
        cursor.execute(
            "SELECT install_date FROM customer_accounts WHERE account_id = ?",
            (account_id,)
        )
        result = cursor.fetchone()
        
        # Default message if no date is scheduled yet
        reminder_msg = "the day before your appointment"
        
        if result and result[0]:
            install_date_str = result[0]
            
            try:
                # Convert string (2026-05-13) to Date Object
                inst_date = datetime.strptime(install_date_str, "%Y-%m-%d")
                
                # Math: Subtract 1 Day
                remind_date = inst_date - timedelta(days=1)
                
                # Format: "May 12, 2026"
                formatted_date = remind_date.strftime("%B %d, %Y")
                reminder_msg = formatted_date
                
            except ValueError:
                # If date format in DB is weird, keep the default message
                pass
        
        # --- STEP 3: RETURN SUCCESS ---
        # Per Requirement 12.3: Always 10:00 AM 
        return {
            "status": "success",
            "message": f"Reminder set. I'll notify you on {reminder_msg} at 10:00 AM with a prep checklist.",
            "reminder_time": "10:00 AM"
        }

    except sqlite3.Error as e:
        return {"status": "error", "message": str(e)}

# --- TEST SNIPPET ---
if __name__ == "__main__":
    conn = sqlite3.connect(":memory:")
    # Setup dummy table with necessary columns
    conn.execute("CREATE TABLE customer_accounts (account_id INTEGER, reminder_active BOOLEAN, install_date TEXT)")
    
    # Insert Muru with an appointment on May 13th
    conn.execute("INSERT INTO customer_accounts VALUES (10001, 0, '2026-05-13')")
    
    print("--- Test 1: Set Reminder for Muru ---")
    # Expected: Reminder set for May 12, 2026 at 10:00 AM
    print(T11_SetReminder(conn, 10001))
    
    conn.close()