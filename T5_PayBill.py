"""
T5_PayBill
Function: The "Cashier." Processes a payment for the specific pending balance amount.
Business Logic: Critical for the "Move Gate"—customers cannot move/cancel until this tool clears their balance to $0.00.
Customer Use Case:
    Primary: "Pay my bill." / "Pay my balance." 
    Secondary: "Use the card on file to clear the balance."
    Implicit (The Gatekeeper): When a user asks to "Move," the Agent checks the balance. If > $0, the Agent automatically triggers this payment flow. 

Logic Specification
    Input: account_id (Required), payment_amount (Optional).
    Logic:
        Check Balance: Query the current pending_balance for the customer.
        Validation:
            If balance is $0.00, return "No balance due."
            If payment_amount is not provided, assume the customer wants to pay the full balance.
            If payment_amount < pending_balance, reduce the balance by that amount (partial pay).
            If payment_amount >= pending_balance, set balance to 0 (full pay).
        Action: Run UPDATE customer_accounts SET pending_balance = [New_Balance].
    Output: Returns a success message confirming the amount paid and the remaining balance (if any).
"""
    
import sqlite3

def T5_PayBill(conn, account_id, payment_amount=None):
    """
    T_Pay: Processes a payment for a customer account.
    
    Args:
        conn: The active database connection object.
        account_id (int or str): The ID of the customer (e.g., 10004).
        payment_amount (float, optional): The amount the user wants to pay.
                                          If this is blank (None), we assume they want to pay the FULL balance.
    
    Returns:
        dict: A summary of what happened (status, amount paid, remaining balance).
    """
    
    # Create a 'cursor'. Think of this as the robot arm that executes SQL commands.
    cursor = conn.cursor()
    
    try:
        # --- STEP 1: CHECK CURRENT BALANCE ---
        # We need to know how much they owe BEFORE we can pay it.
        # We run a SELECT query to get the 'pending_balance' for this specific ID.
        cursor.execute(
            "SELECT pending_balance FROM customer_accounts WHERE account_id = ?", 
            (account_id,)
        )
        result = cursor.fetchone() # Fetch the first (and only) result.
        
        # If result is empty (None), it means that Account ID doesn't exist.
        if not result:
            return {"status": "error", "message": "Account ID not found."}
            
        # Extract the balance number from the result tuple (e.g., (82.45,) -> 82.45)
        current_balance = result[0]
        
        # --- STEP 2: VALIDATE THE PAYMENT ---
        
        # Case A: They don't owe anything.
        if current_balance == 0.0:
            return {
                "status": "info", 
                "message": "Good news! You have no balance due. Your account is fully paid."
            }
        
        # Case B: Determine how much to pay.
        # If 'payment_amount' was provided by the user, use it.
        # If it is None (user said "Pay my bill"), use the full 'current_balance'.
        amount_to_pay = payment_amount if payment_amount is not None else current_balance
        
        # Sanity Check: You can't pay a negative amount.
        if amount_to_pay <= 0:
             return {"status": "error", "message": "Payment amount must be positive."}

        # --- STEP 3: DO THE MATH ---
        
        # Calculate the New Balance.
        # Logic: Current Balance minus Payment.
        # We use 'max(0.0, ...)' to ensure the balance never drops below zero (no negative bills).
        new_balance = max(0.0, current_balance - amount_to_pay)
        
        # Calculate the "Actual" amount paid.
        # Why? If a user tries to pay $100 on a $50 bill, we only charge them $50.
        actual_paid = current_balance - new_balance 
        
        # --- STEP 4: UPDATE THE DATABASE ---
        
        # Run the UPDATE command to save the new balance to the table.
        cursor.execute(
            "UPDATE customer_accounts SET pending_balance = ? WHERE account_id = ?", 
            (new_balance, account_id)
        )
        
        # IMPORTANT: 'commit()' saves the changes permanently. 
        # Without this, the payment would disappear when the script ends.
        conn.commit()
        
        # --- STEP 5: RETURN THE RECEIPT ---
        return {
            "status": "success",
            "message": f"Payment of ${actual_paid:.2f} processed successfully.",
            "paid_amount": actual_paid,
            "remaining_balance": new_balance
        }

    except sqlite3.Error as e:
        # If the database crashes or locks, this catches the error.
        return {"status": "error", "message": str(e)}

# --- TEST SNIPPET ---
# This block runs only if you play this file directly to test it.
if __name__ == "__main__":
    # Connect to the database file
    conn = sqlite3.connect("metro_city.db")
    
    print("--- Test 1: Paying Mike's Bill (Account 10004) ---")
    # Mike owes $82.45. We pass None, so it should pay the full $82.45.
    print(T5_PayBill(conn, 10004))
    
    print("\n--- Test 2: Paying Muru (Account 10001) ---")
    # Muru owes $0.00. The tool should say "No balance due".
    print(T5_PayBill(conn, 10001))
    
    # Close the connection when done testing
    conn.close()