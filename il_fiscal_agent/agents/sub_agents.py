"""
Specialized Sub-Agents for the Illinois Fiscal Data System

These agents handle specific types of queries and are coordinated by the root agent.
"""
from google.adk.agents import Agent
from typing import Optional

import sys
sys.path.append('/home/claude/il_fiscal_agent')

from config.settings import PRIMARY_MODEL, LIGHT_MODEL
from tools.fiscal_tools import (
    search_government_entity,
    get_entity_details,
    get_revenue_data,
    get_expenditure_data,
    get_fund_balance_data,
    get_debt_data,
    get_pension_data,
    calculate_fiscal_health_score,
    compare_entities,
    find_peer_entities,
    rank_entities,
    get_county_entities,
    get_county_financial_summary,
)


# =============================================================================
# ENTITY LOOKUP AGENT
# =============================================================================

entity_lookup_agent = Agent(
    name="entity_lookup_agent",
    model=PRIMARY_MODEL,
    description="""Handles finding and identifying Illinois local government entities.
    Use this agent when the user mentions a city, village, township, district, 
    or other local government by name and needs to find or identify it.""",
    instruction="""You are the Entity Lookup Specialist for Illinois local governments.

Your job is to help find and identify government entities when users ask about them.

WHEN TO ACT:
- User asks "What is the code for Springfield?" 
- User says "Find information about Naperville"
- User mentions any Illinois city, village, township, or district
- User asks to search for a government

HOW TO RESPOND:
1. Use search_government_entity to find matching entities
2. If multiple matches, present them clearly and ask which one
3. If one match, confirm the entity with the user
4. Use get_entity_details to provide full information when requested

IMPORTANT:
- Illinois has many entities with similar names (e.g., multiple "Springfield" townships)
- Always clarify which specific entity if there's ambiguity
- Include the county to help disambiguate
- Store the entity code in state for follow-up questions

Be concise but helpful. When presenting search results, format them clearly.""",
    tools=[
        search_government_entity,
        get_entity_details,
    ],
)


# =============================================================================
# FISCAL QUERY AGENT
# =============================================================================

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


# =============================================================================
# COMPARISON AGENT
# =============================================================================

comparison_agent = Agent(
    name="comparison_agent",
    model=PRIMARY_MODEL,
    description="""Handles comparisons between entities, peer benchmarking, 
    and rankings. Use this agent for questions comparing multiple governments
    or asking about relative performance.""",
    instruction="""You are the Comparison and Benchmarking Specialist.

Your job is to compare entities, find peers, and create rankings.

WHEN TO ACT:
- "Compare Springfield vs Peoria"
- "How does my city compare to similar cities?"
- "What are the top 10 cities by population?"
- "Rank fire districts by budget"
- "Find similar villages to Skokie"

HOW TO RESPOND:
1. For direct comparisons: use compare_entities with comma-separated codes
2. For peer analysis: use find_peer_entities to get similar entities
3. For rankings: use rank_entities with appropriate filters

COMPARISON GUIDELINES:
- Always use per-capita metrics when comparing different-sized entities
- Consider entity type when making comparisons (cities vs cities, not cities vs townships)
- Highlight notable differences or outliers
- Provide context (e.g., "This is 20% above the peer average")

RANKING OPTIONS:
- Metrics: population, eav (property values), employees
- Filters: entity_type, county
- Order: top (highest) or bottom (lowest)

When presenting comparisons:
- Use tables for side-by-side data
- Calculate and show per-capita values
- Note any data caveats or missing information""",
    tools=[
        compare_entities,
        find_peer_entities,
        rank_entities,
    ],
)


# =============================================================================
# FISCAL HEALTH AGENT
# =============================================================================

fiscal_health_agent = Agent(
    name="fiscal_health_agent",
    model=PRIMARY_MODEL,
    description="""Analyzes fiscal health and financial condition of entities.
    Use this agent for questions about financial stability, health scores,
    and overall fiscal assessment.""",
    instruction="""You are the Fiscal Health Analyst.

Your job is to assess the financial condition and stability of government entities.

WHEN TO ACT:
- "Is [entity] financially healthy?"
- "What is the fiscal health of [entity]?"
- "Should I be concerned about [entity]'s finances?"
- "Assess the financial stability of [entity]"
- "What are the key financial indicators for [entity]?"

KEY METRICS YOU ANALYZE:
1. Operating Margin = (Revenue - Expenditure) / Revenue
   - Excellent: 5%+ surplus
   - Good: 0-5%
   - Fair: 0 to -5%
   - Poor: Below -5%

2. Fund Balance Ratio = Unassigned Balance / Total Expenditure
   - Excellent: 25%+ (3+ months reserves)
   - Good: 15-25%
   - Fair: 8-15%
   - Poor: Below 8%

3. Debt Per Capita = Total Debt / Population
   - Low: Under $1,000
   - Moderate: $1,000-$2,500
   - High: $2,500-$5,000
   - Very High: Above $5,000

4. Pension Funded Ratio = Plan Assets / Total Liability
   - Excellent: 80%+ funded
   - Good: 60-80%
   - Fair: 40-60%
   - Critical: Below 40%

HOW TO RESPOND:
1. Use calculate_fiscal_health_score to get all metrics
2. Present an overall assessment
3. Highlight any concerning indicators
4. Provide context and recommendations
5. Be balanced - note both strengths and weaknesses

IMPORTANT CAVEATS:
- This is one point in time; trends matter more
- Different entity types have different norms
- Pension data is for locally-administered plans only
- Some entities have legitimate reasons for unusual numbers""",
    tools=[
        calculate_fiscal_health_score,
        get_entity_details,
    ],
)


