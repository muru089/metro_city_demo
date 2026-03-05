"""
T4_FindMaxSpeedPlan
Function: The "Upsell Engine." It looks at the max speed available at an address (from T2) and pulls the highest-tier plan and price from the catalog.
Business Logic: Supports the "Upsell" journey by always presenting the best possible plan first (e.g., Fiber 1 Gig).
Customer Use Case:
    Primary: "I want the fastest internet you have.", "Upgrade me to the 1 Gig plan."
    Secondary: "What is the price for the 1 Gig plan?"
    Implicit: The Agent calls this during the "Upsell" flow. If T2 says Fiber is available, the Agent calls T4 to get the price to pitch to the customer.

Logic Specification
    Input: address_id (Required).
    Step 1: Call T_Fiber internally to see if the house is Fiber or Copper.
    Step 2: Query the product_catalog table.
        If Copper: Filter for plans where technology = 'Copper'.
        If Fiber: Filter for plans where technology = 'Fiber'.
    Step 3: Sort the plans by speed (High to Low).
    Output: A list of sellable plans. The first item in the list is the "Max Speed" (Upsell Target).
"""


import sqlite3

# We assume T_Fiber is available in the same file or imported
# from tool_fiber import tool_check_fiber

def T4_FindMaxSpeedPlan(conn, address_id):
    """
    T_Max: Determines the best (and all) available plans for a specific address.
    
    Args:
        conn: The active database connection object.
        address_id (str): The unique ID of the target address (e.g., 'A01').
    
    Returns:
        dict: A list of available plans, with the fastest one highlighted.
    """
    
    cursor = conn.cursor()
    
    # --- STEP 1: CHECK INFRASTRUCTURE ---
    # We first need to know what wires are in the ground at this house.
    # We reuse the logic from our previous tool (T_Fiber).
    # Note: We pass the 'conn' and 'address_id' just like before.
    tech_info = tool_check_fiber(conn, address_id)
    
    # If the address is invalid, stop here and return the error.
    if tech_info["status"] == "error":
        return tech_info
        
    # Extract the tech type (e.g., "Fiber" or "Copper")
    # We capitalize it just to be safe (e.g. "fiber" -> "Fiber")
    tech_type = tech_info["tech_type"].capitalize()
    
    try:
        # --- STEP 2: QUERY THE CATALOG ---
        # Now we look at the Menu (product_catalog).
        # We only want plans that match the house's technology.
        # We order by 'speed_mbps DESC' so the FASTEST plan is always first.
        cursor.execute(
            """
            SELECT plan_name, speed_mbps, monthly_price 
            FROM product_catalog 
            WHERE technology = ? 
            ORDER BY speed_mbps DESC
            """, 
            (tech_type,)
        )
        
        available_plans = cursor.fetchall()
        
        if not available_plans:
            return {
                "status": "error", 
                "message": f"No plans found in catalog for technology: {tech_type}"
            }

        # --- STEP 3: FORMAT THE OUTPUT ---
        # We want to give the Agent a clean list of options.
        formatted_plans = []
        for plan in available_plans:
            name, speed, price = plan
            formatted_plans.append({
                "name": name,
                "speed": f"{speed} Mbps",
                "price": f"${price:.2f}"
            })
            
        # The "Best" plan is simply the first one in our sorted list.
        best_plan = formatted_plans[0]
        
        return {
            "status": "success",
            "tech_type": tech_type,
            "max_plan_name": best_plan["name"], # The Upsell Target
            "all_plans": formatted_plans        # The full menu
        }

    except sqlite3.Error as e:
        return {"status": "error", "message": str(e)}

# --- TEST SNIPPET ---
if __name__ == "__main__":
    conn = sqlite3.connect("metro_city.db") 
    
    # Need to make sure the dummy function 'tool_check_fiber' is defined 
    # or imported if running this script alone.
    
    print("--- Test 1: Plans for a Fiber Home (A01) ---")
    # Expected: List starting with 'Fiber 2 Gig' or 'Fiber 1 Gig' (depending on catalog)
    print(T4_FindMaxSpeedPlan(conn, "A01"))
    
    print("\n--- Test 2: Plans for a Copper Home (A03) ---")
    # Expected: List with only 'Internet 100'
    print(T4_FindMaxSpeedPlan(conn, "A03"))
    
    conn.close()