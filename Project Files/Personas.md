
# Persona 1: The "Perfect" Candidate (Waiver Success)
Account ID: 10001 (Muru)
Criteria: Tenure > 3 Years (4.2), AutoPay Active, No Balance.
Experience: The "Happy Path." The Agent will greet you warmly as a loyal customer and successfully grant the $99 installation fee waiver during the move.

# Persona 2: The "New" Customer (Waiver Failure)
Account IDs: 10002 (John), 10008 (Chris), 10010 (James)
Criteria: Tenure < 3 Years.
Experience: The Agent will process the move but deny the fee waiver, explaining that the customer does not meet the tenure or autopay requirements ($99 fee is added).

# Persona 3: The "Debtor" (Billing Gate)
Account ID: 10004 (Mike)
Criteria: Outstanding Balance > $0.00 ($82.45).
Experience: The Agent will block the move request immediately and force you to pay the $82.45 balance using the card on file before proceeding.

# Persona 4: The "Legacy" User (Upsell Target)
Account ID: 10003 (Sarah), 10006 (David)
Criteria: Current Plan is "Internet 100" (Old Technology).
Experience: If you move these users to a "Fiber" address (e.g., A11), the Agent will aggressively pitch the upgrade to Fiber 1 Gig ("Great news, Fiber is available!").

# Persona 5: The "Churned" User (Status Check)
Account IDs: 10011 through 10020 (Robert, Patricia, etc.)
Criteria: Status = CANCELED.
Experience: The Agent will recognize the ID but say "Account 10011 is currently closed." It will then pivot to a Sales flow, asking if you want to set up new service at a new address.

# Persona 6 - Edge Case: The "Double Dipper" (Waiver Fail)
Account ID: 10005 (Emily)
Criteria: Tenure is high (3.1 years), BUT waivers_used_12m = TRUE.
Experience: This tests the "History" rule. Even though she is loyal, the Agent will deny the waiver because she already used one recently.

---

# Stress Test: The "Difficult Customer" (Multi-Challenge Move)
Account ID: 10004 (Mike)
Criteria: Outstanding Balance ($82.45) + 3 embedded challenges mid-flow.
Experience: An 8-turn gauntlet that stress-tests edge cases layered on top of a standard billing-gate move. The agent must handle three curveballs without breaking the move flow.

## Prompt Script (8 Turns)

**Turn 1:** `I want to move to 100 First St. Account 10004.`
→ Agent detects $82.45 balance. Asks for payment consent. Does NOT proceed with move.

**Turn 2 (Challenge 1 — Card Security):** `Can I use a different credit card for this payment?`
→ Agent delivers card security hard stop: cannot accept new card details over chat. Offers to connect a specialist OR proceed with card on file. Does NOT escalate immediately.

**Turn 3:** `No, let's just use the card on file.`
→ Agent processes payment with card on file (ending 8899). Clears balance. Moves into address check + fee check + plan question in one response.

**Turn 4 (Challenge 2 — Plan Browsing):** `Can you show me all available plan options?`
→ Agent presents the full inline Fiber plan table (no tool call needed):
  Fiber 300 · $55/mo | Fiber 500 · $65/mo | Fiber 1 Gig · $80/mo | Fiber 2 Gig · $110/mo

**Turn 5:** `Fiber 1 Gig please.`
→ Agent confirms Fiber 1 Gig at $80/mo. Calls T9 (no date), presents 4 appointment slots.

**Turn 6:** `Option 2 is fine.`
→ Agent confirms the chosen slot. Executes the move: T9(date) + T3 + T12(action=MOVE) + T13 receipt. Offers reminder.

**Turn 7:** `Yes, set the reminder.`
→ Agent calls T11. Sets day-before reminder at 10:00 AM.

**Turn 8 (Challenge 3 — Post-Move Bill Question):** `What will my next bill be? Are there any taxes?`
→ Agent answers from context (does NOT call T7 — old account is CANCELED). States: "Your new Fiber 1 Gig plan is $80/mo, due on the 1st of next month. Flat rate — no added taxes or fees."

## Key Validations
- Card security script fires before any escalation offer
- Plan table displayed inline without routing to sales_agent
- T12 fires with action="MOVE" (not "CANCEL")
- Post-move bill answered from handoff context, not T7
- DB: old account CANCELED, new account ACTIVE at 100 First St (A11), Fiber 1 Gig
