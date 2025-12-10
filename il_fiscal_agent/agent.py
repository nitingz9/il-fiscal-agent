"""
Illinois Local Government Financial Data Agent

Main entry point for the ADK agent. This file exports the root_agent
which ADK uses to run the agent.

Usage:
    adk run il_fiscal_agent
    adk web il_fiscal_agent
"""
import sys
import os

# Add the project root to the path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import the root agent
from agents.root_agent import root_agent

# ADK looks for 'root_agent' by default
__all__ = ['root_agent']
