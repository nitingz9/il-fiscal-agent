"""
Tools for the Illinois Local Government Financial Data Agent

These tools provide the agent with specific capabilities to query and analyze
financial data from Illinois local governments.
"""
from typing import Optional, Dict, Any, List
from google.adk.tools.tool_context import ToolContext

# Import utility functions
import sys
sys.path.append('/home/claude/il_fiscal_agent')

from utils.bigquery_utils import (
    search_entities,
    get_entity_by_code,
    get_entity_revenues,
    get_entity_expenditures,
    get_entity_fund_balances,
    get_entity_debt,
    get_entity_pensions,
    get_entities_by_county,
    get_peer_entities,
    rank_entities_by_metric,
    get_county_summary
)
from config.settings import (
    FUND_TYPES,
    REVENUE_CATEGORIES,
    EXPENDITURE_CATEGORIES,
    ENTITY_TYPES,
    FISCAL_HEALTH_THRESHOLDS
)


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
    print(f"--- Tool: search_government_entity called with: {search_term} ---")
    
    if not search_term or len(search_term) < 2:
        return {
            "status": "error",
            "error_message": "Please provide at least 2 characters to search."
        }
    
    results = search_entities(search_term, limit=10)
    
    if results and "error" in results[0]:
        return {
            "status": "error",
            "error_message": results[0]["error"]
        }
    
    if not results:
        return {
            "status": "not_found",
            "message": f"No entities found matching '{search_term}'. Try a different spelling or search term."
        }
    
    # Store the last search results in state for reference
    tool_context.state["last_search_term"] = search_term
    tool_context.state["last_search_results"] = results
    
    return {
        "status": "success",
        "count": len(results),
        "entities": results
    }


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
    print(f"--- Tool: get_entity_details called for code: {entity_code} ---")
    
    result = get_entity_by_code(entity_code)
    
    if result is None:
        return {
            "status": "error",
            "error_message": f"Entity with code '{entity_code}' not found."
        }
    
    if "error" in result:
        return {
            "status": "error",
            "error_message": result["error"]
        }
    
    # Store current entity in state for follow-up questions
    tool_context.state["current_entity_code"] = entity_code
    tool_context.state["current_entity_name"] = result.get("UnitName")
    tool_context.state["current_entity"] = result
    
    return {
        "status": "success",
        "entity": result
    }


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
    intergovernmental, charges for services, etc.) and by fund type 
    (General Fund, Special Revenue, Enterprise, etc.).
    
    Args:
        entity_code: The unique entity code (e.g., "016/020/32")
        tool_context: ADK tool context for state access
        
    Returns:
        dict: Contains total revenue and breakdown by category showing amounts
              in each fund type. Category codes like '201t' = Property Taxes.
    """
    print(f"--- Tool: get_revenue_data called for: {entity_code} ---")
    
    result = get_entity_revenues(entity_code)
    
    if "error" in result:
        return {
            "status": "error",
            "error_message": result["error"]
        }
    
    # Enhance with category names
    enhanced_categories = []
    for cat in result.get("by_category", []):
        cat_code = cat.get("Category", "")
        cat["CategoryName"] = REVENUE_CATEGORIES.get(cat_code, cat_code)
        enhanced_categories.append(cat)
    
    result["by_category"] = enhanced_categories
    result["status"] = "success"
    result["fund_type_legend"] = FUND_TYPES
    
    return result


def get_expenditure_data(
    entity_code: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Get expenditure breakdown for a government entity.
    
    Returns expenditure data organized by function (general government, 
    public safety, streets, culture/recreation, debt service, etc.) 
    and by fund type.
    
    Args:
        entity_code: The unique entity code (e.g., "016/020/32")
        tool_context: ADK tool context for state access
        
    Returns:
        dict: Contains total expenditure and breakdown by category.
              Category codes like '252t' = Public Safety.
    """
    print(f"--- Tool: get_expenditure_data called for: {entity_code} ---")
    
    result = get_entity_expenditures(entity_code)
    
    if "error" in result:
        return {
            "status": "error",
            "error_message": result["error"]
        }
    
    # Enhance with category names
    enhanced_categories = []
    for cat in result.get("by_category", []):
        cat_code = cat.get("Category", "")
        cat["CategoryName"] = EXPENDITURE_CATEGORIES.get(cat_code, cat_code)
        enhanced_categories.append(cat)
    
    result["by_category"] = enhanced_categories
    result["status"] = "success"
    result["fund_type_legend"] = FUND_TYPES
    
    return result


