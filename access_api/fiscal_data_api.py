"""
Illinois Local Government Financial Data API

This Flask API serves as the Data Layer in a 3-tier architecture:
1. Data Layer (THIS FILE) - Exposes data via REST endpoints
2. Application Layer - Web App or ADK Agent that consumes this API
3. AI Layer - ADK Agent with tools that call this API

PRIMARY DATA SOURCE: MS Access via ODBC
FALLBACK: BigQuery (for cloud deployments)

Usage:
    python fiscal_data_api.py
    
    # Or with Flask CLI:
    flask --app fiscal_data_api run --host=0.0.0.0 --port=5000

Prerequisites for MS Access:
    1. Install Microsoft Access Database Engine (32-bit or 64-bit matching Python)
    2. pip install pyodbc
    3. Set ACCESS_DB_PATH environment variable to your .accdb file path
"""

from flask import Flask, jsonify, request
from functools import wraps
import os
import sys
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from decimal import Decimal

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# =============================================================================
# CONFIGURATION
# =============================================================================

# Data source: 'access' (PRIMARY) or 'bigquery' (FALLBACK)
# DEFAULT IS NOW 'access' - MS Access is the primary data source
DATA_SOURCE = os.environ.get('DATA_SOURCE', 'access')

# MS Access Configuration (PRIMARY)
ACCESS_DRIVER = os.environ.get('ACCESS_DRIVER', '{Microsoft Access Driver (*.mdb, *.accdb)}')
ACCESS_DB_PATH = os.environ.get('ACCESS_DB_PATH', r'C:\FiscalData\data2024.accdb')

# BigQuery Configuration (FALLBACK)
GCP_PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT', 'project-zion-454116')
BQ_DATASET = os.environ.get('BQ_DATASET', 'comp_financial_insights_2024')


# =============================================================================
# DATA TYPE SERIALIZATION HELPER
# =============================================================================

def serialize_value(value):
    """Convert database values to JSON-serializable types."""
    if value is None:
        return None
    elif isinstance(value, Decimal):
        return float(value)
    elif isinstance(value, (datetime, date)):
        return value.isoformat()
    elif isinstance(value, bytes):
        return value.decode('utf-8', errors='ignore')
    else:
        return value


def serialize_row(row_dict: Dict) -> Dict:
    """Serialize all values in a row dictionary."""
    return {key: serialize_value(value) for key, value in row_dict.items()}


# =============================================================================
# DATA ACCESS LAYER - MS ACCESS PRIMARY
# =============================================================================

