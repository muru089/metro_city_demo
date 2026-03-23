"""
test_conversation.py — Metro City ADK Automated Conversation Test
=================================================================
Tests account 10004 (Mike) through the move flow via ADK Runner.
Run from c:\\Muru_Workspace (parent of metro_city_demo):

    python metro_city_demo/Agent\ Sim/test_conversation.py

Account 10004 profile:
  - Balance: $82.45  -> billing gate will fire on Turn 1
  - Tenure: 2.0 yrs  -> fee waiver will FAIL (needs > 3 yrs)
  - Moving to: 100 First St (A11) -> Fiber, Vacant -> technician install
"""

import asyncio
import sys
import os
import io
import traceback as _tb

# Force UTF-8 output on Windows (avoids cp1252 crashes on unicode chars)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Disable experimental progressive SSE streaming — it produces Part(text=None)
# events after multi-tool chains, causing agent_tool.py to return '' instead of
# the agent's actual text response.
os.environ.setdefault("ADK_DISABLE_PROGRESSIVE_SSE_STREAMING", "1")

# File is at metro_city_demo/Agent Sim/test_conversation.py
# Two levels up = c:\Muru_Workspace (where metro_city_demo package lives)
_this_dir   = os.path.dirname(os.path.abspath(__file__))   # .../Agent Sim
_project_dir = os.path.dirname(_this_dir)                   # .../metro_city_demo
_workspace  = os.path.dirname(_project_dir)                 # .../Muru_Workspace
sys.path.insert(0, _workspace)

