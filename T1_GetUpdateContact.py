"""
T1_GetUpdateContact
-------------------
WHAT THIS TOOL DOES:
    Acts as the lightweight CRM interface for the system.
    It can do two things depending on whether a new email is provided:

    READ MODE  (new_email is empty): Returns the customer's current email and first name.
    UPDATE MODE (new_email provided): Saves a new email address to the account.

WHY IT MATTERS (Business Logic):
    - The root_agent calls this in READ mode right after authentication to
      greet the customer by name and confirm their contact info.
    - Billing and Move agents use the email stored here to send receipts via T13.
    - If a customer says "update my email", this is the tool that makes it happen.

INPUTS:
    conn       : Database connection (injected automatically -- agents don't see this).
    account_id : 5-digit customer ID (e.g., 10001).
    new_email  : The new email address to save (optional).
                 If not provided, the tool runs in read-only mode.

OUTPUT:
    Read mode  : {"status": "success", "email": "customer@email.com", "first_name": "Muru"}
    Update mode: {"status": "success", "message": "Updated to ...", "email": "new@email.com"}
    Error      : {"status": "error", "message": "reason"}

BUG FIXED (original file):
    The success return in UPDATE mode was indented inside the error-check block,
    making it unreachable. The indentation has been corrected.
"""

import sqlite3


def T1_GetUpdateContact(conn, account_id, new_email=None):
    """
    Retrieves or updates a customer's contact email address.

    Args:
        conn       : Active SQLite database connection (injected by the agent framework).
        account_id : The customer's 5-digit ID (e.g., 10001).
        new_email  : New email to save. If None, runs in read-only mode.

    Returns:
        dict: See module docstring for return format.
    """

    # A cursor is the "hand" that executes SQL commands against the database.
    cursor = conn.cursor()

    # =========================================================================
    # UPDATE MODE -- Save a new email address
    # Triggered when the agent passes a new_email value.
    # =========================================================================
    if new_email:
        try:
            # UPDATE the email column for this specific account.
            # The '?' placeholders prevent SQL injection -- never concatenate user input directly.
            cursor.execute(
                "UPDATE customer_accounts SET email = ? WHERE account_id = ?",
                (new_email, account_id)
            )

            # commit() saves the change permanently.
            # Without this line, the change disappears when the program ends.
            conn.commit()

            # rowcount tells us how many rows were affected.
            # If it's 0, the account_id didn't exist in the database.
            if cursor.rowcount == 0:
                return {
                    "status": "error",
                    "message": "Account ID not found. Update failed."
                }

            # rowcount > 0 means the update succeeded. Return confirmation.
            return {
                "status": "success",
                "message": f"Contact email successfully updated to {new_email}",
                "email": new_email
            }

        except sqlite3.Error as e:
            return {"status": "error", "message": str(e)}

    # =========================================================================
    # READ MODE -- Retrieve current contact info
    # Triggered when new_email is None (the default). No data is changed.
    # =========================================================================
    else:
        try:
            # SELECT the customer's email and first name so the agent can greet them.
            cursor.execute(
                "SELECT email, first_name FROM customer_accounts WHERE account_id = ?",
                (account_id,)
            )

            result = cursor.fetchone()

            if result:
                # Unpack the tuple (e.g., ('muru@mail.com', 'Muru'))
                email, first_name = result
                return {
                    "status": "success",
                    "email": email,
                    "first_name": first_name
                }
            else:
                return {"status": "error", "message": "Account ID not found."}

        except sqlite3.Error as e:
            return {"status": "error", "message": str(e)}


# =============================================================================
# TEST BLOCK
# Run this file directly (python T1_GetUpdateContact.py) to test in isolation.
# =============================================================================
if __name__ == "__main__":
    import os
    DB_PATH = os.path.join(os.path.dirname(__file__), "metro_city.db")
    conn = sqlite3.connect(DB_PATH)

    print("=== T1_GetUpdateContact -- Manual Test Run ===\n")

    print("--- Test 1: Read email + name for Muru (10001) ---")
    print("Expected: muru@mail.com, first_name=Muru")
    print(T1_GetUpdateContact(conn, 10001))

    print("\n--- Test 2: Update email for Muru ---")
    print("Expected: success with new email")
    print(T1_GetUpdateContact(conn, 10001, "muru_updated@mail.com"))

    print("\n--- Test 3: Verify the update saved ---")
    print("Expected: muru_updated@mail.com")
    print(T1_GetUpdateContact(conn, 10001))

    print("\n--- Test 4: Account ID that doesn't exist ---")
    print("Expected: error / Account ID not found")
    print(T1_GetUpdateContact(conn, 99999))

    conn.close()