class DataAccessLayer:
    """
    Abstract data access layer.
    
    PRIMARY: MS Access via ODBC (pyodbc)
    FALLBACK: BigQuery (google-cloud-bigquery)
    """
    
    def __init__(self, source: str = 'access'):
        self.source = source
        self._client = None
        self._connection_tested = False
        
        print(f"[DataAccessLayer] Initializing with source: {source}")
        
        if source == 'access':
            self._init_access()
        elif source == 'bigquery':
            self._init_bigquery()
        else:
            raise ValueError(f"Unknown data source: {source}. Use 'access' or 'bigquery'.")
    
    def _init_access(self):
        """Initialize MS Access ODBC connection string."""
        self.conn_string = (
            f"DRIVER={ACCESS_DRIVER};"
            f"DBQ={ACCESS_DB_PATH};"
        )
        
        # Table names for MS Access (no schema prefix needed)
        self.tables = {
            'unit_data': 'UnitData',
            'unit_stats': 'UnitStats',
            'revenues': 'Revenues',
            'expenditures': 'Expenditures',
            'fund_balances': 'FundBalances',
            'indebtedness': 'Indebtedness',
            'pensions': 'Pensions',
            'assets': 'Assets',
            'audits': 'Audits',
            'afr_notes': 'AFRNotes',
            'capital_outlay': 'CapitalOutlay',
            'component': 'Component',
            'funds_used': 'FundsUsed',
            'governmental_entities': 'GovernmentalEntities',
            'reporting': 'Reporting',
        }
        
        print(f"[MS Access] Connection string configured")
        print(f"[MS Access] Database path: {ACCESS_DB_PATH}")
        
        # Test the connection
        self._test_access_connection()
    
    def _test_access_connection(self):
        """Test the MS Access connection on startup."""
        try:
            import pyodbc
            cnxn = pyodbc.connect(self.conn_string, timeout=5)
            cursor = cnxn.cursor()
            
            # Test query - get table count
            cursor.execute("SELECT COUNT(*) FROM UnitData")
            count = cursor.fetchone()[0]
            
            cnxn.close()
            self._connection_tested = True
            print(f"[MS Access] ✓ Connection successful! UnitData has {count:,} rows")
            
        except Exception as e:
            print(f"[MS Access] ✗ Connection FAILED: {e}")
            print(f"[MS Access] Make sure:")
            print(f"  1. The file exists: {ACCESS_DB_PATH}")
            print(f"  2. ODBC driver is installed: {ACCESS_DRIVER}")
            print(f"  3. Python architecture matches driver (32-bit vs 64-bit)")
            self._connection_tested = False
    
    def _init_bigquery(self):
        """Initialize BigQuery client."""
        from google.cloud import bigquery
        self._client = bigquery.Client(project=GCP_PROJECT_ID)
        
        # Table names for BigQuery (with full project.dataset.table format)
        self.tables = {
            'unit_data': f"{GCP_PROJECT_ID}.{BQ_DATASET}.UnitData",
            'unit_stats': f"{GCP_PROJECT_ID}.{BQ_DATASET}.UnitStats",
            'revenues': f"{GCP_PROJECT_ID}.{BQ_DATASET}.Revenues",
            'expenditures': f"{GCP_PROJECT_ID}.{BQ_DATASET}.Expenditures",
            'fund_balances': f"{GCP_PROJECT_ID}.{BQ_DATASET}.FundBalances",
            'indebtedness': f"{GCP_PROJECT_ID}.{BQ_DATASET}.Indebtedness",
            'pensions': f"{GCP_PROJECT_ID}.{BQ_DATASET}.Pensions",
        }
        
        print(f"[BigQuery] Client initialized for project: {GCP_PROJECT_ID}")
    
    def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """Execute query and return results as list of dictionaries."""
        if self.source == 'access':
            return self._execute_access(query, params)
        else:
            return self._execute_bigquery(query, params)
    
    def _execute_access(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """
        Execute MS Access query via ODBC.
        
        Note: MS Access SQL syntax differences from standard SQL:
        - Use TOP n instead of LIMIT n
        - Use IIF() instead of COALESCE() or CASE
        - Use & for string concatenation instead of CONCAT()
        - Use * for wildcard instead of %
        - Use ? for parameters instead of @name
        """
        import pyodbc
        
        try:
            # Open connection
            cnxn = pyodbc.connect(self.conn_string)
            cursor = cnxn.cursor()
            
            # Handle parameterized queries
            if params:
                # Convert named params (@name) to positional (?)
                param_values = []
                for key, value in params.items():
                    if f"@{key}" in query:
                        query = query.replace(f"@{key}", "?")
                        param_values.append(value)
                
                cursor.execute(query, param_values)
            else:
                cursor.execute(query)
            
            # Check if query returns results (SELECT) or not (INSERT/UPDATE/DELETE)
            if cursor.description is None:
                cnxn.commit()
                cnxn.close()
                return [{"affected_rows": cursor.rowcount}]
            
            # Get column names
            columns = [column[0] for column in cursor.description]
            
            # Fetch all rows and convert to list of dicts
            rows = []
            for row in cursor.fetchall():
                row_dict = dict(zip(columns, row))
                # Serialize values for JSON compatibility
                rows.append(serialize_row(row_dict))
            
            cnxn.close()
            return rows
            
        except pyodbc.Error as e:
            error_msg = str(e)
            print(f"[MS Access] Query error: {error_msg}")
            print(f"[MS Access] Query was: {query[:200]}...")
            return [{"error": f"Database error: {error_msg}"}]
        except Exception as e:
            print(f"[MS Access] Unexpected error: {e}")
            return [{"error": str(e)}]
    
    def _execute_bigquery(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """Execute BigQuery query."""
        from google.cloud import bigquery
        
        job_config = bigquery.QueryJobConfig()
        if params:
            job_config.query_parameters = [
                bigquery.ScalarQueryParameter(name, "STRING", value)
                for name, value in params.items()
            ]
        
        try:
            results = self._client.query(query, job_config=job_config).result()
            return [serialize_row(dict(row.items())) for row in results]
        except Exception as e:
            print(f"[BigQuery] Query error: {e}")
            return [{"error": str(e)}]


# =============================================================================
# INITIALIZE DATA ACCESS LAYER
# =============================================================================

print("=" * 60)
print("Illinois Fiscal Data API - Initializing")
print("=" * 60)

dal = DataAccessLayer(source=DATA_SOURCE)

print("=" * 60)


# =============================================================================
# FLASK APPLICATION
# =============================================================================

app = Flask(__name__)


def handle_errors(f):
    """Decorator to handle errors consistently."""
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            print(f"[API Error] {e}")
            return jsonify({"status": "error", "error_message": str(e)}), 500
    return decorated


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "data_source": DATA_SOURCE,
        "database_path": ACCESS_DB_PATH if DATA_SOURCE == 'access' else f"{GCP_PROJECT_ID}.{BQ_DATASET}",
        "connection_tested": dal._connection_tested if DATA_SOURCE == 'access' else True,
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/v1/tables', methods=['GET'])
def list_tables():
    """List available tables."""
    return jsonify({
        "status": "success",
        "data_source": DATA_SOURCE,
        "tables": list(dal.tables.keys())
    })


# -----------------------------------------------------------------------------
# ENTITY ENDPOINTS
# -----------------------------------------------------------------------------

@app.route('/api/v1/entities/search', methods=['GET'])
@handle_errors
def search_entities():
    """
    Search for government entities by name.
    
    Query params:
        q: Search term (required)
        limit: Max results (default: 10)
    
    Example:
        GET /api/v1/entities/search?q=Skokie&limit=5
    """
    search_term = request.args.get('q', '')
    limit = request.args.get('limit', 10, type=int)
    
    if not search_term or len(search_term) < 2:
        return jsonify({
            "status": "error",
            "error_message": "Please provide at least 2 characters to search."
        }), 400
    
    if dal.source == 'access':
        # MS Access SQL syntax
        # Use LIKE with * wildcard (Access-style) or % (ANSI-style depending on mode)
        query = f"""
        SELECT TOP {limit}
            Code,
            UnitName,
            Description AS EntityType,
            County
        FROM {dal.tables['unit_data']}
        WHERE 
            UnitName LIKE '%{search_term}%'
            OR County LIKE '%{search_term}%'
        ORDER BY UnitName
        """
        entities = dal.execute_query(query)
    else:
        # BigQuery SQL syntax
        from google.cloud import bigquery
        
        query = f"""
        SELECT 
            Code,
            UnitName,
            Description as EntityType,
            County
        FROM `{dal.tables['unit_data']}`
        WHERE 
            LOWER(UnitName) LIKE LOWER(@search_pattern)
            OR LOWER(County) LIKE LOWER(@search_pattern)
        ORDER BY UnitName
        LIMIT {limit}
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("search_pattern", "STRING", f"%{search_term}%"),
            ]
        )
        results = dal._client.query(query, job_config=job_config).result()
        entities = [serialize_row(dict(row.items())) for row in results]
    
    # Check for errors
    if entities and "error" in entities[0]:
        return jsonify({
            "status": "error",
            "error_message": entities[0]["error"]
        }), 500
    
    if not entities:
        return jsonify({
            "status": "not_found",
            "message": f"No entities found matching '{search_term}'"
        })
    
    return jsonify({
        "status": "success",
        "count": len(entities),
        "entities": entities
    })


@app.route('/api/v1/entities/<path:code>', methods=['GET'])
@handle_errors
def get_entity(code: str):
    """
    Get details for a specific entity by code.
    
    Example:
        GET /api/v1/entities/016/020/32
    """
    if dal.source == 'access':
        # MS Access query
        query = f"""
        SELECT TOP 1
            ud.Code,
            ud.UnitName,
            ud.Description AS EntityType,
            ud.County,
            ud.CEOFName,
            ud.CEOLName,
            ud.CEOTitle,
            ud.CFOFName,
            ud.CFOLName,
            ud.CFOTitle,
            us.Pop AS Population,
            us.EAV AS EquitalizedAssessedValue,
            us.FULL_EMP AS FullTimeEmployees,
            us.PART_EMP AS PartTimeEmployees,
            us.HomeRule,
            us.Debt AS HasDebt,
            us.BondedDebt AS HasBondedDebt
        FROM {dal.tables['unit_data']} AS ud
        LEFT JOIN {dal.tables['unit_stats']} AS us ON ud.Code = us.Code
        WHERE ud.Code = '{code}'
        """
        results = dal.execute_query(query)
    else:
        # BigQuery query
        from google.cloud import bigquery
        
        query = f"""
        SELECT 
            ud.Code,
            ud.UnitName,
            ud.Description as EntityType,
            ud.County,
            ud.CEOFName,
            ud.CEOLName,
            ud.CEOTitle,
            us.Pop as Population,
            us.EAV as EquitalizedAssessedValue,
            us.FULL_EMP as FullTimeEmployees,
            us.PART_EMP as PartTimeEmployees,
            us.HomeRule,
            us.Debt as HasDebt
        FROM `{dal.tables['unit_data']}` ud
        LEFT JOIN `{dal.tables['unit_stats']}` us ON ud.Code = us.Code
        WHERE ud.Code = @code
        LIMIT 1
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("code", "STRING", code),
            ]
        )
        results = list(dal._client.query(query, job_config=job_config).result())
        results = [serialize_row(dict(row.items())) for row in results]
    
    if not results or (results and "error" in results[0]):
        error_msg = results[0].get("error") if results else "Not found"
        return jsonify({
            "status": "error",
            "error_message": f"Entity with code '{code}' not found. {error_msg}"
        }), 404
    
    return jsonify({
        "status": "success",
        "entity": results[0]
    })


