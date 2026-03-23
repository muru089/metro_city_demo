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
**LLM:** `gemini-2.5-flash` for root_agent AND SA1_MovesSupervisor AND DA4_ExecuteMoveAgent; `gemini-2.5-flash-lite` for DA1, DA2, DA3
**Database:** SQLite (`metro_city.db`)
**DB Injection Pattern:** `functools.partial` used to inject `conn` into all DB tools, hiding it from the agent. Helper: `create_db_tool(fn, conn)` defined in each agent file.
**Exception:** T13_SendConfirmationReceipt opens its own DB connection internally — do NOT wrap with `create_db_tool`.
**Server Launch:** Run `adk web` from `c:\Muru_Workspace` (the PARENT of metro_city_demo), NOT from inside the project folder.

```
root_agent         (agent.py)                          gemini-2.5-flash   ← Uber Agent
  +-- T1_GetUpdateContact    (direct tool: auth)
  +-- DA1_SalesAgent         (DA1_Sales_Agent.py)      gemini-2.5-flash-lite  via AgentTool
  +-- DA2_BillingAgent       (DA2_Billing_Agent.py)    gemini-2.5-flash-lite  via AgentTool
  +-- DA3_SchedulingAgent    (DA3_Scheduling_Agent.py) gemini-2.5-flash-lite  via AgentTool
  +-- SA1_MovesSupervisor    (SA1_Moves_Supervisor.py) gemini-2.5-flash       via AgentTool ← Supervisor
        +-- DA2_BillingAgent      (balance, payment, fee waiver)  via AgentTool
        +-- DA3_SchedulingAgent   (appointments, reminder)         via AgentTool
        +-- DA4_ExecuteMoveAgent  (DA4_Execute_Move_Agent.py)      gemini-2.5-flash  via AgentTool ← Squad

Archive/A1_Service_Agent.py        (archived — CP3 reference)
Archive/A2_Sales_Agent.py          (archived — CP3 reference)
Archive/A3_Billing_Agent.py        (archived — CP3 reference)
Archive/A4_Scheduling_Agent.py     (archived — CP3 reference)
Archive/A5_Move_Cancel_Agent.py    (archived — CP3 reference: monolith Squad with inline PRE-SEND CHECK)
Archive/A5_Move_Cancel_LoopAgent.py (archived — CP3 reference: LoopAgent self-reflection pattern)
```

**3-Tier Design:**
| Tier | Agent | Responsibility |
|---|---|---|
| Uber | root_agent | Auth, input safety (PII/injection/toxicity), disambiguation, routing |
| Supervisor | SA1_MovesSupervisor | 7-state macro state machine for moves/cancels. No direct tools. Yields to DAs. |
| Domain | DA1, DA2, DA3 | Narrow specialists. Own their tool sets. Called by root_agent OR SA1. |
| Squad | DA4_ExecuteMoveAgent | Fire-and-return. Executes T3→T12→T13 chain. Called by SA1 only. |

**Guardrail placement:**
- **Layer 1 (Input):** Uber Agent only — PII, prompt injection, toxicity, out-of-scope
- **Layer 2 (Logic):** Each domain agent — domain-specific rules (balance gate, Copper constraint, card security, consent)
- **Layer 3 (Output):** Uber Agent only — variable exposure, contradictions, verbosity

---

## Database Schema (3 Tables — from z_reset_world.py)

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

### Group A — Occupied (Ave addresses, A01-A10)
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

### Group B — Vacant (St addresses, A11-A20)
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

## Demo Accounts — Cheat Sheet (10 Active Personas)

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
2. **Unrecognized ID:** Re-prompt once ("I didn't find that account — double-check and try again."). On second failure, pivot to general help (do NOT keep re-prompting).
3. **CANCELED account:** Inform the customer the account is no longer active. Do NOT attempt reactivation. Offer new account setup via da1_sales_agent.
4. **Tenure-Aware Greeting:** After auth, check `tenure_years`:
   - >= 3 years: use loyalty script ("Thank you for being a valued customer for X years...")
   - < 3 years: use standard greeting
5. **Context Switching:** If user provides a different Account ID mid-conversation, flush all prior context and restart the auth flow for the new ID.

---

## Uber Agent / Router (agent.py — `root_agent`)

**Direct tool:** T1_GetUpdateContact (auth + contact lookup before routing)

