"""
T3_EquipmentLogic
Function: The "Hardware Check." Checks if the new house is "Plug-and-Play" (Pre-wired) or empty.
Business Logic: Decides if we charge a $0 activation fee (Self-Install) or a $99 Installation Fee (Technician Visit).
Customer Use Case:
    Primary: "Do I need a technician to come out?"
    Secondary: "Can I do a self-install?", "Is the house already wired for internet?"
    Implicit: The Agent must call this before booking an appointment to decide if T9_BookAppt is even necessary.

Logic Specification
    Input: new_address (Required - The Destination Street Address).
    Logic:
        1. Normalize Input: Convert address to lowercase to handle matching (e.g. "100 First St").
        2. Evaluate Status:
            If address is in the "Pre-Wired" list (e.g., 100 First St):
                Type: "Self-Install".
                Action: No appointment needed. Fee = $0.00.
            If address is NOT found (or mapped as empty):
                Type: "Technician Install".
                Action: Appointment mandatory. Fee = $99.00.
    Output: A dictionary with install_type, needs_appointment (True/False), and estimated_fee.
"""

import sqlite3

def T3_EquipmentLogic(conn, new_address):
    """
    T3_EquipmentLogic: Determines installation requirements for a target address.
    
    Args:
        conn: The active database connection (kept for compatibility).
        new_address (str): The Destination Address (e.g., '100 First St').
    
    Returns:
        dict: Installation type, appointment requirement, and fee.
    """
    
    # Standard Fee for Tech Visit
    TECH_FEE = 99.00
    
    # Normalize input (Handle None/Empty)
    if not new_address:
        return {"status": "error", "message": "Address is empty."}
        
    # Convert to lowercase for easy matching
    search_addr = new_address.lower().strip()
    
    # --- LOGIC MAPPING ---
    # Instead of looking up cryptic IDs (B01), we map real addresses here.
    # This fixes the issue where the bot asks for an "Address ID".
    
    pre_wired_homes = [
        "100 first st", 
        "100 first street",
        "b01" # Kept for backward compatibility
    ]
    
    try:
        # --- CASE A: Pre-Wired (Self-Install) ---
        if search_addr in pre_wired_homes:
            return {
                "status": "success",
                "install_type": "Self-Install",
                "message": f"Good news! {new_address} is pre-wired. You can do a Self-Install.",
                "needs_appointment": False,
                "installation_fee": 0.00
            }
            
        # --- CASE B: Empty / Unknown (Technician Required) ---
        else:
            return {
                "status": "success",
                "install_type": "Technician Install",
                "message": f"A technician visit is required to set up the line at {new_address}.",
                "needs_appointment": True,
                "installation_fee": TECH_FEE
            }

    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- TEST SNIPPET ---
if __name__ == "__main__":
    # Dummy conn not needed for logic but required for argument
    conn = None 
    
    print("--- Test 1: Checking '100 First St' (Pre-wired) ---")
    # Expected: Self-Install
    print(T3_EquipmentLogic(conn, "100 First St"))
    
    print("\n--- Test 2: Checking '999 Unknown Rd' (Empty) ---")
    # Expected: Technician Install
    print(T3_EquipmentLogic(conn, "999 Unknown Rd"))