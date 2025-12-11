"""
ADK Agent Tools - API-Based Implementation

These tools call the Fiscal Data REST API instead of accessing BigQuery directly.
This enables the 3-layer architecture described in the integration document:
    1. Data Layer: Flask API (fiscal_data_api.py)
    2. Application Layer: These tools + ADK Agent
    3. AI Layer: Gemini model via ADK

Benefits:
    - Decoupled data access from AI logic
    - Can switch between BigQuery and MS Access without changing agent code
    - API can be deployed independently and scaled separately
    - Multiple agents/applications can share the same API

Usage:
    # In your ADK agent definition:
    from tools.fiscal_tools_api import ALL_TOOLS
    
    agent = Agent(
        name="fiscal_agent",
        tools=ALL_TOOLS,
        ...
    )
"""

from typing import Optional, Dict, Any, List
from google.adk.tools.tool_context import ToolContext
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.api_client import FiscalDataClient


# =============================================================================
# API CLIENT SINGLETON
# =============================================================================

_api_client: Optional[FiscalDataClient] = None


def get_api_client() -> FiscalDataClient:
    """Get or create the API client singleton."""
    global _api_client
    if _api_client is None:
        api_url = os.environ.get('FISCAL_API_URL', 'http://localhost:5000')
        _api_client = FiscalDataClient(base_url=api_url)
    return _api_client


# =============================================================================
# CATEGORY MAPPINGS (for enhancing API responses)
# =============================================================================

REVENUE_CATEGORIES = {
    "201t": "Property Taxes",
    "202t": "Personal Property Replacement Tax",
    "203t": "Sales Tax",
    "204t": "Other Taxes",
    "215t": "Intergovernmental Revenue",
    "225t": "Charges for Services",
}

EXPENDITURE_CATEGORIES = {
    "251t": "General Government",
    "252t": "Public Safety",
    "253t": "Highways and Streets",
    "256t": "Culture and Recreation",
    "271t": "Debt Service - Principal",
}

FISCAL_HEALTH_THRESHOLDS = {
    "fund_balance_ratio": {"excellent": 0.25, "good": 0.15, "fair": 0.08},
    "operating_margin": {"excellent": 0.05, "good": 0.0, "fair": -0.05},
    "pension_funded_ratio": {"excellent": 0.80, "good": 0.60, "fair": 0.40},
    "debt_per_capita": {"low": 1000, "moderate": 2500, "high": 5000},
}


# =============================================================================
# ENTITY LOOKUP TOOLS
# =============================================================================

