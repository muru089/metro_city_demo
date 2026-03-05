"""
T6_AutopayToggle
Function: The "Switch." Turns Autopay ON or OFF.
Business Logic: Enabling this is often a requirement to get the Fee Waiver (T10).
Customer Use Case:
    Primary (Write): "Turn on autopay." / "Disable autopay." 
    Secondary (Read): "Is my autopay currently on?"
    Implicit: A user might turn this on specifically to pass the fee waiver check (T8)

Logic Specification
Input:
	account_id (Required).
	action (Optional): Accepted values are "ON", "OFF", or None (Blank).
Logic:
	Normalize Input: Convert action to uppercase (e.g., "on" $\to$ "ON").
	Read Mode (If action is Blank):
		Query the autopay_active column for the user.
		If 1 (True), return "ON". If 0 (False), return "OFF".
	Update Mode (If action is "ON" or "OFF"):
		Convert "ON" to True and "OFF" to False.
		Run UPDATE customer_accounts SET autopay_active = [New_Value].
	Validation: If action is anything else (e.g., "Yes"), return an Error.
Output: A dictionary containing the status (success/error), the message, and the boolean state autopay_active.
"""



import sqlite3

def T6_AutopayToggle(conn, account_id, action=None):
    """
    T_Auto: Manages the Autopay setting for a customer.
    
    Args:
        conn: The active database connection object.
        account_id (int or str): The unique ID of the customer (e.g., 10001).
        action (str, optional): The desired action.
                                - "ON": Turn Autopay ON.
                                - "OFF": Turn Autopay OFF.
                                - None (Blank): Just check the current status.
    
    Returns:
        dict: A summary of the current status or the change made.
    """
    
    cursor = conn.cursor()
    
    # Normalize the input (make it uppercase to handle "on", "On", "ON")
    if action:
        action = action.upper()
    
    try:
        # --- MODE A: UPDATE MODE (Change the setting) ---
        if action in ["ON", "OFF"]:
            
            # Convert "ON"/"OFF" to the format our database expects (TRUE/FALSE)
            # In SQLite, Boolean is often stored as 1 (True) or 0 (False).
            # Python automatically handles the conversion when we pass True/False.
            new_status = (action == "ON") 
            
            # Execute the UPDATE command.
            cursor.execute(
                "UPDATE customer_accounts SET autopay_active = ? WHERE account_id = ?", 
                (new_status, account_id)
            )
            
            # Save the change permanently.
            conn.commit()
            
            # Check if the account actually existed.
            if cursor.rowcount == 0:
                return {"status": "error", "message": "Account ID not found."}
            
            return {
                "status": "success", 
                "message": f"Autopay has been turned {action}.", 
                "autopay_active": new_status
            }
            
        # --- MODE B: READ MODE (Check the setting) ---
        elif action is None:
            # Query the current setting.
            cursor.execute(
                "SELECT autopay_active FROM customer_accounts WHERE account_id = ?", 
                (account_id,)
            )
            result = cursor.fetchone()
            
            if result:
                # 'result[0]' will be 1 (True) or 0 (False).
                is_active = bool(result[0]) 
                
                # Convert it back to a readable string for the Agent.
                status_str = "ON" if is_active else "OFF"
                
                return {
                    "status": "success", 
                    "message": f"Autopay is currently {status_str}.",
                    "autopay_active": is_active
                }
            else:
                return {"status": "error", "message": "Account ID not found."}
        
        # --- ERROR TRAP: INVALID INPUT ---
        else:
            return {
                "status": "error", 
                "message": "Invalid action. Please use 'ON', 'OFF', or leave blank."
            }

    except sqlite3.Error as e:
        return {"status": "error", "message": str(e)}

# --- TEST SNIPPET ---
if __name__ == "__main__":
    conn = sqlite3.connect("metro_city.db") 
    
    print("--- Test 1: Check Status (Account 10001) ---")
    print(T6_AutopayToggle(conn, 10001))
    
    print("\n--- Test 2: Turn OFF (Account 10001) ---")
    print(T6_AutopayToggle(conn, 10001, "OFF"))
    
    print("\n--- Test 3: Verify Change ---")
    print(T6_AutopayToggle(conn, 10001))
    
    conn.close()