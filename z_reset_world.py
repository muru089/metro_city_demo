"""
z_reset_world.py -- Metro City Internet: Database Reset Script
--------------------------------------------------------------
WHAT THIS SCRIPT DOES:
    Completely wipes metro_city.db and rebuilds it from scratch with all
    original seed data. Run this any time you want to return the demo to
    its "Day 1" state (e.g., after a live demo mutated balances or accounts).

HOW TO RUN:
    python z_reset_world.py
    (Run from the metro_city_demo folder, or from any folder with the full path.)

TABLES CREATED:
    1. product_catalog    -- 5 internet plans (Copper + Fiber tiers)
    2. address_inventory  -- 20 addresses (10 Occupied / 10 Vacant)
    3. customer_accounts  -- 20 accounts (10 Active / 10 Canceled)

IMPORTANT NOTES:
    - equipment_installed stores "ONT" (Fiber) or "Modem" (Copper) as text.
      T3_EquipmentLogic reads this column to determine install type.
    - plan_name in customer_accounts must exactly match plan_name in product_catalog.
      T7_CalcNextBill JOINs on plan_name to look up the monthly price.
    - Emily (10005) has a last_waiver_date set to ~6 months ago so T8_CheckFeeWaiver
      correctly identifies her as having used a waiver within the last 12 months.
"""

import sqlite3
import os
from datetime import datetime, timedelta