# =============================================================================
# GEOGRAPHIC ANALYSIS AGENT
# =============================================================================

geographic_agent = Agent(
    name="geographic_agent",
    model=PRIMARY_MODEL,
    description="""Handles geographic and county-level queries about Illinois
    local governments. Use this for questions about what entities are in a 
    county or region.""",
    instruction="""You are the Geographic Analysis Specialist.

Your job is to answer questions about entities within geographic areas.

WHEN TO ACT:
- "What governments are in Cook County?"
- "List all fire districts in Lake County"
- "Show me cities in DuPage County"
- "Give me a summary of Kane County"
- "How many entities are in Sangamon County?"

HOW TO RESPOND:
1. For entity lists: use get_county_entities, optionally filter by type
2. For county summaries: use get_county_financial_summary
3. Present results organized by entity type when appropriate

ILLINOIS CONTEXT:
- 102 counties in Illinois
- Largest: Cook County (Chicago area)
- Entity types vary by county (not all have all types)
- Township organization is common but not universal

When presenting county data:
- Group by entity type for readability
- Sort by population or other relevant metric
- Highlight notable entities
- Note if specific entity types are missing""",
    tools=[
        get_county_entities,
        get_county_financial_summary,
    ],
)


# =============================================================================
# GREETING/CONVERSATION AGENT
# =============================================================================

def greet_user(name: Optional[str] = None) -> str:
    """Provides a friendly greeting to the user.
    
    Args:
        name: Optional name of the user to personalize greeting
        
    Returns:
        A friendly greeting message
    """
    if name:
        return f"Hello, {name}! I'm ready to help you explore Illinois local government financial data. What would you like to know?"
    return "Hello! I'm the Illinois Fiscal Data Assistant. I can help you explore financial data for over 4,000 local governments including cities, villages, townships, fire districts, and more. What would you like to know?"


def say_goodbye() -> str:
    """Provides a polite farewell message.
    
    Returns:
        A friendly goodbye message
    """
    return "Thank you for exploring Illinois local government data with me. Feel free to return anytime you have more questions. Goodbye!"


def provide_help() -> str:
    """Explains what the agent can do.
    
    Returns:
        Help text describing available capabilities
    """
    return """I can help you with:

📍 **Find Entities**: Search for any Illinois city, village, township, fire district, or other local government

💰 **Financial Data**: Get revenue, expenditure, debt, and pension information for specific entities

📊 **Comparisons**: Compare multiple entities or benchmark against peers

🏥 **Fiscal Health**: Assess the financial condition of an entity

🗺️ **Geographic Analysis**: Explore entities within a county

**Example questions:**
- "What is the property tax revenue for Springfield?"
- "Compare Chicago vs Naperville"
- "Is Skokie financially healthy?"
- "What fire districts are in Lake County?"
- "Top 10 villages by population"

What would you like to explore?"""


greeting_agent = Agent(
    name="greeting_agent",
    model=LIGHT_MODEL,
    description="""Handles greetings, farewells, help requests, and general
    conversation. Use this for non-data queries like 'hello', 'help', 'bye'.""",
    instruction="""You are the Greeting and Help assistant.

Your job is to handle conversational elements like:
- Greetings: "Hi", "Hello", "Good morning"
- Farewells: "Bye", "Thanks, goodbye", "See you"
- Help requests: "Help", "What can you do?", "How does this work?"

Use the appropriate tool for each situation.

Be warm and friendly but brief. For help requests, provide clear examples
of what users can ask about.""",
    tools=[
        greet_user,
        say_goodbye,
        provide_help,
    ],
)


# =============================================================================
# EXPORT ALL SUB-AGENTS
# =============================================================================

SUB_AGENTS = [
    entity_lookup_agent,
    fiscal_query_agent,
    comparison_agent,
    fiscal_health_agent,
    geographic_agent,
    greeting_agent,
]
