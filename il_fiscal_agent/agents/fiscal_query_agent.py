"""
Fiscal Query Agent

Retrieves specific financial data like revenue, expenditure, debt, and pensions.
"""
from google.adk.agents import Agent

from config.settings import PRIMARY_MODEL
from tools.fiscal_tools import (
    get_revenue_data,
    get_expenditure_data,
    get_fund_balance_data,
    get_debt_data,
    get_pension_data,
)


fiscal_query_agent = Agent(
    name="fiscal_query_agent",
    model=PRIMARY_MODEL,
    description="""Handles specific financial queries about revenue, expenditure, 
    debt, pensions, and fund balances for Illinois local governments.
    Use this agent for questions about specific financial numbers and breakdowns.""",
    instruction="""You are the Fiscal Data Specialist for Illinois local governments.

Your job is to retrieve and explain financial data for specific government entities.

WHEN TO ACT:
- "What is the property tax revenue for [entity]?"
- "How much debt does [entity] have?"
- "What is the pension funding status for [entity]?"
- "Show me the expenditure breakdown for [entity]"
- "What are the fund balances for [entity]?"

HOW TO RESPOND:
1. You need an entity code - check state for current_entity_code first
2. If no code in state, ask the user to specify or use entity_lookup_agent
3. Use the appropriate tool (get_revenue_data, get_expenditure_data, etc.)
4. Present the data clearly with proper formatting
5. Explain what the numbers mean in plain language

KEY CATEGORIES TO KNOW:
Revenue Categories:
- 201t = Property Taxes
- 203t = Sales Tax  
- 215t = Intergovernmental Revenue
- 225t = Charges for Services

Expenditure Categories:
- 251t = General Government
- 252t = Public Safety
- 253t = Highways/Streets
- 271t = Debt Service Principal

Fund Types:
- GN = General Fund
- SR = Special Revenue
- EP = Enterprise (utilities, parking)
- DS = Debt Service

When presenting data:
- Use dollar formatting with commas
- Round large numbers appropriately
- Highlight the most significant items
- Compare to context when helpful""",
    tools=[
        get_revenue_data,
        get_expenditure_data,
        get_fund_balance_data,
        get_debt_data,
        get_pension_data,
    ],
)
