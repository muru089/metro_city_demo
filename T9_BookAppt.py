"""
T9_BookAppt
-----------
WHAT THIS TOOL DOES:
    Simulates a technician appointment calendar.
    Two modes depending on whether a date is provided:

    NO DATE (Rule of 4): Returns 4 available slots -- 2 days x AM + PM -- starting 2 days out.
    WITH DATE: Validates the requested date and confirms it if it's within the booking window.

WHY IT MATTERS (Business Logic):
    - Only called when T3_EquipmentLogic returns "Technician Install" (Fiber addresses).
      Self-install addresses never need an appointment.
    - The "Rule of 4" pattern: always offer exactly 4 options initially.
      This gives the customer real choices without overwhelming them.
    - 30-day booking window is enforced: no bookings more than 30 days from today.
    - This tool does NOT use the database -- it simulates an always-available calendar
      for demo purposes. In a real system, it would check actual technician availability.

INPUTS:
    conn     : Database connection (passed in for consistency -- not used by this tool).
    date_str : A specific date in YYYY-MM-DD format (optional).
               If not provided, returns the 4 next available slots.
               If provided, confirms or rejects that specific date.

OUTPUT:
    No date  : {"status": "success", "available_slots": ["2026-03-07 (8:00 AM - 12:00 PM)", ...]}
    With date: {"status": "success", "message": "Appointment confirmed for 2026-03-07.", "booked_date": "..."}
    Error    : {"status": "error",   "message": "reason (past date / beyond 30 days / bad format)"}
"""

import sqlite3
from datetime import datetime, timedelta


def T9_BookAppt(conn, date_str=None):
    """
    Lists available appointment slots or confirms a specific date.

    Args:
        conn     : Database connection (not used -- kept for interface consistency).
        date_str : Requested date in YYYY-MM-DD format (optional).
                   Omit to receive the next 4 available slots.

    Returns:
        dict: Available slots list OR confirmation of a specific date.
    """

    today = datetime.now()

    # The 30-day horizon -- the furthest date we will accept for booking.
    max_date = today + timedelta(days=30)

    # =========================================================================
    # SCENARIO A: No date given -- return the Rule of 4 slots
    # Generate 4 options: 2 days x (AM window + PM window), starting 2 days from today.
    # We start 2 days out (not tomorrow) to give logistics time to prepare.
    # =========================================================================
    if not date_str:
        slots = []

        for i in range(2):
            # Day 1 = today + 2, Day 2 = today + 3
            future_date = today + timedelta(days=2 + i)
            formatted_date = future_date.strftime("%Y-%m-%d")

            # Morning window: 8:00 AM to 12:00 PM
            slots.append(f"{formatted_date} (8:00 AM - 12:00 PM)")

            # Afternoon window: 1:00 PM to 5:00 PM
            slots.append(f"{formatted_date} (1:00 PM - 5:00 PM)")

        return {
            "status": "success",
            "message": "Here are the next available appointments:",
            "available_slots": slots  # Always exactly 4 items
        }

    # =========================================================================
    # SCENARIO B: Date given -- validate and confirm it
    # =========================================================================
    else:
        try:
            # Convert the string (e.g., "2026-03-07") to a Python date object.
            # strptime raises ValueError if the format doesn't match.
            requested_date = datetime.strptime(date_str, "%Y-%m-%d")

            # Check 1: Reject past dates
            if requested_date.date() < today.date():
                return {
                    "status": "error",
                    "message": "That date is in the past. Please choose a future date."
                }

            # Check 2: Reject dates beyond the 30-day window
            if requested_date.date() > max_date.date():
                return {
                    "status": "error",
                    "message": (
                        f"I can only book appointments within the next 30 days "
                        f"(before {max_date.strftime('%Y-%m-%d')}). "
                        "Please choose an earlier date."
                    )
                }

            # Passed both checks -- confirm the appointment.
            # (In a real system this would write to a calendar API.)
            return {
                "status": "success",
                "message": f"Appointment confirmed for {date_str}.",
                "booked_date": date_str
            }

        except ValueError:
            # The date string didn't match YYYY-MM-DD format.
            return {
                "status": "error",
                "message": "Invalid date format. Please use YYYY-MM-DD (e.g., 2026-03-15)."
            }


# =============================================================================
# TEST BLOCK
# Run this file directly (python T9_BookAppt.py) to test in isolation.
# No database needed -- pass None as the connection.
# =============================================================================
if __name__ == "__main__":
    print("=== T9_BookAppt -- Manual Test Run ===\n")

    print("--- Test 1: No date -- show Rule of 4 slots ---")
    print("Expected: 4 slots starting 2 days from today")
    print(T9_BookAppt(None))

    print("\n--- Test 2: Valid future date (tomorrow) ---")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"Testing with: {tomorrow}")
    print("Expected: confirmed")
    print(T9_BookAppt(None, tomorrow))

    print("\n--- Test 3: Past date ---")
    print("Expected: error / past date")
    print(T9_BookAppt(None, "2020-01-01"))

    print("\n--- Test 4: Date beyond 30 days ---")
    far_future = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
    print(f"Testing with: {far_future}")
    print("Expected: error / beyond 30 days")
    print(T9_BookAppt(None, far_future))

    print("\n--- Test 5: Bad date format ---")
    print("Expected: error / invalid format")
    print(T9_BookAppt(None, "next tuesday"))
