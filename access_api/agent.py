"""
Illinois Local Government Financial Data Agent (API-Based)

Main entry point for the ADK agent. This version uses a REST API
backend instead of direct BigQuery access.

Architecture:
    User Query → ADK Agent → API Tools → Flask API → BigQuery/Access

Setup:
    1. Start the API server:
       python api/fiscal_data_api.py
    
    2. Run the ADK agent:
       adk web
       
    3. Or run both with the run script:
       python run.py

Environment Variables:
    FISCAL_API_URL: Base URL of the Flask API (default: http://localhost:5000)
    PRIMARY_MODEL: Gemini model to use (default: gemini-2.0-flash)
"""

import sys
import os

# Add project directories to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import the root agent
from agents.root_agent_api import root_agent

# ADK looks for 'root_agent' by default
__all__ = ['root_agent']
