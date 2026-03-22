
# Persona 1: The "Perfect" Candidate (Waiver Success)
**Account ID:** 10001 (Muru)
**Destination:** 200 Second St → A12 (Fiber, Vacant)
**Turn Count:** 4 turns

**Account Snapshot:**
- Tenure: 4.2 years ✅ (Rule A PASS — needs > 3yr)
- Autopay: ON ✅ (Rule B PASS)
- Waiver used in last 12 months: No ✅ (Rule C PASS)
- Balance: $0.00 (no billing gate)
- Current Plan: Fiber 1 Gig

**Waiver Outcome:** GRANTED — all 3 rules pass. $0 install fee.

**Starting Utterance:**
> "Hi, I'd like to move my service to 200 Second St. Account 10001."

**Full Prompt Script:**
- Turn 1: `Hi, I'd like to move my service to 200 Second St. Account 10001.`
- Turn 2: `Fiber 1 Gig`
- Turn 3: `Option 2 is fine`
- Turn 4: `Yes`

**What to Watch For:**
- Agent opens with a loyalty greeting ("Thank you for being a valued customer for 4.2 years")
- No billing gate — move flow starts immediately
- Agent explicitly states all 3 waiver rules pass and fee is waived ($0)
- 4 appointment slots presented (Rule of 4)
- Reminder offer at the end
- Clean, fewest-turns happy path — great opener for any demo

---------------------------------------

# Persona 2: The "New" Customer (Waiver Failure)
**Account IDs:** 10002 (John), 10008 (Chris), 10010 (James)
**Destination:** 400 Fourth St → A14 (Fiber, Vacant) — use for John (10002)
**Turn Count:** 4 turns

**Account Snapshot (John 10002):**
- Tenure: 0.5 years ❌ (Rule A FAIL — needs > 3yr)
- Autopay: OFF ❌ (Rule B FAIL)
- Balance: $0.00 (no billing gate)
- Current Plan: Fiber 500

**Waiver Outcome:** DENIED — 2 rules fail. $99 install fee applies.
Agent must state both specific reasons (tenure too short + autopay not active).

**Starting Utterance:**
> "Hi, I'd like to move my service to 400 Fourth St. Account 10002."

**Full Prompt Script:**
- Turn 1: `Hi, I'd like to move my service to 400 Fourth St. Account 10002.`
- Turn 2: `Fiber 500`
- Turn 3: `Option 1 is fine`
- Turn 4: `Yes`

**What to Watch For:**
- Standard greeting (no loyalty script — tenure < 3yr)
- Agent states $99 fee AND gives both specific failing reasons — never just "you don't qualify"
- Move still completes successfully despite the fee
- Good contrast demo to run immediately after Persona 1 to show the waiver logic

---------------------------------------

# Persona 3: The "Debtor" (Billing Gate)
**Account ID:** 10004 (Mike)
**Destination:** 100 First St → A11 (Fiber, Vacant)
**Turn Count:** 5 turns (extra billing turn at the start)

**Account Snapshot:**
- Balance: $82.45 ⚠️ (billing gate fires — must pay before move)
- Tenure: 2.0 years ❌ (Rule A FAIL — needs > 3yr)
- Autopay: ON ✅ (Rule B PASS)
- Current Plan: Fiber 1 Gig

**Waiver Outcome:** DENIED — tenure < 3yr. $99 install fee applies.

**Starting Utterance:**
> "I want to move to 100 First St. Cancel if fiber not available. Waive fees. Account 10004."

**Full Prompt Script:**
- Turn 1: `I want to move to 100 First St. Cancel if fiber not available. Waive fees. Account 10004.`
- Turn 2: `Sure` ← consent to pay the balance
- Turn 3: `Fiber 1 Gig`
- Turn 4: `Option 2 is fine`
- Turn 5: `Yes`

**What to Watch For:**
- Turn 1: Agent detects balance, asks for payment consent — does NOT proceed with move
- Turn 2: "Sure" is correctly interpreted as payment consent (not routed to billing agent)
- After payment: address check + fee check + plan question all in one response
- "Cancel if fiber not available" in Turn 1 does NOT cause T12 to fire action="CANCEL" — fiber is available, so it's a MOVE
- Agent silently ignores the "waive fees" request (tenure fails Rule A — waiver denied with specific reason)
- Good demo to show the billing gate and multi-intent handling

---------------------------------------

# Persona 4: The "Legacy" User (Copper → Fiber Migration)
**Account IDs:** 10003 (Sarah), 10006 (David)
**Destination:** 500 Fifth St → A15 (Fiber, Vacant) — use for Sarah (10003)
**Turn Count:** 4 turns

**Account Snapshot (Sarah 10003):**
- Tenure: 5.0 years ✅ (Rule A PASS)
- Autopay: ON ✅ (Rule B PASS)
- Balance: $0.00 (no billing gate)
- Current Plan: Internet 100 (Copper) ← triggers tech migration notice

**Waiver Outcome:** GRANTED — all 3 rules pass. $0 install fee.

**Starting Utterance:**
> "Hi, I'd like to move to 500 Fifth St. Account 10003."

**Full Prompt Script:**
- Turn 1: `Hi, I'd like to move to 500 Fifth St. Account 10003.`
- Turn 2: `Fiber 1 Gig`
- Turn 3: `Option 2 is fine`
- Turn 4: `Yes`

**What to Watch For:**
- Agent detects current plan is "Internet 100" (Copper) and new address supports Fiber
- Technology migration notice fires: agent informs customer that their Copper modem is not compatible and a technician will install a new ONT (Fiber) device
- Notice only fires for "Internet 100" — not for any other plan name
- Waiver passes (5yr tenure, autopay on) — good contrast to Persona 2
- Good demo to show the tech migration awareness built into the agent

