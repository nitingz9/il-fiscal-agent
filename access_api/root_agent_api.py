"""
Root Agent (API-Based) for the Illinois Local Government Financial Data System

This version of the root agent uses tools that call a REST API
instead of directly accessing BigQuery. This enables:

1. Decoupled architecture - API can be deployed separately
2. Support for multiple data sources (BigQuery or MS Access)
3. Better scalability and maintainability
4. API can be shared across multiple applications

Architecture:
    User -> ADK Agent -> API Tools -> Flask API -> BigQuery/Access -> Data

Usage:
    1. Start the Flask API: python api/fiscal_data_api.py
    2. Run the ADK agent: adk web
"""

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from typing import Optional, Dict, Any

import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.fiscal_tools_api import ALL_TOOLS


# =============================================================================
# CONFIGURATION
# =============================================================================

PRIMARY_MODEL = os.environ.get("PRIMARY_MODEL", "gemini-2.0-flash")


# =============================================================================
# SAFETY CALLBACKS
# =============================================================================

def input_safety_guardrail(
    callback_context: CallbackContext,
    llm_request: LlmRequest
) -> Optional[LlmResponse]:
    """
    Before-model callback to filter inappropriate or off-topic requests.
    """
    agent_name = callback_context.agent_name
    print(f"--- Callback: input_safety_guardrail for {agent_name} ---")
    
    # Get the last user message
    last_user_message = ""
    if llm_request.contents:
        for content in reversed(llm_request.contents):
            if content.role == 'user' and content.parts:
                if content.parts[0].text:
                    last_user_message = content.parts[0].text.lower()
                    break
    
    # Check for out-of-scope requests
    out_of_scope_keywords = [
        "california", "new york city", "texas", "florida",
        "federal government", "congress", "white house"
    ]
    
    for keyword in out_of_scope_keywords:
        if keyword in last_user_message:
            return LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part(text="""I specialize in Illinois local government financial data only. 
                    
I can help you with:
- Illinois cities, villages, and towns
- Illinois townships  
- Fire protection districts
- Library districts, park districts
- School districts, community colleges
- And other Illinois local governments

Would you like to explore Illinois local government data instead?""")]
                )
            )
    
    return None


def tool_usage_guardrail(
    tool: BaseTool,
    args: Dict[str, Any],
    tool_context: ToolContext
) -> Optional[Dict]:
    """
    Before-tool callback to validate tool arguments.
    """
    tool_name = tool.name
    print(f"--- Callback: tool_usage_guardrail for {tool_name} ---")
    print(f"--- Args: {args} ---")
    
    # Validate entity code format
    if "entity_code" in args:
        code = args["entity_code"]
        if code and not _is_valid_entity_code(code):
            return {
                "status": "error",
                "error_message": f"Invalid entity code format: '{code}'. Expected format: XXX/YYY/ZZ (e.g., '016/020/32')"
            }
    
    # Validate limit parameters
    if "limit" in args:
        limit = args.get("limit", 10)
        if isinstance(limit, int) and limit > 100:
            args["limit"] = 100
    
    return None


def _is_valid_entity_code(code: str) -> bool:
    """Validate entity code format (XXX/YYY/ZZ)."""
    if not code:
        return False
    parts = code.split("/")
    if len(parts) != 3:
        return False
    return all(part.strip() for part in parts)


# =============================================================================
# SUB-AGENTS (Simplified for API-based approach)
# =============================================================================

# Greeting agent tools
def greet_user(name: Optional[str] = None) -> str:
    """Provides a friendly greeting to the user."""
    if name:
        return f"Hello, {name}! I'm ready to help you explore Illinois local government financial data. What would you like to know?"
    return "Hello! I'm the Illinois Fiscal Data Assistant. I can help you explore financial data for over 4,000 local governments including cities, villages, townships, fire districts, and more. What would you like to know?"


def say_goodbye() -> str:
    """Provides a polite farewell message."""
    return "Thank you for exploring Illinois local government data with me. Feel free to return anytime you have more questions. Goodbye!"


def provide_help() -> str:
    """Explains what the agent can do."""
    return """I can help you with:

🔍 **Find Entities**: Search for any Illinois city, village, township, fire district, or other local government

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
    model=PRIMARY_MODEL,
    description="Handles greetings, farewells, and help requests.",
    instruction="Handle greetings, farewells, and help requests warmly.",
    tools=[greet_user, say_goodbye, provide_help],
)


# =============================================================================
# ROOT AGENT DEFINITION
# =============================================================================

root_agent = Agent(
    name="il_fiscal_data_agent",
    model=PRIMARY_MODEL,
    description="""Illinois Local Government Financial Data Assistant.
    Helps users explore financial data for 4,000+ Illinois local governments
    using a REST API backend.""",
    
    instruction="""You are the Illinois Local Government Financial Data Assistant, a sophisticated
AI agent that helps constituents, analysts, and officials explore financial data from 
Annual Financial Reports filed by over 4,000 Illinois local governments.

YOUR CAPABILITIES:
1. Entity Lookup: Find cities, villages, townships, districts by name
2. Financial Data: Revenue, expenditure, debt, pension details  
3. Comparisons: Compare entities, benchmark against peers
4. Fiscal Health: Assess financial condition and stability
5. Geographic Analysis: Explore entities by county

DATA ACCESS:
- You access data via a REST API that connects to the fiscal database
- Data is from FY2024 Annual Financial Reports
- Covers 4,140 local government entities across 102 Illinois counties

RESPONSE GUIDELINES:
- Format numbers with commas and appropriate units
- Use per-capita metrics when comparing different-sized entities
- Provide context and explain what numbers mean
- Be honest about data limitations

EXAMPLES:
User: "What's the property tax revenue for Naperville?"
→ Search for Naperville, get revenue data, present clearly

User: "Compare that to Aurora"  
→ Use context, get Aurora data, show side-by-side

User: "Is Springfield financially healthy?"
→ Clarify which Springfield, then run fiscal health analysis""",

    tools=ALL_TOOLS + [greet_user, say_goodbye, provide_help],
    sub_agents=[greeting_agent],
    before_model_callback=input_safety_guardrail,
    before_tool_callback=tool_usage_guardrail,
    output_key="last_agent_response"
)


# =============================================================================
# EXPORT
# =============================================================================

__all__ = ['root_agent']