# -----------------------------------------------------------------------------
# FINANCIAL DATA ENDPOINTS
# -----------------------------------------------------------------------------

@app.route('/api/v1/entities/<path:code>/revenues', methods=['GET'])
@handle_errors
def get_entity_revenues(code: str):
    """
    Get revenue breakdown for an entity.
    
    Example:
        GET /api/v1/entities/016/020/32/revenues
    """
    if dal.source == 'access':
        # MS Access - use IIF for null handling
        query = f"""
        SELECT 
            Category,
            IIF(GN IS NULL, 0, GN) AS GeneralFund,
            IIF(SR IS NULL, 0, SR) AS SpecialRevenue,
            IIF(CP IS NULL, 0, CP) AS CapitalProjects,
            IIF(DS IS NULL, 0, DS) AS DebtService,
            IIF(EP IS NULL, 0, EP) AS Enterprise,
            IIF(TS IS NULL, 0, TS) AS Trust,
            IIF(FD IS NULL, 0, FD) AS Fiduciary
        FROM {dal.tables['revenues']}
        WHERE Code = '{code}'
        ORDER BY Category
        """
        revenues = dal.execute_query(query)
    else:
        # BigQuery - use COALESCE
        from google.cloud import bigquery
        
        query = f"""
        SELECT 
            Category,
            COALESCE(GN, 0) as GeneralFund,
            COALESCE(SR, 0) as SpecialRevenue,
            COALESCE(CP, 0) as CapitalProjects,
            COALESCE(DS, 0) as DebtService,
            COALESCE(EP, 0) as Enterprise,
            COALESCE(TS, 0) as Trust,
            COALESCE(FD, 0) as Fiduciary
        FROM `{dal.tables['revenues']}`
        WHERE Code = @code
        ORDER BY Category
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("code", "STRING", code),
            ]
        )
        results = dal._client.query(query, job_config=job_config).result()
        revenues = [serialize_row(dict(row.items())) for row in results]
    
    # Check for errors
    if revenues and "error" in revenues[0]:
        return jsonify({
            "status": "error",
            "error_message": revenues[0]["error"]
        }), 500
    
    # Calculate totals and add category names
    category_names = {
        "201t": "Property Taxes",
        "202t": "Personal Property Replacement Tax",
        "203t": "Sales Tax",
        "204t": "Other Taxes",
        "205t": "Special Assessments",
        "211t": "Licenses and Permits",
        "212t": "Fines and Forfeitures",
        "213t": "Interest Earnings",
        "214t": "Rental Income",
        "215t": "Intergovernmental Revenue",
        "225t": "Charges for Services",
        "226t": "Contributions and Donations",
        "231t": "Bond/Loan Proceeds",
        "233t": "Interfund Transfers In",
        "234t": "Other Revenue",
    }
    
    total_revenue = 0
    for rev in revenues:
        # Calculate row total
        row_total = (
            (rev.get('GeneralFund') or 0) +
            (rev.get('SpecialRevenue') or 0) +
            (rev.get('CapitalProjects') or 0) +
            (rev.get('DebtService') or 0) +
            (rev.get('Enterprise') or 0) +
            (rev.get('Trust') or 0) +
            (rev.get('Fiduciary') or 0)
        )
        rev['Total'] = row_total
        total_revenue += row_total
        
        # Add category name
        cat = rev.get('Category', '')
        rev['CategoryName'] = category_names.get(cat, cat)
    
    return jsonify({
        "status": "success",
        "code": code,
        "total_revenue": total_revenue,
        "by_category": revenues
    })


@app.route('/api/v1/entities/<path:code>/expenditures', methods=['GET'])
@handle_errors
def get_entity_expenditures(code: str):
    """
    Get expenditure breakdown for an entity.
    
    Example:
        GET /api/v1/entities/016/020/32/expenditures
    """
    if dal.source == 'access':
        query = f"""
        SELECT 
            Category,
            IIF(GN IS NULL, 0, GN) AS GeneralFund,
            IIF(SR IS NULL, 0, SR) AS SpecialRevenue,
            IIF(CP IS NULL, 0, CP) AS CapitalProjects,
            IIF(DS IS NULL, 0, DS) AS DebtService,
            IIF(EP IS NULL, 0, EP) AS Enterprise,
            IIF(TS IS NULL, 0, TS) AS Trust,
            IIF(FD IS NULL, 0, FD) AS Fiduciary
        FROM {dal.tables['expenditures']}
        WHERE Code = '{code}'
        ORDER BY Category
        """
        expenditures = dal.execute_query(query)
    else:
        from google.cloud import bigquery
        
        query = f"""
        SELECT 
            Category,
            COALESCE(GN, 0) as GeneralFund,
            COALESCE(SR, 0) as SpecialRevenue,
            COALESCE(CP, 0) as CapitalProjects,
            COALESCE(DS, 0) as DebtService,
            COALESCE(EP, 0) as Enterprise,
            COALESCE(TS, 0) as Trust,
            COALESCE(FD, 0) as Fiduciary
        FROM `{dal.tables['expenditures']}`
        WHERE Code = @code
        ORDER BY Category
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("code", "STRING", code),
            ]
        )
        results = dal._client.query(query, job_config=job_config).result()
        expenditures = [serialize_row(dict(row.items())) for row in results]
    
    if expenditures and "error" in expenditures[0]:
        return jsonify({
            "status": "error",
            "error_message": expenditures[0]["error"]
        }), 500
    
    # Add category names
    category_names = {
        "251t": "General Government",
        "252t": "Public Safety",
        "253t": "Highways and Streets",
        "254t": "Sanitation",
        "255t": "Health and Welfare",
        "256t": "Culture and Recreation",
        "257t": "Conservation and Development",
        "258t": "Education",
        "259t": "Other Expenditures",
        "260t": "Capital Outlay",
        "271t": "Debt Service - Principal",
        "272t": "Debt Service - Interest",
        "275t": "Interfund Transfers Out",
    }
    
    total_expenditure = 0
    for exp in expenditures:
        row_total = (
            (exp.get('GeneralFund') or 0) +
            (exp.get('SpecialRevenue') or 0) +
            (exp.get('CapitalProjects') or 0) +
            (exp.get('DebtService') or 0) +
            (exp.get('Enterprise') or 0) +
            (exp.get('Trust') or 0) +
            (exp.get('Fiduciary') or 0)
        )
        exp['Total'] = row_total
        total_expenditure += row_total
        
        cat = exp.get('Category', '')
        exp['CategoryName'] = category_names.get(cat, cat)
    
    return jsonify({
        "status": "success",
        "code": code,
        "total_expenditure": total_expenditure,
        "by_category": expenditures
    })


