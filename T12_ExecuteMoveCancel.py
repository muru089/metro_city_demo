"""
T12_ExecuteMoveCancel
Function: The "Big Red Button." This performs the atomic transaction of closing the old account and creating the new one (Move) or just closing the account (Cancel). This tool we built effectively "clones" the customer's identity into the new account so they don't have to start over - Personal Info (Name, Email), Loyalty Status, Preference (Autopay).
Business Logic:
    Billing Gate: Fails immediately if Balance > $0.
    Move: Disconnects old address on Date - 1 and activates new address on Date.
Customer Use Case:
    Use Case A (Move): "I am moving to [Address] on [Date]." 
    Use Case B (Transfer): "Transfer my service to my new house."
    Use Case C (Cancel): "Cancel my internet." / "Stop my service." 
    Use Case D (Disconnect): "I want to disconnect my line."

Logic Specification
    Input:
        account_id (Required).
        action (Required: "MOVE" or "CANCEL").
        effective_date (Required: The Move-In Date or Cancellation Date).
        new_address_id (Required only for MOVE).
        new_plan_name (Required only for MOVE).
    Billing Gate (The Guardrail):
        Check pending_balance for the account.
        Rule: If pending_balance > 0, STOP. Return error: "Balance must be paid first." 
    Logic (Branch A: CANCEL):
        Update the current row: Set status = 'CANCELED' and end_date = effective_date.
    Logic (Branch B: MOVE):
        Step 1 (Disconnect Old): Calculate disconnect_date = (effective_date - 1 Day). Update old row to 'CANCELED' with this end date.
    Step 2 (Create New): Insert a new row into customer_accounts.
        New ID: Generate max(account_id) + 1 (e.g., 10001 $\rightarrow$ 10021).
        Attributes: Copy Name/Contact from old account. Set address_id = new_address_id, plan_name = new_plan_name, status = 'ACTIVE', start_date = effective_date.
    Output: A detailed success message including the New Account ID (for Moves) and the finalized dates.
"""




import sqlite3
from datetime import datetime, timedelta

