"""
T10_ReschedAppt
---------------
WHAT THIS TOOL DOES:
    Moves an existing technician appointment to a new date and time slot.
    Two validations run before any database update is made:
    - The new date must be tomorrow or later (no same-day or past rescheduling).
    - The new date must be within the next 30 days (no far-future booking).

WHY IT MATTERS (Business Logic):
    - A customer whose schedule changed needs a quick way to move their install.
    - The 30-day window prevents booking so far out that the slot becomes meaningless.
    - Called by scheduling_agent when a customer says "move my appointment" or
      "can we do Thursday instead?"

INPUTS:
    conn         : Database connection (injected automatically).
    account_id   : Customer's 5-digit ID (e.g., 10001).
    new_date_str : The desired new date in "YYYY-MM-DD" format.
    new_slot     : "AM" (8AM-12PM) or "PM" (1PM-5PM).

OUTPUT:
    Success: {"status": "success", "message": "...confirmed...", "details": {"date": ..., "slot": ...}}
    Error  : {"status": "error",   "message": "reason"}
"""

import sqlite3
from datetime import datetime, timedelta


def T10_ReschedAppt(conn, account_id, new_date_str, new_slot):
    """
    Moves a customer's technician appointment to a new date and slot.

    Args:
        conn         : Active SQLite database connection (injected by the agent framework).
        account_id   : The customer's 5-digit ID (e.g., 10001).
        new_date_str : Desired date string in "YYYY-MM-DD" format.
        new_slot     : Desired time window -- "AM" (8AM-12PM) or "PM" (1PM-5PM).

    Returns:
        dict: Confirmation with the finalized date and slot, or an error reason.
    """

    cursor = conn.cursor()

    # =====================================================================
    # STEP 1: VALIDATE THE DATE
    # Two rules apply: must be in the future, and within the 30-day window.
    # =====================================================================
    try:
        # Parse the incoming string into a proper date object for comparison.
        requested_date = datetime.strptime(new_date_str, "%Y-%m-%d")
        today = datetime.now()
        max_date = today + timedelta(days=30)

        # Rule A: Date must be tomorrow or later -- no same-day or past scheduling.
        if requested_date.date() <= today.date():
            return {
                "status": "error",
                "message": "Appointments can only be scheduled for future dates (tomorrow or later)."
            }

        # Rule B: Date must be within 30 days -- no bookings too far into the future.
        if requested_date.date() > max_date.date():
            return {
                "status": "error",
                "message": (
                    f"I can only reschedule within the next 30 days "
                    f"(before {max_date.strftime('%Y-%m-%d')}). Please choose an earlier date."
                )
            }

    except ValueError:
        # The date string was not in a parseable format.
        return {"status": "error", "message": "Invalid date format. Please use YYYY-MM-DD."}

    # =====================================================================
    # STEP 2: VALIDATE THE SLOT
    # Only "AM" or "PM" are accepted -- normalize first to handle "am", "Pm", etc.
    # =====================================================================
    slot_clean = new_slot.upper().strip()

    if slot_clean not in ["AM", "PM"]:
        return {
            "status": "error",
            "message": "Invalid time slot. Please choose 'AM' (8AM-12PM) or 'PM' (1PM-5PM)."
        }

    # =====================================================================
    # STEP 3: UPDATE THE DATABASE
    # Both validations passed -- write the new date and slot to the account.
    # =====================================================================
    try:
        cursor.execute(
            "UPDATE customer_accounts SET install_date = ?, install_slot = ? WHERE account_id = ?",
            (new_date_str, slot_clean, account_id)
        )
        conn.commit()

        # rowcount = 0 means no rows matched the account_id -- account doesn't exist.
        if cursor.rowcount == 0:
            return {"status": "error", "message": "Account ID not found."}

        return {
            "status": "success",
            "message": f"Appointment successfully rescheduled to {new_date_str} ({slot_clean}).",
            "details": {"date": new_date_str, "slot": slot_clean}
        }

    except sqlite3.Error as e:
        return {"status": "error", "message": str(e)}


# =============================================================================
# TEST BLOCK
# Run this file directly (python T10_ReschedAppt.py) to test in isolation.
# Uses an in-memory database so no real data is affected.
# =============================================================================
if __name__ == "__main__":
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE customer_accounts "
        "(account_id INTEGER, install_date TEXT, install_slot TEXT)"
    )
    conn.execute("INSERT INTO customer_accounts VALUES (10001, '2026-05-12', 'AM')")

    print("=== T10_ReschedAppt -- Manual Test Run ===\n")

    print("--- Test 1: Valid reschedule to tomorrow (should PASS) ---")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    print(T10_ReschedAppt(conn, 10001, tomorrow, "pm"))

    print("\n--- Test 2: Past date (should FAIL -- not in future) ---")
    print(T10_ReschedAppt(conn, 10001, "2020-01-01", "AM"))

    print("\n--- Test 3: Too far in the future (should FAIL -- beyond 30 days) ---")
    far_future = (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d")
    print(T10_ReschedAppt(conn, 10001, far_future, "AM"))

    print("\n--- Test 4: Invalid slot string (should FAIL) ---")
    print(T10_ReschedAppt(conn, 10001, tomorrow, "NOON"))

    conn.close()