**Routing table:**
| User says...                                              | Route to                |
|-----------------------------------------------------------|-------------------------|
| "moving", "new address", "transfer service", "cancel"     | sa1_moves_supervisor    |
| "serviceability", "fiber available", "coverage"           | da1_sales_agent         |
| "upgrade", "downgrade", "change plan", "new customer"     | da1_sales_agent         |
| "pay bill", "balance", "autopay", "next bill", "invoice"  | da2_billing_agent       |
| "schedule", "appointment", "reschedule", "reminder"       | da3_scheduling_agent    |

**Disambiguation rules:**
- "Cancel" alone → ask: "Are you canceling your service, or a technician appointment?"
- "Change" alone → ask: "Are you changing your plan, or your address?"
- Affirmative responses mid-move ("Sure", "Yes", "OK") → sa1_moves_supervisor, NOT da2_billing_agent
- Date/slot follow-ups mid-move → sa1_moves_supervisor, NOT da3_scheduling_agent
- Fee waiver questions mid-move → sa1_moves_supervisor, NOT da1_sales_agent
- Plan selections mid-move → sa1_moves_supervisor, NOT da1_sales_agent
- "Cancel unless fiber available" → sa1_moves_supervisor (handles both outcomes)
- New card request during an active move → sa1_moves_supervisor (handles card security script)
- Standalone card update (no active move) → ESCALATION

**SA1 handoff requirement:** root_agent MUST include the full conversation transcript in every sa1_moves_supervisor call so SA1 can reconstruct its state (Approach B — ephemeral state via history reconstruction).

---

## Agent Definitions

### DA1 — da1_sales_agent (DA1_Sales_Agent.py)

**Purpose:** Check serviceability at an address; present and confirm internet plans.
**Absorbs:** Former A1 (serviceability) and A2 (sales) — no tool duplication.
**Tools:** T2_FiberCheckServiceability, T4_FindMaxSpeedPlan
**Model:** gemini-2.5-flash-lite

**State machine:**
- STATE 1: Identify address_id (A01–A20 format)
- STATE 2: Check serviceability via T2 — Fiber or Copper
- STATE 3: Present plans via T4 — Fiber plans only if Fiber confirmed

**Key rules:**
- T2 takes `address_id` (e.g., "A01"), NOT a street string
- **Copper Constraint:** Never offer Fiber plans at a Copper-only address
- T4 must never be called without T2 succeeding first
- Plan changes effective next billing cycle — no proration, no credits
- No fee for plan changes

---

### DA2 — da2_billing_agent (DA2_Billing_Agent.py)

**Purpose:** Handle all billing operations.
**Tools:** T5_PayBill, T5a_GetBalance, T6_AutopayToggle, T7_CalcNextBill, T8_CheckFeeWaiver, T13_SendConfirmationReceipt
**Model:** gemini-2.5-flash-lite
**Called by:** root_agent (standalone billing) AND SA1_MovesSupervisor (balance check, payment, fee waiver during move flow)

**Tasks (one per invocation):**
- BALANCE_CHECK → T5a
- PAYMENT → card security check → T5 → T13
- FEE_WAIVER → T8 (result is ground truth — never infer from context)
- NEXT_BILL → T7 (CASE B) OR from context (CASE A — post-move, do NOT call T7)
- AUTOPAY → T6

**Key rules:**
- **Card Security HARD STOP:** Cannot accept new card details. Only card on file.
- **Consent Gate:** "I guess" / "maybe" = NOT consent. Only explicit "Yes" / "Go ahead".
- **T8 ground truth:** Fee waiver result comes ONLY from T8 output — never infer.
- **T7 vs Context:** After a move, old account is CANCELED — T7 returns stale data. Use CASE A (from context) for post-move billing questions.

---

### DA3 — da3_scheduling_agent (DA3_Scheduling_Agent.py)

**Purpose:** Book and manage technician installation appointments; set reminders.
**Tools:** T9_BookAppt, T10_ReschedAppt, T11_SetReminder
**Model:** gemini-2.5-flash-lite
**Called by:** root_agent (standalone scheduling) AND SA1_MovesSupervisor (appointments + reminder during move flow)

**Tasks (one per invocation):**
- LIST_SLOTS → T9 (no date) → exactly 4 slots
- CONFIRM_DATE → T9 (date_str)
- RESCHEDULE → T10
- SET_REMINDER → T11

**Key rules:**
- Rule of 4: always exactly 4 slots when listing
- 30-day max window; no same-day booking
- AM/PM only — never confirm specific times
- Repair scheduling is out of scope

---

### SA1 — sa1_moves_supervisor (SA1_Moves_Supervisor.py)

**Purpose:** Macro state machine for service moves and cancellations.
**Tools:** AgentTool(da2_billing_agent), AgentTool(da3_scheduling_agent), AgentTool(da4_execute_move_agent)
**Model:** gemini-2.5-flash (NOT flash-lite — multi-tool chains, avoid Part(text=None) bug)
**Has NO direct tools** — all operations delegated to domain agents.

