"""
Runner Script for Illinois Fiscal Data Agent System

This script provides convenient ways to run the system:
1. API only - Start just the Flask API
2. Agent only - Start just the ADK agent (assumes API is running)
3. Both - Start API in background, then ADK agent

Usage:
    python run.py api        # Start Flask API only
    python run.py agent      # Start ADK agent only
    python run.py both       # Start both (API in background)
    python run.py test       # Run tests
"""

import subprocess
import sys
import os
import time
import argparse


def run_api(port: int = 5000):
    """Start the Flask API server."""
    print("=" * 60)
    print("Starting Illinois Fiscal Data API...")
    print(f"Server will be available at: http://localhost:{port}")
    print("=" * 60)
    
    api_path = os.path.join(os.path.dirname(__file__), "api", "fiscal_data_api.py")
    subprocess.run([sys.executable, api_path], env={
        **os.environ,
        "FLASK_APP": "fiscal_data_api.py",
    })


def run_agent():
    """Start the ADK agent."""
    print("=" * 60)
    print("Starting Illinois Fiscal Data Agent...")
    print("Open http://localhost:8000 in your browser")
    print("=" * 60)
    
    project_dir = os.path.dirname(__file__)
    subprocess.run(["adk", "web"], cwd=project_dir)


def run_both():
    """Start both API and agent."""
    import threading
    
    print("=" * 60)
    print("Starting Illinois Fiscal Data System")
    print("=" * 60)
    
    # Start API in a thread
    def start_api():
        api_path = os.path.join(os.path.dirname(__file__), "api", "fiscal_data_api.py")
        subprocess.run([sys.executable, api_path], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL)
    
    api_thread = threading.Thread(target=start_api, daemon=True)
    api_thread.start()
    
    print("✓ API starting on http://localhost:5000")
    time.sleep(2)  # Give API time to start
    
    # Start ADK agent
    print("✓ Starting ADK agent on http://localhost:8000")
    run_agent()


def run_tests():
    """Run system tests."""
    print("=" * 60)
    print("Running Illinois Fiscal Data System Tests")
    print("=" * 60)
    
    # Test 1: Check if API client can connect
    print("\n1. Testing API Client...")
    try:
        from utils.api_client import FiscalDataClient
        client = FiscalDataClient()
        result = client.health_check()
        if result.get("status") == "healthy":
            print("   ✓ API is healthy")
            print(f"   Data source: {result.get('data_source')}")
        else:
            print(f"   ✗ API returned: {result}")
    except Exception as e:
        print(f"   ✗ Could not connect to API: {e}")
        print("   Make sure the API is running: python run.py api")
    
    # Test 2: Check imports
    print("\n2. Testing imports...")
    try:
        from agents.root_agent_api import root_agent
        print(f"   ✓ Root agent loaded: {root_agent.name}")
    except Exception as e:
        print(f"   ✗ Import error: {e}")
    
    try:
        from tools.fiscal_tools_api import ALL_TOOLS
        print(f"   ✓ Tools loaded: {len(ALL_TOOLS)} tools")
    except Exception as e:
        print(f"   ✗ Tools import error: {e}")
    
    # Test 3: Test entity search (requires running API)
    print("\n3. Testing entity search...")
    try:
        from utils.api_client import FiscalDataClient
        client = FiscalDataClient()
        result = client.search_entities("Skokie")
        if result.get("status") == "success":
            print(f"   ✓ Found {result.get('count')} entities")
            for entity in result.get("entities", [])[:3]:
                print(f"      - {entity.get('UnitName')} ({entity.get('EntityType')})")
        else:
            print(f"   ✗ Search failed: {result.get('error_message')}")
    except Exception as e:
        print(f"   ✗ Test failed: {e}")
    
    print("\n" + "=" * 60)
    print("Tests complete!")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Run the Illinois Fiscal Data System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run.py api       # Start Flask API only
    python run.py agent     # Start ADK agent only  
    python run.py both      # Start both (API in background)
    python run.py test      # Run tests
        """
    )
    
    parser.add_argument(
        "command",
        choices=["api", "agent", "both", "test"],
        help="Command to run"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port for Flask API (default: 5000)"
    )
    
    args = parser.parse_args()
    
    if args.command == "api":
        run_api(args.port)
    elif args.command == "agent":
        run_agent()
    elif args.command == "both":
        run_both()
    elif args.command == "test":
        run_tests()


if __name__ == "__main__":
    main()
