"""
T12_ExecuteMoveCancel
---------------------
WHAT THIS TOOL DOES:
    Executes the final, irreversible database transaction for a Move or Cancel.
    This is the "big red button" -- it only runs AFTER all checks have passed.

    CANCEL path: Marks the current account as CANCELED with an end date.
    MOVE path  : Cancels the old account and creates a brand-new account record
                 at the new address, preserving the customer's name, email,
                 autopay preference, and tenure (loyalty is earned, not reset).

WHY IT MATTERS (Business Logic):
    - The billing gate enforces that balance must be $0 before any action runs.
      This prevents service from being moved/canceled while money is still owed.
    - Move creates a new account_id (MAX + 1) rather than updating in-place.
      This preserves the full history of the old account for audit purposes.
    - Disconnect date for a Move is set to effective_date - 1 day so there is
      no gap in service and no overlap in billing.
    - Called exclusively by move_cancel_loop after STATE 1 (billing gate) and
      STATE 3A/3B (move or cancel decision) have both been resolved.

INPUTS:
    conn           : Database connection (injected automatically).
    account_id     : Customer's current 5-digit ID.
    action         : "MOVE" or "CANCEL" (case-insensitive).
    effective_date : "YYYY-MM-DD". For Move = activation date at new address.
                     For Cancel = the service end date.
    new_address_id : Required for MOVE. The destination address code (e.g., "A11").
    new_plan_name  : Required for MOVE. Plan name to activate (e.g., "Fiber 1 Gig").

OUTPUT:
    Cancel: {"status": "success", "message": "Service canceled effective [date]."}
    Move  : {"status": "success", "message": "Move finalized.", "details": {old/new IDs, dates, address, plan}}
    Error : {"status": "error",   "message": "reason", "code": "BILLING_BLOCK" (if applicable)}
"""

import sqlite3
from datetime import datetime, timedelta


def T12_ExecuteMoveCancel(conn, account_id, action, effective_date,
                          new_address_id=None, new_plan_name=None):
    """
    Executes the final Move or Cancel transaction against the database.
    Enforces the billing gate before any account changes are made.

    Args:
        conn           : Active SQLite database connection (injected by the agent framework).
        account_id     : The customer's current 5-digit ID.
        action         : "MOVE" or "CANCEL".
        effective_date : Target date string in "YYYY-MM-DD" format.
        new_address_id : Destination address code -- required for MOVE (e.g., "A11").
        new_plan_name  : Plan to activate at new address -- required for MOVE.

    Returns:
        dict: Success summary with new account details (Move) or cancellation confirmation.
    """

    cursor = conn.cursor()
    action = action.upper()

    try:
        # =====================================================================
        # STEP 1: BILLING GATE
        # Hard rule: no Move or Cancel is allowed if the account has an
        # outstanding balance. The agent must clear it via T5_PayBill first.
        # =====================================================================
        cursor.execute(
            "SELECT pending_balance FROM customer_accounts WHERE account_id = ?",
            (account_id,)
        )
        result = cursor.fetchone()

        if not result:
            return {"status": "error", "message": "Account ID not found."}

        pending_balance = result[0]

        if pending_balance > 0:
            return {
                "status": "error",
                "code": "BILLING_BLOCK",
                "message": (
                    f"Order blocked. Outstanding balance of ${pending_balance:.2f} "
                    "must be paid before this can proceed."
                )
            }

        # =====================================================================
        # STEP 2A: CANCEL PATH
        # Simple update -- mark the account CANCELED and record the end date.
        # =====================================================================
        if action == "CANCEL":
            cursor.execute(
                "UPDATE customer_accounts SET status = 'CANCELED', end_date = ? WHERE account_id = ?",
                (effective_date, account_id)
            )
            conn.commit()
            return {
                "status": "success",
                "message": (
                    f"Service for account {account_id} has been canceled "
                    f"effective {effective_date}."
                )
            }

        # =====================================================================
        # STEP 2B: MOVE PATH
        # More complex -- cancel the old account, then create a new one.
        # Both operations are inside the same try block so they succeed or
        # fail together (atomic transaction).
        # =====================================================================
        elif action == "MOVE":
            if not new_address_id or not new_plan_name:
                return {
                    "status": "error",
                    "message": "Move requires both new_address_id and new_plan_name."
                }

            # Calculate the disconnect date: one day before the move-in date.
            # Example: moving in May 13 -> old service ends May 12 (no gap, no overlap).
            try:
                start_dt = datetime.strptime(effective_date, "%Y-%m-%d")
                disconnect_date_str = (start_dt - timedelta(days=1)).strftime("%Y-%m-%d")
            except ValueError:
                return {"status": "error", "message": "Invalid date format. Use YYYY-MM-DD."}

            # Fetch the customer details we need to copy to the new account.
            # Note: the schema has no last_name column -- only first_name.
            cursor.execute(
                """
                SELECT first_name, email, autopay_active, tenure_years
                FROM   customer_accounts
                WHERE  account_id = ?
                """,
                (account_id,)
            )
            cust_data = cursor.fetchone()

            if not cust_data:
                return {"status": "error", "message": "Could not retrieve account data."}

            fname, email, autopay, tenure = cust_data

            # New account ID = current highest ID + 1.
            # Simple auto-increment approach (no gaps, always unique).
            cursor.execute("SELECT MAX(account_id) FROM customer_accounts")
            max_id = cursor.fetchone()[0]
            new_account_id = max_id + 1

            # Cancel the old account -- service ends the day before move-in.
            cursor.execute(
                "UPDATE customer_accounts SET status = 'CANCELED', end_date = ? WHERE account_id = ?",
                (disconnect_date_str, account_id)
            )

            # Create the new account at the new address.
            # Balance starts at $0.00 -- no charges carry over to the new account.
            # Tenure and autopay are preserved -- customer earns those, they don't reset.
            cursor.execute(
                """
                INSERT INTO customer_accounts
                    (account_id, first_name, email, address_id, plan_name,
                     pending_balance, status, start_date, autopay_active, tenure_years)
                VALUES (?, ?, ?, ?, ?, 0.00, 'ACTIVE', ?, ?, ?)
                """,
                (new_account_id, fname, email, new_address_id, new_plan_name,
                 effective_date, autopay, tenure)
            )

            conn.commit()

            return {
                "status": "success",
                "message": "Move order finalized.",
                "details": {
                    "old_account_id":    account_id,
                    "old_disconnect_date": disconnect_date_str,
                    "new_account_id":    new_account_id,
                    "new_start_date":    effective_date,
                    "new_address":       new_address_id,
                    "new_plan":          new_plan_name
                }
            }

        else:
            return {"status": "error", "message": "Invalid action. Use 'MOVE' or 'CANCEL'."}

    except sqlite3.Error as e:
        return {"status": "error", "message": str(e)}


