"""
T5a_GetBalance 
Function: The "Accountant." Purely reads and reports the customer's current outstanding balance without making any changes. 
Business Logic: Ensures a safe "read-only" operation. This allows the Agent to answer billing inquiries confidently without the risk of accidentally triggering a payment transaction. 
Customer Use Case: 
    Primary: "What is my current balance?" / "How much do I owe?" 
    Secondary: "Is my bill paid off?" 
    Implicit: Called silently by the Agent before T5_PayBill to confirm the amount due, or by A5_Move_Cancel_Agent to check if the user is eligible to close their account.

Logic Specification 
    Input: account_id (Required). 
    Logic: Query: Execute SELECT pending_balance FROM customer_accounts for the specific ID. 
    Validation: If the account ID is not found, return an error. If the ID exists, retrieve the float value of the balance. 
    Action: None (Read-Only). 
    Output: Returns a dictionary containing the status and the exact numeric balance (e.g., {"status": "success", "current_balance": 82.45}).
"""


import sqlite3

def T5a_GetBalance(conn, account_id):
    """
    T5a_GetBalance: Retrieves the current pending balance for a customer.
    
    Args:
        conn: The database connection.
        account_id: The customer's ID.
        
    Returns:
        dict: The current balance status.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT pending_balance FROM customer_accounts WHERE account_id = ?", (account_id,))
    result = cursor.fetchone()
    
    if result:
        return {"status": "success", "current_balance": result[0]}
    else:
        return {"status": "error", "message": "Account ID not found."}