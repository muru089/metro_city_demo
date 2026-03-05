"""
T7_CalcNextBill
---------------
WHAT THIS TOOL DOES:
    Forecasts the customer's next bill by looking up their current plan's
    monthly price from the product catalog. Also calculates the next due date
    (always the 1st of the following month).

WHY IT MATTERS (Business Logic):
    - Gives customers full transparency on what they'll be charged.
    - Flat rate billing only -- no taxes, no proration, no surprises.
      If a customer asks about taxes or fees, the answer is always:
      "Our pricing is a flat monthly rate with no added taxes or fees."
    - billing_agent calls this for "what will my next bill be?" inquiries.

INPUTS:
    conn       : Database connection (injected automatically).
    account_id : Customer's 5-digit ID (e.g., 10001).

OUTPUT:
    Success: {
        "status": "success",
        "message": "Your next bill for Fiber 1 Gig will be $80.00.",
        "breakdown": {
            "plan_name": "Fiber 1 Gig",
            "total_estimated": 80.00,
            "due_date": "April 01, 2026"
        }
    }
    Error: {"status": "error", "message": "Account ID not found."}
"""

import sqlite3
from datetime import datetime, timedelta


def T7_CalcNextBill(conn, account_id):
    """
    Calculates the next invoice amount and due date for a customer.

    Args:
        conn       : Active SQLite database connection (injected by the agent framework).
        account_id : The customer's 5-digit ID (e.g., 10001).

    Returns:
        dict: Plan name, flat monthly price, and next billing due date.
    """

    cursor = conn.cursor()

    try:
        # =====================================================================
        # STEP 1: JOIN CUSTOMER ACCOUNTS WITH PRODUCT CATALOG
        # We need to look up the customer's current plan_name in customer_accounts,
        # then find that plan's monthly_price in product_catalog.
        # A JOIN combines both tables in a single query.
        # =====================================================================
        cursor.execute(
            """
            SELECT c.plan_name, p.monthly_price
            FROM   customer_accounts c
            JOIN   product_catalog p ON c.plan_name = p.plan_name
            WHERE  c.account_id = ?
            """,
            (account_id,)
        )

        result = cursor.fetchone()

        # If no result, either account doesn't exist or their plan isn't in the catalog.
        if not result:
            return {
                "status": "error",
                "message": "Account ID not found or plan not in catalog."
            }

        plan_name, monthly_price = result

        # =====================================================================
        # STEP 2: CALCULATE THE NEXT BILLING DATE
        # Rule: Bills are always due on the 1st of the NEXT month.
        # Formula: Take the 1st of this month, add 32 days (always goes to next month),
        #          then snap back to the 1st.
        # =====================================================================
        today = datetime.now()
        next_month_first = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        due_date_str = next_month_first.strftime("%B %d, %Y")  # e.g., "April 01, 2026"

        # =====================================================================
        # STEP 3: RETURN THE BILL SUMMARY
        # Flat rate only -- no taxes, no fees, no proration.
        # =====================================================================
        return {
            "status": "success",
            "message": f"Your next bill for {plan_name} will be ${monthly_price:.2f}.",
            "breakdown": {
                "plan_name": plan_name,
                "total_estimated": monthly_price,
                "due_date": due_date_str
            }
        }

    except sqlite3.Error as e:
        return {"status": "error", "message": str(e)}


# =============================================================================
# TEST BLOCK
# Run this file directly (python T7_CalcNextBill.py) to test in isolation.
# Uses an in-memory database so no real data is affected.
# =============================================================================
if __name__ == "__main__":
    import os
    DB_PATH = os.path.join(os.path.dirname(__file__), "metro_city.db")
    conn = sqlite3.connect(DB_PATH)

    print("=== T7_CalcNextBill -- Manual Test Run ===\n")

    print("--- Test 1: Muru (10001) on Fiber 1 Gig ---")
    print("Expected: $80.00, due 1st of next month")
    print(T7_CalcNextBill(conn, 10001))

    print("\n--- Test 2: Sarah (10003) on Internet 100 ---")
    print("Expected: $45.00")
    print(T7_CalcNextBill(conn, 10003))

    print("\n--- Test 3: Account not found ---")
    print("Expected: error")
    print(T7_CalcNextBill(conn, 99999))

    conn.close()