def get_fund_balance_data(
    entity_code: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Get fund balance information for a government entity.
    
    Fund balances are classified per GASB 54 standards:
    - Nonspendable (302t): Cannot be spent (inventory, prepaid items)
    - Restricted (303t): Constrained by external parties
    - Committed (304t): Constrained by government action
    - Assigned (305t): Intended for specific purposes
    - Unassigned (307t): Available for any purpose (key fiscal health indicator)
    
    Args:
        entity_code: The unique entity code
        tool_context: ADK tool context for state access
        
    Returns:
        dict: Fund balance amounts by classification and fund type
    """
    print(f"--- Tool: get_fund_balance_data called for: {entity_code} ---")
    
    result = get_entity_fund_balances(entity_code)
    
    if "error" in result:
        return {
            "status": "error",
            "error_message": result["error"]
        }
    
    # Add category descriptions
    balance_categories = {
        "302t": "Nonspendable",
        "303t": "Restricted",
        "304t": "Committed",
        "305t": "Assigned",
        "307t": "Unassigned",
        "308t": "Total Fund Balance"
    }
    
    for fb in result.get("fund_balances", []):
        cat_code = fb.get("Category", "")
        fb["CategoryName"] = balance_categories.get(cat_code, cat_code)
    
    result["status"] = "success"
    result["category_descriptions"] = balance_categories
    
    return result


def get_debt_data(
    entity_code: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Get debt and indebtedness information for a government entity.
    
    Returns breakdown of debt by type:
    - General Obligation (GO) Bonds: Backed by full taxing power
    - Revenue Bonds: Backed by specific revenue streams
    - Alternate Revenue Bonds: Hybrid GO/Revenue
    - Contractual Commitments: Leases, installment purchases
    - Other Long-term Debt: Notes, compensated absences
    
    Args:
        entity_code: The unique entity code
        tool_context: ADK tool context for state access
        
    Returns:
        dict: Total debt and breakdown by debt type with beginning balances,
              additions, and retirements
    """
    print(f"--- Tool: get_debt_data called for: {entity_code} ---")
    
    result = get_entity_debt(entity_code)
    
    if "error" in result:
        return {
            "status": "error",
            "error_message": result["error"]
        }
    
    result["status"] = "success"
    result["debt_type_descriptions"] = {
        "GOBonds": "General Obligation Bonds - backed by full faith and credit",
        "RevenueBonds": "Revenue Bonds - backed by specific revenue streams",
        "AltRevenueBonds": "Alternate Revenue Bonds - hybrid backing",
        "Contractual": "Contractual Commitments - leases, installment purchases",
        "OtherDebt": "Other Long-term Debt - notes, compensated absences"
    }
    
    return result


def get_pension_data(
    entity_code: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Get pension and OPEB liability information for a government entity.
    
    Returns data for applicable pension systems:
    - IMRF: Illinois Municipal Retirement Fund (most municipal employees)
    - Police: Article 3 Police Pension Fund (locally administered)
    - Fire: Article 4 Firefighter Pension Fund (locally administered)
    - OPEB: Other Post-Employment Benefits (retiree health insurance)
    
    Key metrics include:
    - Total Pension Liability: Present value of future benefits owed
    - Plan Assets: Assets available to pay benefits
    - Net Position: Liability minus assets (positive = underfunded)
    - Funded Ratio: Assets / Liability as percentage
    
    Args:
        entity_code: The unique entity code
        tool_context: ADK tool context for state access
        
    Returns:
        dict: Pension data by system including liability, assets, and funded ratio
    """
    print(f"--- Tool: get_pension_data called for: {entity_code} ---")
    
    result = get_entity_pensions(entity_code)
    
    if "error" in result:
        return {
            "status": "error",
            "error_message": result["error"]
        }
    
    result["status"] = "success"
    result["funded_ratio_thresholds"] = FISCAL_HEALTH_THRESHOLDS["pension_funded_ratio"]
    
    return result


# =============================================================================
# FISCAL HEALTH ANALYSIS TOOLS
# =============================================================================

def calculate_fiscal_health_score(
    entity_code: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Calculate comprehensive fiscal health indicators for an entity.
    
    Computes key financial ratios and assigns ratings:
    - Operating Margin: (Revenue - Expenditure) / Revenue
    - Fund Balance Ratio: Unassigned Fund Balance / Total Expenditure
    - Debt Per Capita: Total Debt / Population
    - Pension Funded Ratio: Plan Assets / Total Pension Liability
    
    Each indicator is rated as Excellent, Good, Fair, or Poor/Critical.
    
    Args:
        entity_code: The unique entity code
        tool_context: ADK tool context for state access
        
    Returns:
        dict: Calculated metrics with values and ratings
    """
    print(f"--- Tool: calculate_fiscal_health_score called for: {entity_code} ---")
    
    # Get all necessary data
    entity = get_entity_by_code(entity_code)
    revenues = get_entity_revenues(entity_code)
    expenditures = get_entity_expenditures(entity_code)
    fund_balances = get_entity_fund_balances(entity_code)
    debt = get_entity_debt(entity_code)
    pensions = get_entity_pensions(entity_code)
    
    if entity is None:
        return {
            "status": "error",
            "error_message": f"Entity with code '{entity_code}' not found."
        }
    
    # Calculate metrics
    total_revenue = revenues.get("total_revenue", 0) or 0
    total_expenditure = expenditures.get("total_expenditure", 0) or 0
    total_debt = debt.get("total_debt", 0) or 0
    population = entity.get("Population", 0) or 0
    
    # Get unassigned fund balance (307t category, GN column)
    unassigned_balance = 0
    for fb in fund_balances.get("fund_balances", []):
        if fb.get("Category") == "307t":
            unassigned_balance = fb.get("GeneralFund", 0) or 0
            break
    
    # Calculate ratios
    metrics = {}
    
    # Operating Margin
    if total_revenue > 0:
        operating_margin = (total_revenue - total_expenditure) / total_revenue
        metrics["operating_margin"] = {
            "value": round(operating_margin * 100, 2),
            "unit": "percent",
            "rating": _rate_metric(operating_margin, FISCAL_HEALTH_THRESHOLDS["operating_margin"])
        }
    
    # Fund Balance Ratio
    if total_expenditure > 0:
        fund_balance_ratio = unassigned_balance / total_expenditure
        metrics["fund_balance_ratio"] = {
            "value": round(fund_balance_ratio * 100, 2),
            "unit": "percent",
            "rating": _rate_metric(fund_balance_ratio, FISCAL_HEALTH_THRESHOLDS["fund_balance_ratio"])
        }
    
    # Debt Per Capita
    if population > 0:
        debt_per_capita = total_debt / population
        metrics["debt_per_capita"] = {
            "value": round(debt_per_capita, 2),
            "unit": "dollars",
            "rating": _rate_debt_per_capita(debt_per_capita)
        }
    
    # Pension Funded Ratio (use lowest if multiple systems)
    pension_systems = pensions.get("pension_systems", {})
    if pension_systems:
        lowest_funded = 100
        for system, data in pension_systems.items():
            funded_ratio = data.get("funded_ratio", 0) or 0
            if funded_ratio > 0 and funded_ratio < lowest_funded:
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
            "unassigned_fund_balance": unassigned_balance,
            "total_debt": total_debt,
            "population": population
        }
    }


