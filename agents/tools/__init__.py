"""Agent tools, exposed over MCP as Unity Catalog functions (PLAN 8.3).

Each tool is a Python function with a pure-logic core (testable against pandas
frames) and a UC-function registration wrapper. The triage agent calls them
over MCP; the pure cores let the demo prove the tool loop offline.
"""
