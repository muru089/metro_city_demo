# CLAUDE.md — Metro City Telecom: Multi-Agent Agentic Demo
> This file is the single authoritative reference for all agent logic, business rules, tool design, and debugging.
> Do NOT generate any agent behavior, business rule, or tool response that contradicts this document.
> Code always supersedes the PDF requirements document where they conflict.

---

## Project Overview

A **multi-agent demo** for a fictional metro city telecom company. Simulates a Voice Assistant (VA) handling common fiber/copper service requests via specialized AI sub-agents. Built with **Google ADK**.

**Supported Intents:**
1. Check fiber/copper serviceability at an address
2. Move service to a new address
3. Select / Change internet plan (upgrade, downgrade, lateral)
4. Cancel service
5. Billing (pay bill, autopay, next bill, balance check)
6. Scheduling (book/reschedule tech appointment, set reminder)

---

## System Architecture

**Framework:** Google ADK (`google.adk.agents.Agent`, `google.adk.tools.FunctionTool`, `google.adk.tools.agent_tool.AgentTool`)
**LLM:** `gemini-2.5-flash` for root_agent; `gemini-2.5-flash-lite` for all domain sub-agents
**Database:** SQLite (`metro_city.db`)
**DB Injection Pattern:** `functools.partial` used to inject `conn` into all DB tools, hiding it from the agent. Helper: `create_db_tool(fn, conn)` defined in each agent file.
**Exception:** T13_SendConfirmationReceipt opens its own DB connection internally -- do NOT wrap with `create_db_tool`.
**Server Launch:** Run `adk web` from `c:\Muru_Workspace` (the PARENT of metro_city_demo), NOT from inside the project folder.

```
root_agent  (agent.py)                               gemini-2.5-flash
  +-- T1_GetUpdateContact  (direct tool)
  +-- service_agent        (A1_Service_Agent.py)    via AgentTool
  +-- sales_agent          (A2_Sales_Agent.py)       via AgentTool
  +-- billing_agent        (A3_Billing_Agent.py)     via AgentTool
  +-- scheduling_agent     (A4_Scheduling_Agent.py)  via AgentTool
  +-- move_cancel_loop     (A5_Move_Cancel_LoopAgent.py) via AgentTool ← LIVE
        +-- MoverDrafter         (LlmAgent, flash-lite, 8 tools)
        +-- BusinessRulesCritic  (LlmAgent, flash, no tools)
        +-- RefinerOrExiter      (LlmAgent, flash-lite, no tools)

Archive/A5_Move_Cancel_Agent.py                      (archived — inline PRE-SEND CHECK reference)
```

---

## Database Schema (3 Tables -- from z_reset_world.py)

```sql
CREATE TABLE product_catalog (
    plan_id        TEXT PRIMARY KEY,
    plan_name      TEXT,
    technology     TEXT,      -- "Copper" or "Fiber"
    speed_mbps     INTEGER,
    monthly_price  REAL
);

CREATE TABLE address_inventory (
    addr_id            TEXT PRIMARY KEY,  -- e.g. "A01"
    street             TEXT,
    city_state_zip     TEXT,
    max_tech_type      TEXT,              -- "Fiber" or "Copper"
    max_speed          INTEGER,
    equipment_installed TEXT,             -- "ONT" or "Modem"
    status             TEXT              -- "Occupied" or "Vacant"
);

CREATE TABLE customer_accounts (
    account_id       INTEGER PRIMARY KEY,
    first_name       TEXT,
    address_id       TEXT,               -- FK to address_inventory.addr_id
    plan_name        TEXT,
    tenure_years     REAL,
    autopay_active   INTEGER,            -- 1=True, 0=False (SQLite boolean)
    waivers_used_12m INTEGER,            -- 1=True, 0=False
    pending_balance  REAL,
    status           TEXT,               -- "ACTIVE" or "CANCELED"
    email            TEXT,
    phone_number     TEXT,
    install_date     TEXT,               -- "YYYY-MM-DD"
    install_slot     TEXT,               -- "AM" or "PM"
    reminder_active  INTEGER,            -- 1=True, 0=False
    last_waiver_date TEXT,               -- "YYYY-MM-DD" or NULL
    start_date       TEXT,
    end_date         TEXT
);
```

---

## Product Catalog (5 Plans)