def _rate_metric(value: float, thresholds: Dict[str, float]) -> str:
    """Helper to rate a metric based on thresholds."""
    if value >= thresholds.get("excellent", float('inf')):
        return "Excellent"
    elif value >= thresholds.get("good", float('inf')):
        return "Good"
    elif value >= thresholds.get("fair", float('inf')):
        return "Fair"
    else:
        return "Poor"


def _rate_debt_per_capita(value: float) -> str:
    """Helper to rate debt per capita."""
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
# COMPARISON AND BENCHMARKING TOOLS
# =============================================================================

def compare_entities(
    entity_codes: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Compare financial metrics across multiple entities.
    
    Provides side-by-side comparison of key metrics for the specified entities,
    including population, EAV, total revenue, total expenditure, and per-capita values.
    
    Args:
        entity_codes: Comma-separated list of entity codes to compare
                     (e.g., "016/020/32,016/030/30,016/040/32")
        tool_context: ADK tool context for state access
        
    Returns:
        dict: Comparison table with metrics for each entity
    """
    print(f"--- Tool: compare_entities called for: {entity_codes} ---")
    
    codes = [code.strip() for code in entity_codes.split(",")]
    
    if len(codes) < 2:
        return {
            "status": "error",
            "error_message": "Please provide at least 2 entity codes separated by commas."
        }
    
    if len(codes) > 10:
        return {
            "status": "error",
            "error_message": "Maximum 10 entities can be compared at once."
        }
    
    comparisons = []
    for code in codes:
        entity = get_entity_by_code(code)
        revenues = get_entity_revenues(code)
        expenditures = get_entity_expenditures(code)
        
        if entity:
            population = entity.get("Population", 0) or 0
            total_rev = revenues.get("total_revenue", 0) or 0
            total_exp = expenditures.get("total_expenditure", 0) or 0
            
            comparisons.append({
                "code": code,
                "name": entity.get("UnitName"),
                "type": entity.get("EntityType"),
                "county": entity.get("County"),
                "population": population,
                "eav": entity.get("EquitalizedAssessedValue", 0) or 0,
                "total_revenue": total_rev,
                "total_expenditure": total_exp,
                "revenue_per_capita": round(total_rev / population, 2) if population > 0 else 0,
                "expenditure_per_capita": round(total_exp / population, 2) if population > 0 else 0
            })
    
    return {
        "status": "success",
        "entity_count": len(comparisons),
        "comparison": comparisons
    }


def find_peer_entities(
    entity_code: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Find peer entities for benchmarking comparison.
    
    Identifies similar entities based on:
    - Same entity type (e.g., all Villages)
    - Similar population size (±25%)
    
    Useful for answering questions like "How does my city compare to similar cities?"
    
    Args:
        entity_code: The entity code to find peers for
        tool_context: ADK tool context for state access
        
    Returns:
        dict: List of peer entities with basic statistics
    """
    print(f"--- Tool: find_peer_entities called for: {entity_code} ---")
    
    peers = get_peer_entities(entity_code, population_range_pct=0.25, same_type=True, limit=10)
    
    if peers and "error" in peers[0]:
        return {
            "status": "error",
            "error_message": peers[0]["error"]
        }
    
    # Store peers in state
    tool_context.state["current_entity_peers"] = peers
    
    return {
        "status": "success",
        "peer_count": len(peers),
        "peers": peers
    }


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
    
    Creates rankings to answer questions like:
    - "What are the largest cities in Illinois?"
    - "Which fire districts have the most employees?"
    - "Top 10 villages in Cook County by EAV"
    
    Args:
        metric: What to rank by - 'population', 'eav', or 'employees'
        tool_context: ADK tool context for state access
        entity_type: Optional filter - 'City', 'Village', 'Township', 
                    'Fire Protection District', etc.
        county: Optional filter by county name
        top_or_bottom: 'top' for highest values, 'bottom' for lowest
        limit: Number of results (default 10, max 50)
        
    Returns:
        dict: Ranked list of entities with their metric values
    """
    print(f"--- Tool: rank_entities called - metric: {metric}, type: {entity_type}, county: {county} ---")
    
    order = "DESC" if top_or_bottom.lower() == "top" else "ASC"
    limit = min(limit, 50)  # Cap at 50
    
    results = rank_entities_by_metric(
        metric=metric,
        entity_type=entity_type,
        county=county,
        order=order,
        limit=limit
    )
    
    if results and "error" in results[0]:
        return {
            "status": "error",
            "error_message": results[0]["error"]
        }
    
    return {
        "status": "success",
        "metric": metric,
        "order": top_or_bottom,
        "filters": {
            "entity_type": entity_type,
            "county": county
        },
        "count": len(results),
        "rankings": results
    }


# =============================================================================
# GEOGRAPHIC ANALYSIS TOOLS
# =============================================================================

def get_county_entities(
    county: str,
    tool_context: ToolContext,
    entity_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get all government entities within a specific Illinois county.
    
    Use this to answer questions like:
    - "What governments are in Cook County?"
    - "List all fire districts in Lake County"
    - "Show me cities in DuPage County"
    
    Args:
        county: Illinois county name (e.g., "Cook", "DuPage", "Lake")
        tool_context: ADK tool context for state access
        entity_type: Optional filter - 'City', 'Village', 'Township',
                    'Fire Protection District', etc.
        
    Returns:
        dict: List of entities in the county with basic info
    """
    print(f"--- Tool: get_county_entities called for: {county}, type: {entity_type} ---")
    
    entities = get_entities_by_county(county, entity_type)
    
    if entities and "error" in entities[0]:
        return {
            "status": "error",
            "error_message": entities[0]["error"]
        }
    
    return {
        "status": "success",
        "county": county,
        "entity_type_filter": entity_type,
        "count": len(entities),
        "entities": entities
    }


def get_county_financial_summary(
    county: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Get aggregated financial summary for an entire county.
    
    Provides county-level statistics including:
    - Total number of government entities
    - Types of entities present
    - Aggregate population served
    - Total EAV (property values)
    - Employment statistics
    - Home rule entity count
    
    Args:
        county: Illinois county name
        tool_context: ADK tool context for state access
        
    Returns:
        dict: Aggregated statistics for the county
    """
    print(f"--- Tool: get_county_financial_summary called for: {county} ---")
    
    summary = get_county_summary(county)
    
    if "error" in summary:
        return {
            "status": "error",
            "error_message": summary["error"]
        }
    
    return {
        "status": "success",
        "summary": summary
    }


# =============================================================================
# EXPORT ALL TOOLS
# =============================================================================

# List of all tools for the agent
ALL_TOOLS = [
    # Entity lookup
    search_government_entity,
    get_entity_details,
    
    # Financial data
    get_revenue_data,
    get_expenditure_data,
    get_fund_balance_data,
    get_debt_data,
    get_pension_data,
    
    # Analysis
    calculate_fiscal_health_score,
    
    # Comparison
    compare_entities,
    find_peer_entities,
    rank_entities,
    
    # Geographic
    get_county_entities,
    get_county_financial_summary,
]
