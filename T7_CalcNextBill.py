"""
T7_CalcNextBill
Function: The "Forecaster." Quotes the monthly price of the customer's current plan.
Business Logic: Provides price transparency. Strictly quotes the catalog price (no taxes/fees added).
Customer Use Case:
    Primary: "How much will my next bill be?"
    Secondary: "What is the monthly rate for my current plan?"

Logic Specification
    Input: account_id (Required).
    Logic:
        1. Retrieve Data: Join customer_accounts with product_catalog on plan_name.
        2. Fetch Price: Get the monthly_price for the customer's current plan.
        3. No Calculation: Do not apply tax or fees.
        4. Determine Due Date: Calculate the 1st day of the next month.
    Output: A dictionary with the status, message, and the flat amount.
"""



import sqlite3
from datetime import datetime, timedelta

def T7_CalcNextBill(conn, account_id):
    """
    T_NextBill: Calculates the next bill amount.
    Logic: Returns the flat catalog price (No tax, no proration).
    
    Args:
        conn: The active database connection object.
        account_id (int or str): The unique ID of the customer.
    
    Returns:
        dict: A breakdown of the bill (Plan Price, Due Date).
    """
    
    cursor = conn.cursor()
    
    try:
        # --- STEP 1: GET PLAN INFO ---
        # Join customer table with catalog to get the 'monthly_price'
        query = """
        SELECT c.plan_name, p.monthly_price 
        FROM customer_accounts c
        JOIN product_catalog p ON c.plan_name = p.plan_name
        WHERE c.account_id = ?
        """
        
        cursor.execute(query, (account_id,))
        result = cursor.fetchone()
        
        if not result:
            return {"status": "error", "message": "Account ID not found."}
            
        plan_name, monthly_price = result
        
        # --- STEP 2: DETERMINE DUE DATE ---
        # Rule: Bill is posted on the 1st of the next month (Section 9.1)
        today = datetime.now()
        next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        due_date_str = next_month.strftime("%B %d, %Y")
        
        # --- STEP 3: RETURN THE SUMMARY ---
        # Updated: Removed "(plus taxes)" from the message string.
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

# --- TEST SNIPPET ---
if __name__ == "__main__":
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE customer_accounts (account_id INTEGER, plan_name TEXT)")
    conn.execute("CREATE TABLE product_catalog (plan_name TEXT, monthly_price REAL)")
    
    conn.execute("INSERT INTO product_catalog VALUES ('Fiber 1 Gig', 80.00)")
    conn.execute("INSERT INTO customer_accounts VALUES (10001, 'Fiber 1 Gig')")
    
    print("--- Test 1: Calculate Bill for Muru (Fiber 1 Gig) ---")
    # Expected: $80.00 exactly
    print(T7_CalcNextBill(conn, 10001))
    
    conn.close()