| plan_id | plan_name     | Technology | Speed (Mbps) | Monthly Price |
|---------|---------------|------------|--------------|---------------|
| P001    | Internet 100  | Copper     | 100          | $45.00        |
| P002    | Fiber 300     | Fiber      | 300          | $55.00        |
| P003    | Fiber 500     | Fiber      | 500          | $65.00        |
| P004    | Fiber 1 Gig   | Fiber      | 1000         | $80.00        |
| P005    | Fiber 2 Gig   | Fiber      | 2000         | $110.00       |

---

## Address Universe (20 Addresses)

### Group A -- Occupied (Ave addresses, A01-A10)
| addr_id | Street           | Tech   | Max Speed | Equipment | Status   |
|---------|------------------|--------|-----------|-----------|----------|
| A01     | 100 First Ave    | Fiber  | 1000      | ONT       | Occupied |
| A02     | 200 Second Ave   | Fiber  | 1000      | ONT       | Occupied |
| A03     | 300 Third Ave    | Copper | 100       | Modem     | Occupied |
| A04     | 400 Fourth Ave   | Fiber  | 1000      | ONT       | Occupied |
| A05     | 500 Fifth Ave    | Fiber  | 1000      | ONT       | Occupied |
| A06     | 600 Sixth Ave    | Copper | 100       | Modem     | Occupied |
| A07     | 700 Seventh Ave  | Fiber  | 1000      | ONT       | Occupied |
| A08     | 800 Eighth Ave   | Fiber  | 2000      | ONT       | Occupied |
| A09     | 900 Ninth Ave    | Copper | 100       | Modem     | Occupied |
| A10     | 1000 Tenth Ave   | Fiber  | 1000      | ONT       | Occupied |

### Group B -- Vacant (St addresses, A11-A20)
| addr_id | Street          | Tech   | Max Speed | Equipment | Status |
|---------|-----------------|--------|-----------|-----------|--------|
| A11     | 100 First St    | Fiber  | 1000      | ONT       | Vacant |
| A12     | 200 Second St   | Fiber  | 1000      | ONT       | Vacant |
| A13     | 300 Third St    | Copper | 100       | Modem     | Vacant |
| A14     | 400 Fourth St   | Fiber  | 1000      | ONT       | Vacant |
| A15     | 500 Fifth St    | Fiber  | 1000      | ONT       | Vacant |
| A16     | 600 Sixth St    | Copper | 100       | Modem     | Vacant |
| A17     | 700 Seventh St  | Fiber  | 1000      | ONT       | Vacant |
| A18     | 800 Eighth St   | Fiber  | 2000      | ONT       | Vacant |
| A19     | 900 Ninth St    | Copper | 100       | Modem     | Vacant |
| A20     | 1000 Tenth St   | Fiber  | 1000      | ONT       | Vacant |

---

## Demo Accounts -- Cheat Sheet (10 Active Personas)

| ID    | Name    | Addr | Plan         | Tenure | Autopay | Balance | Archetype                               |
|-------|---------|------|--------------|--------|---------|---------|-----------------------------------------|
| 10001 | Muru    | A01  | Fiber 1 Gig  | 4.2yr  | ON      | $0.00   | Perfect waiver candidate                |
| 10002 | John    | A02  | Fiber 500    | 0.5yr  | OFF     | $0.00   | New customer, waiver FAIL               |
| 10003 | Sarah   | A03  | Internet 100 | 5.0yr  | ON      | $0.00   | Copper legacy / upsell target           |
| 10004 | Mike    | A04  | Fiber 1 Gig  | 2.0yr  | ON      | $82.45  | Debtor / billing gate demo              |
| 10005 | Emily   | A05  | Fiber 300    | 3.1yr  | ON      | $0.00   | Recent waiver used (waivers_used_12m=1) |
| 10006 | David   | A06  | Internet 100 | 1.0yr  | OFF     | $0.00   | Copper + no autopay                     |
| 10007 | Jessica | A07  | Fiber 1 Gig  | 6.0yr  | OFF     | $0.00   | Long tenure but autopay OFF             |
| 10008 | Chris   | A08  | Fiber 2 Gig  | 0.2yr  | ON      | $0.00   | New + top tier plan                     |
| 10009 | Amanda  | A09  | Internet 100 | 10.0yr | ON      | $15.00  | Long tenure + small balance             |
| 10010 | James   | A10  | Fiber 500    | 2.5yr  | ON      | $0.00   | Just under 3yr tenure                   |

