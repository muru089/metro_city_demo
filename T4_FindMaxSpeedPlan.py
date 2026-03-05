"""
T4_FindMaxSpeedPlan
-------------------
WHAT THIS TOOL DOES:
    Given an address ID, returns the full list of available internet plans
    sorted from fastest to slowest. The first item in the list is always the
    "upsell target" -- the best plan available at that address.

    To do this, it first checks the address's technology type (Fiber or Copper)
    via T2_FiberCheckServiceability, then filters the product catalog accordingly.

WHY IT MATTERS (Business Logic):
    - Powers the sales_agent's upsell and downsell flow.
    - Automatically respects the Copper Constraint: a Copper address only sees
      Copper plans; a Fiber address only sees Fiber plans.
    - The agent can lead with the best plan and step down if the customer
      pushes back on price -- all from the same tool call.

INPUTS:
    conn       : Database connection (injected automatically).
    address_id : The address code (e.g., "A01"). Must be a valid addr_id.

OUTPUT:
    Success: {
        "status": "success",
        "tech_type": "Fiber",
        "max_plan_name": "Fiber 1 Gig",   <- the upsell target (fastest plan)
        "all_plans": [                     <- full sorted plan menu
            {"name": "Fiber 1 Gig", "speed": "1000 Mbps", "price": "$80.00"},
            {"name": "Fiber 500",   "speed": "500 Mbps",  "price": "$65.00"},
            ...
        ]
    }
    Error: {"status": "error", "message": "reason"}

BUG FIXED (original file):
    The original code called tool_check_fiber() which was never defined or imported.
    Fixed to call T2_FiberCheckServiceability() directly, which is the correct function.
"""

import sqlite3
from .T2_FiberCheckServiceability import T2_FiberCheckServiceability


def T4_FindMaxSpeedPlan(conn, address_id):
    """
    Returns all available internet plans for an address, fastest first.

    Args:
        conn       : Active SQLite database connection (injected by the agent framework).
        address_id : The address code to look up (e.g., 'A01').

    Returns:
        dict: Technology type, best plan name, and full sorted plan list.
    """

    cursor = conn.cursor()

    # =========================================================================
    # STEP 1: CHECK WHAT TECHNOLOGY THIS ADDRESS SUPPORTS
    # We call T2 to find out if this address is Fiber or Copper.
    # This drives everything -- Fiber addresses get Fiber plans, Copper gets Copper.
    # =========================================================================
    tech_info = T2_FiberCheckServiceability(conn, address_id)

    # If T2 returned an error (address not found, DB issue), pass it through.
    if tech_info["status"] == "error":
        return tech_info

    # Extract and normalize the tech type (handles any casing from the DB)
    tech_type = tech_info["tech_type"].capitalize()  # e.g., "fiber" -> "Fiber"

    try:
        # =====================================================================
        # STEP 2: QUERY THE PRODUCT CATALOG FOR MATCHING PLANS
        # Filter by technology type and sort fastest-to-slowest.
        # The agent always leads with the best (fastest/most expensive) plan.
        # =====================================================================
        cursor.execute(
            """
            SELECT plan_name, speed_mbps, monthly_price
            FROM   product_catalog
            WHERE  technology = ?
            ORDER  BY speed_mbps DESC
            """,
            (tech_type,)
        )

        available_plans = cursor.fetchall()

        if not available_plans:
            return {
                "status": "error",
                "message": f"No plans found in catalog for technology: {tech_type}"
            }

        # =====================================================================
        # STEP 3: FORMAT THE PLAN LIST FOR THE AGENT
        # Convert raw DB rows into clean dicts the agent can read easily.
        # =====================================================================
        formatted_plans = []
        for plan_name, speed_mbps, monthly_price in available_plans:
            formatted_plans.append({
                "name": plan_name,
                "speed": f"{speed_mbps} Mbps",
                "price": f"${monthly_price:.2f}"
            })

        # The upsell target is simply the first item (fastest plan due to ORDER BY DESC).
        best_plan = formatted_plans[0]

        return {
            "status": "success",
            "tech_type": tech_type,
            "max_plan_name": best_plan["name"],  # The agent leads with this
            "all_plans": formatted_plans          # Full menu for downsell negotiation
        }

    except sqlite3.Error as e:
        return {"status": "error", "message": str(e)}


# =============================================================================
# TEST BLOCK
# Run this file directly (python T4_FindMaxSpeedPlan.py) to test in isolation.
# Note: T4 calls T2 internally, so both must be importable for this test to work.
# =============================================================================
if __name__ == "__main__":
    import os
    import sys
    # Add parent directory to path so relative imports work when running directly
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from metro_city_demo.T2_FiberCheckServiceability import T2_FiberCheckServiceability

    DB_PATH = os.path.join(os.path.dirname(__file__), "metro_city.db")
    conn = sqlite3.connect(DB_PATH)

    print("=== T4_FindMaxSpeedPlan -- Manual Test Run ===\n")

    print("--- Test 1: Fiber address (A01 -- Muru's home) ---")
    print("Expected: Fiber plans sorted fastest first")
    print(T4_FindMaxSpeedPlan(conn, "A01"))

    print("\n--- Test 2: Copper address (A03 -- Sarah's home) ---")
    print("Expected: Only Internet 100")
    print(T4_FindMaxSpeedPlan(conn, "A03"))

    print("\n--- Test 3: Invalid address ---")
    print("Expected: error from T2")
    print(T4_FindMaxSpeedPlan(conn, "Z99"))

    conn.close()