**State reconstruction:** AgentTool creates a fresh InMemorySession per invocation. root_agent passes FULL conversation transcript in every handoff so SA1 can self-determine its state (Approach B).

**HANDOFF SIGNALS (checked in priority order E → D → A → B → C → F):**
- **SIGNAL E:** Move/cancel executed; customer responding to reminder question → call DA3 set reminder or close
- **SIGNAL D:** Slot selected → call DA4 execute move (MODE B). action="MOVE" always.
- **SIGNAL A:** Plan selected, no appointment → call DA3 list slots (4 slots), HARD STOP
- **SIGNAL B:** Fee result known, no plan → ask plan question, HARD STOP
- **SIGNAL C:** Customer consented to payment → DA2 pay → DA4 addr check → DA2 fee check (chain in one turn)
- **SIGNAL F:** Cancel intent, no address → CANCEL FLOW

**Move Flow (7 states):**
1. Balance Gate — DA2 balance check. Block if > $0.
2. Address Check — DA4 MODE A. Validates Vacant/Occupied/Not-Found/Same.
3. Fee Check — DA2 fee waiver. $0 or $99 with specific reason.
4. Plan Selection — Present from catalog (no DA1 needed). Wait for explicit plan.
5. Appointment — DA3 list 4 slots. Wait for selection.
5B. Confirm Date — DA3 confirm chosen date.
6. Execute — DA4 MODE B (T3 → T12 → T13). action="MOVE" always.
7. Reminder — DA3 set reminder.

**Cancel Flow:** Balance Gate → Confirm explicit YES → DA4 MODE C (T12 → T13).

**CRITICAL:** action="MOVE" at SIGNAL D regardless of any earlier "cancel if fiber not available" language. Cancel condition is evaluated in STATE 2 only. Reaching STATE 6 means fiber was confirmed and the customer chose a plan.

**Technology Migration Rule:** Copper-to-Fiber move → notify customer that Copper modem is incompatible and a technician will install a new ONT device.

---

### DA4 — da4_execute_move_agent (DA4_Execute_Move_Agent.py)

**Purpose:** Squad agent. Address validation and move/cancel execution.
**Tools:** T3_EquipmentLogic, T12_ExecuteMoveCancel, T13_SendConfirmationReceipt
**Model:** gemini-2.5-flash (NOT flash-lite — multi-tool chain)
**Called by:** SA1_MovesSupervisor only.

**Modes (triggered by verb in message):**
- **MODE A** ("check address") — T3 only. Read-only. T12 never called in MODE A.
- **MODE B** ("execute move") — T3 → T12(action="MOVE") → T13. T3 must succeed before T12.
- **MODE C** ("execute cancel") — T12(action="CANCEL") → T13.

**Key rules:**
- Always strip trailing punctuation (.,!?;:) from street strings before passing to T3
- T3 gate: T12 must NEVER be called if T3 returned an error (MODE B)
- action="MOVE" in MODE B always. action="CANCEL" in MODE C always. Never swap.

---

## Tool Reference (T1–T13)

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
| T13  | T13_SendConfirmationReceipt.py    | (account_id, action_type, details={})             | Generate receipt — opens own DB conn       |

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

### Fee Waiver — 3-Rule Logic (T8)
All three must be true for $0 fee. Any single failure = $99 install fee.
- **Rule A:** tenure_years > 3
- **Rule B:** autopay_active = 1
- **Rule C:** last_waiver_date is NULL or older than 12 months

On failure: return specific failing reason(s). Never just say "you do not qualify."

### Balance Gate
pending_balance must be $0.00 before Move or Cancel proceeds. No exceptions.

