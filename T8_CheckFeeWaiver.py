"""
T8_CheckFeeWaiver
-----------------
WHAT THIS TOOL DOES:
    Evaluates whether a customer qualifies for a $0 installation fee.
    This is a strict "AND gate" -- ALL THREE rules must pass.
    If any single rule fails, the $99 fee applies.

    Rule A -- Tenure:   Customer must have been with Metro City for MORE than 3 years.
    Rule B -- Autopay:  Customer must have autopay currently active.
    Rule C -- History:  Customer must NOT have used a waiver in the last 12 months.

WHY IT MATTERS (Business Logic):
    - The $99 fee is standard for any tech-install appointment.
    - Loyal, trusted customers (long tenure + autopay) get rewarded with a free install.
    - The tool always returns the SPECIFIC reason for failure -- never a vague "you don't qualify."
      This helps the agent explain clearly, and gives the customer a path to qualify next time.
    - Called by move_cancel_loop (during Technician Install flows), billing_agent (discount inquiries),
      and sales_agent (when a customer asks for a promotion or discount).

INPUTS:
    conn       : Database connection (injected automatically).
    account_id : Customer's 5-digit ID (e.g., 10001).

OUTPUT:
    Waiver approved: {"status": "success", "waiver_applied": True,  "installation_fee": 0.00,  "message": "..."}
    Waiver denied  : {"status": "success", "waiver_applied": False, "installation_fee": 99.00, "message": "...reason..."}
    Error          : {"status": "error",   "message": "reason"}

NOTE: status="success" on a denied waiver is intentional -- the tool ran successfully,
it just determined the customer doesn't qualify. The waiver_applied flag is the real signal.
"""

import sqlite3
from datetime import datetime, timedelta


def T8_CheckFeeWaiver(conn, account_id):
    """
    Checks if a customer qualifies for the $99 installation fee waiver.
    All three rules (tenure, autopay, waiver history) must pass.

    Args:
        conn       : Active SQLite database connection (injected by the agent framework).
        account_id : The customer's 5-digit ID (e.g., 10001).

    Returns:
        dict: Waiver result, final fee amount, and specific reason if denied.
    """

    cursor = conn.cursor()

    # The standard installation fee -- applied when any rule fails.
    INSTALL_FEE = 99.00

    try:
        # Fetch the three data points we need to evaluate the rules.
        cursor.execute(
            """
            SELECT tenure_years, autopay_active, last_waiver_date
            FROM   customer_accounts
            WHERE  account_id = ?
            """,
            (account_id,)
        )
        result = cursor.fetchone()

        if not result:
            return {"status": "error", "message": "Account ID not found."}

        tenure_years, autopay_active, last_waiver_date = result

        # =====================================================================
        # EVALUATE THE THREE RULES
        # We collect all failure reasons so the agent can explain each one.
        # This is better than stopping at the first failure -- the customer
        # might need to fix multiple things to qualify in the future.
        # =====================================================================
        reasons_for_failure = []

        # Rule A: Tenure must be MORE than 3 years (not equal to 3)
        if tenure_years <= 3:
            reasons_for_failure.append(
                f"Tenure is {tenure_years} years (must be greater than 3 years)"
            )

        # Rule B: Autopay must be active
        # SQLite stores booleans as 1 (True) or 0 (False)
        if not autopay_active:
            reasons_for_failure.append("Autopay is not active on your account")

        # Rule C: No waiver used in the last 12 months
        # If last_waiver_date is NULL (never used), this rule passes automatically.
        if last_waiver_date:
            try:
                last_date = datetime.strptime(last_waiver_date, "%Y-%m-%d")
                one_year_ago = datetime.now() - timedelta(days=365)

                if last_date > one_year_ago:
                    reasons_for_failure.append(
                        "A waiver was already used within the last 12 months"
                    )
            except ValueError:
                # If the date in the DB is malformed, give the benefit of the doubt.
                pass

        # =====================================================================
        # DETERMINE THE OUTCOME
        # =====================================================================
        if not reasons_for_failure:
            # All rules passed -- waiver approved
            return {
                "status": "success",
                "waiver_applied": True,
                "installation_fee": 0.00,
                "message": "Great news -- your installation fee is waived!"
            }
        else:
            # One or more rules failed -- fee applies, with full explanation
            reason_str = "; ".join(reasons_for_failure)
            return {
                "status": "success",   # Tool ran successfully -- just the waiver that failed
                "waiver_applied": False,
                "installation_fee": INSTALL_FEE,
                "message": f"The ${INSTALL_FEE:.2f} installation fee applies because: {reason_str}."
            }

    except sqlite3.Error as e:
        return {"status": "error", "message": str(e)}


# =============================================================================
# TEST BLOCK
# Run this file directly (python T8_CheckFeeWaiver.py) to test in isolation.
# Uses an in-memory database so no real data is affected.
# =============================================================================
if __name__ == "__main__":
    # Build a minimal in-memory DB for testing -- no need for the full metro_city.db
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE customer_accounts "
        "(account_id INTEGER, tenure_years REAL, autopay_active INTEGER, last_waiver_date TEXT)"
    )

    # Muru: 4.2yr tenure, autopay ON, no waiver history -> should PASS all 3 rules
    conn.execute("INSERT INTO customer_accounts VALUES (10001, 4.2, 1, NULL)")

    # John: 0.5yr tenure, autopay OFF -> should FAIL rules A and B
    conn.execute("INSERT INTO customer_accounts VALUES (10002, 0.5, 0, NULL)")

    # Emily: 3.1yr tenure, autopay ON, waiver used 2 months ago -> FAIL rules A and C
    from datetime import datetime, timedelta
    recent_waiver = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
    conn.execute(f"INSERT INTO customer_accounts VALUES (10005, 3.1, 1, '{recent_waiver}')")

    print("=== T8_CheckFeeWaiver -- Manual Test Run ===\n")

    print("--- Test 1: Muru (should PASS -- waiver approved) ---")
    print(T8_CheckFeeWaiver(conn, 10001))

    print("\n--- Test 2: John (should FAIL -- tenure + autopay) ---")
    print(T8_CheckFeeWaiver(conn, 10002))

    print("\n--- Test 3: Emily (should FAIL -- tenure + recent waiver) ---")
    print(T8_CheckFeeWaiver(conn, 10005))

    conn.close()
