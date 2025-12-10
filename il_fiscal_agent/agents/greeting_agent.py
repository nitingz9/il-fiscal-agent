"""
Greeting Agent

Manages greetings, farewells, and help requests.
"""
from typing import Optional

from google.adk.agents import Agent

from config.settings import LIGHT_MODEL


# =============================================================================
# GREETING TOOLS
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


# =============================================================================
# AGENT DEFINITION
# =============================================================================

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
