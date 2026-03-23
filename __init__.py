"""
metro_city_demo
---------------
Multi-agent demo for Metro City Internet, built with Google ADK.

Entry point: agent.py (root_agent)

3-Tier Architecture:
    Uber:       agent.py (root_agent)
    Supervisor: SA1_Moves_Supervisor
    Domain:     DA1_Sales_Agent, DA2_Billing_Agent, DA3_Scheduling_Agent
    Squad:      DA4_Execute_Move_Agent

Tools: T1 through T13 (see CLAUDE.md for full reference)

To reset the database to its original state:
    python z_reset_world.py
"""