def reset_world():
    """
    Drops and recreates all tables, then seeds the full Metro City dataset.
    Deletes the old .db file first for a truly clean slate.
    """

    db_path = os.path.join(os.path.dirname(__file__), "metro_city.db")

    # Delete the old DB file to guarantee no stale schema or data carries over.
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print("  Deleted old database file.")
        except PermissionError:
            print("  Could not delete file (it may be locked). Attempting to drop tables instead.")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("--- INITIATING GLOBAL RESET ---\n")

    # =========================================================================
    # STEP 1: CREATE TABLES
    # Drop first (in case the delete above failed and old tables exist).
    # =========================================================================

    # --- product_catalog ---
    # Stores the 5 internet plans. plan_name is the join key used by T7.
    cursor.execute("DROP TABLE IF EXISTS product_catalog")
    cursor.execute("""
        CREATE TABLE product_catalog (
            plan_id        TEXT PRIMARY KEY,
            plan_name      TEXT,
            technology     TEXT,     -- "Fiber" or "Copper"
            speed_mbps     INTEGER,
            monthly_price  REAL
        )
    """)

    # --- address_inventory ---
    # 20 addresses across the city. equipment_installed drives T3's install logic.
    # "ONT" = Fiber (needs technician to activate). "Modem" = Copper (plug-and-play).
    cursor.execute("DROP TABLE IF EXISTS address_inventory")
    cursor.execute("""
        CREATE TABLE address_inventory (
            addr_id             TEXT PRIMARY KEY,  -- Short code, e.g. "A01"
            street              TEXT,
            city_state_zip      TEXT,
            max_tech_type       TEXT,              -- "Fiber" or "Copper"
            max_speed           INTEGER,           -- Max Mbps at this address
            equipment_installed TEXT,              -- "ONT" (Fiber) or "Modem" (Copper)
            status              TEXT               -- "Occupied" or "Vacant"
        )
    """)

    # --- customer_accounts ---
    # One row per account. Active customers have status="ACTIVE".
    # Canceled customers have status="CANCELED" and an end_date.
    cursor.execute("DROP TABLE IF EXISTS customer_accounts")
    cursor.execute("""
        CREATE TABLE customer_accounts (
            account_id       INTEGER PRIMARY KEY,
            first_name       TEXT,
            address_id       TEXT,              -- FK to address_inventory.addr_id
            plan_name        TEXT,              -- Must match product_catalog.plan_name
            tenure_years     REAL,
            autopay_active   INTEGER,           -- 1 = True, 0 = False
            waivers_used_12m INTEGER,           -- 1 = True, 0 = False (informational)
            pending_balance  REAL,
            status           TEXT,              -- "ACTIVE" or "CANCELED"
            email            TEXT,
            phone_number     TEXT,
            install_date     TEXT,              -- "YYYY-MM-DD" or NULL
            install_slot     TEXT,              -- "AM" or "PM" or NULL
            reminder_active  INTEGER,           -- 1 = True, 0 = False
            last_waiver_date TEXT,              -- "YYYY-MM-DD" or NULL
            start_date       TEXT,
            end_date         TEXT
        )
    """)

    print("Tables created.\n")

    # =========================================================================
    # STEP 2: SEED PRODUCT CATALOG
    # 5 plans: 1 Copper entry-level + 4 Fiber tiers.
    # plan_name values here must match exactly what customer_accounts.plan_name uses.
    # =========================================================================
    products = [
        ('P001', 'Internet 100', 'Copper',  100,  45.00),
        ('P002', 'Fiber 300',    'Fiber',   300,  55.00),
        ('P003', 'Fiber 500',    'Fiber',   500,  65.00),
        ('P004', 'Fiber 1 Gig', 'Fiber',  1000,  80.00),
        ('P005', 'Fiber 2 Gig', 'Fiber',  2000, 110.00),
    ]
    cursor.executemany("INSERT INTO product_catalog VALUES (?,?,?,?,?)", products)
    print(f"Product Catalog: {len(products)} plans loaded.")

    # =========================================================================
    # STEP 3: SEED ADDRESS INVENTORY
    # Group A (A01-A10): Occupied homes -- where current customers live.
    # Group B (A11-A20): Vacant homes -- available destinations for moves.
    #
    # equipment_installed rules:
    #   Fiber address -> "ONT"   (T3 returns "Technician Install")
    #   Copper address -> "Modem" (T3 returns "Self-Install")
    # =========================================================================
    addresses = [
        # --- Occupied Addresses (A01-A10) ---
        # addr_id  street              city_state_zip        tech     spd  equip    status
        ('A01', '100 First Ave',    'Dallas, TX 75202', 'Fiber',  1000, 'ONT',   'Occupied'),
        ('A02', '200 Second Ave',   'Dallas, TX 75202', 'Fiber',  1000, 'ONT',   'Occupied'),
        ('A03', '300 Third Ave',    'Dallas, TX 75202', 'Copper',  100, 'Modem', 'Occupied'),
        ('A04', '400 Fourth Ave',   'Dallas, TX 75202', 'Fiber',  1000, 'ONT',   'Occupied'),
        ('A05', '500 Fifth Ave',    'Dallas, TX 75202', 'Fiber',  1000, 'ONT',   'Occupied'),
        ('A06', '600 Sixth Ave',    'Dallas, TX 75202', 'Copper',  100, 'Modem', 'Occupied'),
        ('A07', '700 Seventh Ave',  'Dallas, TX 75202', 'Fiber',  1000, 'ONT',   'Occupied'),
        ('A08', '800 Eighth Ave',   'Dallas, TX 75202', 'Fiber',  2000, 'ONT',   'Occupied'),
        ('A09', '900 Ninth Ave',    'Dallas, TX 75202', 'Copper',  100, 'Modem', 'Occupied'),
        ('A10', '1000 Tenth Ave',   'Dallas, TX 75202', 'Fiber',  1000, 'ONT',   'Occupied'),

        # --- Vacant Addresses (A11-A20) ---
        # These are the destinations customers can move to.
        ('A11', '100 First St',    'Dallas, TX 75202', 'Fiber',  1000, 'ONT',   'Vacant'),
        ('A12', '200 Second St',   'Dallas, TX 75202', 'Fiber',  1000, 'ONT',   'Vacant'),
        ('A13', '300 Third St',    'Dallas, TX 75202', 'Copper',  100, 'Modem', 'Vacant'),
        ('A14', '400 Fourth St',   'Dallas, TX 75202', 'Fiber',  1000, 'ONT',   'Vacant'),
        ('A15', '500 Fifth St',    'Dallas, TX 75202', 'Fiber',  1000, 'ONT',   'Vacant'),
        ('A16', '600 Sixth St',    'Dallas, TX 75202', 'Copper',  100, 'Modem', 'Vacant'),
        ('A17', '700 Seventh St',  'Dallas, TX 75202', 'Fiber',  1000, 'ONT',   'Vacant'),
        ('A18', '800 Eighth St',   'Dallas, TX 75202', 'Fiber',  2000, 'ONT',   'Vacant'),
        ('A19', '900 Ninth St',    'Dallas, TX 75202', 'Copper',  100, 'Modem', 'Vacant'),
        ('A20', '1000 Tenth St',   'Dallas, TX 75202', 'Fiber',  1000, 'ONT',   'Vacant'),
    ]
    cursor.executemany("INSERT INTO address_inventory VALUES (?,?,?,?,?,?,?)", addresses)
    print(f"Address Inventory: {len(addresses)} addresses loaded.")

    # =========================================================================
    # STEP 4: SEED CUSTOMER ACCOUNTS
    #
    # ACTIVE ACCOUNTS (10001-10010) -- The 10 demo personas.
    #   Each has a specific archetype designed to trigger different agent paths.
    #   See CLAUDE.md "Demo Accounts Cheat Sheet" for the full explanation.
    #
    # CANCELED ACCOUNTS (10011-10020) -- Available for win-back demos.
    #   All have no address (they've left), Fiber 300 plan, 1.5yr tenure,
    #   autopay OFF, $0 balance, and status=CANCELED.
    #
    # KEY NOTES:
    #   - plan_name must exactly match product_catalog (e.g., "Internet 100" not "Copper 100")
    #   - Emily (10005) has last_waiver_date ~6 months ago -> T8 Rule C fails for her
    #   - Mike (10004) has $82.45 pending_balance -> triggers billing gate in moves_agent
    #   - autopay_active and reminder_active stored as integers: 1=True, 0=False
    # =========================================================================

    # Emily's waiver was used ~6 months ago (within the 12-month window T8 checks).
    emily_waiver_date = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")

    # Columns: account_id, first_name, address_id, plan_name, tenure_years,
    #          autopay_active, waivers_used_12m, pending_balance, status,
    #          email, phone_number, install_date, install_slot, reminder_active,
    #          last_waiver_date, start_date, end_date
    customers = [
        # --- Active Customers ---
        # 10001 Muru: 4.2yr tenure, autopay ON, $0 balance -> perfect waiver candidate (all 3 rules pass)
        (10001, 'Muru',    'A01', 'Fiber 1 Gig',  4.2, 1, 0,  0.00, 'ACTIVE', 'muru@mail.com',     '555-010-0001', None, None, 0, None,              None, None),
        # 10002 John: 0.5yr tenure, autopay OFF -> waiver FAIL on Rules A and B
        (10002, 'John',    'A02', 'Fiber 500',    0.5, 0, 0,  0.00, 'ACTIVE', 'john@mail.com',     '555-010-0002', None, None, 0, None,              None, None),
        # 10003 Sarah: Copper legacy customer (A03) -> upsell target for fiber
        (10003, 'Sarah',   'A03', 'Internet 100', 5.0, 1, 0,  0.00, 'ACTIVE', 'sarah@mail.com',    '555-010-0003', None, None, 0, None,              None, None),
        # 10004 Mike: $82.45 balance -> billing gate demo (must pay before move/cancel)
        (10004, 'Mike',    'A04', 'Fiber 1 Gig',  2.0, 1, 0, 82.45, 'ACTIVE', 'mike@mail.com',     '555-010-0004', None, None, 0, None,              None, None),
        # 10005 Emily: 3.1yr tenure + recent waiver -> T8 Rule A (tenure) and Rule C (waiver) both fail
        (10005, 'Emily',   'A05', 'Fiber 300',    3.1, 1, 1,  0.00, 'ACTIVE', 'emily@mail.com',    '555-010-0005', None, None, 0, emily_waiver_date, None, None),
        # 10006 David: Copper + no autopay -> two waiver failures + upsell target
        (10006, 'David',   'A06', 'Internet 100', 1.0, 0, 0,  0.00, 'ACTIVE', 'david@mail.com',    '555-010-0006', None, None, 0, None,              None, None),
        # 10007 Jessica: 6yr tenure but autopay OFF -> waiver fails Rule B only
        (10007, 'Jessica', 'A07', 'Fiber 1 Gig',  6.0, 0, 0,  0.00, 'ACTIVE', 'jessica@mail.com',  '555-010-0007', None, None, 0, None,              None, None),
        # 10008 Chris: Very new customer (0.2yr), top-tier plan
        (10008, 'Chris',   'A08', 'Fiber 2 Gig',  0.2, 1, 0,  0.00, 'ACTIVE', 'chris@mail.com',    '555-010-0008', None, None, 0, None,              None, None),
        # 10009 Amanda: 10yr tenure, small $15 balance -> long-loyal but owes a little
        (10009, 'Amanda',  'A09', 'Internet 100', 10.0, 1, 0, 15.00, 'ACTIVE', 'amanda@mail.com',   '555-010-0009', None, None, 0, None,              None, None),
        # 10010 James: 2.5yr tenure (just under 3yr threshold) -> waiver fails Rule A
        (10010, 'James',   'A10', 'Fiber 500',    2.5, 1, 0,  0.00, 'ACTIVE', 'james@mail.com',    '555-010-0010', None, None, 0, None,              None, None),

        # --- Canceled Customers (win-back demos) ---
        (10011, 'Robert',    None, 'Fiber 300', 1.5, 0, 0, 0.00, 'CANCELED', 'robert@mail.com',    '555-010-0011', None, None, 0, None, None, None),
        (10012, 'Patricia',  None, 'Fiber 300', 1.5, 0, 0, 0.00, 'CANCELED', 'patricia@mail.com',  '555-010-0012', None, None, 0, None, None, None),
        (10013, 'Jennifer',  None, 'Fiber 300', 1.5, 0, 0, 0.00, 'CANCELED', 'jennifer@mail.com',  '555-010-0013', None, None, 0, None, None, None),
        (10014, 'Michael',   None, 'Fiber 300', 1.5, 0, 0, 0.00, 'CANCELED', 'michael@mail.com',   '555-010-0014', None, None, 0, None, None, None),
        (10015, 'Linda',     None, 'Fiber 300', 1.5, 0, 0, 0.00, 'CANCELED', 'linda@mail.com',     '555-010-0015', None, None, 0, None, None, None),
        (10016, 'Elizabeth', None, 'Fiber 300', 1.5, 0, 0, 0.00, 'CANCELED', 'elizabeth@mail.com', '555-010-0016', None, None, 0, None, None, None),
        (10017, 'William',   None, 'Fiber 300', 1.5, 0, 0, 0.00, 'CANCELED', 'william@mail.com',   '555-010-0017', None, None, 0, None, None, None),
        (10018, 'Barbara',   None, 'Fiber 300', 1.5, 0, 0, 0.00, 'CANCELED', 'barbara@mail.com',   '555-010-0018', None, None, 0, None, None, None),
        (10019, 'Richard',   None, 'Fiber 300', 1.5, 0, 0, 0.00, 'CANCELED', 'richard@mail.com',   '555-010-0019', None, None, 0, None, None, None),
        (10020, 'Susan',     None, 'Fiber 300', 1.5, 0, 0, 0.00, 'CANCELED', 'susan@mail.com',     '555-010-0020', None, None, 0, None, None, None),
    ]
    cursor.executemany(
        "INSERT INTO customer_accounts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        customers
    )
    print(f"Customer Accounts: {len(customers)} accounts loaded.")

    conn.commit()
    conn.close()

    print("\n--- GLOBAL RESET COMPLETE. Metro City is back to Day 1. ---")


# =============================================================================
# ENTRY POINT
# =============================================================================
if __name__ == "__main__":
    reset_world()
