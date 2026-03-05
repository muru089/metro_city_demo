"""
T6_AutopayToggle
----------------
WHAT THIS TOOL DOES:
    Manages the autopay setting on a customer account.
    Has two modes depending on whether an action is provided:

    READ MODE  (no action): Returns whether autopay is currently ON or OFF.
    UPDATE MODE (action="ON" or "OFF"): Switches autopay to the requested state.

WHY IT MATTERS (Business Logic):
    - Autopay ON is one of the three requirements to qualify for the $99 install
      fee waiver (checked by T8_CheckFeeWaiver).
    - A customer who wants to qualify for the waiver might ask to enable autopay
      mid-conversation -- this tool makes that happen instantly.
    - billing_agent calls this when a customer says "turn on autopay" or "disable autopay".

INPUTS:
    conn       : Database connection (injected automatically).
    account_id : Customer's 5-digit ID (e.g., 10001).
    action     : "ON", "OFF", or None.
                 None (default) = read-only status check.
                 Any other value returns an error (prevents accidental changes).

OUTPUT:
    Read   : {"status": "success", "message": "Autopay is currently ON.", "autopay_active": True}
    Update : {"status": "success", "message": "Autopay has been turned OFF.", "autopay_active": False}
    Error  : {"status": "error",   "message": "reason"}
"""

import sqlite3


def T6_AutopayToggle(conn, account_id, action=None):
    """
    Reads or changes the autopay setting for a customer account.

    Args:
        conn       : Active SQLite database connection (injected by the agent framework).
        account_id : The customer's 5-digit ID (e.g., 10001).
        action     : "ON" to enable, "OFF" to disable, or None to check current status.

    Returns:
        dict: Current autopay status and confirmation message.
    """

    cursor = conn.cursor()

    # Normalize input so "on", "On", "ON" all work the same way.
    if action:
        action = action.upper()

    try:
        # =====================================================================
        # UPDATE MODE -- Change the autopay setting
        # =====================================================================
        if action in ["ON", "OFF"]:

            # Convert the string "ON"/"OFF" to a boolean.
            # SQLite stores booleans as 1 (True) or 0 (False).
            # Python's True/False converts automatically when passed to SQLite.
            new_status = (action == "ON")

            cursor.execute(
                "UPDATE customer_accounts SET autopay_active = ? WHERE account_id = ?",
                (new_status, account_id)
            )

            # commit() saves the change permanently.
            conn.commit()

            # If rowcount is 0, no rows were updated -- account doesn't exist.
            if cursor.rowcount == 0:
                return {"status": "error", "message": "Account ID not found."}

            return {
                "status": "success",
                "message": f"Autopay has been turned {action}.",
                "autopay_active": new_status
            }

        # =====================================================================
        # READ MODE -- Check current autopay status without changing anything
        # =====================================================================
        elif action is None:
            cursor.execute(
                "SELECT autopay_active FROM customer_accounts WHERE account_id = ?",
                (account_id,)
            )
            result = cursor.fetchone()

            if result:
                # SQLite returns 1 or 0 -- convert to Python bool for clarity
                is_active = bool(result[0])
                status_str = "ON" if is_active else "OFF"

                return {
                    "status": "success",
                    "message": f"Autopay is currently {status_str}.",
                    "autopay_active": is_active
                }
            else:
                return {"status": "error", "message": "Account ID not found."}

        # =====================================================================
        # INVALID INPUT -- Reject anything that isn't ON, OFF, or None
        # =====================================================================
        else:
            return {
                "status": "error",
                "message": "Invalid action. Please use 'ON', 'OFF', or leave blank to check status."
            }

    except sqlite3.Error as e:
        return {"status": "error", "message": str(e)}


# =============================================================================
# TEST BLOCK
# Run this file directly (python T6_AutopayToggle.py) to test in isolation.
# WARNING: This writes to the real database. Run z_reset_world.py to restore.
# =============================================================================
if __name__ == "__main__":
    import os
    DB_PATH = os.path.join(os.path.dirname(__file__), "metro_city.db")
    conn = sqlite3.connect(DB_PATH)

    print("=== T6_AutopayToggle -- Manual Test Run ===\n")

    print("--- Test 1: Check current status for Muru (10001, autopay=ON) ---")
    print("Expected: autopay_active=True")
    print(T6_AutopayToggle(conn, 10001))

    print("\n--- Test 2: Turn autopay OFF for Muru ---")
    print("Expected: success, autopay_active=False")
    print(T6_AutopayToggle(conn, 10001, "OFF"))

    print("\n--- Test 3: Verify the change ---")
    print("Expected: autopay_active=False")
    print(T6_AutopayToggle(conn, 10001))

    print("\n--- Test 4: Invalid action string ---")
    print("Expected: error / invalid action")
    print(T6_AutopayToggle(conn, 10001, "MAYBE"))

    conn.close()
