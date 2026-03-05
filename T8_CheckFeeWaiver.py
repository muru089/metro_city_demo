"""
T8_CheckFeeWaiver
Function: The "Judge." Evaluates if the customer deserves a free installation.
Business Logic: Checks the strict "3-Rule Logic": Tenure > 3 Years AND Autopay On AND No recent waivers.
Customer Use Case:
    Primary: "Can you waive the installation fee?" 
    Secondary (Explanation): "Why are you charging me $99?" (The tool returns the specific failure reason, e.g., "Tenure < 3 years"). 
    Implicit: The Agent proactively runs this during a "Move" flow to delight the customer ("Good news! You qualify for a waiver").

Logic Specification
    Input: account_id (Required).
    Logic:
        1. Retrieve Data: Query the customer's tenure_years, autopay_active status, and last_waiver_date.
        2. Evaluate Rules (The "AND" Gate):
            Rule A (Tenure): Is tenure_years > 3? 
            Rule B (Autopay): Is autopay_active TRUE? 
            Rule C (History): Is last_waiver_date either Null (never used) or older than 12 months? 
        3. Determine Outcome:
            Pass (All True): Fee is $0.00. Return success message.
            Fail (Any False): Fee is $99.00. Return failure message with the specific reason (e.g., "Tenure is less than 3 years").
    Output: A dictionary containing the waiver_status (Pass/Fail), the installation_fee amount ($0 or $99), and the explanation.
"""


import sqlite3
from datetime import datetime, timedelta

def T8_CheckFeeWaiver(conn, account_id):
    """
    T_CheckFeeWaiver: Evaluates eligibility for the $99 installation fee waiver.
    Logic: Must meet ALL 3 criteria (Tenure > 3, Autopay = On, No Recent Waivers).
    
    Args:
        conn: The active database connection.
        account_id (int or str): The customer's ID.
    
    Returns:
        dict: Waiver status and the final fee amount.
    """
    
    cursor = conn.cursor()
    
    # Standard Fee
    INSTALL_FEE = 99.00
    
    try:
        # --- STEP 1: FETCH CUSTOMER DATA ---
        # We need tenure, autopay status, and waiver history
        cursor.execute(
            "SELECT tenure_years, autopay_active, last_waiver_date FROM customer_accounts WHERE account_id = ?",
            (account_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            return {"status": "error", "message": "Account ID not found."}
            
        tenure_years, autopay_active, last_waiver_date = result
        
        # --- STEP 2: EVALUATE RULES ---
        reasons_for_failure = []
        
        # Rule A: Tenure > 3 Years
        if tenure_years <= 3:
            reasons_for_failure.append(f"Tenure is {tenure_years} years (Requires > 3)")
            
        # Rule B: Autopay Must be Active
        # SQLite Booleans: 1 = True, 0 = False
        if not autopay_active:
            reasons_for_failure.append("Autopay is not active")
            
        # Rule C: No Waivers in Last 12 Months
        if last_waiver_date:
            try:
                last_date = datetime.strptime(last_waiver_date, "%Y-%m-%d")
                one_year_ago = datetime.now() - timedelta(days=365)
                
                if last_date > one_year_ago:
                    reasons_for_failure.append("Waiver used within the last 12 months")
            except ValueError:
                # If date is invalid, we ignore it (Benefit of the doubt)
                pass

        # --- STEP 3: DETERMINE OUTCOME ---
        
        # PASS: No failures found
        if not reasons_for_failure:
            return {
                "status": "success",
                "waiver_applied": True,
                "installation_fee": 0.00,
                "message": "Good news, I can waive the installation fee."
            }
            
        # FAIL: At least one failure found
        else:
            reason_str = "; ".join(reasons_for_failure)
            return {
                "status": "success", # The check "succeeded", even if the waiver failed
                "waiver_applied": False,
                "installation_fee": INSTALL_FEE,
                "message": f"I checked your eligibility, but the ${INSTALL_FEE:.2f} fee applies because: {reason_str}."
            }

    except sqlite3.Error as e:
        return {"status": "error", "message": str(e)}

# --- TEST SNIPPET ---
if __name__ == "__main__":
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE customer_accounts (account_id INTEGER, tenure_years REAL, autopay_active BOOLEAN, last_waiver_date TEXT)")
    
    # 1. Muru (Perfect Candidate): 5 years, Autopay ON, No History
    conn.execute("INSERT INTO customer_accounts VALUES (10001, 5.0, 1, NULL)")
    
    # 2. John (Newbie): 1 year, Autopay OFF
    conn.execute("INSERT INTO customer_accounts VALUES (10002, 1.0, 0, NULL)")
    
    print("--- Test 1: Muru (Should Pass) ---")
    print(T8_CheckFeeWaiver(conn, 10001))
    
    print("\n--- Test 2: John (Should Fail) ---")
    print(T8_CheckFeeWaiver(conn, 10002))
    
    conn.close()
