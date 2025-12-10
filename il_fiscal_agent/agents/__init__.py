"""
Sub-Agents for the Illinois Fiscal Data System

This module exports all specialized sub-agents that are coordinated by the root agent.
"""
from .entity_lookup_agent import entity_lookup_agent
from .fiscal_query_agent import fiscal_query_agent
from .comparison_agent import comparison_agent
from .fiscal_health_agent import fiscal_health_agent
from .geographic_agent import geographic_agent
from .greeting_agent import greeting_agent


# All sub-agents for the root agent to coordinate
SUB_AGENTS = [
    entity_lookup_agent,
    fiscal_query_agent,
    comparison_agent,
    fiscal_health_agent,
    geographic_agent,
    greeting_agent,
]

__all__ = [
    'entity_lookup_agent',
    'fiscal_query_agent',
    'comparison_agent',
    'fiscal_health_agent',
    'geographic_agent',
    'greeting_agent',
    'SUB_AGENTS',
]