# Load .env from metro_city_demo/ (same place adk web reads it)
_env_path = os.path.join(_project_dir, ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

from metro_city_demo.agent import root_agent

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# =============================================================================
# PERSONA SCRIPTS -- select ONE active scenario by uncommenting TURNS + USER_ID
# =============================================================================

# ---------------------------------------------------------------------------
# PERSONA 1 (ACTIVE): Account 10001 (Muru) -- Archetype A: Perfect Waiver
# ---------------------------------------------------------------------------
# Balance: $0 | Tenure: 4.2yr | Autopay: ON | Waiver: PASS (all 3 rules)
# Moving to: 200 Second St (A12) -> Fiber, Vacant -> 4-turn happy path
# ---------------------------------------------------------------------------
# TURNS = [
#     (1, "Hi, I'd like to move my service to 200 Second St. Account 10001."),
#     (2, "Fiber 1 Gig"),
#     (3, "Option 2 is fine"),
#     (4, "Yes"),
# ]
# APP_NAME = "metro_test"
# USER_ID  = "test_10001"

# ---------------------------------------------------------------------------
# PERSONA 2: Account 10002 (John) -- Archetype B: Waiver Failure
# ---------------------------------------------------------------------------
# Balance: $0 | Tenure: 0.5yr | Autopay: OFF | Waiver: FAIL (2 reasons)
# Moving to: 400 Fourth St (A14) -> Fiber, Vacant -> 4-turn, $99 fee
# ---------------------------------------------------------------------------
# TURNS = [
#     (1, "Hi, I'd like to move my service to 400 Fourth St. Account 10002."),
#     (2, "Fiber 500"),
#     (3, "Option 1 is fine"),
#     (4, "Yes"),
# ]
# APP_NAME = "metro_test"
# USER_ID  = "test_10002"

# ---------------------------------------------------------------------------
# PERSONA 3: Account 10004 (Mike) -- Archetype C: Debtor / Billing Gate
# ---------------------------------------------------------------------------
# Balance: $82.45 | Tenure: 2.0yr | Autopay: ON | Waiver: FAIL (tenure)
# Moving to: 100 First St (A11) -> Fiber, Vacant -> 5-turn (extra billing turn)
# ---------------------------------------------------------------------------
# TURNS = [
#     (1, "I want to move to 100 First St. Cancel if fiber not available. Waive fees. Account 10004."),
#     (2, "Sure"),
#     (3, "Fiber 1 Gig"),
#     (4, "Option 2 is fine"),
#     (5, "Yes"),
# ]
# APP_NAME = "metro_test"
# USER_ID  = "test_10004"

# ---------------------------------------------------------------------------
# PERSONA 4: Account 10003 (Sarah) -- Archetype D: Legacy Upsell
# ---------------------------------------------------------------------------
# Balance: $0 | Tenure: 5.0yr | Autopay: ON | Waiver: PASS
# Current plan: Internet 100 (Copper) -> Moving to Fiber -> tech migration notice
# Moving to: 500 Fifth St (A15) -> Fiber, Vacant -> 4-turn + migration messaging
# ---------------------------------------------------------------------------
# TURNS = [
#     (1, "Hi, I'd like to move to 500 Fifth St. Account 10003."),
#     (2, "Fiber 1 Gig"),
#     (3, "Option 2 is fine"),
#     (4, "Yes"),
# ]
# APP_NAME = "metro_test"
# USER_ID  = "test_10003"

# ---------------------------------------------------------------------------
# PERSONA 5: Account 10011 (Robert) -- Archetype E: Churned / Win-back
# ---------------------------------------------------------------------------
# Status: CANCELED | No address | Plan: Fiber 300 | Tenure: 1.5yr | Autopay: OFF
# ---------------------------------------------------------------------------
# TURNS = [
#     (1, "Hi, I'd like to check on my account. Account 10011."),
#     (2, "Yes, I'd like to sign up again."),
# ]
# APP_NAME = "metro_test"
# USER_ID  = "test_10011"

# ---------------------------------------------------------------------------
# PERSONA 6: Account 10005 (Emily) -- Archetype F: Double Dipper
# ---------------------------------------------------------------------------
# Balance: $0 | Tenure: 3.1yr (Rule A PASS) | Autopay: ON (Rule B PASS)
# waivers_used_12m: 1 (Rule C FAIL -- waiver already used in last 12 months)
# Expected: $99 fee denied with specific reason: prior waiver used recently
# Moving to: 700 Seventh St (A17) -> Fiber, Vacant -> 4-turn, $99 fee
# ---------------------------------------------------------------------------
# TURNS = [
#     (1, "Hi, I'd like to move to 700 Seventh St. Account 10005."),
#     (2, "Fiber 300"),
#     (3, "Option 1 is fine"),
#     (4, "Yes"),
# ]
# APP_NAME = "metro_test"
# USER_ID  = "test_10005"

# ---------------------------------------------------------------------------
# STRESS TEST (ACTIVE): Account 10004 (Mike) -- 8-Turn Difficult Customer
# ---------------------------------------------------------------------------
# 3 embedded challenges:
#   Turn 2: Card security hard stop (tries to pay with new card)
#   Turn 4: Plan browsing mid-flow (asks to see all Fiber options)
#   Turn 8: Post-move bill question (must NOT call T7 -- old account CANCELED)
# Balance: $82.45 | Tenure: 2yr | Autopay: ON | Waiver: FAIL (tenure)
# Moving to: 100 First St (A11) -> Fiber, Vacant
# ---------------------------------------------------------------------------
TURNS = [
    (1, "I want to move to 100 First St. Cancel if fiber not available. Waive fees. Account 10004."),
    (2, "Sure"),
    (3, "Fiber 1 Gig"),
    (4, "Option 2 is fine"),
    (5, "Yes"),
]
APP_NAME = "metro_test"
USER_ID  = "test_10004"

SEP = "=" * 70


def extract_events(event, turn_num, tools_log, t12_calls):
    """Parse a single ADK event for tool calls and final text."""
    agent_text = ""

    if not event.content or not event.content.parts:
        return agent_text

    for part in event.content.parts:
        # Tool call (agent -> tool)
        if hasattr(part, "function_call") and part.function_call:
            fc = part.function_call
            args = dict(fc.args) if fc.args else {}
            tools_log.append(f"  Turn {turn_num}  {fc.name}({args})")
            if fc.name == "T12_ExecuteMoveCancel":
                t12_calls.append({"turn": turn_num, "args": args})

        # Final text response
        if event.is_final_response() and hasattr(part, "text") and part.text:
            agent_text += part.text

    return agent_text


async def run_test():
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    session = await session_service.create_session(app_name=APP_NAME, user_id=USER_ID)

    tools_log  = []   # ordered list of all tool calls
    t12_calls  = []   # T12 calls with full args
    errors     = []   # any exceptions

    for turn_num, user_text in TURNS:
        print(f"\n{SEP}")
        print(f"TURN {turn_num} -> USER: {user_text}")
        print(SEP)

        msg = types.Content(role="user", parts=[types.Part(text=user_text)])
        agent_response = ""

        try:
            async for event in runner.run_async(
                user_id=USER_ID,
                session_id=session.id,
                new_message=msg,
            ):
                chunk = extract_events(event, turn_num, tools_log, t12_calls)
                if chunk:
                    agent_response += chunk

        except Exception as e:
            err = f"Turn {turn_num}: {type(e).__name__}: {e}"
            errors.append(err)
            print(f"  !! ERROR: {err}")
            _tb.print_exc()
            break

        print(f"\nTURN {turn_num} -> AGENT:\n{agent_response.strip() or '(no text response)'}")

    # -----------------------------------------------------------------------
    # Summary + Verification Table
    # -----------------------------------------------------------------------
    print(f"\n{SEP}")
    print("SUMMARY")
    print(SEP)

    print(f"\nTools called ({len(tools_log)} total):")
    if tools_log:
        for entry in tools_log:
            print(entry)
    else:
        print("  (none recorded)")

    print(f"\nT12_ExecuteMoveCancel:")
    if t12_calls:
        for call in t12_calls:
            print(f"  Called on Turn {call['turn']} with args:")
            for k, v in call["args"].items():
                print(f"    {k}: {v}")
    else:
        print("  NOT called (may be inside SA1->DA4 chain — check DB below)")

    print(f"\nErrors / Exceptions:")
    if errors:
        for e in errors:
            print(f"  {e}")
    else:
        print("  None")

    # -----------------------------------------------------------------------
    # DB Verification Table (always printed after every run)
    # Shows: original account status, new account at destination, address status
    # -----------------------------------------------------------------------
    print(f"\n{SEP}")
    print("DB VERIFICATION")
    print(SEP)
    try:
        import sqlite3 as _sqlite3
        _db = _sqlite3.connect(
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "metro_city.db")
        )
        _cur = _db.cursor()

        # All accounts touched in this run (original + any new accounts > 10020)
        _ids = [uid for _, uid in TURNS[:1]]  # extract account_id from first turn if embedded
        # Pull account_id from TURNS[0] message if present
        import re as _re
        _match = _re.search(r'\b(1000\d|1001\d|1002\d)\b', TURNS[0][1])
        _acct  = int(_match.group(1)) if _match else None

        if _acct:
            print(f"\nOriginal account {_acct}:")
            _cur.execute(
                "SELECT account_id, first_name, address_id, plan_name, status, "
                "install_date, install_slot, start_date, end_date "
                "FROM customer_accounts WHERE account_id=?", (_acct,)
            )
            _row = _cur.fetchone()
            if _row:
                _cols = ["account_id","first_name","address_id","plan_name","status",
                         "install_date","install_slot","start_date","end_date"]
                for _c, _v in zip(_cols, _row):
                    print(f"  {_c:15s}: {_v}")

        print(f"\nNew accounts created (account_id > 10020):")
        _cur.execute(
            "SELECT account_id, first_name, address_id, plan_name, status, "
            "install_date, install_slot, start_date, end_date "
            "FROM customer_accounts WHERE account_id > 10020"
        )
        _rows = _cur.fetchall()
        if _rows:
            _cols = ["account_id","first_name","address_id","plan_name","status",
                     "install_date","install_slot","start_date","end_date"]
            for _row in _rows:
                for _c, _v in zip(_cols, _row):
                    print(f"  {_c:15s}: {_v}")
                print()
        else:
            print("  (none — T12 may not have been called or DB was not written)")

        _db.close()
    except Exception as _e:
        print(f"  DB check failed: {_e}")

    print(f"\n{SEP}\n")


if __name__ == "__main__":
    asyncio.run(run_test())