def T12_ExecuteMoveCancel(conn, account_id, action, effective_date, new_address_id=None, new_plan_name=None):
    """
    T_ExecMoveCancel: Executes the final Move or Cancel order.
    Enforces Billing Logic and updates Account Status.
    
    Args:
        conn: The active database connection.
        account_id (int/str): The customer's CURRENT ID.
        action (str): "MOVE" or "CANCEL".
        effective_date (str): YYYY-MM-DD (Start Date for Move, or End Date for Cancel).
        new_address_id (str): Required for MOVE (e.g., 'B01').
        new_plan_name (str): Required for MOVE (e.g., 'Fiber 1 Gig').
    
    Returns:
        dict: Success summary with new account details.
    """
    
    cursor = conn.cursor()
    action = action.upper()
    
    try:
        # --- STEP 1: THE BILLING GATE ---
        # Requirement 10.1 / 10.2: Cannot proceed if balance > 0.
        cursor.execute("SELECT pending_balance FROM customer_accounts WHERE account_id = ?", (account_id,))
        result = cursor.fetchone()
        
        if not result:
            return {"status": "error", "message": "Account ID not found."}
            
        pending_balance = result[0]
        
        if pending_balance > 0:
            return {
                "status": "error", 
                "code": "BILLING_BLOCK",
                "message": f"Order blocked. Outstanding balance of ${pending_balance:.2f} must be paid first."
            }

        # --- STEP 2: HANDLE 'CANCEL' ACTION ---
        if action == "CANCEL":
            cursor.execute(
                "UPDATE customer_accounts SET status = 'CANCELED', end_date = ? WHERE account_id = ?",
                (effective_date, account_id)
            )
            conn.commit()
            return {
                "status": "success",
                "message": f"Service for Account {account_id} has been canceled effective {effective_date}."
            }

        # --- STEP 3: HANDLE 'MOVE' ACTION ---
        elif action == "MOVE":
            if not new_address_id or not new_plan_name:
                return {"status": "error", "message": "Move requires new_address_id and new_plan_name."}

            # A. Calculate Disconnect Date (Start Date - 1 Day)
            # Section 10.1: "Disconnect Date is set to 1 Day Prior to Activation Date"
            try:
                start_dt = datetime.strptime(effective_date, "%Y-%m-%d")
                disconnect_dt = start_dt - timedelta(days=1)
                disconnect_date_str = disconnect_dt.strftime("%Y-%m-%d")
            except ValueError:
                return {"status": "error", "message": "Invalid date format. Use YYYY-MM-DD."}

            # B. Fetch Current Customer Details (to copy to new account)
            # We assume a simple schema: First, Last, Email. 
            # In a real app, we'd select all columns dynamically.
            cursor.execute(
                "SELECT first_name, last_name, email, autopay_active, tenure_years FROM customer_accounts WHERE account_id = ?",
                (account_id,)
            )
            cust_data = cursor.fetchone()
            fname, lname, email, autopay, tenure = cust_data

            # C. Generate New Account ID (Max + 1)
            cursor.execute("SELECT MAX(account_id) FROM customer_accounts")
            max_id = cursor.fetchone()[0]
            new_account_id = max_id + 1

            # D. EXECUTE UPDATES
            
            # 1. Cancel Old Account
            cursor.execute(
                "UPDATE customer_accounts SET status = 'CANCELED', end_date = ? WHERE account_id = ?",
                (disconnect_date_str, account_id)
            )
            
            # 2. Create New Account
            # Note: Balance starts at 0.00. 
            cursor.execute(
                """
                INSERT INTO customer_accounts 
                (account_id, first_name, last_name, email, address_id, plan_name, 
                 pending_balance, status, start_date, autopay_active, tenure_years)
                VALUES (?, ?, ?, ?, ?, ?, 0.00, 'ACTIVE', ?, ?, ?)
                """,
                (new_account_id, fname, lname, email, new_address_id, new_plan_name, effective_date, autopay, tenure)
            )
            
            conn.commit()
            
            return {
                "status": "success",
                "message": "Move order finalized.",
                "details": {
                    "old_account_id": account_id,
                    "old_disconnect_date": disconnect_date_str,
                    "new_account_id": new_account_id,
                    "new_start_date": effective_date,
                    "new_address": new_address_id,
                    "new_plan": new_plan_name
                }
            }

        else:
            return {"status": "error", "message": "Invalid Action. Use MOVE or CANCEL."}

    except sqlite3.Error as e:
        return {"status": "error", "message": str(e)}

# --- TEST SNIPPET ---
if __name__ == "__main__":
    conn = sqlite3.connect(":memory:")
    # Create Table with ALL necessary columns
    conn.execute("""
        CREATE TABLE customer_accounts (
            account_id INTEGER, first_name TEXT, last_name TEXT, email TEXT,
            address_id TEXT, plan_name TEXT, pending_balance REAL, 
            status TEXT, start_date TEXT, end_date TEXT, 
            autopay_active BOOLEAN, tenure_years REAL
        )
    """)
    
    # Insert Muru (Account 10001) - Active, $0 Balance, at Address A01
    conn.execute("""
        INSERT INTO customer_accounts VALUES 
        (10001, 'Muru', 'A', 'muru@mail.com', 'A01', 'Internet 100', 0.00, 
         'ACTIVE', '2022-01-01', NULL, 1, 5.0)
    """)
    
    print("--- Test 1: Move Muru to B01 on May 13 ---")
    # Expected: Old -> Canceled (May 12). New (10002) -> Active (May 13).
    print(T12_ExecuteMoveCancel(conn, 10001, "MOVE", "2026-05-13", "B01", "Fiber 1 Gig"))
    
    print("\n--- Test 2: Check Database Rows ---")
    cur = conn.cursor()
    cur.execute("SELECT account_id, status, start_date, end_date, address_id FROM customer_accounts")
    for row in cur.fetchall():
        print(row)
        
    conn.close()
