"""
Comparison Agent

Compares multiple entities, finds peers, and creates rankings.
"""
from google.adk.agents import Agent

from config.settings import PRIMARY_MODEL
from tools.fiscal_tools import (
    compare_entities,
    find_peer_entities,
    rank_entities,
)


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