### Billing Rules
- Bill due: 1st of next month
- **Flat monthly rate only — no taxes, no fees, no surcharges**
- **No proration — ever.** Full rule:
  - The current billing month is always charged at the **old rate in full**, regardless of when a plan change or move occurs during the month.
  - The new rate takes effect at the start of the **next billing cycle (1st of next month)**.
  - There are no partial-month credits, no pro-rated refunds, and no mid-cycle adjustments.
  - Example: Customer on Fiber 1 Gig ($80/mo) moves to Fiber 500 ($65/mo) on March 15. March bill = **$80**. April 1st bill = **$65**.
  - If a customer asks "do I get credit for the days I was on the old plan?" → Answer: "Plan changes take effect at the start of your next billing cycle. Your current month is billed at your existing rate in full — there's no proration or partial-month credit."
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
| Account status = CANCELED             | Inform, do not reactivate, offer da1_sales_agent                     |
| Move to same address                  | "You are already at that address."                                   |
| Move to Occupied address              | "That address is already in service."                                |
| Address not in DB                     | "We do not serve that area."                                         |
| Copper address, customer wants Fiber  | Explain Copper constraint; do not offer Fiber                        |
| Ambiguous consent to payment          | Require explicit Yes/No — do not charge                              |
| Customer asks to update card          | Card Security HARD STOP script                                       |
| Customer asks for discount/promo      | Pivot to T8 waiver check — do NOT hard-stop                          |
| Customer asks about proration/credit  | "No proration. Current month billed at old rate. New rate from 1st." |
| Customer asks about taxes             | "Flat monthly rate — no added taxes or fees."                        |
| Appointment more than 30 days out     | Reject; ask for earlier date                                         |
| Appointment in the past               | Reject; ask for future date                                          |
| Cancel on already-CANCELED account    | "Account is already canceled."                                       |
| Copper → Fiber move                   | Notify: Copper modem incompatible, technician installs new ONT       |
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

## LoopAgent Self-Reflection Architecture (CP3 Reference)

**Status:** Archived — `Archive/A5_Move_Cancel_LoopAgent.py`. Replaced in CP4 by the 3-tier architecture (SA1 + DA agents). Kept for reference as a self-reflection pattern demonstration.

**Pattern comparison:**
| Approach | Where | Status | Notes |
|---|---|---|---|
| 3-tier SA1 + DAs | SA1_Moves_Supervisor.py + DA1-DA4 | **LIVE (CP4)** | True yield-and-resume; clean tool ownership |
| Inline PRE-SEND CHECK | Archive/A5_Move_Cancel_Agent.py | Archived (CP3) | Monolith Squad — 1 LLM call/turn |
| True LoopAgent critique | Archive/A5_Move_Cancel_LoopAgent.py | Archived (CP3) | 3 LLM calls/turn self-reflection pattern |

**LoopAgent three-agent structure (reference):**
| Agent | Model | Tools | Role |
|---|---|---|---|
| MoverDrafter | gemini-2.5-flash-lite | All 8 | Generates customer response |
| BusinessRulesCritic | gemini-2.5-flash | None | Audits 7 business rules |
| RefinerOrExiter | gemini-2.5-flash-lite | None | Passes or rewrites |

**Import path (if restoring):** `from metro_city_demo.Archive.A5_Move_Cancel_LoopAgent import move_cancel_loop`

---

## Coding Conventions

- **Language:** Python 3
- **Framework:** Google ADK (`google.adk.agents`, `google.adk.tools`)
- **LLM:** `gemini-2.5-flash` for root_agent, SA1_MovesSupervisor, DA4_ExecuteMoveAgent; `gemini-2.5-flash-lite` for DA1, DA2, DA3
- **SA1 and DA4 MUST use `gemini-2.5-flash`** — flash-lite intermittently returns `Part(text=None)` after multi-tool chains, causing agent_tool.py to return '' and breaking multi-step flows. Do NOT downgrade.
- **DB:** SQLite via `sqlite3`; connection object passed as `conn`
- **Tool injection:** `functools.partial(tool_fn, conn)` wraps all DB tools before FunctionTool
- **Tool naming:** T{N}_{PascalCaseName}.py — file name and function name match
- **Agent naming:** DA{N}_{PascalCase} for domain agents; SA{N}_{PascalCase} for supervisors
- **Each tool file has a `if __name__ == "__main__":` test block** for isolated testing
- **T13 exception:** Opens its own sqlite3.connect("metro_city.db") — never wrap with create_db_tool
- **All tool responses are dicts** with at minimum a "status" key ("success" / "error" / "info")
- **Server launch:** `cd c:\Muru_Workspace && adk web` — must run from PARENT directory
- **Archive/:** Contains CP3 reference implementations — do not delete, do not import into live agent.py

---

## Test Infrastructure

**File:** `metro_city_demo/Agent Sim/test_conversation.py`
**Run from:** `c:\Muru_Workspace` (parent directory)
**Command:** `py "metro_city_demo/Agent Sim/test_conversation.py"`

**How it works:**
- Loads `.env` from `metro_city_demo/` for the Gemini API key
- Creates an ADK `Runner` with `InMemorySessionService` directly (bypasses `adk web`)
- Runs a hardcoded multi-turn conversation against the live `root_agent`
- Prints each turn's user input and agent response
- Tracks root-level tool calls (T1, SA1_MovesSupervisor visible; inner DA/T12 calls inside SA1 not visible at root level)
- Prints DB verification table after every run (original account status + new accounts created)

