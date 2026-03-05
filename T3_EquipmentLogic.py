"""
T3_EquipmentLogic
-----------------
WHAT THIS TOOL DOES:
    When a customer wants to move, we need to know two things about their new address:
    1. Is the new address in our service area and currently available (Vacant)?
    2. Will they need a technician to come out, or can they self-install?

    This tool answers both questions by looking up the address in our database.

WHY IT MATTERS (Business Logic):
    - If the address is VACANT with a Modem (Copper) already installed:
        -> "Self-Install" -- the customer just plugs in their existing equipment. No fee, no appointment.
    - If the address is VACANT with an ONT (Fiber) -- fiber optic equipment:
        -> "Technician Install" -- the ONT must be activated by a technician. $99 fee (unless waived by T8).
    - If the address is OCCUPIED:
        -> Error -- someone already lives there. We can't move the customer in.
    - If the address is not in our system:
        -> Error -- we don't serve that area.

INPUTS:
    conn        : The database connection (passed in automatically -- agents don't see this).
    new_address : The street address the customer is moving to (e.g., "200 Second St").
                  Accepts partial matches and is NOT case-sensitive.

OUTPUT (a Python dictionary):
    On success:
        {
            "status": "success",
            "install_type": "Self-Install" OR "Technician Install",
            "tech_type": "Fiber" OR "Copper",   <-- CRITICAL for the cancel-if-no-fiber decision
            "addr_id": "A12",                    <-- The internal address ID for downstream tools
            "needs_appointment": True OR False,
            "installation_fee": 0.00 OR 99.00,
            "message": "Human-readable summary"
        }
    On error:
        {
            "status": "error",
            "message": "Reason for failure (Occupied / Not Found / etc.)"
        }
"""

import sqlite3