**Accounts 10011-10020:** Various names, no address, Fiber 300, 1.5yr tenure, Autopay OFF, $0 balance, **CANCELED** (win-back demos)

---

## Authentication Rules

1. **Auth Required:** Before any account action, collect the 5-digit Account ID.
2. **Unrecognized ID:** Re-prompt once ("I didn't find that account -- double-check and try again."). On second failure, pivot to general help (do NOT keep re-prompting).
3. **CANCELED account:** Inform the customer the account is no longer active. Do NOT attempt reactivation. Offer new account setup via sales_agent.
4. **Tenure-Aware Greeting:** After auth, check `tenure_years`:
   - >= 3 years: use loyalty script ("Thank you for being a valued customer for X years...")
   - < 3 years: use standard greeting
5. **Context Switching:** If user provides a different Account ID mid-conversation, flush all prior context and restart the auth flow for the new ID.

---

## Supervisor / Router (agent.py -- `root_agent`)

**Direct tool:** T1_GetUpdateContact (for contact info read/update without sub-agent handoff)

**Routing table:**
| User says...                                              | Route to         |
|-----------------------------------------------------------|------------------|
| "moving", "new address", "transfer service", "cancel"     | moves_agent      |
| "serviceability", "fiber available", "coverage"           | service_agent    |
| "upgrade", "downgrade", "change plan", "new customer"     | sales_agent      |
| "pay bill", "balance", "autopay", "next bill", "invoice"  | billing_agent    |
| "schedule", "appointment", "reschedule", "reminder"       | scheduling_agent |

**Disambiguation rules:**
- "Cancel" always routes to moves_agent (cancellation flow)
- "Change" -- clarify: plan change (sales_agent) vs. address change (moves_agent)
- Ambiguous intent: ask one clarifying question; do NOT guess
- Date/slot follow-ups mid-move (e.g. "March 8 doesn't work") → moves_agent, NOT scheduling_agent
- Affirmative responses mid-move ("Sure", "Yes", "OK") → moves_agent, NOT billing_agent
- Fee waiver questions mid-move → moves_agent, NOT sales_agent
- "Cancel unless fiber available" → moves_agent (multi-intent: moves_agent handles both move and cancel outcomes)

---

## Agent Definitions

### A1 -- service_agent (A1_Service_Agent.py)

**Purpose:** Check serviceability (tech type + max speed) at a given address.
**Tools:** T2_FiberCheckServiceability

**Key rules:**
- Takes `address_id` (e.g., "A01"), NOT a street string -- agent must look up or ask for the address ID
- **Copper Constraint:** If address max_tech_type is Copper, do NOT offer Fiber plans
- **Out of Footprint:** If address_id not found in DB, inform customer we do not serve that area
- **Hard Stop:** Troubleshooting / repair requests are out of scope -- use standard handoff phrase

---

### A2 -- sales_agent (A2_Sales_Agent.py)

**Purpose:** Present plans, handle upgrades, downgrades, lateral moves, new customer signups.
**Tools:** T1_GetUpdateContact, T2_FiberCheckServiceability, T4_FindMaxSpeedPlan, T8_CheckFeeWaiver

**Scenarios:**
- **Upgrade:** Confirm new plan, price delta, effective next billing cycle
- **Downgrade:** Confirm customer understands speed reduction; no fee
- **Lateral:** Same speed tier, confirm price difference
- **New customer (unauthenticated):** Use T2 to check address serviceability; present plans without Account ID
- **Discount/Promotion pivot:** Customer asks for a discount or promotion -- do NOT hard-stop. Run T8_CheckFeeWaiver. If eligible apply; if not, explain specific failing reason.

**Key rules:**
- Plan changes effective next billing cycle (no proration, no credits)
- No fee for plan changes
- Copper Constraint applies: never offer Fiber plans at Copper-only addresses

---

### A3 -- billing_agent (A3_Billing_Agent.py)

**Purpose:** Handle payments, autopay, balance inquiries, next bill forecasts.
**Tools:** T5_PayBill, T5a_GetBalance, T6_AutopayToggle, T7_CalcNextBill, T8_CheckFeeWaiver, T13_SendConfirmationReceipt