**Note:** Always run `py metro_city_demo/z_reset_world.py` before each test to ensure a clean DB state.

**Limitations:**
- T12 and inner DA tool calls are not captured at root level — verify via DB verification table
- Only one persona active at a time (comment/uncomment TURNS block)

---

## Bug Fix History

Bugs discovered and fixed during CP3 and CP4 simulation runs:

| Bug | Root Cause | Fix Applied |
|-----|-----------|-------------|
| **Balance gate bypass** | SIGNAL detection saw "Fiber 1 Gig" in T1 result and falsely triggered plan selection | Rewrote SIGNAL detection to be transcript-text-based |
| **"Sure" misrouted** | root_agent routed consent-to-pay "Sure" to billing_agent instead of moves_agent | Strengthened disambiguation: affirmatives mid-move → sa1_moves_supervisor |
| **Step merging** | Agent combined multiple state machine steps into one response | Added HARD STOP instructions and ONE-STEP-PER-RESPONSE guardrails |
| **T12 fires action="CANCEL"** | "Cancel if fiber not available" bled into SIGNAL D | Guardrail: action="MOVE" mandatory at SIGNAL D; cancel evaluated in STATE 2 only |
| **Silent after fee (no plan question)** | Hard stop prevented the plan question from being asked after fee check | All SIGNAL C paths close with the plan question before hard stop |
| **Wrong fee waiver claimed** | SA1 hallucinated "fee waived" after payment, conflating balance clearing with fee waiver | Added explicit grounding: fee result comes ONLY from DA2 response text. Payment ≠ waiver. |
| **"Taxes apply" in post-move bill** | root_agent handoff to DA2 included "taxes will apply" context; DA2 echoed it | DA2 CASE A now always outputs "No added taxes or fees" regardless of incoming context |
| **Part(text=None) after T9** | gemini-2.5-flash-lite returns Part(text=None) after multi-tool chains | SA1 and DA4 upgraded to gemini-2.5-flash — do NOT revert |
| **T3 NOT_FOUND with trailing period** | LLMs append periods to street addresses; T3's LIKE query fails on "200 Second St." | Strip trailing punctuation before passing to T3 |

---

## Validated Personas (CP4 — 2026-03-23)

All personas run end-to-end with DB confirmation against the 3-tier CP4 architecture.

| Persona | Account | Archetype | Key Conditions | Turns | DB Result |
|---------|---------|-----------|----------------|-------|-----------|
| 1 — Muru    | 10001 | Perfect waiver     | $0 balance, waiver PASS (4.2yr, autopay ON)      | 4 | ✅ CANCELED→10021 ACTIVE A12, Fiber 1G |
| 2 — John    | 10002 | Waiver FAIL x2     | $0 balance, tenure 0.5yr + autopay OFF           | 4 | ✅ CANCELED→10021 ACTIVE A14, Fiber 500 |
| 3 — Mike    | 10004 | Billing gate       | $82.45 balance, waiver FAIL (tenure 2yr)         | 5 | ✅ CANCELED→10021 ACTIVE A11, Fiber 1G |
| 4 — Sarah   | 10003 | Copper→Fiber       | $0 balance, waiver PASS (5yr), ONT migration msg | 4 | ✅ CANCELED→10021 ACTIVE A15, Fiber 1G |
| 5 — Robert  | 10011 | Churned win-back   | CANCELED account, routed to DA1 for new service  | 2 | ✅ No DB write (new service not completed) |
| 6 — Emily   | 10005 | Double dipper      | $0 balance, Rule C FAIL (prior waiver 12m)       | 4 | ✅ CANCELED→10021 ACTIVE A17, Fiber 300 |
| Stress Test | 10004 | Difficult customer | Card security + plan browsing + post-move bill   | 8 | ✅ CANCELED→10021 ACTIVE A11, Fiber 1G |

**Stress test must-not-break checklist:**
- Turn 2: Card security hard stop — new card rejected, no payment attempted
- Turn 3: Card-on-file consent → SIGNAL C chain (pay + addr + fee DENIED $99)
- Turn 4: Full Fiber plan table shown inline — no DA1 call, no detour
- Turn 6: Move executed — DB write confirmed
- Turn 8: Post-move bill answered from context — T7 NOT called (old account CANCELED)

---

## Data Reset

Run `z_reset_world.py` to drop and recreate all tables, re-seed all 20 addresses, 20 accounts, and 5 plans.

```bash
py metro_city_demo/z_reset_world.py
```