@app.route('/api/v1/entities/<path:code>/debt', methods=['GET'])
@handle_errors
def get_entity_debt(code: str):
    """Get debt information for an entity."""
    if dal.source == 'access':
        query = f"""
        SELECT 
            IIF(t404 IS NULL, 0, t404) AS TotalDebt_LongTerm,
            IIF(t410 IS NULL, 0, t410) AS TotalDebt_ShortTerm,
            IIF(a401 IS NULL, 0, a401) AS GOBonds_Beginning,
            IIF(b401 IS NULL, 0, b401) AS RevenueBonds_Beginning,
            IIF(c401 IS NULL, 0, c401) AS AltRevenueBonds_Beginning,
            IIF(d401 IS NULL, 0, d401) AS Contractual_Beginning,
            IIF(e401 IS NULL, 0, e401) AS OtherDebt_Beginning
        FROM {dal.tables['indebtedness']}
        WHERE Code = '{code}'
        """
        results = dal.execute_query(query)
    else:
        from google.cloud import bigquery
        query = f"""
        SELECT 
            COALESCE(t404, 0) as TotalDebt_LongTerm,
            COALESCE(t410, 0) as TotalDebt_ShortTerm
        FROM `{dal.tables['indebtedness']}`
        WHERE Code = @code
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("code", "STRING", code)]
        )
        results = list(dal._client.query(query, job_config=job_config).result())
        results = [serialize_row(dict(row.items())) for row in results]
    
    if results and "error" in results[0]:
        return jsonify({"status": "error", "error_message": results[0]["error"]}), 500
    
    if results:
        row = results[0]
        total_debt = (row.get('TotalDebt_LongTerm') or 0) + (row.get('TotalDebt_ShortTerm') or 0)
    else:
        total_debt = 0
        row = {}
    
    return jsonify({"status": "success", "code": code, "total_debt": total_debt, "details": row})


@app.route('/api/v1/entities/<path:code>/pensions', methods=['GET'])
@handle_errors
def get_entity_pensions(code: str):
    """Get pension information for an entity."""
    if dal.source == 'access':
        query = f"""
        SELECT 
            IMRF_t501_3 AS IMRF_TotalLiability,
            IMRF_t502_3 AS IMRF_PlanAssets,
            IMRF_t504_3 AS IMRF_FundedRatio,
            Police_t501_3 AS Police_TotalLiability,
            Police_t502_3 AS Police_PlanAssets,
            Police_t504_3 AS Police_FundedRatio,
            Fire_t501_3 AS Fire_TotalLiability,
            Fire_t502_3 AS Fire_PlanAssets,
            Fire_t504_3 AS Fire_FundedRatio
        FROM {dal.tables['pensions']}
        WHERE Code = '{code}'
        """
        results = dal.execute_query(query)
    else:
        from google.cloud import bigquery
        query = f"""
        SELECT 
            IMRF_t501_3 as IMRF_TotalLiability,
            IMRF_t502_3 as IMRF_PlanAssets,
            IMRF_t504_3 as IMRF_FundedRatio,
            Police_t501_3 as Police_TotalLiability,
            Police_t502_3 as Police_PlanAssets,
            Police_t504_3 as Police_FundedRatio,
            Fire_t501_3 as Fire_TotalLiability,
            Fire_t502_3 as Fire_PlanAssets,
            Fire_t504_3 as Fire_FundedRatio
        FROM `{dal.tables['pensions']}`
        WHERE Code = @code
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("code", "STRING", code)]
        )
        results = list(dal._client.query(query, job_config=job_config).result())
        results = [serialize_row(dict(row.items())) for row in results]
    
    if results and "error" in results[0]:
        return jsonify({"status": "error", "error_message": results[0]["error"]}), 500
    
    pension_systems = {}
    if results:
        row = results[0]
        for system in ['IMRF', 'Police', 'Fire']:
            liability = row.get(f'{system}_TotalLiability') or 0
            if liability > 0:
                pension_systems[system] = {
                    "total_liability": liability,
                    "plan_assets": row.get(f'{system}_PlanAssets') or 0,
                    "funded_ratio": row.get(f'{system}_FundedRatio') or 0
                }
    
    return jsonify({"status": "success", "code": code, "pension_systems": pension_systems})