**Key rules:**
- **Card Security HARD STOP:** Cannot update, add, or change card on file. Script: "For security, card updates must be done through our secure self-service portal or by visiting a store. I can only process payments using the card already on file."
- **Payment only uses card on file** -- no alternative payment methods
- **Ambiguous consent:** "I guess" / "maybe" / "sure I suppose" -- require explicit "Yes" or "No" before any charge
- **Continuity Handoff:** After payment triggered by a Move flow, MUST ask: "Your balance is now cleared. Would you like to proceed with your move?"
- **Next bill:** Due 1st of next month. Flat rate only (no proration)
- **Autopay toggle:** T6 requires explicit "on" or "off" action; if ambiguous, confirm before acting

---

### A4 -- scheduling_agent (A4_Scheduling_Agent.py)

**Purpose:** Book and reschedule technician installation appointments; set day-before reminders.
**Tools:** T9_BookAppt, T10_ReschedAppt, T11_SetReminder

**Key rules:**
- **30-day booking window:** Cannot book more than 30 days from today
- **Rule of 4:** When no date specified, always present exactly 4 slots (2 days x AM + PM)
- **AM/PM only:** 8AM-12PM = AM; 1PM-5PM = PM. No specific times beyond this.
- **Repair Hard Stop:** Installation only. Repair/outage requests are out of scope.
- **Reminder:** T11 sets notification at 10:00 AM the day before install date

---

### A5 -- moves_agent (A5_Move_Cancel_Agent.py)

**Purpose:** Execute service moves to a new address and service cancellations.
**Tools:** T5a_GetBalance, T5_PayBill, T3_EquipmentLogic, T8_CheckFeeWaiver, T9_BookAppt, T12_ExecuteMoveCancel, T11_SetReminder, T13_SendConfirmationReceipt

**State Machine:** STATE 0 (Init + Resume Detection) → STATE 1 (Billing Gate) → STATE 2 (Address Check) → STATE 3A/3B (Move or Cancel Flow) → STATE 4 (Execute)

**STATE 0 -- Resume Detection:** On every invocation, moves_agent scans conversation history for 4 signals (slots presented, plan offered, fee communicated, fiber confirmed) and jumps directly to the pending step. This prevents re-running the full flow on each ADK re-invocation.

**Move Flow (6 steps in order):**
1. **Balance Gate:** Call T5a_GetBalance. If pending_balance > 0, offer T5_PayBill. Cannot proceed until balance = $0.
2. **Destination Check:** Call T3_EquipmentLogic(street_address). T3 returns tech_type ("Fiber"/"Copper"), install_type, and addr_id. Validates Vacant/Occupied/Not-Found.
3. **Fee Check:** Call T8_CheckFeeWaiver. Inform customer of $0 (waived) or $99 fee with specific failing reason(s).
4. **Plan Selection:** Offer "Fiber 1 Gig at $80/mo" as default. Customer may request full plan table. chosen_plan MUST be confirmed before scheduling.
5. **Appointment:** Call T9_BookAppt() (no date) → present 4 slots. Call T9_BookAppt(date_str) to confirm chosen date.
6. **Execute + Confirm:** T12_ExecuteMoveCancel(action="MOVE", new_address_id=addr_id_from_T3, new_plan_name=chosen_plan, effective_date=T9_date). Then T13_SendConfirmationReceipt; offer T11_SetReminder.

**Cancel Flow:**
1. **Balance Gate:** Balance must be $0 first.
2. **Confirm Intent:** Explicit YES required before proceeding.
3. **Execute:** T12_ExecuteMoveCancel(action="CANCEL"). Then T13_SendConfirmationReceipt.

**PRE-SEND CHECK (inline self-reflection):** The instruction includes a 6-point critique checklist the agent runs before every response (repetition, multiple asks, variable name exposure, premature tool calls, unauthorized T12, multi-step merging). See reflection/ for the true two-LLM LoopAgent version.

**Address Validation Traps:**
- **Same-address trap:** New address = current address: "You are already at that address."
- **Occupied trap:** Destination status = "Occupied": "That address is already in service."
- **Out-of-footprint:** Address ID not found: "We don't serve that area."

**Technology Migration Rule:**
- Moving from Copper (Modem) to Fiber (ONT): notify customer that their Copper modem is not compatible and a technician will install a new ONT device.

---

## Tool Reference (T1-T13)

