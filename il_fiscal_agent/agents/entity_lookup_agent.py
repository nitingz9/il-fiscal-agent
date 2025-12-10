"""
Entity Lookup Agent

Finds and identifies Illinois local government entities by name or code.
"""
from google.adk.agents import Agent

from config.settings import PRIMARY_MODEL
from tools.fiscal_tools import (
    search_government_entity,
    get_entity_details,
)


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