---------------------------------------

# Persona 5: The "Churned" User (Win-Back)
**Account IDs:** 10011–10020 (Robert, Patricia, Linda, Barbara, Michael, William, David, Richard, Joseph, Thomas)
**Turn Count:** 2 turns

**Account Snapshot (Robert 10011):**
- Status: CANCELED ← key condition
- Tenure: 1.5 years
- Autopay: OFF
- Balance: $0.00
- Plan: Fiber 300 (on record, account closed)
- Address: None on file

**Starting Utterance:**
> "Hi, I'd like to check on my account. Account 10011."

**Full Prompt Script:**
- Turn 1: `Hi, I'd like to check on my account. Account 10011.`
- Turn 2: `Yes, I'd like to sign up again.`

**What to Watch For:**
- Agent immediately detects CANCELED status — does NOT attempt reactivation
- Agent informs customer the account is no longer active and pivots to sales_agent win-back flow
- Sales agent offers to set up new service at a new address
- Demonstrates the CANCELED account guard and clean agent handoff
- Shortest persona — useful as a quick insert in a demo to show account status handling

---------------------------------------

# Persona 6: The "Double Dipper" (Waiver History Fail)
**Account ID:** 10005 (Emily)
**Destination:** 700 Seventh St → A17 (Fiber, Vacant)
**Turn Count:** 4 turns

**Account Snapshot:**
- Tenure: 3.1 years ✅ (Rule A PASS — just over 3yr)
- Autopay: ON ✅ (Rule B PASS)
- Waiver used in last 12 months: YES ❌ (Rule C FAIL)
- Balance: $0.00 (no billing gate)
- Current Plan: Fiber 300

**Waiver Outcome:** DENIED — Rule C fails (prior waiver used recently). $99 install fee applies.
This is the tricky one: Rules A and B both pass — the denial comes from waiver history only.

**Starting Utterance:**
> "Hi, I'd like to move to 700 Seventh St. Account 10005."

**Full Prompt Script:**
- Turn 1: `Hi, I'd like to move to 700 Seventh St. Account 10005.`
- Turn 2: `Fiber 300`
- Turn 3: `Option 1 is fine`
- Turn 4: `Yes`

**What to Watch For:**
- Loyalty greeting fires (3.1yr tenure > 3yr)
- Agent checks all 3 waiver rules — Rules A and B pass, but Rule C fails
- Specific denial reason stated: "A fee waiver was already used within the last 12 months"
- $99 fee applied despite the customer being a loyal autopay user
- Good demo to show the nuance of the 3-rule logic — loyalty alone isn't enough

---------------------------------------

# Stress Test: The "Difficult Customer" (Multi-Challenge Move)
**Account ID:** 10004 (Mike)
**Destination:** 100 First St → A11 (Fiber, Vacant)
**Turn Count:** 8 turns (3 embedded mid-flow challenges)

**Account Snapshot:**
- Balance: $82.45 ⚠️ (billing gate)
- Tenure: 2.0 years ❌ (waiver FAIL — Rule A)
- Autopay: ON ✅
- Current Plan: Fiber 1 Gig

**Starting Utterance:**
> "I want to move to 100 First St. Account 10004."

**Full Prompt Script:**

**Turn 1:** `I want to move to 100 First St. Account 10004.`
→ Agent detects $82.45 balance. Asks for payment consent. Does NOT proceed with move.

**Turn 2 (Challenge 1 — Card Security):** `Can I use a different credit card for this payment?`
→ Agent delivers card security hard stop: cannot accept new card details over chat. Offers to connect a specialist OR proceed with card on file. Does NOT escalate immediately.

**Turn 3:** `No, let's just use the card on file.`
→ Agent processes payment with card on file (ending 8899). Clears balance. Continues into address check + fee check + plan question in one response.

**Turn 4 (Challenge 2 — Plan Browsing):** `Can you show me all available plan options?`
→ Agent presents the full inline Fiber plan table (no tool call needed):
  Fiber 300 · $55/mo | Fiber 500 · $65/mo | Fiber 1 Gig · $80/mo | Fiber 2 Gig · $110/mo

**Turn 5:** `Fiber 1 Gig please.`
→ Agent confirms Fiber 1 Gig at $80/mo. Calls T9 (no date), presents 4 appointment slots.

**Turn 6:** `Option 2 is fine.`
→ Agent confirms chosen slot. Executes move: T9(date) + T3 + T12(action=MOVE) + T13 receipt. Offers reminder.

**Turn 7:** `Yes, set the reminder.`
→ Agent calls T11. Sets day-before reminder at 10:00 AM.

**Turn 8 (Challenge 3 — Post-Move Bill Question):** `What will my next bill be? Are there any taxes?`
→ Agent answers from context (does NOT call T7 — old account is CANCELED). "Your new Fiber 1 Gig plan is $80/mo, due on the 1st of next month. Flat rate — no added taxes or fees."

**What to Watch For:**
- Card security script fires before any escalation offer (Turn 2)
- Full plan table displayed inline — no detour to sales_agent (Turn 4)
- T12 fires with action="MOVE" despite "Cancel if fiber not available" style phrasing (not used here, but the flow handles it)
- Post-move bill answered from handoff context, not from T7 (which would return stale data from the old CANCELED account)
- DB result: old account CANCELED with end_date set; new account ACTIVE at A11, Fiber 1 Gig
- Best persona to run last — demonstrates the full agent under pressure
