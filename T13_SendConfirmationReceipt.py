"""
T13_SendConfirmationReceipt
---------------------------
WHAT THIS TOOL DOES:
    Generates a formatted confirmation receipt at the end of a Move, Cancel,
    or Payment transaction. Looks up the customer's email from the database
    and produces a professional summary block the agent can read aloud or
    reference when saying "I'll send you a confirmation now."

WHY IT MATTERS (Business Logic):
    - Provides the customer with a formal record of what just happened.
    - A random Order Reference ID (e.g., #ORD-9X21B) adds realism and gives
      the customer something to quote if they call back.
    - Receipt content is action-specific: Move includes new address and fees,
      Cancel includes disconnect date, Payment includes amount paid.
    - Called at the END of every completed flow in moves_agent and billing_agent.

SPECIAL NOTE -- NO conn INJECTION:
    Unlike all other tools, T13 opens its own database connection internally.
    This is intentional: the agent framework cannot inject conn into T13 because
    its function signature does not include it (keeping the interface clean for
    the LLM). Do NOT wrap this tool with create_db_tool.

INPUTS:
    account_id  : Customer's 5-digit ID (used to look up email).
    action_type : "MOVE", "CANCEL", or "PAYMENT".
    details     : Dict with action-specific fields:
                  MOVE    -> new_address, start_date, plan_name, monthly_price, install_fee
                  PAYMENT -> amount
                  CANCEL  -> end_date

OUTPUT:
    Success: {"status": "success", "order_ref": "#ORD-XXXXX", "receipt_text": "..."}
    The receipt_text is the full formatted block ready for the agent to present.
"""

import os
import random
import string
import sqlite3


def T13_SendConfirmationReceipt(account_id, action_type, details=None):
    """
    Generates a formatted confirmation receipt for a completed transaction.
    Opens its own DB connection to fetch the customer email.

    Args:
        account_id  : The customer's 5-digit ID (used for email lookup).
        action_type : The type of transaction -- "MOVE", "CANCEL", or "PAYMENT".
        details     : Dict of action-specific context. Can be empty or omitted.

    Returns:
        dict: Order reference ID and the fully formatted receipt text block.
    """

    # =====================================================================
    # STEP 1: LOOK UP THE CUSTOMER'S EMAIL
    # Open a local DB connection -- T13 manages its own connection by design.
    # Fallback to a placeholder if the account isn't found or email is blank.
    # =====================================================================
    db_path = os.path.join(os.path.dirname(__file__), "metro_city.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    customer_email = "No Email On File"  # Safe fallback

    try:
        cursor.execute(
            "SELECT email FROM customer_accounts WHERE account_id = ?",
            (account_id,)
        )
        result = cursor.fetchone()
        if result and result[0]:
            customer_email = result[0]
    except Exception as e:
        # Non-fatal: if email lookup fails, the receipt still generates.
        print(f"[T13] Email lookup failed: {e}")
    finally:
        conn.close()

    # =====================================================================
    # STEP 2: GENERATE A UNIQUE ORDER REFERENCE ID
    # 5-character alphanumeric suffix (e.g., 9X21B) for realism.
    # Not cryptographically secure -- this is a demo identifier only.
    # =====================================================================
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    order_ref = f"#ORD-{suffix}"

    # =====================================================================
    # STEP 3: BUILD THE RECEIPT LINES
    # Each action type has its own section. The agent reads this block
    # to the customer (or references it when saying "email sent").
    # =====================================================================
    if not details:
        details = {}

    lines = []
    lines.append(f"ORDER CONFIRMATION: {order_ref}")
    lines.append(f"Sent to: {customer_email}")
    lines.append("-" * 35)

    if action_type == "MOVE":
        # Fields expected in details: new_address, start_date, plan_name, monthly_price, install_fee
        new_addr = details.get("new_address",   "New Address")
        date     = details.get("start_date",    "TBD")
        plan     = details.get("plan_name",     "Internet Plan")
        price    = details.get("monthly_price", 0.00)
        fee      = details.get("install_fee",   0.00)

        lines.append(f"Action          : Move Service")
        lines.append(f"New Address     : {new_addr}")
        lines.append(f"Activation Date : {date}")
        lines.append(f"New Plan        : {plan}")
        lines.append(f"Monthly Rate    : ${price:.2f}/mo (plus taxes & fees)")
        lines.append(f"Installation    : ${fee:.2f} one-time charge")
        lines.append("-" * 35)
        lines.append("Next Steps:")
        lines.append("  - A prepaid return label has been emailed to you.")
        lines.append("  - Return your old equipment within 14 days to avoid fees.")
        lines.append("  - Technicians cannot accept equipment at the door.")

    elif action_type == "PAYMENT":
        # Fields expected in details: amount
        amount = details.get("amount", 0.00)

        lines.append(f"Action          : Payment Received")
        lines.append(f"Amount Paid     : ${amount:.2f}")
        lines.append(f"Balance         : $0.00 (paid in full)")
        lines.append("-" * 35)
        lines.append("Thank you for your payment!")

    elif action_type == "CANCEL":
        # Fields expected in details: end_date
        date = details.get("end_date", "Immediate")

        lines.append(f"Action          : Service Cancellation")
        lines.append(f"Disconnect Date : {date}")
        lines.append(f"Final Balance   : $0.00 (paid in full)")
        lines.append("-" * 35)
        lines.append("Next Steps:")
        lines.append("  - Use the prepaid return label sent to your email.")
        lines.append("  - Return all equipment within 14 days to avoid unreturned equipment fees.")

    else:
        # Unknown action type -- still return a generic receipt rather than failing.
        lines.append(f"Action: {action_type}")
        lines.append("Transaction completed successfully.")

    # =====================================================================
    # STEP 4: RETURN THE PACKAGED RECEIPT
    # =====================================================================
    return {
        "status":       "success",
        "order_ref":    order_ref,
        "receipt_text": "\n".join(lines)
    }


# =============================================================================
# TEST BLOCK
# Run this file directly (python T13_SendConfirmationReceipt.py) to test.
# Note: email lookup requires metro_city.db to exist with account 10001.
# If DB is missing, the receipt still generates with "No Email On File".
# =============================================================================
if __name__ == "__main__":
    print("=== T13_SendConfirmationReceipt -- Manual Test Run ===\n")

    print("--- Test 1: Move Receipt ---")
    move_details = {
        "new_address":   "100 First St",
        "start_date":    "2026-05-13",
        "plan_name":     "Fiber 1 Gig",
        "monthly_price": 80.00,
        "install_fee":   0.00
    }
    result = T13_SendConfirmationReceipt(10001, "MOVE", move_details)
    print(result["receipt_text"])

    print("\n--- Test 2: Payment Receipt ---")
    pay_details = {"amount": 82.45}
    result = T13_SendConfirmationReceipt(10004, "PAYMENT", pay_details)
    print(result["receipt_text"])

    print("\n--- Test 3: Cancel Receipt ---")
    cancel_details = {"end_date": "2026-06-01"}
    result = T13_SendConfirmationReceipt(10001, "CANCEL", cancel_details)
    print(result["receipt_text"])