def search_government_entity(
    search_term: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Search for Illinois local government entities by name.
    
    Use this tool when the user mentions a city, village, township, district, 
    or other local government by name and you need to find its unique code
    for further queries.
    
    Args:
        search_term: The name or partial name to search for (e.g., "Springfield", 
                    "Naperville", "Chicago Fire"). Can also search by county name.
        tool_context: ADK tool context for state access
                    
    Returns:
        dict: Contains 'status' ('success' or 'error') and either:
              - 'entities': List of matching entities with Code, UnitName, EntityType, County
              - 'error_message': Description of the error
    """
    print(f"--- Tool: search_government_entity (API) called with: {search_term} ---")
    
    if not search_term or len(search_term) < 2:
        return {
            "status": "error",
            "error_message": "Please provide at least 2 characters to search."
        }
    
    client = get_api_client()
    result = client.search_entities(search_term, limit=10)
    
    if result.get("status") == "success":
        # Store results in state for reference
        tool_context.state["last_search_term"] = search_term
        tool_context.state["last_search_results"] = result.get("entities", [])
    
    return result


def get_entity_details(
    entity_code: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Get comprehensive details about a specific government entity.
    
    Use this tool after you have an entity code (from search_government_entity)
    to get full information about the entity including population, property values,
    employees, and contact information.
    
    Args:
        entity_code: The unique entity code in format XXX/YYY/ZZ 
                    (e.g., "016/020/32" for Village of Skokie)
        tool_context: ADK tool context for state access
                    
    Returns:
        dict: Contains entity details including name, type, county, population,
              EAV, employees, home rule status, and CEO/CFO information
    """
    print(f"--- Tool: get_entity_details (API) called for code: {entity_code} ---")
    
    client = get_api_client()
    result = client.get_entity_details(entity_code)
    
    if result.get("status") == "success":
        entity = result.get("entity", {})
        # Store current entity in state for follow-up questions
        tool_context.state["current_entity_code"] = entity_code
        tool_context.state["current_entity_name"] = entity.get("UnitName")
        tool_context.state["current_entity"] = entity
    
    return result


# =============================================================================
# FINANCIAL DATA TOOLS
# =============================================================================

def get_revenue_data(
    entity_code: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Get revenue breakdown for a government entity.
    
    Returns revenue data organized by category (property tax, sales tax, 
    intergovernmental, charges for services, etc.) and by fund type.
    
    Args:
        entity_code: The unique entity code (e.g., "016/020/32")
        tool_context: ADK tool context for state access
        
    Returns:
        dict: Contains total revenue and breakdown by category.
    """
    print(f"--- Tool: get_revenue_data (API) called for: {entity_code} ---")
    
    client = get_api_client()
    result = client.get_entity_revenues(entity_code)
    
    if result.get("status") == "success":
        # Enhance categories with full names if not already present
        for cat in result.get("by_category", []):
            if "CategoryName" not in cat:
                cat_code = cat.get("Category", "")
                cat["CategoryName"] = REVENUE_CATEGORIES.get(cat_code, cat_code)
    
    return result


def get_expenditure_data(
    entity_code: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Get expenditure breakdown for a government entity.
    
    Returns expenditure data organized by function (general government, 
    public safety, streets, culture/recreation, debt service, etc.).
    
    Args:
        entity_code: The unique entity code (e.g., "016/020/32")
        tool_context: ADK tool context for state access
        
    Returns:
        dict: Contains total expenditure and breakdown by category.
    """
    print(f"--- Tool: get_expenditure_data (API) called for: {entity_code} ---")
    
    client = get_api_client()
    result = client.get_entity_expenditures(entity_code)
    
    if result.get("status") == "success":
        # Enhance categories with full names
        for cat in result.get("by_category", []):
            if "CategoryName" not in cat:
                cat_code = cat.get("Category", "")
                cat["CategoryName"] = EXPENDITURE_CATEGORIES.get(cat_code, cat_code)
    
    return result


def get_debt_data(
    entity_code: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Get debt and indebtedness information for a government entity.
    
    Returns breakdown of debt including long-term and short-term debt.
    
    Args:
        entity_code: The unique entity code
        tool_context: ADK tool context for state access
        
    Returns:
        dict: Total debt and breakdown by debt type.
    """
    print(f"--- Tool: get_debt_data (API) called for: {entity_code} ---")
    
    client = get_api_client()
    return client.get_entity_debt(entity_code)


def get_pension_data(
    entity_code: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Get pension and OPEB liability information for a government entity.
    
    Returns data for applicable pension systems:
    - IMRF: Illinois Municipal Retirement Fund
    - Police: Article 3 Police Pension Fund
    - Fire: Article 4 Firefighter Pension Fund
    
    Args:
        entity_code: The unique entity code
        tool_context: ADK tool context for state access
        
    Returns:
        dict: Pension data by system including liability, assets, and funded ratio
    """
    print(f"--- Tool: get_pension_data (API) called for: {entity_code} ---")
    
    client = get_api_client()
    result = client.get_entity_pensions(entity_code)
    
    if result.get("status") == "success":
        result["funded_ratio_thresholds"] = FISCAL_HEALTH_THRESHOLDS["pension_funded_ratio"]
    
    return result


# =============================================================================
# FISCAL HEALTH ANALYSIS
# =============================================================================

def calculate_fiscal_health_score(
    entity_code: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Calculate comprehensive fiscal health indicators for an entity.
    
    Computes key financial ratios and assigns ratings:
    - Operating Margin: (Revenue - Expenditure) / Revenue
    - Debt Per Capita: Total Debt / Population
    - Pension Funded Ratio: Plan Assets / Total Pension Liability
    
    Args:
        entity_code: The unique entity code
        tool_context: ADK tool context for state access
        
    Returns:
        dict: Calculated metrics with values and ratings
    """
    print(f"--- Tool: calculate_fiscal_health_score (API) called for: {entity_code} ---")
    
    client = get_api_client()
    
    # Fetch all required data via API
    entity_result = client.get_entity_details(entity_code)
    revenues_result = client.get_entity_revenues(entity_code)
    expenditures_result = client.get_entity_expenditures(entity_code)
    debt_result = client.get_entity_debt(entity_code)
    pensions_result = client.get_entity_pensions(entity_code)
    
    if entity_result.get("status") != "success":
        return entity_result
    
    entity = entity_result.get("entity", {})
    total_revenue = revenues_result.get("total_revenue", 0) or 0
    total_expenditure = expenditures_result.get("total_expenditure", 0) or 0
    total_debt = debt_result.get("total_debt", 0) or 0
    population = entity.get("Population", 0) or 0
    
    metrics = {}
    
    # Operating Margin
    if total_revenue > 0:
        operating_margin = (total_revenue - total_expenditure) / total_revenue
        metrics["operating_margin"] = {
            "value": round(operating_margin * 100, 2),
            "unit": "percent",
            "rating": _rate_metric(operating_margin, FISCAL_HEALTH_THRESHOLDS["operating_margin"])
        }
    
    # Debt Per Capita
    if population > 0:
        debt_per_capita = total_debt / population
        metrics["debt_per_capita"] = {
            "value": round(debt_per_capita, 2),
            "unit": "dollars",
            "rating": _rate_debt_per_capita(debt_per_capita)
        }
    
    # Pension Funded Ratio
    pension_systems = pensions_result.get("pension_systems", {})
    if pension_systems:
        lowest_funded = 100
        for system, data in pension_systems.items():
            funded_ratio = data.get("funded_ratio", 0) or 0
            if 0 < funded_ratio < lowest_funded:
                lowest_funded = funded_ratio
        
        if lowest_funded < 100:
            metrics["pension_funded_ratio"] = {
                "value": round(lowest_funded, 2),
                "unit": "percent",
                "rating": _rate_metric(lowest_funded / 100, FISCAL_HEALTH_THRESHOLDS["pension_funded_ratio"])
            }
    
    # Store in state
    tool_context.state["last_fiscal_health"] = metrics
    
    return {
        "status": "success",
        "entity_code": entity_code,
        "entity_name": entity.get("UnitName"),
        "metrics": metrics,
        "raw_values": {
            "total_revenue": total_revenue,
            "total_expenditure": total_expenditure,
            "total_debt": total_debt,
            "population": population
        }
    }


def _rate_metric(value: float, thresholds: Dict[str, float]) -> str:
    """Rate a metric based on thresholds."""
    if value >= thresholds.get("excellent", float('inf')):
        return "Excellent"
    elif value >= thresholds.get("good", float('inf')):
        return "Good"
    elif value >= thresholds.get("fair", float('inf')):
        return "Fair"
    else:
        return "Poor"


def _rate_debt_per_capita(value: float) -> str:
    """Rate debt per capita."""
    thresholds = FISCAL_HEALTH_THRESHOLDS["debt_per_capita"]
    if value <= thresholds["low"]:
        return "Low"
    elif value <= thresholds["moderate"]:
        return "Moderate"
    elif value <= thresholds["high"]:
        return "High"
    else:
        return "Very High"


# =============================================================================
# COMPARISON TOOLS
# =============================================================================

def compare_entities(
    entity_codes: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Compare financial metrics across multiple entities.
    
    Args:
        entity_codes: Comma-separated list of entity codes
        tool_context: ADK tool context for state access
        
    Returns:
        dict: Comparison table with metrics for each entity
    """
    print(f"--- Tool: compare_entities (API) called for: {entity_codes} ---")
    
    codes = [code.strip() for code in entity_codes.split(",")]
    
    if len(codes) < 2:
        return {
            "status": "error",
            "error_message": "Please provide at least 2 entity codes separated by commas."
        }
    
    client = get_api_client()
    return client.compare_entities(codes)


def rank_entities(
    metric: str,
    tool_context: ToolContext,
    entity_type: Optional[str] = None,
    county: Optional[str] = None,
    top_or_bottom: str = "top",
    limit: int = 10
) -> Dict[str, Any]:
    """
    Rank entities by a specific metric.
    
    Args:
        metric: What to rank by - 'population', 'eav', or 'employees'
        tool_context: ADK tool context
        entity_type: Optional filter by entity type
        county: Optional filter by county
        top_or_bottom: 'top' for highest, 'bottom' for lowest
        limit: Number of results (default 10)
        
    Returns:
        dict: Ranked list of entities
    """
    print(f"--- Tool: rank_entities (API) called - metric: {metric} ---")
    
    client = get_api_client()
    return client.rank_entities(
        metric=metric,
        entity_type=entity_type,
        county=county,
        order=top_or_bottom,
        limit=min(limit, 50)
    )


# =============================================================================
# GEOGRAPHIC TOOLS
# =============================================================================

def get_county_entities(
    county: str,
    tool_context: ToolContext,
    entity_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get all government entities within a specific Illinois county.
    
    Args:
        county: Illinois county name (e.g., "Cook", "DuPage")
        tool_context: ADK tool context
        entity_type: Optional filter by entity type
        
    Returns:
        dict: List of entities in the county
    """
    print(f"--- Tool: get_county_entities (API) called for: {county} ---")
    
    client = get_api_client()
    return client.get_county_entities(county, entity_type)


def get_county_financial_summary(
    county: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Get aggregated financial summary for an entire county.
    
    Args:
        county: Illinois county name
        tool_context: ADK tool context
        
    Returns:
        dict: Aggregated statistics for the county
    """
    print(f"--- Tool: get_county_financial_summary (API) called for: {county} ---")
    
    client = get_api_client()
    return client.get_county_summary(county)


# =============================================================================
# EXPORT ALL TOOLS
# =============================================================================

ALL_TOOLS = [
    # Entity lookup
    search_government_entity,
    get_entity_details,
    
    # Financial data
    get_revenue_data,
    get_expenditure_data,
    get_debt_data,
    get_pension_data,
    
    # Analysis
    calculate_fiscal_health_score,
    
    # Comparison
    compare_entities,
    rank_entities,
    
    # Geographic
    get_county_entities,
    get_county_financial_summary,
]
