"""
Geographic Agent

Handles county-level queries and geographic analysis.
"""
from google.adk.agents import Agent

from config.settings import PRIMARY_MODEL
from tools.fiscal_tools import (
    get_county_entities,
    get_county_financial_summary,
)


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
