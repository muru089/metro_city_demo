"""
T2_FiberCheckServiceability
---------------------------
WHAT THIS TOOL DOES:
    Looks up a specific address in our service database and returns what
    technology we can deliver there (Fiber or Copper) and the maximum speed.

    Think of it as the "Coverage Map Lookup" -- before we sell or move
    a customer, we need to know what the physical infrastructure supports.

WHY IT MATTERS (Business Logic):
    - Enforces the "Copper Constraint": if an address only supports Copper,
      we must never offer Fiber plans there. This tool is the gatekeeper.
    - Used by service_agent (direct coverage checks) and sales_agent (before
      presenting plans). T3_EquipmentLogic handles the same lookup via street
      address for the moves flow.

INPUTS:
    conn       : Database connection (injected automatically).
    address_id : The short address code (e.g., "A01", "A11").
                 IMPORTANT: This takes an addr_id code, NOT a street string.
                 Use T3_EquipmentLogic if you only have a street address.

OUTPUT:
    Found    : {"status": "success", "tech_type": "Fiber", "max_speed": 1000}
    Not found: {"status": "error", "message": "Address ID not found..."}
"""

import sqlite3


def T2_FiberCheckServiceability(conn, address_id):
    """
    Checks the maximum internet technology available at a given address ID.

    Args:
        conn       : Active SQLite database connection (injected by the agent framework).
        address_id : The address code to look up (e.g., 'A01', 'A11').

    Returns:
        dict: Technology type (Fiber/Copper) and maximum speed in Mbps.
    """

    # A cursor executes SQL queries against the database.
    cursor = conn.cursor()

    try:
        # Look up the technology type and max speed for this address.
        # We only fetch the two columns we need -- keeping the query focused.
        cursor.execute(
            "SELECT max_tech_type, max_speed FROM address_inventory WHERE addr_id = ?",
            (address_id,)
        )

        result = cursor.fetchone()

        if result:
            # Unpack the row tuple (e.g., ('Fiber', 1000))
            tech_type, max_speed = result
            return {
                "status": "success",
                "tech_type": tech_type,   # "Fiber" or "Copper" -- drives plan eligibility
                "max_speed": max_speed    # Maximum Mbps at this address
            }
        else:
            return {
                "status": "error",
                "message": f"Address ID '{address_id}' not found. Please verify the address code."
            }

    except sqlite3.Error as e:
        return {"status": "error", "message": str(e)}


# =============================================================================
# TEST BLOCK
# Run this file directly (python T2_FiberCheckServiceability.py) to test.
# =============================================================================
if __name__ == "__main__":
    import os
    DB_PATH = os.path.join(os.path.dirname(__file__), "metro_city.db")
    conn = sqlite3.connect(DB_PATH)

    print("=== T2_FiberCheckServiceability -- Manual Test Run ===\n")

    print("--- Test 1: Fiber address (A01 -- 100 First Ave) ---")
    print("Expected: Fiber, 1000 Mbps")
    print(T2_FiberCheckServiceability(conn, "A01"))

    print("\n--- Test 2: Copper address (A03 -- 300 Third Ave) ---")
    print("Expected: Copper, 100 Mbps")
    print(T2_FiberCheckServiceability(conn, "A03"))

    print("\n--- Test 3: Vacant fiber address (A11 -- 100 First St) ---")
    print("Expected: Fiber, 1000 Mbps")
    print(T2_FiberCheckServiceability(conn, "A11"))

    print("\n--- Test 4: Address ID not in our system ---")
    print("Expected: error / not found")
    print(T2_FiberCheckServiceability(conn, "Z99"))

    conn.close()
