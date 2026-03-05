"""
T1_GetUpdateContact
Function: Acts as the CRM interface. It retrieves the customer's current contact info or updates it in the database.
Business Logic: Ensures we have a valid email/phone for sending receipts and reminders.
Customer Use Case:  
    Primary: "Update my email address to [email]."
    Secondary (Read Mode): "What email do you have on file?", "Who is the account holder?"
    Secondary (Phone): "Update my phone number." 
    Implicit: The Agent often calls this silently at the start of a "Move" flow to confirm where to send the receipt.

Logic Specification:
    Input: account_id (Required), new_email (Optional).
    Read Mode: If new_email is None, run SELECT email for the ID. Return the email.
    Update Mode: If new_email is provided, run UPDATE customer_accounts and return a success message.
"""

import sqlite3
def T1_GetUpdateContact(conn, account_id, new_email=None):
    """
    T1_GetUpdateContact: Retrieves or updates a customer's contact email.
    
    Args:
        conn: The active database connection object.
        account_id (int or str): The unique ID of the customer (e.g., 10001).
        new_email (str, optional): The NEW email address to save.
                                   - If provided, the tool switches to 'Update Mode'.
                                   - If None (blank), the tool stays in 'Read Mode'.
    
    Returns:
        dict: A summary containing the status and the email address.
    """
    
    # Create the 'cursor' to execute SQL commands.
    cursor = conn.cursor()
    
    # --- MODE A: UPDATE MODE (Write to DB) ---
    # We check: Did the user provide a 'new_email'? If yes, we update.
    if new_email:
        try:
            # Execute the UPDATE command.
            # We use '?' placeholders to prevent hackers from injecting bad code (SQL Injection).
            cursor.execute(
                "UPDATE customer_accounts SET email = ? WHERE account_id = ?", 
                (new_email, account_id)
            )
            
            # IMPORTANT: Save the changes! 
            # Without 'commit()', the database will forget the change immediately.
            conn.commit()
            
            # Check: Did we actually find a row to update?
            # 'rowcount' tells us how many rows were changed.
            if cursor.rowcount == 0:
                return {
                    "status": "error", 
                    "message": "Account ID not found. Update failed."
                }
            # Return success message
                return {
                    "status": "success", 
                    "message": f"Contact email successfully updated to {new_email}", 
                    "email": new_email
                }
            
        except sqlite3.Error as e:
            # Catch database errors (e.g., database is locked)
            return {"status": "error", "message": str(e)}

    # --- MODE B: READ MODE (Read from DB) ---
    # If 'new_email' was None, we just want to see the current info.
    else:
        try:
            # Execute the SELECT query to find the current email.
            cursor.execute(
                "SELECT email FROM customer_accounts WHERE account_id = ?", 
                (account_id,)
            )
            
            # Fetch the first result found.
            result = cursor.fetchone()
            
            # Case 1: Account Found
            if result:
                # Extract the email from the result tuple (e.g., ('muru@mail.com',) -> 'muru@mail.com')
                current_email = result[0]
                return {"status": "success", "email": current_email}
            
            # Case 2: Account Not Found
            else:
                return {"status": "error", "message": "Account ID not found."}
                
        except sqlite3.Error as e:
            return {"status": "error", "message": str(e)}



# --- TEST SNIPPET ---
# This block runs only if you play this file directly. The "Test Snippet" block (if __name__ == "__main__":) is a lifesaver because it lets you test the tool in isolation without needing the full Agent system running.
if __name__ == "__main__":
    # Connect to the database file
    conn = sqlite3.connect("metro_city.db") 
    
    print("--- Test 1: Read Email for Muru (10001) ---")
    # Expected: muru@mail.com
    print(T1_GetUpdateContact(conn, 10001))
    
    print("\n--- Test 2: Update Email for Muru ---")
    # We change it to 'new_muru@test.com'
    print(T1_GetUpdateContact(conn, 10001, "new_muru@test.com"))
    
    print("\n--- Test 3: Verify the Update Worked ---")
    # We read it again to make sure it saved.
    print(T1_GetUpdateContact(conn, 10001))
    
    conn.close()