# =============================================================================
# TEST BLOCK
# Run this file directly (python T12_ExecuteMoveCancel.py) to test in isolation.
# Uses an in-memory database so no real data is affected.
# =============================================================================
if __name__ == "__main__":
    conn = sqlite3.connect(":memory:")

    # Create table matching the real schema (no last_name column).
    conn.execute("""
        CREATE TABLE customer_accounts (
            account_id      INTEGER,
            first_name      TEXT,
            email           TEXT,
            address_id      TEXT,
            plan_name       TEXT,
            pending_balance REAL,
            status          TEXT,
            start_date      TEXT,
            end_date        TEXT,
            autopay_active  INTEGER,
            tenure_years    REAL
        )
    """)

    # Muru -- active, $0 balance (move should succeed).
    conn.execute(
        "INSERT INTO customer_accounts VALUES (10001,'Muru','muru@mail.com','A01','Fiber 1 Gig',0.00,'ACTIVE','2022-01-01',NULL,1,4.2)"
    )

    # Mike -- active, $82.45 balance (billing gate should block).
    conn.execute(
        "INSERT INTO customer_accounts VALUES (10004,'Mike','mike@mail.com','A04','Fiber 1 Gig',82.45,'ACTIVE','2024-01-01',NULL,1,2.0)"
    )

    print("=== T12_ExecuteMoveCancel -- Manual Test Run ===\n")

    print("--- Test 1: Move Muru to A11 on 2026-05-13 (should PASS) ---")
    print(T12_ExecuteMoveCancel(conn, 10001, "MOVE", "2026-05-13", "A11", "Fiber 1 Gig"))

    print("\n--- Test 2: Verify database -- old account CANCELED, new account ACTIVE ---")
    cur = conn.cursor()
    cur.execute(
        "SELECT account_id, first_name, status, start_date, end_date, address_id "
        "FROM customer_accounts ORDER BY account_id"
    )
    for row in cur.fetchall():
        print(row)

    print("\n--- Test 3: Mike tries to move (billing gate should BLOCK) ---")
    print(T12_ExecuteMoveCancel(conn, 10004, "MOVE", "2026-05-13", "A12", "Fiber 1 Gig"))

    print("\n--- Test 4: Cancel a different account ---")
    conn.execute(
        "INSERT INTO customer_accounts VALUES (10005,'Emily','emily@mail.com','A05','Fiber 300',0.00,'ACTIVE','2023-01-01',NULL,1,3.1)"
    )
    print(T12_ExecuteMoveCancel(conn, 10005, "CANCEL", "2026-06-01"))

    conn.close()
