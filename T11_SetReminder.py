"""
T11_SetReminder
---------------
WHAT THIS TOOL DOES:
    Sets a "day before install" notification flag on a customer account.
    Calculates the exact reminder date (install_date minus 1 day) and
    confirms the reminder will fire at 10:00 AM on that day.

WHY IT MATTERS (Business Logic):
    - Reduces failed installs caused by customers forgetting their appointment.
    - Proactive customer service: the agent offers this at the end of every
      Move or scheduling flow without waiting for the customer to ask.
    - The 10:00 AM time is fixed per business rules -- no customization needed.
    - Called by moves_agent (after T9 confirms a date) and scheduling_agent
      (after T9 books a new appointment).

INPUTS:
    conn       : Database connection (injected automatically).
    account_id : Customer's 5-digit ID (e.g., 10001).

OUTPUT:
    Success: {"status": "success", "message": "Reminder set for [date] at 10:00 AM.", "reminder_time": "10:00 AM"}
    Error  : {"status": "error",   "message": "reason"}
"""

import sqlite3
from datetime import datetime, timedelta


def T11_SetReminder(conn, account_id):
    """
    Enables the day-before installation reminder for a customer account.
    Calculates the reminder date from the stored install_date.

    Args:
        conn       : Active SQLite database connection (injected by the agent framework).
        account_id : The customer's 5-digit ID (e.g., 10001).

    Returns:
        dict: Confirmation with the specific reminder date and time (always 10:00 AM).
    """

    cursor = conn.cursor()

    try:
        # =====================================================================
        # STEP 1: ENABLE THE REMINDER FLAG
        # Write reminder_active = 1 to the account record.
        # This flag tells the notification system to fire the morning alert.
        # =====================================================================
        cursor.execute(
            "UPDATE customer_accounts SET reminder_active = 1 WHERE account_id = ?",
            (account_id,)
        )
        conn.commit()

        # rowcount = 0 means no rows were updated -- account doesn't exist.
        if cursor.rowcount == 0:
            return {"status": "error", "message": "Account ID not found."}

        # =====================================================================
        # STEP 2: CALCULATE THE REMINDER DATE
        # Look up the scheduled install date, then subtract 1 day to get
        # the "day before" date for the reminder message.
        # =====================================================================
        cursor.execute(
            "SELECT install_date FROM customer_accounts WHERE account_id = ?",
            (account_id,)
        )
        result = cursor.fetchone()

        # Safe fallback if no install date is set yet (edge case in testing).
        reminder_msg = "the day before your appointment"

        if result and result[0]:
            install_date_str = result[0]
            try:
                # Parse "YYYY-MM-DD" string into a date object for math.
                inst_date = datetime.strptime(install_date_str, "%Y-%m-%d")

                # Day before = install date minus 1 day.
                remind_date = inst_date - timedelta(days=1)

                # Format as a friendly string: "May 12, 2026"
                reminder_msg = remind_date.strftime("%B %d, %Y")

            except ValueError:
                # Malformed date in DB -- fallback message is still helpful.
                pass

        # =====================================================================
        # STEP 3: RETURN CONFIRMATION
        # Business rule: reminder always fires at 10:00 AM (never customizable).
        # =====================================================================
        return {
            "status": "success",
            "message": f"Reminder set! You'll receive a notification on {reminder_msg} at 10:00 AM.",
            "reminder_time": "10:00 AM"
        }

    except sqlite3.Error as e:
        return {"status": "error", "message": str(e)}


# =============================================================================
# TEST BLOCK
# Run this file directly (python T11_SetReminder.py) to test in isolation.
# Uses an in-memory database so no real data is affected.
# =============================================================================
if __name__ == "__main__":
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE customer_accounts "
        "(account_id INTEGER, reminder_active INTEGER, install_date TEXT)"
    )

    # Muru has an install scheduled for May 13 -- reminder should fire May 12.
    conn.execute("INSERT INTO customer_accounts VALUES (10001, 0, '2026-05-13')")

    # Bob has no install date set yet -- should still succeed with a generic message.
    conn.execute("INSERT INTO customer_accounts VALUES (10002, 0, NULL)")

    print("=== T11_SetReminder -- Manual Test Run ===\n")

    print("--- Test 1: Muru (install May 13 -> reminder May 12) ---")
    print(T11_SetReminder(conn, 10001))

    print("\n--- Test 2: Bob (no install date -> generic reminder message) ---")
    print(T11_SetReminder(conn, 10002))

    print("\n--- Test 3: Account not found ---")
    print(T11_SetReminder(conn, 99999))

    conn.close()