| Tool | File                              | Signature                                         | Purpose                                    |
|------|-----------------------------------|---------------------------------------------------|--------------------------------------------|
| T1   | T1_GetUpdateContact.py            | (conn, account_id, new_email=None)                | Read or update customer email/contact      |
| T2   | T2_FiberCheckServiceability.py    | (conn, address_id)                                | Check max_tech_type + max_speed at addr_id |
| T3   | T3_EquipmentLogic.py              | (conn, street_address)                            | DB lookup: Fiber/Copper, Vacant/Occupied, install_type, addr_id (street str input) |
| T4   | T4_FindMaxSpeedPlan.py            | (conn, address_id)                                | Best plan options for address              |
| T5   | T5_PayBill.py                     | (conn, account_id, payment_amount=None)           | Process payment (full or partial)          |
| T5a  | T5a_GetBalance.py                 | (conn, account_id)                                | Read-only balance check                    |
| T6   | T6_AutopayToggle.py               | (conn, account_id, action=None)                   | Toggle autopay ON/OFF                      |
| T7   | T7_CalcNextBill.py                | (conn, account_id)                                | Forecast next bill (1st of next month)     |
| T8   | T8_CheckFeeWaiver.py              | (conn, account_id)                                | 3-rule waiver check                        |
| T9   | T9_BookAppt.py                    | (conn, date_str=None)                             | List 4 slots or confirm specific date      |
| T10  | T10_ReschedAppt.py                | (conn, account_id, new_date_str, new_slot)        | Reschedule existing appointment            |
| T11  | T11_SetReminder.py                | (conn, account_id)                                | Day-before reminder at 10AM                |
| T12  | T12_ExecuteMoveCancel.py          | (conn, account_id, action, ...)                   | Execute MOVE or CANCEL                     |
| T13  | T13_SendConfirmationReceipt.py    | (account_id, action_type, details={})             | Generate receipt -- opens own DB conn      |

**Critical input difference:**
- T2 takes `address_id` (e.g., "A01")
- T3 takes a street string (e.g., "100 First St") and returns `addr_id` in its response

**T3 return dict:**
```python
{
    "status": "success" | "error",
    "install_type": "Self-Install" | "Technician Install",
    "tech_type": "Fiber" | "Copper",
    "addr_id": "A11",          # use this as new_address_id in T12
    "needs_appointment": True | False,
    "message": "..."
}
```

---

## Shared Business Rules

### Fee Waiver -- 3-Rule Logic (T8)
All three must be true for $0 fee. Any failure = $99 install fee.
- **Rule A:** tenure_years > 3
- **Rule B:** autopay_active = 1
- **Rule C:** last_waiver_date is NULL or older than 12 months

On failure: return specific failing reason(s). Never just say "you do not qualify."

### Balance Gate
pending_balance must be $0.00 before Move or Cancel proceeds. No exceptions.

### Billing Rules
- Bill due: 1st of next month
- Flat monthly rate only -- no proration, no credits
- No early termination fee (month-to-month)
- Equipment return: within 14 days to avoid unreturned equipment fee

### Appointment Rules
- 30-day max booking window (T9 enforces)
- Cannot book same-day (minimum: tomorrow)
- Rule of 4: offer 4 slots initially
- AM = 8:00 AM - 12:00 PM; PM = 1:00 PM - 5:00 PM
- Reminder (T11) always at 10:00 AM day before install

### Notification Rules
- Confirmation via email + SMS (T13 handles both)
- Always offer reminder at end of Move/Schedule flow
- Reminder at 10:00 AM day before install

---

## Graceful Handling and Edge Cases

| Scenario                              | Required Behavior                                                    |
|---------------------------------------|----------------------------------------------------------------------|
| Wrong account ID twice                | Pivot to general help; stop prompting                                |
| Account status = CANCELED             | Inform, do not reactivate, offer sales_agent                         |
| Move to same address                  | "You are already at that address."                                   |
| Move to Occupied address              | "That address is already in service."                                |
| Address not in DB                     | "We do not serve that area."                                         |
| Copper address, customer wants Fiber  | Explain Copper constraint; do not offer Fiber                        |
| Ambiguous consent to payment          | Require explicit Yes/No -- do not charge                             |
| Customer asks to update card          | Card Security HARD STOP script                                       |
| Customer asks for discount/promo      | Pivot to T8 waiver check -- do NOT hard-stop                         |
| Appointment more than 30 days out     | Reject; ask for earlier date                                         |
| Appointment in the past               | Reject; ask for future date                                          |
| Cancel on already-CANCELED account    | "Account is already canceled."                                       |
| Troubleshooting / repair request      | Out-of-scope hard stop                                               |