# -----------------------------------------------------------------------------
# GEOGRAPHIC ENDPOINTS
# -----------------------------------------------------------------------------

@app.route('/api/v1/counties/<county>/entities', methods=['GET'])
@handle_errors
def get_county_entities(county: str):
    """Get all entities in a county."""
    entity_type = request.args.get('entity_type')
    
    if dal.source == 'access':
        type_filter = f"AND ud.Description = '{entity_type}'" if entity_type else ""
        query = f"""
        SELECT 
            ud.Code, ud.UnitName, ud.Description AS EntityType,
            us.Pop AS Population, us.EAV AS EquitalizedAssessedValue
        FROM {dal.tables['unit_data']} AS ud
        LEFT JOIN {dal.tables['unit_stats']} AS us ON ud.Code = us.Code
        WHERE ud.County = '{county}' {type_filter}
        ORDER BY us.Pop DESC
        """
        entities = dal.execute_query(query)
    else:
        from google.cloud import bigquery
        type_filter = "AND LOWER(ud.Description) = LOWER(@entity_type)" if entity_type else ""
        params = [bigquery.ScalarQueryParameter("county", "STRING", county)]
        if entity_type:
            params.append(bigquery.ScalarQueryParameter("entity_type", "STRING", entity_type))
        query = f"""
        SELECT ud.Code, ud.UnitName, ud.Description as EntityType,
               us.Pop as Population, us.EAV as EquitalizedAssessedValue
        FROM `{dal.tables['unit_data']}` ud
        LEFT JOIN `{dal.tables['unit_stats']}` us ON ud.Code = us.Code
        WHERE LOWER(ud.County) = LOWER(@county) {type_filter}
        ORDER BY us.Pop DESC NULLS LAST
        """
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        results = dal._client.query(query, job_config=job_config).result()
        entities = [serialize_row(dict(row.items())) for row in results]
    
    if entities and "error" in entities[0]:
        return jsonify({"status": "error", "error_message": entities[0]["error"]}), 500
    
    return jsonify({
        "status": "success", "county": county,
        "entity_type_filter": entity_type, "count": len(entities), "entities": entities
    })


