"""
T2_FiberCheckServiceability
Function: The "Coverage Map." Checks a specific physical address to see if it supports Fiber or only Copper.
Business Logic: Enforces the "Copper Constraint" (don't sell Fiber if the address can't handle it).
Customer Use Case:
    Primary: "Is fiber available at 100 First St?"
    Secondary (Speed Check): "What is the fastest speed I can get at [Address]?"
    Secondary (Tech Check): "Can I get Copper internet there?" (Checking specific technology).
    Edge Case: "I am moving to [Address]..." (The Agent implicitly calls this to see if the move is even possible).

Logic Specification:
    Input: address_id (Required string, e.g., "A01").
    Action: Query the address_inventory table for the specific addr_id.
    Logic: 
        Run SELECT max_tech_type, max_speed FROM address_inventory WHERE addr_id = [Input].
    Output:
        If Found: Return a dictionary with the technology type and max speed (e.g., {"status": "success", "tech_type": "Fiber", "max_speed": 1000}).
        If Not Found: Return {"status": "error", "message": "Address ID not found."}.
"""


import sqlite3

def T2_FiberCheckServiceability(conn, address_id):
    """
    T_Fiber: Checks the maximum technology available at an address.
    
    Args:
        conn: The active database connection object.
        address_id (str): The unique ID of the address (e.g., 'A01').
    
    Returns:
        dict: A summary containing the technology type (Fiber/Copper) and max speed.
    """
    
    # Create the 'cursor' to execute SQL commands.
    cursor = conn.cursor()
    
    try:
        # --- STEP 1: EXECUTE THE QUERY ---
        # We need to look up the technology details for the specific address provided.
        # We select two columns: 'max_tech_type' (e.g., Fiber) and 'max_speed' (e.g., 1000).
        cursor.execute(
            "SELECT max_tech_type, max_speed FROM address_inventory WHERE addr_id = ?", 
            (address_id,)
        )
        
        # --- STEP 2: FETCH THE RESULT ---
        # Retrieve the first matching row found by the database.
        result = cursor.fetchone()
        
        # --- STEP 3: PROCESS THE DATA ---
        
        # Case A: The Address ID was found.
        if result:
            # Unpack the tuple (e.g., ('Fiber', 1000)) into two variables.
            tech_type, max_speed = result
            
            # Return a success dictionary with the details.
            return {
                "status": "success", 
                "tech_type": tech_type, # Useful for logic: "If Fiber, offer 1 Gig"
                "max_speed": max_speed  # Useful for logic: "Don't offer 2 Gig if max is 1000"
            }
            
        # Case B: The Address ID does not exist in our table.
        else:
            return {
                "status": "error", 
                "message": "Address ID not found. Please check the ID and try again."
            }
            
    except sqlite3.Error as e:
        # Catch any database errors (like a locked file or broken connection).
        return {"status": "error", "message": str(e)}




# --- TEST SNIPPET ---
# This block runs only if you play this file directly. The "Test Snippet" block (if __name__ == "__main__":) is a lifesaver because it lets you test the tool in isolation without needing the full Agent system running.
if __name__ == "__main__":
    # Connect to the database file
    conn = sqlite3.connect("metro_city.db")
    
    print("--- Test 1: Check Fiber Address (A01) ---")
    # Expected: Fiber, 1000 Mbps
    print(T2_FiberCheckServiceability(conn, "A01"))
    
    print("\n--- Test 2: Check Copper Address (A03) ---")
    # Expected: Copper, 100 Mbps
    print(T2_FiberCheckServiceability(conn, "A03"))
    
    print("\n--- Test 3: Check Invalid Address (Z99) ---")
    # Expected: Error message
    print(T2_FiberCheckServiceability(conn, "Z99"))
    
    conn.close()