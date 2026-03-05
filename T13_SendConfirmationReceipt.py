"""
T13_SendConfirmationReceipt
Function: The "Paper Trail." Handles Notification Logic defined in Section 12.1. It generates a professional "Receipt" text block (with a fake Order ID) to close the conversation.
Business Logic: Provides the customer with a formal record of the transaction. Now automatically retrieves the customer's email from the database to ensure accuracy.
Customer Use Case:
    Primary: (Implicit) Generates the text summary at the end of a Move, Cancel, or Payment.
    Secondary: "Can you email me a confirmation?"
    
Logic Specification
    Input:
        account_id (Required: Used to look up the customer's email address)
        action_type (Required: "MOVE", "CANCEL", or "PAYMENT")
        details (Required: A dictionary containing relevant data like amount, date, address, plan_name, etc.).
    Logic: 
        1. Email Lookup: Query the database using account_id to find the customer's email. If missing, default to "No Email On File". 
        2. Generate Order Reference: Create a random alphanumeric string (e.g., #ORD-9X21B) for realism. 
        3. Format Summary: Construct a text block specific to the action: 
            * Move: Include New Address, Activation Date, Plan Name, Price, and Fees. 
            * Payment: Include Amount Paid and Remaining Balance. 
            * Cancel: Include Disconnect Date and Final Balance status. 
        4. Append Instructions: Add standard footer text (e.g., "Return equipment via mail").
    Output: A dictionary containing the order_ref and the fully formatted receipt_text.
"""


import random
import string
import sqlite3
import os

def T13_SendConfirmationReceipt(account_id, action_type, details):
    """
    T13_SendConfirmationReceipt: Generates the final summary block and looks up the user's email.
    
    Args:
        account_id (int/str): The customer's ID (used to fetch the email).
        action_type (str): "MOVE", "CANCEL", or "PAYMENT".
        details (dict): Context specific data (e.g., {'amount': 82.45, 'date': '2026-05-13'...}).
    
    Returns:
        dict: The generated Order ID and the formatted text block for the Agent to say.
    """
    
    # --- STEP 0: LOOK UP EMAIL FROM DB ---
    # We open a local connection here to avoid complicating the Agent wrapper.
    db_path = os.path.join(os.path.dirname(__file__), 'metro_city.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    customer_email = "No Email On File" # Default fallback
    try:
        cursor.execute("SELECT email FROM customer_accounts WHERE account_id = ?", (account_id,))
        result = cursor.fetchone()
        if result and result[0]:
            customer_email = result[0]
    except Exception as e:
        print(f"Error fetching email: {e}")
    finally:
        conn.close()

    # --- STEP 1: GENERATE FAKE ORDER ID ---
    # Random 5-char alphanumeric suffix (e.g., 9X21B)
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    order_ref = f"#ORD-{suffix}"
    
    # Initialize the message
    lines = []
    lines.append(f"📄 **ORDER CONFIRMATION: {order_ref}**")
    lines.append(f"Sent to: {customer_email}")
    lines.append("-" * 30)
    
    # --- STEP 2: BUILD CONTENT BASED ON ACTION ---
    # Safety check: ensure details is a dict
    if not details: details = {}
    
    if action_type == "MOVE":
        # Required details: new_address, start_date, plan_name, monthly_price, install_fee
        new_addr = details.get("new_address", "Unknown Address")
        date = details.get("start_date", "TBD")
        plan = details.get("plan_name", "Internet Plan")
        price = details.get("monthly_price", 0.00)
        fee = details.get("install_fee", 0.00)
        
        lines.append(f"**Action:** Move Service to {new_addr}")
        lines.append(f"**Activation Date:** {date}")
        lines.append(f"**New Plan:** {plan}")
        lines.append(f"**Monthly:** ${price:.2f}/mo (plus taxes)")
        lines.append(f"**One-Time Charges:** ${fee:.2f} (Installation)")
        
        # Add Return Instruction 
        lines.append("-" * 30)
        lines.append("**Next Steps:** A prepaid return label has been emailed to you.")
        lines.append("Please return your old gateway via mail to avoid non-return fees.")
        lines.append("Technicians cannot accept equipment returns.")

    elif action_type == "PAYMENT":
        # Required details: amount
        amount = details.get("amount", 0.00)
        
        lines.append(f"**Action:** Payment Received")
        lines.append(f"**Amount Paid:** ${amount:.2f}")
        lines.append(f"**Balance Remaining:** $0.00")
        lines.append("-" * 30)
        lines.append("Thank you for your payment.")

    elif action_type == "CANCEL":
        # Required details: end_date
        date = details.get("end_date", "Immediate")
        
        lines.append(f"**Action:** Service Cancellation")
        lines.append(f"**Disconnect Date:** {date}")
        lines.append(f"**Final Balance:** Paid in Full")
        lines.append("-" * 30)
        lines.append("**Next Steps:** Please use the prepaid label sent to your email")
        lines.append("to return your equipment immediately.")

    # --- STEP 3: RETURN THE PACKAGE ---
    return {
        "status": "success",
        "order_ref": order_ref,
        "receipt_text": "\n".join(lines)
    }

# --- TEST SNIPPET ---
if __name__ == "__main__":
    # Test 1: Move Receipt (Using ID 10001 who has email muru@mail.com)
    move_details = {
        "new_address": "100 First St",
        "start_date": "2026-05-13",
        "plan_name": "Fiber 1 Gig",
        "monthly_price": 80.00,
        "install_fee": 0.00 
    }
    print("--- Test 1: Move Receipt ---")
    # Note: If running this test directly, ensure your local DB has ID 10001
    print(T13_SendConfirmationReceipt(10001, "MOVE", move_details)["receipt_text"])
    
    # Test 2: Payment Receipt
    pay_details = {"amount": 82.45}
    print("\n--- Test 2: Payment Receipt ---")
    print(T13_SendConfirmationReceipt(10001, "PAYMENT", pay_details)["receipt_text"])