@app.route('/api/v1/counties/<county>/summary', methods=['GET'])
@handle_errors
def get_county_summary(county: str):
    """Get aggregated summary for a county."""
    if dal.source == 'access':
        query = f"""
        SELECT ud.County, COUNT(*) AS EntityCount,
               SUM(us.Pop) AS TotalPopulation, SUM(us.EAV) AS TotalEAV,
               SUM(us.FULL_EMP) AS TotalFullTimeEmployees
        FROM {dal.tables['unit_data']} AS ud
        LEFT JOIN {dal.tables['unit_stats']} AS us ON ud.Code = us.Code
        WHERE ud.County = '{county}'
        GROUP BY ud.County
        """
        results = dal.execute_query(query)
    else:
        from google.cloud import bigquery
        query = f"""
        SELECT ud.County, COUNT(DISTINCT ud.Code) as EntityCount,
               SUM(us.Pop) as TotalPopulation, SUM(us.EAV) as TotalEAV,
               SUM(us.FULL_EMP) as TotalFullTimeEmployees
        FROM `{dal.tables['unit_data']}` ud
        LEFT JOIN `{dal.tables['unit_stats']}` us ON ud.Code = us.Code
        WHERE LOWER(ud.County) = LOWER(@county)
        GROUP BY ud.County
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("county", "STRING", county)]
        )
        results = list(dal._client.query(query, job_config=job_config).result())
        results = [serialize_row(dict(row.items())) for row in results]
    
    if not results:
        return jsonify({"status": "error", "error_message": f"County '{county}' not found"}), 404
    
    return jsonify({"status": "success", "summary": results[0]})


# -----------------------------------------------------------------------------
# COMPARISON ENDPOINTS
# -----------------------------------------------------------------------------

@app.route('/api/v1/entities/compare', methods=['GET'])
@handle_errors
def compare_entities():
    """Compare multiple entities."""
    codes_str = request.args.get('codes', '')
    codes = [c.strip() for c in codes_str.split(',') if c.strip()]
    
    if len(codes) < 2:
        return jsonify({"status": "error", "error_message": "Provide at least 2 entity codes"}), 400
    
    comparisons = []
    for code in codes:
        if dal.source == 'access':
            query = f"""
            SELECT TOP 1 ud.Code, ud.UnitName, ud.Description AS EntityType, ud.County,
                   us.Pop AS Population, us.EAV AS EquitalizedAssessedValue
            FROM {dal.tables['unit_data']} AS ud
            LEFT JOIN {dal.tables['unit_stats']} AS us ON ud.Code = us.Code
            WHERE ud.Code = '{code}'
            """
            results = dal.execute_query(query)
        else:
            from google.cloud import bigquery
            query = f"""
            SELECT ud.Code, ud.UnitName, ud.Description as EntityType, ud.County,
                   us.Pop as Population, us.EAV as EquitalizedAssessedValue
            FROM `{dal.tables['unit_data']}` ud
            LEFT JOIN `{dal.tables['unit_stats']}` us ON ud.Code = us.Code
            WHERE ud.Code = @code
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("code", "STRING", code)]
            )
            results = list(dal._client.query(query, job_config=job_config).result())
            results = [serialize_row(dict(row.items())) for row in results]
        
        if results and "error" not in results[0]:
            comparisons.append(results[0])
    
    return jsonify({"status": "success", "entity_count": len(comparisons), "comparison": comparisons})


