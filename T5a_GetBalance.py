"""
T5a_GetBalance
--------------
WHAT THIS TOOL DOES:
    A read-only balance check. Returns the customer's current outstanding balance
    without making any changes to the database.

WHY IT MATTERS (Business Logic):
    - Safety first: agents use this to CHECK a balance before deciding whether
      to ask the customer to pay. T5_PayBill is the tool that actually charges --
      these two tools are intentionally separate to prevent accidental charges.
    - The billing gate in move_cancel_loop calls this first to determine if the
      customer can proceed with a move or cancellation.
    - Used any time the customer asks "what do I owe?" or "is my account paid up?"

INPUTS:
    conn       : Database connection (injected automatically).
    account_id : Customer's 5-digit ID (e.g., 10004).

OUTPUT:
    Found    : {"status": "success", "current_balance": 82.45}
    Not found: {"status": "error",   "message": "Account ID not found."}
"""

import sqlite3


def T5a_GetBalance(conn, account_id):
    """
    Read-only balance lookup. Does NOT charge the customer.

    Args:
        conn       : Active SQLite database connection (injected by the agent framework).
        account_id : The customer's 5-digit ID (e.g., 10004).

    Returns:
        dict: The current pending balance as a float.
    """

    # A cursor executes SQL queries against the database.
    cursor = conn.cursor()

    try:
        # Simple SELECT -- we only need the one column we're reporting.
        cursor.execute(
            "SELECT pending_balance FROM customer_accounts WHERE account_id = ?",
            (account_id,)
        )
        result = cursor.fetchone()

        if result:
            # result is a tuple like (82.45,) -- extract the float value
            return {"status": "success", "current_balance": result[0]}
        else:
            return {"status": "error", "message": "Account ID not found."}

    except sqlite3.Error as e:
        return {"status": "error", "message": str(e)}


# =============================================================================
# TEST BLOCK
# Run this file directly (python T5a_GetBalance.py) to test in isolation.
# This is read-only -- safe to run without worrying about changing any data.
# =============================================================================
if __name__ == "__main__":
    import os
    DB_PATH = os.path.join(os.path.dirname(__file__), "metro_city.db")
    conn = sqlite3.connect(DB_PATH)

    print("=== T5a_GetBalance -- Manual Test Run ===\n")

    print("--- Test 1: Muru (10001) -- should have $0.00 ---")
    print(T5a_GetBalance(conn, 10001))

    print("\n--- Test 2: Mike (10004) -- should have $82.45 ---")
    print(T5a_GetBalance(conn, 10004))

    print("\n--- Test 3: Amanda (10009) -- should have $15.00 ---")
    print(T5a_GetBalance(conn, 10009))

    print("\n--- Test 4: Account not found ---")
    print("Expected: error / Account ID not found")
    print(T5a_GetBalance(conn, 99999))

    conn.close()