def T3_EquipmentLogic(conn, new_address):
    """
    Determines installation requirements for a customer's destination address.
    Queries the database directly -- no hardcoded address lists.

    Args:
        conn        : Active SQLite database connection (injected by the agent framework).
        new_address : Street address string from the customer (e.g., "100 First St").

    Returns:
        dict: See module docstring for full return format.
    """

    # --- GUARD: Make sure the agent actually passed an address ---
    # If the address is empty or None, we can't do anything. Return an error immediately.
    if not new_address or not new_address.strip():
        return {
            "status": "error",
            "message": "No address was provided. Please ask the customer for their new address."
        }

    # Standard installation fee -- this applies when a technician visit is required.
    # The fee can be waived later by T8_CheckFeeWaiver if the customer qualifies.
    TECH_FEE = 99.00

    # Create a database cursor.
    # Think of the cursor as the "hand" that reaches into the database and runs queries.
    cursor = conn.cursor()

    try:
        # --- DATABASE LOOKUP ---
        # We search the address_inventory table for the customer's new address.
        #
        # Key design choices:
        # 1. We use LOWER() on both sides so "100 First St" matches "100 first st" matches "100 FIRST ST".
        # 2. We use LIKE with wildcards (%...%) so a partial input like "First St" still finds the row.
        #    This makes the demo forgiving -- customers rarely type exact addresses.
        # 3. We only fetch the columns we actually need (addr_id, status, max_tech_type, equipment_installed).
        cursor.execute(
            """
            SELECT addr_id, status, max_tech_type, equipment_installed
            FROM   address_inventory
            WHERE  LOWER(street) LIKE LOWER(?)
            LIMIT  1
            """,
            (f"%{new_address.strip()}%",)  # The % symbols are wildcards for partial matching
        )

        # Fetch the first (and only) matching row.
        result = cursor.fetchone()

        # --- CASE 1: Address Not Found ---
        # If result is None, the address is not in our service area at all.
        if not result:
            return {
                "status": "error",
                "error_type": "NOT_FOUND",
                "message": (
                    f"I was unable to find '{new_address}' in our service area. "
                    "We may not serve that address yet. Please verify the address or try a nearby street."
                )
            }

        # Unpack the row into named variables so the rest of the code is readable.
        addr_id, status, max_tech_type, equipment_installed = result

        # --- CASE 2: Address is Already Occupied ---
        # "Occupied" means a current Metro City customer lives there.
        # We cannot move the customer into an address that already has active service.
        if status == "Occupied":
            return {
                "status": "error",
                "error_type": "OCCUPIED",
                "message": (
                    f"The address '{new_address}' is currently occupied by another customer. "
                    "Please provide a different destination address."
                )
            }

        # --- CASE 3: Address is Vacant -- Determine Install Type ---
        # The address is available (Vacant). Now we figure out what kind of install is needed.
        # This is determined by the equipment_installed field:
        #
        #   "Modem"  = Copper infrastructure. The modem hardware may already be present.
        #              Customer can likely self-install (plug in their existing equipment).
        #
        #   "ONT"    = Optical Network Terminal (Fiber). This requires a technician to:
        #              - Activate the fiber line at the ONT device
        #              - Confirm signal and provision the account
        #              The customer CANNOT self-install fiber.

        if equipment_installed == "Modem":
            # --- COPPER / SELF-INSTALL PATH ---
            # Good news for the customer: no technician needed, no fee, no appointment.
            return {
                "status": "success",
                "install_type": "Self-Install",
                "tech_type": max_tech_type,      # Will be "Copper"
                "addr_id": addr_id,              # e.g., "A13" -- used by T12 to execute the move
                "needs_appointment": False,
                "installation_fee": 0.00,
                "message": (
                    f"Good news! {new_address} supports {max_tech_type} service and is ready for "
                    "self-installation. The customer can plug in their existing equipment."
                )
            }

        else:
            # --- FIBER / TECHNICIAN INSTALL PATH ---
            # equipment_installed == "ONT" (or anything else we don't recognize defaults to tech install)
            # A technician is required. The $99 fee applies unless T8 says it's waived.
            return {
                "status": "success",
                "install_type": "Technician Install",
                "tech_type": max_tech_type,      # Will be "Fiber"
                "addr_id": addr_id,              # e.g., "A11" -- used by T12 to execute the move
                "needs_appointment": True,
                "installation_fee": TECH_FEE,
                "message": (
                    f"A technician visit is required to activate the Fiber ONT at {new_address}. "
                    f"The standard installation fee is ${TECH_FEE:.2f} (subject to waiver check)."
                )
            }

    except sqlite3.Error as db_error:
        # If the database itself throws an error (locked, missing table, etc.),
        # we catch it here and return a clean error message instead of crashing.
        return {
            "status": "error",
            "message": f"Database error while checking address: {str(db_error)}"
        }


# =============================================================================
# TEST BLOCK
# Run this file directly (python T3_EquipmentLogic.py) to test it in isolation.
# This block does NOT run when the agent imports the file -- only during manual testing.
# =============================================================================
if __name__ == "__main__":
    import os

    # Connect to the real database for testing
    DB_PATH = os.path.join(os.path.dirname(__file__), "metro_city.db")
    conn = sqlite3.connect(DB_PATH)

    print("=== T3_EquipmentLogic -- Manual Test Run ===\n")

    print("--- Test 1: Fiber/Vacant address (100 First St = A11) ---")
    print("Expected: Technician Install, Fiber")
    print(T3_EquipmentLogic(conn, "100 First St"))

    print("\n--- Test 2: Copper/Vacant address (300 Third St = A13) ---")
    print("Expected: Self-Install, Copper")
    print(T3_EquipmentLogic(conn, "300 Third St"))

    print("\n--- Test 3: Occupied address (100 First Ave = A01) ---")
    print("Expected: error / OCCUPIED")
    print(T3_EquipmentLogic(conn, "100 First Ave"))

    print("\n--- Test 4: Address not in our system ---")
    print("Expected: error / NOT_FOUND")
    print(T3_EquipmentLogic(conn, "999 Nowhere Rd"))

    print("\n--- Test 5: Partial address match (case-insensitive) ---")
    print("Expected: Technician Install, Fiber (matches A12)")
    print(T3_EquipmentLogic(conn, "second st"))

    print("\n--- Test 6: Empty address (guardrail test) ---")
    print("Expected: error / no address provided")
    print(T3_EquipmentLogic(conn, ""))

    conn.close()