@app.route('/api/v1/entities/rank', methods=['GET'])
@handle_errors
def rank_entities():
    """Rank entities by a metric."""
    metric = request.args.get('metric', 'population')
    entity_type = request.args.get('entity_type')
    county = request.args.get('county')
    order = request.args.get('order', 'top')
    limit = request.args.get('limit', 10, type=int)
    
    metric_columns = {
        "population": "us.Pop",
        "eav": "us.EAV",
        "employees": "(IIF(us.FULL_EMP IS NULL, 0, us.FULL_EMP) + IIF(us.PART_EMP IS NULL, 0, us.PART_EMP))" if dal.source == 'access' else "COALESCE(us.FULL_EMP, 0) + COALESCE(us.PART_EMP, 0)",
    }
    
    if metric.lower() not in metric_columns:
        return jsonify({"status": "error", "error_message": f"Unknown metric: {metric}"}), 400
    
    metric_col = metric_columns[metric.lower()]
    order_dir = "DESC" if order.lower() == "top" else "ASC"
    
    if dal.source == 'access':
        filters = []
        if entity_type: filters.append(f"ud.Description = '{entity_type}'")
        if county: filters.append(f"ud.County = '{county}'")
        where_clause = " AND ".join(filters) if filters else "1=1"
        
        query = f"""
        SELECT TOP {limit} ud.Code, ud.UnitName, ud.Description AS EntityType,
               ud.County, {metric_col} AS MetricValue
        FROM {dal.tables['unit_data']} AS ud
        LEFT JOIN {dal.tables['unit_stats']} AS us ON ud.Code = us.Code
        WHERE {where_clause} AND {metric_col} IS NOT NULL
        ORDER BY {metric_col} {order_dir}
        """
        rankings = dal.execute_query(query)
        for i, r in enumerate(rankings): r['Rank'] = i + 1
    else:
        from google.cloud import bigquery
        filters, params = ["1=1"], []
        if entity_type:
            filters.append("LOWER(ud.Description) = LOWER(@entity_type)")
            params.append(bigquery.ScalarQueryParameter("entity_type", "STRING", entity_type))
        if county:
            filters.append("LOWER(ud.County) = LOWER(@county)")
            params.append(bigquery.ScalarQueryParameter("county", "STRING", county))
        
        query = f"""
        SELECT ud.Code, ud.UnitName, ud.Description as EntityType, ud.County,
               {metric_col} as MetricValue,
               RANK() OVER (ORDER BY {metric_col} {order_dir}) as Rank
        FROM `{dal.tables['unit_data']}` ud
        LEFT JOIN `{dal.tables['unit_stats']}` us ON ud.Code = us.Code
        WHERE {" AND ".join(filters)} AND {metric_col} IS NOT NULL
        ORDER BY {metric_col} {order_dir}
        LIMIT {limit}
        """
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        results = dal._client.query(query, job_config=job_config).result()
        rankings = [serialize_row(dict(row.items())) for row in results]
    
    return jsonify({
        "status": "success", "metric": metric, "order": order,
        "filters": {"entity_type": entity_type, "county": county},
        "count": len(rankings), "rankings": rankings
    })


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("Illinois Fiscal Data API - Starting Server")
    print("=" * 60)
    print(f"Data Source: {DATA_SOURCE.upper()} (PRIMARY)")
    
    if DATA_SOURCE == 'access':
        print(f"Database: {ACCESS_DB_PATH}")
        print(f"Driver: {ACCESS_DRIVER}")
    else:
        print(f"Project: {GCP_PROJECT_ID}")
        print(f"Dataset: {BQ_DATASET}")
    
    print("=" * 60)
    print("Server starting on http://0.0.0.0:5000")
    print("=" * 60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
