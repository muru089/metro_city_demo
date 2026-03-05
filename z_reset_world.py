import sqlite3
import os

def reset_world():
    """
    reset_world: Completely wipes the database and restores the original 
    seed data for Accounts, Inventory, and Products.
    """
    db_path = os.path.join(os.path.dirname(__file__), 'metro_city.db')
    
    # Delete the old DB file if it exists to ensure a perfectly clean slate
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print("🗑️  Deleted old database file.")
        except PermissionError:
            print("⚠️  Could not delete file (it might be locked). Attempting to drop tables instead.")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("--- 🌍 INITIATING GLOBAL RESET ---")

    # ==========================================
    # 1. CREATE TABLES
    # ==========================================
    
    # PRODUCT CATALOG
    cursor.execute("DROP TABLE IF EXISTS product_catalog")
    cursor.execute("""
        CREATE TABLE product_catalog (
            plan_id TEXT PRIMARY KEY,
            plan_name TEXT,
            technology TEXT,
            speed_mbps INTEGER,
            monthly_price REAL
        )
    """)

    # ADDRESS INVENTORY
    cursor.execute("DROP TABLE IF EXISTS address_inventory")
    cursor.execute("""
        CREATE TABLE address_inventory (
            addr_id TEXT PRIMARY KEY,
            street TEXT,
            city_state_zip TEXT,
            max_tech_type TEXT,
            max_speed INTEGER,
            equipment_installed BOOLEAN,
            status TEXT
        )
    """)

    # CUSTOMER ACCOUNTS
    cursor.execute("DROP TABLE IF EXISTS customer_accounts")
    cursor.execute("""
        CREATE TABLE customer_accounts (
            account_id INTEGER PRIMARY KEY,
            first_name TEXT,
            address_id TEXT,
            plan_name TEXT,
            tenure_years REAL,
            autopay_active BOOLEAN,
            waivers_used_12m BOOLEAN,
            pending_balance REAL,
            status TEXT,
            email TEXT,
            phone_number TEXT,
            install_date TEXT,
            install_slot TEXT,
            reminder_active BOOLEAN,
            last_waiver_date TEXT,
            start_date TEXT,
            end_date TEXT
        )
    """)
    print("✅ Tables Created.")

    # ==========================================
    # 2. POPULATE PRODUCT CATALOG
    # ==========================================
    products = [
        ('P_COP_100', 'Internet 100', 'Copper', 100, 45.0),
        ('P_FIB_300', 'Fiber 300',    'Fiber',  300, 55.0),
        ('P_FIB_500', 'Fiber 500',    'Fiber',  500, 65.0),
        ('P_FIB_1000','Fiber 1 Gig',  'Fiber', 1000, 80.0),
        ('P_FIB_2000','Fiber 2 Gig',  'Fiber', 2000, 110.0)
    ]
    cursor.executemany("INSERT INTO product_catalog VALUES (?,?,?,?,?)", products)
    print(f"✅ Product Catalog Restored ({len(products)} plans).")

    # ==========================================
    # 3. POPULATE ADDRESS INVENTORY
    # ==========================================
    addresses = [
        # Occupied Homes (A01-A10)
        ('A01', '100 First Ave',   'Dallas, TX 75202', 'Fiber', 1000, True,  'Occupied'),
        ('A02', '200 Second Ave',  'Dallas, TX 75202', 'Fiber', 2000, False, 'Occupied'),
        ('A03', '300 Third Ave',   'Dallas, TX 75202', 'Copper', 100, True,  'Occupied'),
        ('A04', '400 Fourth Ave',  'Dallas, TX 75202', 'Fiber', 1000, True,  'Occupied'),
        ('A05', '500 Fifth Ave',   'Dallas, TX 75202', 'Fiber',  500, False, 'Occupied'),
        ('A06', '600 Sixth Ave',   'Dallas, TX 75202', 'Copper', 100, True,  'Occupied'),
        ('A07', '700 Seventh Ave', 'Dallas, TX 75202', 'Fiber', 1000, True,  'Occupied'),
        ('A08', '800 Eighth Ave',  'Dallas, TX 75202', 'Fiber', 2000, True,  'Occupied'),
        ('A09', '900 Ninth Ave',   'Dallas, TX 75202', 'Copper', 100, False, 'Occupied'),
        ('A10', '1000 Tenth Ave',  'Dallas, TX 75202', 'Fiber', 1000, True,  'Occupied'),
        
        # Vacant Homes (A11-A20) - Destination addresses for moves
        ('A11', '100 First St',    'Dallas, TX 75202', 'Fiber', 1000, True,  'Vacant'),
        ('A12', '200 Second St',   'Dallas, TX 75202', 'Fiber', 2000, False, 'Vacant'),
        ('A13', '300 Third St',    'Dallas, TX 75202', 'Copper', 100, True,  'Vacant'),
        ('A14', '400 Fourth St',   'Dallas, TX 75202', 'Fiber',  500, True,  'Vacant'),
        ('A15', '500 Fifth St',    'Dallas, TX 75202', 'Fiber', 1000, False, 'Vacant'),
        ('A16', '600 Sixth St',    'Dallas, TX 75202', 'Copper', 100, False, 'Vacant'),
        ('A17', '700 Seventh St',  'Dallas, TX 75202', 'Fiber', 2000, True,  'Vacant'),
        ('A18', '800 Eighth St',   'Dallas, TX 75202', 'Fiber', 1000, True,  'Vacant'),
        ('A19', '900 Ninth St',    'Dallas, TX 75202', 'Copper', 100, True,  'Vacant'),
        ('A20', '1000 Tenth St',   'Dallas, TX 75202', 'Fiber', 1000, False, 'Vacant'),
    ]
    cursor.executemany("INSERT INTO address_inventory VALUES (?,?,?,?,?,?,?)", addresses)
    print(f"✅ Address Inventory Restored ({len(addresses)} locations).")

    # ==========================================
    # 4. POPULATE CUSTOMER ACCOUNTS
    # ==========================================
    # Columns: account_id, first_name, address_id, plan_name, tenure_years, autopay_active, 
    #          waivers_used_12m, pending_balance, status, email, phone_number,
    #          install_date, install_slot, reminder_active, last_waiver_date, start_date, end_date
    
    customers = [
        # Active Customers (1-10)
        (10001, 'Muru',   'A01', 'Fiber 1 Gig', 4.2, True,  False,  0.00, 'ACTIVE', 'muru@mail.com', '555-010-0001', None, None, 0, None, None, None),
        (10002, 'John',   'A02', 'Fiber 500',   0.5, False, False,  0.00, 'ACTIVE', 'john@mail.com', '555-010-0002', None, None, 0, None, None, None),
        (10003, 'Sarah',  'A03', 'Copper 100',  5.0, True,  False,  0.00, 'ACTIVE', 'sarah@mail.com', '555-010-0003', None, None, 0, None, None, None),
        
        # Mike (10004) - The primary demo user with a balance
        (10004, 'Mike',   'A04', 'Fiber 1 Gig', 2.0, True,  False, 82.45, 'ACTIVE', 'mike@mail.com', '555-010-0004', None, None, 0, None, None, None),
        
        (10005, 'Emily',  'A05', 'Fiber 300',   3.1, True,  True,   0.00, 'ACTIVE', 'emily@mail.com', '555-010-0005', None, None, 0, None, None, None),
        (10006, 'David',  'A06', 'Copper 100',  1.0, False, False,  0.00, 'ACTIVE', 'david@mail.com', '555-010-0006', None, None, 0, None, None, None),
        (10007, 'Jessica','A07', 'Fiber 1 Gig', 6.0, False, False,  0.00, 'ACTIVE', 'jessica@mail.com','555-010-0007', None, None, 0, None, None, None),
        (10008, 'Chris',  'A08', 'Fiber 2 Gig', 0.2, True,  False,  0.00, 'ACTIVE', 'chris@mail.com', '555-010-0008', None, None, 0, None, None, None),
        (10009, 'Amanda', 'A09', 'Copper 100', 10.0, True,  False, 15.00, 'ACTIVE', 'amanda@mail.com', '555-010-0009', None, None, 0, None, None, None),
        (10010, 'James',  'A10', 'Fiber 500',   2.5, True,  False,  0.00, 'ACTIVE', 'james@mail.com', '555-010-0010', None, None, 0, None, None, None),

        # Canceled Customers (11-20) - Useful for "Win-Back" demos if you build them later
        (10011, 'Robert',  None,  'Fiber 300',   1.5, False, False,  0.00, 'CANCELED', 'robert@mail.com', '555-010-0011', None, None, 0, None, None, None),
        (10012, 'Patricia',None,  'Fiber 300',   1.5, False, False,  0.00, 'CANCELED', 'patricia@mail.com','555-010-0012', None, None, 0, None, None, None),
        (10013, 'Jennifer',None,  'Fiber 300',   1.5, False, False,  0.00, 'CANCELED', 'jennifer@mail.com','555-010-0013', None, None, 0, None, None, None),
        (10014, 'Michael', None,  'Fiber 300',   1.5, False, False,  0.00, 'CANCELED', 'michael@mail.com','555-010-0014', None, None, 0, None, None, None),
        (10015, 'Linda',   None,  'Fiber 300',   1.5, False, False,  0.00, 'CANCELED', 'linda@mail.com',  '555-010-0015', None, None, 0, None, None, None),
        (10016, 'Elizabeth',None, 'Fiber 300',   1.5, False, False,  0.00, 'CANCELED', 'elizabeth@mail.com','555-010-0016', None, None, 0, None, None, None),
        (10017, 'William', None,  'Fiber 300',   1.5, False, False,  0.00, 'CANCELED', 'william@mail.com', '555-010-0017', None, None, 0, None, None, None),
        (10018, 'Barbara', None,  'Fiber 300',   1.5, False, False,  0.00, 'CANCELED', 'barbara@mail.com', '555-010-0018', None, None, 0, None, None, None),
        (10019, 'Richard', None,  'Fiber 300',   1.5, False, False,  0.00, 'CANCELED', 'richard@mail.com', '555-010-0019', None, None, 0, None, None, None),
        (10020, 'Susan',   None,  'Fiber 300',   1.5, False, False,  0.00, 'CANCELED', 'susan@mail.com',   '555-010-0020', None, None, 0, None, None, None),
    ]
    cursor.executemany("INSERT INTO customer_accounts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", customers)
    print(f"✅ Customer Accounts Restored ({len(customers)} accounts).")

    conn.commit()
    conn.close()
    print("\n🎉 GLOBAL RESET COMPLETE. Metro City is back to Day 1.")

if __name__ == "__main__":
    reset_world()