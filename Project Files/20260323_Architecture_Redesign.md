# CP4: Architecture Redesign — 3-Tier Multi-Agent Graph

## Context
Current A5 is a monolith: owns the macro state machine, holds all billing/scheduling/sales tools,
and does yield-and-resume internally via HANDOFF SIGNALS. This violates the Uber→Supervisor→Domain
tier model. The redesign introduces SA1_Moves_Supervisor as the true orchestrator, thin domain
agents with clean tool ownership, and genuine yield-and-resume via conversation history reconstruction.

---

## Numbered Checklist

### Phase 1 — Archive + Cleanup
1. Move A1_Service_Agent.py, A2_Sales_Agent.py, A3_Billing_Agent.py, A4_Scheduling_Agent.py,
   A5_Move_Cancel_Agent.py to Archive/ (preserve git history, keep as reference)

### Phase 2 — Create New Domain Agents
2. Create DA1_Sales_Agent.py — absorbs serviceability + sales (T2, T4). No A1 needed separately.
3. Create DA2_Billing_Agent.py — from A3 (T5, T5a, T6, T7, T8, T13)
4. Create DA3_Scheduling_Agent.py — from A4 (T9, T10, T11)
5. Create DA4_Execute_Move_Agent.py — thin Squad agent (T3, T12, T13 only)

### Phase 3 — Create Move Supervisor
6. Create SA1_Moves_Supervisor.py — macro state machine, no tools, yields to DAs via AgentTool.
   Owns the 7-state sequence: Balance Gate → Address Check → Fee Check → Plan Selection →
   Appointment → Execute → Reminder. Reconstructs position from conversation history each turn.

### Phase 4 — Wire Uber Agent
7. Update agent.py — replace A1-A5 AgentTool references with DA1/DA2/DA3/SA1.
   Remove USE_LOOP_AGENT toggle (no longer needed). root_agent stays thin.

### Phase 5 — Validate (Simulations)
8. Run Persona 1 (Muru, 10001) — happy path, $0 balance, waiver PASS. Simplest first.
9. Run Persona 3 (Mike, 10004) — billing gate. Tests yield billing_agent → resume supervisor.
10. Run Personas 2, 4, 5, 6 — waiver fail, copper migration, canceled, double dipper.
11. Run 8-turn stress test — card security, plan browsing, post-move bill.

### Phase 6 — Wrap
12. Update CLAUDE.md to reflect new architecture, agent names, tool ownership.
13. Git commit + push as CP4.

---

## Key Design Decisions

| Decision | Choice |
|---|---|
| State management | Ephemeral — conversation history reconstruction (no session.state, no SQL) |
| SA1_Moves_Supervisor model | gemini-2.5-flash (not flash-lite — avoids Part(text=None) bug on multi-tool chains) |
| DA agents model | gemini-2.5-flash-lite |
| T13 exception | Opens its own DB connection — never wrapped with create_db_tool |
| LoopAgent | Stays archived (Archive/A5_Move_Cancel_LoopAgent.py) — not wired in CP4 |
| Old A1-A5 files | Moved to Archive/ — not deleted, git history preserved |

---

## Files Changing

| Action | File |
|---|---|
| Archive | A1_Service_Agent.py → Archive/ |
| Archive | A2_Sales_Agent.py → Archive/ |
| Archive | A3_Billing_Agent.py → Archive/ |
| Archive | A4_Scheduling_Agent.py → Archive/ |
| Archive | A5_Move_Cancel_Agent.py → Archive/ |
| Create  | DA1_Sales_Agent.py |
| Create  | DA2_Billing_Agent.py |
| Create  | DA3_Scheduling_Agent.py |
| Create  | DA4_Execute_Move_Agent.py |
| Create  | SA1_Moves_Supervisor.py |
| Modify  | agent.py |
| Modify  | CLAUDE.md |

---

## New Agent Naming Convention

| File | Tier | Role |
|---|---|---|
| agent.py | Uber | Auth · Disambiguate · Route only |
| SA1_Moves_Supervisor.py | Supervisor | Macro state machine · Yield & Resume |
| DA1_Sales_Agent.py | Domain | Serviceability + Plans (T2, T4) |
| DA2_Billing_Agent.py | Domain | Payments · Autopay · Fee Waiver (T5, T5a, T6, T7, T8, T13) |
| DA3_Scheduling_Agent.py | Domain | Appointments · Reminder (T9, T10, T11) |
| DA4_Execute_Move_Agent.py | Domain (Squad) | Equipment + Execute (T3, T12, T13) |
