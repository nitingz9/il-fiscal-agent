"""
Test Script for Illinois Local Government Financial Data Agent

This script tests the agent locally using simulated data.
Run this to verify the agent structure is correct before connecting to BigQuery.
"""
import asyncio
import os
import sys

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types


# =============================================================================
# MOCK DATA FOR TESTING (without BigQuery connection)
# =============================================================================

MOCK_ENTITIES = {
    "016/020/32": {
        "Code": "016/020/32",
        "UnitName": "Skokie",
        "EntityType": "Village",
        "County": "Cook",
        "Population": 67824,
        "EquitalizedAssessedValue": 5200000000,
        "FullTimeEmployees": 450,
        "PartTimeEmployees": 125,
        "HomeRule": "Y",
        "CEOFName": "George",
        "CEOLName": "Van Dusen",
        "CEOTitle": "Mayor"
    },
    "016/030/30": {
        "Code": "016/030/30",
        "UnitName": "Evanston",
        "EntityType": "City",
        "County": "Cook",
        "Population": 78110,
        "EquitalizedAssessedValue": 6100000000,
        "FullTimeEmployees": 850,
        "PartTimeEmployees": 200,
        "HomeRule": "Y",
        "CEOFName": "Daniel",
        "CEOLName": "Biss",
        "CEOTitle": "Mayor"
    }
}

MOCK_REVENUES = {
    "016/020/32": {
        "total_revenue": 180000000,
        "by_category": [
            {"Category": "201t", "CategoryName": "Property Taxes", "GeneralFund": 45000000, "Total": 45000000},
            {"Category": "203t", "CategoryName": "Sales Tax", "GeneralFund": 25000000, "Total": 25000000},
            {"Category": "215t", "CategoryName": "Intergovernmental", "GeneralFund": 15000000, "Total": 15000000},
        ]
    }
}


# =============================================================================
# TEST TOOLS (Mock implementations)
# =============================================================================

def mock_search_entity(search_term: str) -> dict:
    """Mock entity search for testing."""
    results = []
    for code, entity in MOCK_ENTITIES.items():
        if search_term.lower() in entity["UnitName"].lower():
            results.append({
                "Code": code,
                "UnitName": entity["UnitName"],
                "EntityType": entity["EntityType"],
                "County": entity["County"]
            })
    
    if results:
        return {"status": "success", "entities": results}
    return {"status": "not_found", "message": f"No entities found for '{search_term}'"}


def mock_get_entity(code: str) -> dict:
    """Mock entity details for testing."""
    if code in MOCK_ENTITIES:
        return {"status": "success", "entity": MOCK_ENTITIES[code]}
    return {"status": "error", "error_message": f"Entity {code} not found"}


def mock_get_revenue(code: str) -> dict:
    """Mock revenue data for testing."""
    if code in MOCK_REVENUES:
        return {"status": "success", **MOCK_REVENUES[code]}
    return {"status": "success", "total_revenue": 0, "by_category": []}


# =============================================================================
# SIMPLE TEST AGENT
# =============================================================================

test_agent = Agent(
    name="test_fiscal_agent",
    model="gemini-2.0-flash",
    description="Test agent for Illinois fiscal data",
    instruction="""You are a test agent for Illinois local government data.
    You can search for entities and get basic information about them.
    Use the available tools to answer questions.""",
    tools=[mock_search_entity, mock_get_entity, mock_get_revenue]
)


# =============================================================================
# TEST RUNNER
# =============================================================================

async def run_test():
    """Run test conversation with the agent."""
    print("=" * 60)
    print("Illinois Fiscal Data Agent - Test Mode")
    print("=" * 60)
    
    # Setup
    session_service = InMemorySessionService()
    APP_NAME = "test_fiscal_app"
    USER_ID = "test_user"
    SESSION_ID = "test_session_001"
    
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )
    print(f"✅ Session created: {SESSION_ID}")
    
    runner = Runner(
        agent=test_agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    print(f"✅ Runner created for: {test_agent.name}")
    print()
    
    # Test queries
    test_queries = [
        "Search for Skokie",
        "Get details for entity 016/020/32",
        "What is the revenue for 016/020/32?"
    ]
    
    for query in test_queries:
        print(f">>> User: {query}")
        
        content = types.Content(
            role='user',
            parts=[types.Part(text=query)]
        )
        
        async for event in runner.run_async(
            user_id=USER_ID,
            session_id=SESSION_ID,
            new_message=content
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    response = event.content.parts[0].text
                    print(f"<<< Agent: {response[:500]}...")  # Truncate for readability
                break
        
        print()
    
    print("=" * 60)
    print("Test completed!")
    print("=" * 60)


# =============================================================================
# CONFIGURATION TEST
# =============================================================================

def test_configuration():
    """Test that all configuration is properly set up."""
    print("Testing configuration...")
    
    # Check imports
    try:
        from config.settings import GCP_PROJECT_ID, TABLES, FUND_TYPES
        print(f"✅ Config imported successfully")
        print(f"   Project: {GCP_PROJECT_ID}")
        print(f"   Tables: {len(TABLES)} defined")
        print(f"   Fund Types: {len(FUND_TYPES)} defined")
    except ImportError as e:
        print(f"❌ Config import failed: {e}")
        return False
    
    # Check tools
    try:
        from tools.fiscal_tools import ALL_TOOLS
        print(f"✅ Tools imported successfully: {len(ALL_TOOLS)} tools")
        for tool in ALL_TOOLS:
            print(f"   - {tool.__name__}")
    except ImportError as e:
        print(f"❌ Tools import failed: {e}")
        return False
    
    # Check agents
    try:
        from agents.sub_agents import SUB_AGENTS
        print(f"✅ Sub-agents imported successfully: {len(SUB_AGENTS)} agents")
        for agent in SUB_AGENTS:
            print(f"   - {agent.name}")
    except ImportError as e:
        print(f"❌ Sub-agents import failed: {e}")
        return False
    
    # Check root agent
    try:
        from agents.root_agent import root_agent
        print(f"✅ Root agent imported successfully: {root_agent.name}")
    except ImportError as e:
        print(f"❌ Root agent import failed: {e}")
        return False
    
    print("\n✅ All configuration tests passed!")
    return True


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the Illinois Fiscal Data Agent")
    parser.add_argument("--config", action="store_true", help="Test configuration only")
    parser.add_argument("--agent", action="store_true", help="Run agent test conversation")
    args = parser.parse_args()
    
    if args.config:
        test_configuration()
    elif args.agent:
        asyncio.run(run_test())
    else:
        # Run both by default
        print("\n" + "=" * 60)
        print("CONFIGURATION TEST")
        print("=" * 60 + "\n")
        test_configuration()
        
        print("\n" + "=" * 60)
        print("AGENT TEST")
        print("=" * 60 + "\n")
        asyncio.run(run_test())
