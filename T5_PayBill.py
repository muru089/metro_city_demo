"""
T5_PayBill
----------
WHAT THIS TOOL DOES:
    Processes a payment against a customer's outstanding balance.
    Supports full payment (pay everything) or partial payment (pay a specific amount).

WHY IT MATTERS (Business Logic):
    - This is the "unlock" tool for moves and cancellations. Customers cannot
      move or cancel service until their balance is $0.00. This tool clears it.
    - Called by billing_agent during direct payment requests and by move_cancel_loop
      when a customer agrees to pay their balance inline during a move flow.
    - Always uses the card on file -- no new card details are ever accepted.

INPUTS:
    conn           : Database connection (injected automatically).
    account_id     : Customer's 5-digit ID (e.g., 10004).
    payment_amount : How much to charge (optional).
                     If not provided, defaults to the full outstanding balance.
                     If provided and less than the balance, reduces it by that amount.
                     Overpayment is capped at the balance (no negative bills).

OUTPUT:
    Success: {"status": "success", "message": "...", "paid_amount": 82.45, "remaining_balance": 0.0}
    No bill: {"status": "info",    "message": "No balance due."}
    Error  : {"status": "error",   "message": "reason"}
"""

import sqlite3


def T5_PayBill(conn, account_id, payment_amount=None):
    """
    Processes a payment on a customer account.

    Args:
        conn           : Active SQLite database connection (injected by the agent framework).
        account_id     : The customer's 5-digit ID (e.g., 10004).
        payment_amount : Amount to pay (float, optional). Omit to pay the full balance.

    Returns:
        dict: Payment result including amount paid and remaining balance.
    """

    # A cursor executes SQL commands against the database.
    cursor = conn.cursor()

    try:
        # =====================================================================
        # STEP 1: READ THE CURRENT BALANCE
        # We need to know what they owe before we can process a payment.
        # =====================================================================
        cursor.execute(
            "SELECT pending_balance FROM customer_accounts WHERE account_id = ?",
            (account_id,)
        )
        result = cursor.fetchone()

        if not result:
            return {"status": "error", "message": "Account ID not found."}

        # Extract the balance from the row tuple (e.g., (82.45,) -> 82.45)
        current_balance = result[0]

        # =====================================================================
        # STEP 2: VALIDATE -- IS THERE ANYTHING TO PAY?
        # =====================================================================
        if current_balance == 0.0:
            return {
                "status": "info",
                "message": "Good news! You have no balance due. Your account is fully paid."
            }

        # If no payment_amount given, pay the full balance.
        # This is the most common case: agent calls T5_PayBill without specifying an amount.
        # Cast to float in case the LLM passes the amount as a string (e.g., "82.45").
        amount_to_pay = float(payment_amount) if payment_amount is not None else current_balance

        if amount_to_pay <= 0:
            return {"status": "error", "message": "Payment amount must be a positive number."}

        # =====================================================================
        # STEP 3: CALCULATE THE NEW BALANCE
        # max(0.0, ...) ensures the balance never goes negative.
        # If the customer overpays, we only charge them what they actually owe.
        # =====================================================================
        new_balance = max(0.0, current_balance - amount_to_pay)

        # Actual amount charged = what they owed minus what's left
        # (handles the overpayment case cleanly)
        actual_paid = current_balance - new_balance

        # =====================================================================
        # STEP 4: WRITE THE NEW BALANCE TO THE DATABASE
        # =====================================================================
        cursor.execute(
            "UPDATE customer_accounts SET pending_balance = ? WHERE account_id = ?",
            (new_balance, account_id)
        )

        # commit() makes the change permanent -- without it, the update is lost.
        conn.commit()

        # =====================================================================
        # STEP 5: RETURN THE RECEIPT SUMMARY
        # =====================================================================
        return {
            "status": "success",
            "message": f"Payment of ${actual_paid:.2f} processed successfully.",
            "paid_amount": actual_paid,
            "remaining_balance": new_balance
        }

    except sqlite3.Error as e:
        return {"status": "error", "message": str(e)}


# =============================================================================
# TEST BLOCK
# Run this file directly (python T5_PayBill.py) to test in isolation.
# WARNING: This writes to the real database. Run z_reset_world.py to restore.
# =============================================================================
if __name__ == "__main__":
    import os
    DB_PATH = os.path.join(os.path.dirname(__file__), "metro_city.db")
    conn = sqlite3.connect(DB_PATH)

    print("=== T5_PayBill -- Manual Test Run ===\n")

    print("--- Test 1: Pay Mike's full balance (10004 owes $82.45) ---")
    print("Expected: paid_amount=82.45, remaining_balance=0.0")
    print(T5_PayBill(conn, 10004))

    print("\n--- Test 2: Try to pay again (balance should now be $0) ---")
    print("Expected: info / no balance due")
    print(T5_PayBill(conn, 10004))

    print("\n--- Test 3: Partial payment on Amanda (10009 owes $15.00) ---")
    print("Expected: paid_amount=10.00, remaining_balance=5.00")
    print(T5_PayBill(conn, 10009, 10.00))

    print("\n--- Test 4: Account not found ---")
    print("Expected: error / Account ID not found")
    print(T5_PayBill(conn, 99999))

    conn.close()
