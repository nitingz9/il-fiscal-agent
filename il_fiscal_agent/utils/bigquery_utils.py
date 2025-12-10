"""
BigQuery utility functions for data access
"""
from google.cloud import bigquery
from typing import List, Dict, Any, Optional
import json

from config.settings import GCP_PROJECT_ID, TABLES

# Initialize BigQuery client (singleton pattern)
_bq_client = None

def get_bq_client() -> bigquery.Client:
    """Get or create BigQuery client singleton."""
    global _bq_client
    if _bq_client is None:
        _bq_client = bigquery.Client(project=GCP_PROJECT_ID)
    return _bq_client


def execute_query(query: str, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
    """
    Execute a BigQuery SQL query and return results as list of dictionaries.
    
    Args:
        query: SQL query string
        params: Optional query parameters for parameterized queries
        
    Returns:
        List of dictionaries, each representing a row
    """
    client = get_bq_client()
    
    job_config = bigquery.QueryJobConfig()
    if params:
        job_config.query_parameters = [
            bigquery.ScalarQueryParameter(name, "STRING", value)
            for name, value in params.items()
        ]
    
    try:
        query_job = client.query(query, job_config=job_config)
        results = query_job.result()
        
        # Convert to list of dicts
        rows = []
        for row in results:
            rows.append(dict(row.items()))
        
        return rows
    except Exception as e:
        return [{"error": str(e)}]


def search_entities(search_term: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for government entities by name using fuzzy matching.
    
    Args:
        search_term: Name or partial name to search for
        limit: Maximum number of results to return
        
    Returns:
        List of matching entities with their codes and details
    """
    query = f"""
    SELECT 
        Code,
        UnitName,
        Description as EntityType,
        County,
        CONCAT(UnitName, ', ', County, ' County (', Description, ')') as FullDescription
    FROM `{TABLES['unit_data']}`
    WHERE 
        LOWER(UnitName) LIKE LOWER(@search_pattern)
        OR LOWER(County) LIKE LOWER(@search_pattern)
    ORDER BY 
        CASE 
            WHEN LOWER(UnitName) = LOWER(@exact_term) THEN 0
            WHEN LOWER(UnitName) LIKE LOWER(@starts_with) THEN 1
            ELSE 2
        END,
        UnitName
    LIMIT {limit}
    """
    
    client = get_bq_client()
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("search_pattern", "STRING", f"%{search_term}%"),
            bigquery.ScalarQueryParameter("exact_term", "STRING", search_term),
            bigquery.ScalarQueryParameter("starts_with", "STRING", f"{search_term}%"),
        ]
    )
    
    try:
        results = client.query(query, job_config=job_config).result()
        return [dict(row.items()) for row in results]
    except Exception as e:
        return [{"error": str(e)}]


def get_entity_by_code(code: str) -> Optional[Dict[str, Any]]:
    """
    Get entity details by its unique code.
    
    Args:
        code: Entity code (format: XXX/YYY/ZZ)
        
    Returns:
        Entity details dictionary or None if not found
    """
    query = f"""
    SELECT 
        ud.Code,
        ud.UnitName,
        ud.Description as EntityType,
        ud.County,
        ud.CEOFName,
        ud.CEOLName,
        ud.CEOTitle,
        ud.CFOFName,
        ud.CFOLName,
        ud.CFOTitle,
        us.Pop as Population,
        us.EAV as EquitalizedAssessedValue,
        us.FULL_EMP as FullTimeEmployees,
        us.PART_EMP as PartTimeEmployees,
        us.HomeRule,
        us.Utilities,
        us.TIF_District,
        us.AccountingMethod,
        us.Debt as HasDebt,
        us.BondedDebt as HasBondedDebt
    FROM `{TABLES['unit_data']}` ud
    LEFT JOIN `{TABLES['unit_stats']}` us ON ud.Code = us.Code
    WHERE ud.Code = @code
    LIMIT 1
    """
    
    client = get_bq_client()
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("code", "STRING", code),
        ]
    )
    
    try:
        results = list(client.query(query, job_config=job_config).result())
        if results:
            return dict(results[0].items())
        return None
    except Exception as e:
        return {"error": str(e)}


def get_entity_revenues(code: str) -> Dict[str, Any]:
    """
    Get revenue breakdown for an entity.
    
    Args:
        code: Entity code
        
    Returns:
        Dictionary with revenue details by category and fund
    """
    query = f"""
    SELECT 
        Category,
        COALESCE(GN, 0) as GeneralFund,
        COALESCE(SR, 0) as SpecialRevenue,
        COALESCE(CP, 0) as CapitalProjects,
        COALESCE(DS, 0) as DebtService,
        COALESCE(EP, 0) as Enterprise,
        COALESCE(TS, 0) as Trust,
        COALESCE(FD, 0) as Fiduciary,
        COALESCE(DP, 0) as DebtPrincipal,
        (COALESCE(GN, 0) + COALESCE(SR, 0) + COALESCE(CP, 0) + 
         COALESCE(DS, 0) + COALESCE(EP, 0) + COALESCE(TS, 0) + 
         COALESCE(FD, 0) + COALESCE(DP, 0)) as Total
    FROM `{TABLES['revenues']}`
    WHERE Code = @code
    ORDER BY Category
    """
    
    client = get_bq_client()
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("code", "STRING", code),
        ]
    )
    
    try:
        results = list(client.query(query, job_config=job_config).result())
        revenues = [dict(row.items()) for row in results]
        
        # Calculate totals
        total_revenue = sum(r.get('Total', 0) or 0 for r in revenues)
        
        return {
            "code": code,
            "total_revenue": total_revenue,
            "by_category": revenues
        }
    except Exception as e:
        return {"error": str(e)}


def get_entity_expenditures(code: str) -> Dict[str, Any]:
    """
    Get expenditure breakdown for an entity.
    
    Args:
        code: Entity code
        
    Returns:
        Dictionary with expenditure details by category and fund
    """
    query = f"""
    SELECT 
        Category,
        COALESCE(GN, 0) as GeneralFund,
        COALESCE(SR, 0) as SpecialRevenue,
        COALESCE(CP, 0) as CapitalProjects,
        COALESCE(DS, 0) as DebtService,
        COALESCE(EP, 0) as Enterprise,
        COALESCE(TS, 0) as Trust,
        COALESCE(FD, 0) as Fiduciary,
        COALESCE(DP, 0) as DebtPrincipal,
        (COALESCE(GN, 0) + COALESCE(SR, 0) + COALESCE(CP, 0) + 
         COALESCE(DS, 0) + COALESCE(EP, 0) + COALESCE(TS, 0) + 
         COALESCE(FD, 0) + COALESCE(DP, 0)) as Total
    FROM `{TABLES['expenditures']}`
    WHERE Code = @code
    ORDER BY Category
    """
    
    client = get_bq_client()
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("code", "STRING", code),
        ]
    )
    
    try:
        results = list(client.query(query, job_config=job_config).result())
        expenditures = [dict(row.items()) for row in results]
        
        # Calculate totals
        total_expenditure = sum(e.get('Total', 0) or 0 for e in expenditures)
        
        return {
            "code": code,
            "total_expenditure": total_expenditure,
            "by_category": expenditures
        }
    except Exception as e:
        return {"error": str(e)}


def get_entity_fund_balances(code: str) -> Dict[str, Any]:
    """
    Get fund balance breakdown for an entity.
    
    Args:
        code: Entity code
        
    Returns:
        Dictionary with fund balance details
    """
    query = f"""
    SELECT 
        Category,
        COALESCE(GN, 0) as GeneralFund,
        COALESCE(SR, 0) as SpecialRevenue,
        COALESCE(CP, 0) as CapitalProjects,
        COALESCE(DS, 0) as DebtService,
        COALESCE(EP, 0) as Enterprise,
        COALESCE(TS, 0) as Trust,
        COALESCE(FD, 0) as Fiduciary,
        COALESCE(DP, 0) as DebtPrincipal
    FROM `{TABLES['fund_balances']}`
    WHERE Code = @code
    ORDER BY Category
    """
    
    client = get_bq_client()
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("code", "STRING", code),
        ]
    )
    
    try:
        results = list(client.query(query, job_config=job_config).result())
        return {
            "code": code,
            "fund_balances": [dict(row.items()) for row in results]
        }
    except Exception as e:
        return {"error": str(e)}


def get_entity_debt(code: str) -> Dict[str, Any]:
    """
    Get debt information for an entity.
    
    Args:
        code: Entity code
        
    Returns:
        Dictionary with debt details by type
    """
    query = f"""
    SELECT 
        -- GO Bonds
        COALESCE(a401, 0) + COALESCE(a400, 0) as GOBonds_Beginning,
        COALESCE(a407, 0) + COALESCE(a406, 0) as GOBonds_Additions,
        COALESCE(a413, 0) + COALESCE(a412, 0) as GOBonds_Retirements,
        
        -- Revenue Bonds
        COALESCE(b401, 0) + COALESCE(b400, 0) as RevenueBonds_Beginning,
        COALESCE(b407, 0) + COALESCE(b406, 0) as RevenueBonds_Additions,
        COALESCE(b413, 0) + COALESCE(b412, 0) as RevenueBonds_Retirements,
        
        -- Alt Revenue Bonds
        COALESCE(c401, 0) + COALESCE(c400, 0) as AltRevenueBonds_Beginning,
        COALESCE(c407, 0) + COALESCE(c406, 0) as AltRevenueBonds_Additions,
        COALESCE(c413, 0) + COALESCE(c412, 0) as AltRevenueBonds_Retirements,
        
        -- Contractual
        COALESCE(d401, 0) + COALESCE(d400, 0) as Contractual_Beginning,
        COALESCE(d407, 0) + COALESCE(d406, 0) as Contractual_Additions,
        COALESCE(d413, 0) + COALESCE(d412, 0) as Contractual_Retirements,
        
        -- Other Debt
        COALESCE(e401, 0) + COALESCE(e400, 0) as OtherDebt_Beginning,
        COALESCE(e407, 0) + COALESCE(e406, 0) as OtherDebt_Additions,
        COALESCE(e413, 0) + COALESCE(e412, 0) as OtherDebt_Retirements,
        
        -- Totals
        COALESCE(t404, 0) as TotalDebt_Ending_LongTerm,
        COALESCE(t410, 0) as TotalDebt_Ending_ShortTerm
        
    FROM `{TABLES['indebtedness']}`
    WHERE Code = @code
    """
    
    client = get_bq_client()
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("code", "STRING", code),
        ]
    )
    
    try:
        results = list(client.query(query, job_config=job_config).result())
        if results:
            row = dict(results[0].items())
            
            total_debt = (row.get('TotalDebt_Ending_LongTerm', 0) or 0) + \
                        (row.get('TotalDebt_Ending_ShortTerm', 0) or 0)
            
            return {
                "code": code,
                "total_debt": total_debt,
                "details": row
            }
        return {"code": code, "total_debt": 0, "details": {}}
    except Exception as e:
        return {"error": str(e)}


def get_entity_pensions(code: str) -> Dict[str, Any]:
    """
    Get pension information for an entity.
    
    Args:
        code: Entity code
        
    Returns:
        Dictionary with pension details by system
    """
    query = f"""
    SELECT 
        -- IMRF (most recent year - _3 suffix)
        IMRF_t500_3 as IMRF_MeasurementDate,
        IMRF_t501_3 as IMRF_TotalLiability,
        IMRF_t502_3 as IMRF_PlanAssets,
        IMRF_t503_3 as IMRF_NetPosition,
        IMRF_t504_3 as IMRF_FundedRatio,
        
        -- Police Pension
        Police_t500_3 as Police_MeasurementDate,
        Police_t501_3 as Police_TotalLiability,
        Police_t502_3 as Police_PlanAssets,
        Police_t503_3 as Police_NetPosition,
        Police_t504_3 as Police_FundedRatio,
        
        -- Fire Pension
        Fire_t500_3 as Fire_MeasurementDate,
        Fire_t501_3 as Fire_TotalLiability,
        Fire_t502_3 as Fire_PlanAssets,
        Fire_t503_3 as Fire_NetPosition,
        Fire_t504_3 as Fire_FundedRatio,
        
        -- OPEB
        OPEB_t500_3 as OPEB_MeasurementDate,
        OPEB_t501_3 as OPEB_TotalLiability,
        OPEB_t502_3 as OPEB_PlanAssets,
        OPEB_t503_3 as OPEB_NetPosition,
        OPEB_t504_3 as OPEB_FundedRatio
        
    FROM `{TABLES['pensions']}`
    WHERE Code = @code
    """
    
    client = get_bq_client()
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("code", "STRING", code),
        ]
    )
    
    try:
        results = list(client.query(query, job_config=job_config).result())
        if results:
            row = dict(results[0].items())
            
            # Structure the pension data
            pensions = {}
            for system in ['IMRF', 'Police', 'Fire', 'OPEB']:
                liability = row.get(f'{system}_TotalLiability') or 0
                if liability > 0:
                    pensions[system] = {
                        "measurement_date": row.get(f'{system}_MeasurementDate'),
                        "total_liability": liability,
                        "plan_assets": row.get(f'{system}_PlanAssets') or 0,
                        "net_position": row.get(f'{system}_NetPosition') or 0,
                        "funded_ratio": row.get(f'{system}_FundedRatio') or 0
                    }
            
            return {
                "code": code,
                "pension_systems": pensions
            }
        return {"code": code, "pension_systems": {}}
    except Exception as e:
        return {"error": str(e)}


def get_entities_by_county(county: str, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get all entities in a specific county.
    
    Args:
        county: County name
        entity_type: Optional filter by entity type (e.g., 'City', 'Village')
        
    Returns:
        List of entities in the county
    """
    type_filter = ""
    if entity_type:
        type_filter = "AND LOWER(ud.Description) = LOWER(@entity_type)"
    
    query = f"""
    SELECT 
        ud.Code,
        ud.UnitName,
        ud.Description as EntityType,
        us.Pop as Population,
        us.EAV as EquitalizedAssessedValue
    FROM `{TABLES['unit_data']}` ud
    LEFT JOIN `{TABLES['unit_stats']}` us ON ud.Code = us.Code
    WHERE LOWER(ud.County) = LOWER(@county)
    {type_filter}
    ORDER BY us.Pop DESC NULLS LAST
    """
    
    client = get_bq_client()
    params = [bigquery.ScalarQueryParameter("county", "STRING", county)]
    if entity_type:
        params.append(bigquery.ScalarQueryParameter("entity_type", "STRING", entity_type))
    
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    
    try:
        results = client.query(query, job_config=job_config).result()
        return [dict(row.items()) for row in results]
    except Exception as e:
        return [{"error": str(e)}]


def get_peer_entities(
    code: str, 
    population_range_pct: float = 0.25,
    same_type: bool = True,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get peer entities for comparison (similar size, same type).
    
    Args:
        code: Entity code to find peers for
        population_range_pct: Population range as percentage (0.25 = ±25%)
        same_type: Whether to filter to same entity type
        limit: Maximum number of peers to return
        
    Returns:
        List of peer entities
    """
    type_filter = ""
    if same_type:
        type_filter = "AND ud.Description = target.Description"
    
    query = f"""
    WITH target AS (
        SELECT 
            ud.Code,
            ud.Description,
            us.Pop as Population
        FROM `{TABLES['unit_data']}` ud
        LEFT JOIN `{TABLES['unit_stats']}` us ON ud.Code = us.Code
        WHERE ud.Code = @code
    )
    SELECT 
        ud.Code,
        ud.UnitName,
        ud.Description as EntityType,
        ud.County,
        us.Pop as Population,
        us.EAV as EquitalizedAssessedValue,
        ABS(us.Pop - target.Population) as PopulationDifference
    FROM `{TABLES['unit_data']}` ud
    LEFT JOIN `{TABLES['unit_stats']}` us ON ud.Code = us.Code
    CROSS JOIN target
    WHERE 
        ud.Code != @code
        AND us.Pop IS NOT NULL
        AND us.Pop BETWEEN target.Population * (1 - @range_pct) AND target.Population * (1 + @range_pct)
        {type_filter}
    ORDER BY PopulationDifference
    LIMIT {limit}
    """
    
    client = get_bq_client()
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("code", "STRING", code),
            bigquery.ScalarQueryParameter("range_pct", "FLOAT64", population_range_pct),
        ]
    )
    
    try:
        results = client.query(query, job_config=job_config).result()
        return [dict(row.items()) for row in results]
    except Exception as e:
        return [{"error": str(e)}]


def rank_entities_by_metric(
    metric: str,
    entity_type: Optional[str] = None,
    county: Optional[str] = None,
    order: str = "DESC",
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Rank entities by a specific metric.
    
    Args:
        metric: Metric to rank by (population, eav, revenue, expenditure, debt)
        entity_type: Optional filter by entity type
        county: Optional filter by county
        order: ASC or DESC
        limit: Number of results
        
    Returns:
        Ranked list of entities
    """
    # Build metric expression based on requested metric
    metric_expressions = {
        "population": "us.Pop",
        "eav": "us.EAV",
        "employees": "COALESCE(us.FULL_EMP, 0) + COALESCE(us.PART_EMP, 0)",
    }
    
    if metric.lower() not in metric_expressions:
        return [{"error": f"Unknown metric: {metric}. Available: {list(metric_expressions.keys())}"}]
    
    metric_expr = metric_expressions[metric.lower()]
    
    # Build filters
    filters = ["1=1"]
    params = []
    
    if entity_type:
        filters.append("LOWER(ud.Description) = LOWER(@entity_type)")
        params.append(bigquery.ScalarQueryParameter("entity_type", "STRING", entity_type))
    
    if county:
        filters.append("LOWER(ud.County) = LOWER(@county)")
        params.append(bigquery.ScalarQueryParameter("county", "STRING", county))
    
    where_clause = " AND ".join(filters)
    order_dir = "DESC" if order.upper() == "DESC" else "ASC"
    
    query = f"""
    SELECT 
        ud.Code,
        ud.UnitName,
        ud.Description as EntityType,
        ud.County,
        {metric_expr} as MetricValue,
        RANK() OVER (ORDER BY {metric_expr} {order_dir}) as Rank
    FROM `{TABLES['unit_data']}` ud
    LEFT JOIN `{TABLES['unit_stats']}` us ON ud.Code = us.Code
    WHERE {where_clause}
        AND {metric_expr} IS NOT NULL
    ORDER BY {metric_expr} {order_dir}
    LIMIT {limit}
    """
    
    client = get_bq_client()
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    
    try:
        results = client.query(query, job_config=job_config).result()
        return [dict(row.items()) for row in results]
    except Exception as e:
        return [{"error": str(e)}]


def get_county_summary(county: str) -> Dict[str, Any]:
    """
    Get aggregated summary statistics for a county.
    
    Args:
        county: County name
        
    Returns:
        Dictionary with county-level aggregated statistics
    """
    query = f"""
    SELECT 
        ud.County,
        COUNT(DISTINCT ud.Code) as EntityCount,
        COUNT(DISTINCT ud.Description) as EntityTypeCount,
        SUM(us.Pop) as TotalPopulation,
        SUM(us.EAV) as TotalEAV,
        SUM(us.FULL_EMP) as TotalFullTimeEmployees,
        SUM(us.PART_EMP) as TotalPartTimeEmployees,
        COUNTIF(us.HomeRule = 'Y') as HomeRuleCount,
        COUNTIF(us.Debt = 'Y') as EntitiesWithDebt
    FROM `{TABLES['unit_data']}` ud
    LEFT JOIN `{TABLES['unit_stats']}` us ON ud.Code = us.Code
    WHERE LOWER(ud.County) = LOWER(@county)
    GROUP BY ud.County
    """
    
    client = get_bq_client()
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("county", "STRING", county),
        ]
    )
    
    try:
        results = list(client.query(query, job_config=job_config).result())
        if results:
            return dict(results[0].items())
        return {"error": f"County '{county}' not found"}
    except Exception as e:
        return {"error": str(e)}
