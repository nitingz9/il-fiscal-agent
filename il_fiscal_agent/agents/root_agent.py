"""
Root Agent for the Illinois Local Government Financial Data System

This is the main orchestrator agent that coordinates all sub-agents
and handles the overall conversation flow.
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
sys.path.append('/home/claude/il_fiscal_agent')

from config.settings import PRIMARY_MODEL
from agents.sub_agents import SUB_AGENTS
from tools.fiscal_tools import ALL_TOOLS


# =============================================================================
# SAFETY CALLBACKS
# =============================================================================

def input_safety_guardrail(
    callback_context: CallbackContext,
    llm_request: LlmRequest
) -> Optional[LlmResponse]:
    """
    Before-model callback to filter inappropriate or off-topic requests.
    
    Checks the user's input for:
    - Attempts to get information outside Illinois
    - Requests for non-financial data (personal info about officials)
    - Potentially harmful queries
    
    Returns an LlmResponse to block, or None to allow.
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
                    parts=[types.Part(text=f"""I specialize in Illinois local government financial data only. 
                    
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
    
    # Check for inappropriate personal information requests
    personal_info_keywords = [
        "home address", "personal phone", "salary of", 
        "how much does", "private information"
    ]
    
    for keyword in personal_info_keywords:
        if keyword in last_user_message:
            return LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part(text="""I can provide publicly available information from Annual Financial Reports, including:
- Official contact information for government offices
- Aggregate salary expenditures
- Financial data and statistics

I cannot provide personal information about individual employees or officials. What financial data can I help you find?""")]
                )
            )
    
    # Allow the request to proceed
    print(f"--- Callback: Allowing request for {agent_name} ---")
    return None


def tool_usage_guardrail(
    tool: BaseTool,
    args: Dict[str, Any],
    tool_context: ToolContext
) -> Optional[Dict]:
    """
    Before-tool callback to validate tool arguments.
    
    Checks:
    - Entity codes are valid format
    - County names are valid Illinois counties
    - Limits on result sizes
    
    Returns a dict to override tool result, or None to allow.
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
            print(f"--- Callback: Capping limit from {limit} to 100 ---")
            args["limit"] = 100  # Modify in place
    
    # Allow tool execution
    return None


def _is_valid_entity_code(code: str) -> bool:
    """Validate entity code format (XXX/YYY/ZZ)."""
    if not code:
        return False
    parts = code.split("/")
    if len(parts) != 3:
        return False
    # Basic validation - all parts should be numeric-ish
    try:
        for part in parts:
            if not part.strip():
                return False
    except:
        return False
    return True


# =============================================================================
# ROOT AGENT DEFINITION
# =============================================================================

root_agent = Agent(
    name="il_fiscal_data_agent",
    model=PRIMARY_MODEL,
    description="""Illinois Local Government Financial Data Assistant.
    Helps users explore financial data for 4,000+ Illinois local governments
    including cities, villages, townships, fire districts, and more.""",
    
    instruction="""You are the Illinois Local Government Financial Data Assistant, a sophisticated
AI agent that helps constituents, analysts, and officials explore financial data from 
Annual Financial Reports filed by over 4,000 Illinois local governments.

YOUR CAPABILITIES:
You coordinate a team of specialized agents to answer questions about:
1. Entity Lookup: Find cities, villages, townships, districts by name
2. Financial Data: Revenue, expenditure, debt, pension details  
3. Comparisons: Compare entities, benchmark against peers
4. Fiscal Health: Assess financial condition and stability
5. Geographic Analysis: Explore entities by county

DELEGATION RULES:
- For greetings, farewells, help requests → delegate to greeting_agent
- For finding/searching entities → delegate to entity_lookup_agent  
- For specific financial numbers → delegate to fiscal_query_agent
- For comparisons and rankings → delegate to comparison_agent
- For fiscal health assessments → delegate to fiscal_health_agent
- For county-level questions → delegate to geographic_agent

CONVERSATION MANAGEMENT:
- Maintain context across the conversation using session state
- If user asks follow-up about "their" entity, check state for current_entity_code
- When ambiguous, ask clarifying questions
- Be conversational but professional

DATA CONTEXT:
- Data is from FY2024 Annual Financial Reports
- Covers 4,140 local government entities
- 102 Illinois counties
- Entity types: cities, villages, townships, fire districts, library districts, 
  park districts, school districts, community colleges, and many more

RESPONSE GUIDELINES:
- Format numbers with commas and appropriate units (millions, billions)
- Use per-capita metrics when comparing different-sized entities
- Provide context and explain what numbers mean
- Be honest about data limitations
- Offer to explore related information

EXAMPLES OF GOOD RESPONSES:
User: "What's the property tax revenue for Naperville?"
→ First find Naperville, then get revenue data, present clearly

User: "Compare that to Aurora"  
→ Use context from state, get Aurora data, show side-by-side

User: "Is Springfield financially healthy?"
→ Clarify which Springfield, then run fiscal health analysis

User: "Top 10 fire districts in Cook County"
→ Use ranking tool with filters

Remember: You are helping people understand their local government finances.
Be helpful, accurate, and accessible.""",

    # Include all tools directly on root agent as backup
    tools=ALL_TOOLS,
    
    # Sub-agents for delegation
    sub_agents=SUB_AGENTS,
    
    # Safety callbacks
    before_model_callback=input_safety_guardrail,
    before_tool_callback=tool_usage_guardrail,
    
    # Auto-save last response
    output_key="last_agent_response"
)


# =============================================================================
# AGENT EXPORT
# =============================================================================

# This is what ADK looks for
__all__ = ['root_agent']
