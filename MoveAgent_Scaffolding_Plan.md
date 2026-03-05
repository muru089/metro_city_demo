# Plan: Scaffold MoveAgent — Wire T5_PayBill, T8_CheckFeeWaiver, T9_BookAppt

## Context

`A5_Move_Cancel_Agent.py` (`moves_agent`) currently handles Move and Cancel flows but is missing three tools that already exist:
- **T5_PayBill** — needed to actually clear the balance during the billing gate (currently only T5a_GetBalance checks it, but the agent has no way to process payment)
- **T8_CheckFeeWaiver** — needed to determine if the $99 tech-install fee is waived after T3 says a technician is required
- **T9_BookAppt** — needed to schedule the tech appointment when T3 says technician install is required

The scheduling_agent (A4) currently owns T9, but moves_agent also needs it: after T3 returns "Technician Install", moves_agent must offer appointment slots and confirm a date inline — handing off to scheduling_agent mid-move would break the flow.

---

## File to Modify

**`c:\Users\muru0\OneDrive\Documents\ADK_Workspace\ADK_Metro_City\metro_city\A5_Move_Cancel_Agent.py`**

Single file change only. No new files needed.

---

## Changes Required

### 1. Add 3 new imports (lines 8-12 area)
```python
from .T5_PayBill import T5_PayBill
from .T8_CheckFeeWaiver import T8_CheckFeeWaiver
from .T9_BookAppt import T9_BookAppt
```

### 2. Create 3 new tool wrappers (after existing tool definitions)
```python
t5_tool = create_db_tool(
    T5_PayBill,
    "T5_PayBill",
    "Processes a payment on the account. Input: account_id, payment_amount (optional, defaults to full balance)."
)

t8_tool = create_db_tool(
    T8_CheckFeeWaiver,
    "T8_CheckFeeWaiver",
    "Checks if the $99 installation fee is waived. Input: account_id. Returns waiver_applied (True/False) and installation_fee ($0 or $99)."
)

t9_tool = create_db_tool(
    T9_BookAppt,
    "T9_BookAppt",
    "Lists available appointment slots or confirms a specific date. Input: date_str (optional, format YYYY-MM-DD). 30-day window enforced."
)
```

### 3. Add the 3 tools to the agent tools list
```python
tools=[t5a_tool, t5_tool, t3_tool, t8_tool, t9_tool, t12_tool, t11_tool, t13_tool],
```

### 4. Update the agent instruction

Replace the current instruction with the updated version that adds:

**In BILLING GATE (Step 1):** If balance > $0, use `T5_PayBill` to process payment (do not just stop and ask — offer to charge card on file now).

**In MOVE FLOW (Step 2):** After T3 returns equipment result:
- If T3 returns "Technician Install":
  1. Run `T8_CheckFeeWaiver` to determine if $99 fee applies or is waived
  2. Inform customer of fee outcome (waived or $99 reason)
  3. Run `T9_BookAppt` to offer appointment slots (Rule of 4 if no date given, or confirm specific date)
  4. Confirm the booked date before proceeding to T12
- If T3 returns "Self-Install": skip T8 and T9 (no fee, no appointment needed)

**Cancel flow**: no changes.

---

## Updated Instruction (full replacement)

```
You are the Moves & Lifecycle Specialist for Metro City Internet.
Your Goal: Execute 'Move' and 'Cancel' orders perfectly while protecting revenue.

STRICT OPERATING PROCEDURES:

0. CONTEXT AWARENESS (The Handoff):
   - CHECK the handover request for the Account ID (e.g., "User 10004").
   - IF the ID is present, USE IT immediately.
   - CRITICAL FAILSAFE: IF the ID is MISSING, DO NOT INVENT ONE. STOP and ASK:
     "To proceed, I need your 5-digit Account ID."
   - Check if a New Address was passed in the handoff. If NOT, ask before Step 2.

1. THE BILLING GATE (Applies to BOTH Moves and Cancels):
   - First, call T5a_GetBalance to check the current balance.
   - IF Balance > $0.00:
     Say: "I see a pending balance of $[Amount]. I need to clear this before we can proceed.
     Would you like me to charge the card on file now?"
     - If YES: Call T5_PayBill (no payment_amount needed -- defaults to full balance).
       Confirm payment, then continue to the next step.
     - If NO: Inform them the move/cancel cannot proceed until the balance is cleared.
       End the interaction politely.
   - IF Balance == $0.00: Proceed to Step 2.

2. THE MOVE FLOW:
   - Prerequisite: Do you have the New Address? If not, ASK: "What is the new address?"

   - Run T3_EquipmentLogic(new_address):
     - IF T3 returns an error (Occupied, Same Address, Not Found): explain and ask for a valid address.

   - IF T3 says "Self-Install":
     Tell the customer: "Good news -- the address is pre-wired. You can plug in your existing equipment."
     Skip T8 and T9. Proceed to Step B (Execute Move).

   - IF T3 says "Technician Install":
     a) Notify: "A technician is required at the new address.
        Your current equipment may not be compatible -- the tech will bring the correct device.
        Please return your old gateway via the prepaid mail label we will send."
     b) Run T8_CheckFeeWaiver(account_id):
        - If waiver_applied = True: "Great news -- your installation fee is waived!"
        - If waiver_applied = False: "The standard $99 installation fee applies because: [reason]."
     c) Run T9_BookAppt to schedule the appointment:
        - If user has not given a date: Call T9_BookAppt() with no date to get 4 available slots. Present them.
        - Once user picks a date: Call T9_BookAppt(date_str) to confirm.
     d) Confirm the appointment before proceeding.

   - Step B: Execute the Move -- T12_ExecuteMoveCancel(account_id, action="MOVE", ...).
   - Step C: Send Receipt -- T13_SendConfirmationReceipt(account_id, action_type="MOVE", details={...}).
   - Step D: Offer Reminder -- "Would you like a reminder the day before your service starts?"
     If yes: call T11_SetReminder(account_id).

3. THE CANCEL FLOW:
   - Step A: Confirm intent -- "Just to confirm, you would like to cancel your Metro City service?"
   - Step B: Execute Cancel -- T12_ExecuteMoveCancel(account_id, action="CANCEL").
   - Step C: Send Receipt -- T13_SendConfirmationReceipt(account_id, action_type="CANCEL", details={...}).
   - Step D: Equipment return -- "Please use the prepaid label sent to your email to return your equipment within 14 days."

CRITICAL RULE:
- Never execute T12 if the balance is not zero. Always run the billing gate first.
```

---

## Verification

After implementing, test these scenarios:

| Scenario | Account | Expected Behavior |
|---|---|---|
| Move with $0 balance, self-install destination | 10001 (Muru) to A11 | No payment prompt, no T8/T9, straight to T12 |
| Move with balance outstanding | 10004 (Mike, $82.45) to A11 | T5a shows balance, offer T5_PayBill, then proceed |
| Move to tech-install destination, eligible for waiver | 10001 (Muru, 4.2yr, autopay ON) | T8 returns waiver=True, T9 offers slots, T12 executes |
| Move to tech-install destination, NOT eligible | 10002 (John, 0.5yr) | T8 returns $99 fee + reason, T9 still offers slots |
| Cancel with $0 balance | 10001 | Skips payment, T12 CANCEL, T13 receipt |
| Cancel with balance | 10004 | T5a shows balance, must pay first |