---

## Out-of-Scope Hard Stop

**Standard script (use verbatim):**
"I am not able to help with that through this system. For [topic], please contact our technical support team at 1-800-METRO-CITY or visit metrocity.com/support. Is there anything else I can help you with today?"

**Out-of-scope topics:**
- Network troubleshooting / outages / repair tickets
- Equipment malfunction (beyond install)
- Business account inquiries
- Porting phone numbers
- TV / streaming service questions
- Refund disputes beyond pending_balance
- Any request requiring access to systems outside this demo DB

---

## LoopAgent Self-Reflection Reference (reflection/)

**File:** `reflection/A5_Move_Cancel_LoopAgent.py`
**Purpose:** Reference implementation of the true two-LLM self-reflection pattern. NOT wired into agent.py — standalone demo for team review.

**Status:** LIVE — `move_cancel_loop` is wired into `agent.py` and handles all move/cancel flows.
`A5_Move_Cancel_Agent.py` is retained as a reference for the inline PRE-SEND CHECK pattern.

**Pattern vs. A5 inline check:**
| Approach | Where | Status | Reliability |
|---|---|---|---|
| Inline PRE-SEND CHECK | A5_Move_Cancel_Agent.py | Reference only | Same LLM checks its own output — lower |
| True LoopAgent critique | reflection/A5_Move_Cancel_LoopAgent.py | **LIVE in demo** | Separate LLM audits independently — higher |

**Three agents in the loop:**
| Agent | Model | Tools | Role |
|---|---|---|---|
| MoverDrafter | gemini-2.5-flash-lite | All 8 | Generates customer response. No self-check. |
| BusinessRulesCritic | gemini-2.5-flash | None | Audits 6 business rules. Outputs APPROVED or VIOLATION lines. |
| RefinerOrExiter | gemini-2.5-flash-lite | None | Passes approved draft unchanged; rewrites only flagged violations. |

**Loop mechanics:**
- `LoopAgent(max_iterations=2)` is the circuit breaker — guarantees response even if violations persist
- Exit via `event.actions.escalate` (ADK native) — no `exit_loop` tool (that is a LangGraph pattern)
- State shared via conversation history (`include_contents='default'`) — no TypedDict (also LangGraph)

**Business rules audited (6):** Balance Gate, Explicit Consent, Fee Waiver Integrity, Address Check Before Order, Plan Confirmed Before Scheduling, No Internal Variable Exposure

**Import path:** `from metro_city_demo.A5_Move_Cancel_LoopAgent import move_cancel_loop`

---

## Coding Conventions

- **Language:** Python 3
- **Framework:** Google ADK (`google.adk.agents`, `google.adk.tools`)
- **LLM:** `gemini-2.5-flash` for root_agent; `gemini-2.5-flash-lite` for all domain agents
- **DB:** SQLite via `sqlite3`; connection object passed as `conn`
- **Tool injection:** `functools.partial(tool_fn, conn)` wraps all DB tools before FunctionTool
- **Tool naming:** T{N}_{PascalCaseName}.py -- file name and function name match
- **Agent naming:** snake_case Python variable (e.g., service_agent, moves_agent)
- **Each tool file has a `if __name__ == "__main__":` test block** for isolated testing
- **T13 exception:** Opens its own sqlite3.connect("metro_city.db") -- never wrap with create_db_tool
- **All tool responses are dicts** with at minimum a "status" key ("success" / "error" / "info")
- **Server launch:** `cd c:\Muru_Workspace && adk web` — must run from PARENT directory, not from inside metro_city_demo/
- **Archive/:** `Archive/` contains retired agent files kept for reference (e.g., A5_Move_Cancel_Agent.py with inline PRE-SEND CHECK pattern)
- **reflection/:** `reflection/` folder and `__init__.py` retained but empty of live code — LoopAgent moved to main folder

---

## Data Reset

Run `z_reset_world.py` to drop and recreate all tables, re-seed all 20 addresses, 20 accounts, and 5 plans.

```bash
python z_reset_world.py
```
