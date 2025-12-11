# Illinois Fiscal Agent: API-Based Architecture Deep Dive

## Table of Contents
1. [Complete System Flow](#complete-system-flow)
2. [Layer-by-Layer Breakdown](#layer-by-layer-breakdown)
3. [Agent and Sub-Agent Coordination](#agent-and-sub-agent-coordination)
4. [MS Access Connection Explained](#ms-access-connection-explained)
5. [Step-by-Step Query Walkthrough](#step-by-step-query-walkthrough)
6. [Data Flow Diagrams](#data-flow-diagrams)

---

## Complete System Flow

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER                                            │
│                 "What is the property tax revenue for Skokie?"              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ (1) Natural Language Query
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ADK WEB INTERFACE                                    │
│                        (http://localhost:8000)                              │
│                                                                              │
│  • Receives user input                                                       │
│  • Sends to ADK Runner                                                       │
│  • Displays agent responses                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ (2) Query forwarded to Agent
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ROOT AGENT (Orchestrator)                            │
│                        agents/root_agent_api.py                             │
│                                                                              │
│  Model: gemini-2.0-flash                                                    │
│  Role: Understands intent, coordinates tools/sub-agents                     │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ DECISION: "User wants revenue data for Skokie"                      │   │
│  │                                                                      │   │
│  │ Step 1: Need to find Skokie's entity code                           │   │
│  │         → Call search_government_entity("Skokie")                   │   │
│  │                                                                      │   │
│  │ Step 2: Get revenue data for that entity                            │   │
│  │         → Call get_revenue_data("016/020/32")                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ (3) Agent calls tools
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ADK TOOLS (API-Based)                                │
│                        tools/fiscal_tools_api.py                            │
│                                                                              │
│  These tools DON'T access the database directly!                            │
│  Instead, they make HTTP requests to the Flask API.                         │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ def search_government_entity(search_term, tool_context):            │   │
│  │     client = FiscalDataClient()  # HTTP client                      │   │
│  │     result = client.search_entities(search_term)  # HTTP GET        │   │
│  │     return result                                                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ (4) HTTP Request
                                      │ GET /api/v1/entities/search?q=Skokie
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         API CLIENT                                           │
│                        utils/api_client.py                                  │
│                                                                              │
│  Python class that wraps HTTP calls to the Flask API                        │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ class FiscalDataClient:                                              │   │
│  │     def search_entities(self, search_term):                         │   │
│  │         response = requests.get(                                     │   │
│  │             f"{self.base_url}/api/v1/entities/search",              │   │
│  │             params={"q": search_term}                                │   │
│  │         )                                                            │   │
│  │         return response.json()                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ (5) HTTP GET Request
                                      │ http://localhost:5000/api/v1/entities/search?q=Skokie
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FLASK REST API                                       │
│                        api/fiscal_data_api.py                               │
│                        (http://localhost:5000)                              │
│                                                                              │
│  This is the KEY ABSTRACTION LAYER!                                         │
│  It can connect to EITHER BigQuery OR MS Access                             │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ @app.route('/api/v1/entities/search')                               │   │
│  │ def search_entities():                                               │   │
│  │     search_term = request.args.get('q')                             │   │
│  │                                                                      │   │
│  │     if DATA_SOURCE == 'bigquery':                                   │   │
│  │         # Use BigQuery client                                        │   │
│  │         results = query_bigquery(search_term)                       │   │
│  │     else:  # DATA_SOURCE == 'access'                                │   │
│  │         # Use ODBC to query MS Access                               │   │
│  │         results = query_access(search_term)                         │   │
│  │                                                                      │   │
│  │     return jsonify(results)                                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                        ┌─────────────┴─────────────┐
                        │                           │
                        ▼                           ▼
┌─────────────────────────────────┐ ┌─────────────────────────────────┐
│      BIGQUERY (Cloud)           │ │      MS ACCESS (Local)          │
│                                 │ │                                 │
│  google-cloud-bigquery library  │ │  pyodbc + ODBC Driver           │
│                                 │ │                                 │
│  project-zion-454116            │ │  C:\path\to\data2024.accdb     │
│  .comp_financial_insights_2024  │ │                                 │
│                                 │ │  Connection String:             │
│  SQL Query:                     │ │  DRIVER={Microsoft Access       │
│  SELECT Code, UnitName...       │ │  Driver (*.mdb, *.accdb)};     │
│  FROM `project.dataset.table`   │ │  DBQ=C:\path\to\file.accdb     │
│  WHERE UnitName LIKE '%Skokie%' │ │                                 │
└─────────────────────────────────┘ └─────────────────────────────────┘
                        │                           │
                        └─────────────┬─────────────┘
                                      │
                                      │ (6) Query Results
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         JSON RESPONSE                                        │
│                                                                              │
│  {                                                                           │
│    "status": "success",                                                      │
│    "count": 1,                                                               │
│    "entities": [                                                             │
│      {                                                                       │
│        "Code": "016/020/32",                                                │
│        "UnitName": "Skokie",                                                │
│        "EntityType": "Village",                                             │
│        "County": "Cook"                                                     │
│      }                                                                       │
│    ]                                                                         │
│  }                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ (7) Response flows back up
                                      │
                                      ▼
                    (Back through API Client → Tool → Agent → User)
```

---

## Layer-by-Layer Breakdown

### LAYER 1: Data Layer (Flask REST API)

**File:** `api/fiscal_data_api.py`

**Purpose:** Provide a unified interface to the data, regardless of where it's stored.

```python
# The magic happens in the DataAccessLayer class

class DataAccessLayer:
    def __init__(self, source: str = 'bigquery'):
        self.source = source
        
        if source == 'bigquery':
            # Initialize BigQuery client
            from google.cloud import bigquery
            self._client = bigquery.Client(project=GCP_PROJECT_ID)
            
        elif source == 'access':
            # Initialize ODBC connection string for MS Access
            self.conn_string = (
                f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};"
                f"DBQ={ACCESS_DB_PATH};"
            )
    
    def execute_query(self, query, params=None):
        if self.source == 'bigquery':
            return self._execute_bigquery(query, params)
        else:
            return self._execute_access(query, params)
```

**Key Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Health check |
| `/api/v1/entities/search` | GET | Search entities by name |
| `/api/v1/entities/{code}` | GET | Get entity details |
| `/api/v1/entities/{code}/revenues` | GET | Get revenue data |
| `/api/v1/entities/{code}/expenditures` | GET | Get expenditure data |
| `/api/v1/entities/{code}/debt` | GET | Get debt data |
| `/api/v1/entities/{code}/pensions` | GET | Get pension data |
| `/api/v1/counties/{county}/entities` | GET | Get entities in county |
| `/api/v1/counties/{county}/summary` | GET | Get county summary |

---

### LAYER 2: Application Layer (API Client + Tools)

**Files:** `utils/api_client.py` + `tools/fiscal_tools_api.py`

**Purpose:** Translate ADK tool calls into HTTP requests.

```python
# utils/api_client.py - The HTTP Client

class FiscalDataClient:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self._session = requests.Session()
    
    def search_entities(self, search_term, limit=10):
        """Make HTTP GET to /api/v1/entities/search"""
        response = self._session.get(
            f"{self.base_url}/api/v1/entities/search",
            params={"q": search_term, "limit": limit}
        )
        return response.json()
    
    def get_entity_revenues(self, entity_code):
        """Make HTTP GET to /api/v1/entities/{code}/revenues"""
        response = self._session.get(
            f"{self.base_url}/api/v1/entities/{entity_code}/revenues"
        )
        return response.json()
```

```python
# tools/fiscal_tools_api.py - ADK Tools that use the client

def search_government_entity(search_term: str, tool_context: ToolContext) -> dict:
    """
    ADK Tool: Search for government entities.
    
    This tool is called by the Gemini model when it needs to find an entity.
    Instead of querying the database directly, it calls the REST API.
    """
    print(f"--- Tool: search_government_entity called with: {search_term} ---")
    
    # Get the API client
    client = get_api_client()  # Returns FiscalDataClient instance
    
    # Make HTTP request to Flask API
    result = client.search_entities(search_term, limit=10)
    
    # Store in state for follow-up questions
    if result.get("status") == "success":
        tool_context.state["last_search_results"] = result.get("entities", [])
    
    return result
```

---

### LAYER 3: AI Layer (ADK Agent)

**File:** `agents/root_agent_api.py`

**Purpose:** Understand user intent and orchestrate tool calls.

```python
root_agent = Agent(
    name="il_fiscal_data_agent",
    model="gemini-2.0-flash",
    
    instruction="""You are the Illinois Local Government Financial Data Assistant.
    
    YOUR CAPABILITIES:
    1. Entity Lookup: Find cities, villages, townships by name
    2. Financial Data: Revenue, expenditure, debt, pension details
    3. Comparisons: Compare entities, benchmark against peers
    4. Fiscal Health: Assess financial condition
    5. Geographic Analysis: Explore entities by county
    
    WORKFLOW:
    - When user asks about a specific entity, FIRST search for it
    - Use the entity code from search results for subsequent queries
    - Present data clearly with proper formatting
    """,
    
    # These are the API-based tools
    tools=[
        search_government_entity,    # Calls /api/v1/entities/search
        get_entity_details,          # Calls /api/v1/entities/{code}
        get_revenue_data,            # Calls /api/v1/entities/{code}/revenues
        get_expenditure_data,        # Calls /api/v1/entities/{code}/expenditures
        get_debt_data,               # Calls /api/v1/entities/{code}/debt
        get_pension_data,            # Calls /api/v1/entities/{code}/pensions
        calculate_fiscal_health_score,
        compare_entities,
        rank_entities,
        get_county_entities,
        get_county_financial_summary,
    ],
    
    # Safety callbacks
    before_model_callback=input_safety_guardrail,
    before_tool_callback=tool_usage_guardrail,
)
```

---

## Agent and Sub-Agent Coordination

### How Sub-Agents Work

In ADK, sub-agents are specialized agents that the root agent can delegate to. Each has its own:
- Model (can be different from root)
- Instruction set (specialized for its task)
- Tools (subset relevant to its task)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ROOT AGENT                                         │
│                      (il_fiscal_data_agent)                                 │
│                                                                              │
│  "I'm the orchestrator. I understand the user's intent and decide           │
│   which sub-agent or tool is best suited to handle it."                     │
│                                                                              │
│  Decision Logic:                                                             │
│  ├─ Greeting/Help → delegate to greeting_agent                              │
│  ├─ Find entity → use search_government_entity tool                         │
│  ├─ Financial data → use get_revenue_data, get_expenditure_data tools      │
│  ├─ Comparisons → use compare_entities, rank_entities tools                 │
│  └─ Geographic → use get_county_entities tool                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
        ┌───────────────────┐ ┌───────────────┐ ┌───────────────────┐
        │  greeting_agent   │ │  (Direct      │ │  (Other sub-      │
        │                   │ │   Tool Use)   │ │   agents if       │
        │  Handles:         │ │               │ │   needed)         │
        │  - "Hello"        │ │  Root agent   │ │                   │
        │  - "Help"         │ │  can call     │ │  Could add:       │
        │  - "Goodbye"      │ │  tools        │ │  - analysis_agent │
        │                   │ │  directly     │ │  - report_agent   │
        │  Tools:           │ │  without      │ │                   │
        │  - greet_user     │ │  delegating   │ │                   │
        │  - provide_help   │ │               │ │                   │
        │  - say_goodbye    │ │               │ │                   │
        └───────────────────┘ └───────────────┘ └───────────────────┘
```

### Original Multi-Agent Structure (Your Current Project)

In your original `sub_agents.py`, you have 6 specialized sub-agents:

```python
# Original structure with multiple sub-agents
SUB_AGENTS = [
    entity_lookup_agent,    # Specializes in finding entities
    fiscal_query_agent,     # Specializes in financial data
    comparison_agent,       # Specializes in comparisons
    fiscal_health_agent,    # Specializes in health analysis
    geographic_agent,       # Specializes in county-level queries
    greeting_agent,         # Handles conversation
]
```

### Simplified API-Based Structure

In the API-based version, I simplified to just one sub-agent (greeting) because:

1. **The tools are stateless** - They just make HTTP calls
2. **The root agent is capable** - Gemini can handle tool selection
3. **Less complexity** - Fewer moving parts to debug

But you CAN add back all sub-agents if you prefer that organization:

```python
# You can still use sub-agents with API-based tools

entity_lookup_agent = Agent(
    name="entity_lookup_agent",
    model="gemini-2.0-flash",
    description="Finds and identifies Illinois local government entities",
    instruction="You specialize in finding entities. Use search and details tools.",
    tools=[
        search_government_entity,  # API-based tool
        get_entity_details,        # API-based tool
    ],
)

fiscal_query_agent = Agent(
    name="fiscal_query_agent", 
    model="gemini-2.0-flash",
    description="Retrieves financial data for entities",
    instruction="You specialize in financial data queries.",
    tools=[
        get_revenue_data,      # API-based tool
        get_expenditure_data,  # API-based tool
        get_debt_data,         # API-based tool
        get_pension_data,      # API-based tool
    ],
)

# Then in root_agent:
root_agent = Agent(
    ...
    sub_agents=[
        entity_lookup_agent,
        fiscal_query_agent,
        greeting_agent,
    ],
)
```

---

## MS Access Connection Explained

### How pyodbc Connects to MS Access

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         YOUR WINDOWS SERVER                                  │
│                                                                              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐ │
│  │  Flask API      │    │  ODBC Driver    │    │  MS Access Database     │ │
│  │  (Python)       │───▶│  Manager        │───▶│  (data2024.accdb)       │ │
│  │                 │    │                 │    │                         │ │
│  │  Uses pyodbc    │    │  Microsoft      │    │  Tables:                │ │
│  │  library        │    │  Access Driver  │    │  - UnitData             │ │
│  │                 │    │  (ACE OLEDB)    │    │  - Revenues             │ │
│  └─────────────────┘    └─────────────────┘    │  - Expenditures         │ │
│                                                 │  - etc.                 │ │
│                                                 └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Step-by-Step MS Access Query Flow

```python
# In api/fiscal_data_api.py

import pyodbc

# 1. Define connection string
ACCESS_DRIVER = "{Microsoft Access Driver (*.mdb, *.accdb)}"
ACCESS_DB_PATH = "C:\\FiscalData\\data2024.accdb"

CONN_STRING = (
    f"DRIVER={ACCESS_DRIVER};"
    f"DBQ={ACCESS_DB_PATH};"
)

# 2. Function to execute queries
def query_access(sql_query):
    """Execute a query against MS Access database."""
    
    # Open connection
    connection = pyodbc.connect(CONN_STRING)
    cursor = connection.cursor()
    
    # Execute query
    cursor.execute(sql_query)
    
    # Get column names
    columns = [column[0] for column in cursor.description]
    
    # Fetch results as list of dictionaries
    results = []
    for row in cursor.fetchall():
        results.append(dict(zip(columns, row)))
    
    # Close connection
    connection.close()
    
    return results

# 3. Example: Search for Skokie
sql = """
    SELECT Code, UnitName, Description, County
    FROM UnitData
    WHERE UnitName LIKE '%Skokie%'
"""
results = query_access(sql)
# Returns: [{"Code": "016/020/32", "UnitName": "Skokie", ...}]
```

### Prerequisites for MS Access Connection

1. **Install ODBC Driver** on the server running the Flask API:
   - Download: "Microsoft Access Database Engine 2016 Redistributable"
   - Must match your Python architecture (32-bit or 64-bit)

2. **Install pyodbc**:
   ```bash
   pip install pyodbc
   ```

3. **Configure environment**:
   ```env
   DATA_SOURCE=access
   ACCESS_DRIVER={Microsoft Access Driver (*.mdb, *.accdb)}
   ACCESS_DB_PATH=C:\FiscalData\data2024.accdb
   ```

### SQL Syntax Differences

| Operation | BigQuery | MS Access |
|-----------|----------|-----------|
| String concat | `CONCAT(a, b)` | `a & b` |
| Case insensitive | `LOWER(x) LIKE LOWER(y)` | `x LIKE y` (default) |
| Limit results | `LIMIT 10` | `SELECT TOP 10` |
| Null handling | `COALESCE(x, 0)` | `IIF(x IS NULL, 0, x)` |
| Boolean | `TRUE/FALSE` | `Yes/No` or `-1/0` |

The Flask API handles these differences internally:

```python
@app.route('/api/v1/entities/search')
def search_entities():
    search_term = request.args.get('q')
    limit = request.args.get('limit', 10)
    
    if DATA_SOURCE == 'bigquery':
        # BigQuery SQL
        query = f"""
            SELECT Code, UnitName, Description as EntityType, County
            FROM `{PROJECT}.{DATASET}.UnitData`
            WHERE LOWER(UnitName) LIKE LOWER(@search_pattern)
            LIMIT {limit}
        """
    else:
        # MS Access SQL
        query = f"""
            SELECT TOP {limit} Code, UnitName, Description as EntityType, County
            FROM UnitData
            WHERE UnitName LIKE '%{search_term}%'
        """
    
    # Execute and return results
    results = dal.execute_query(query)
    return jsonify({"status": "success", "entities": results})
```

---

## Step-by-Step Query Walkthrough

### Example: "What is the property tax revenue for Skokie?"

```
TIME    COMPONENT               ACTION
─────────────────────────────────────────────────────────────────────────────
T+0ms   User                    Types: "What is the property tax revenue for Skokie?"
        │
T+10ms  ADK Web UI              Sends query to ADK Runner
        │
T+20ms  ADK Runner              Passes query to root_agent
        │
T+30ms  Root Agent              Gemini model processes query
        │                       Thought: "User wants property tax revenue for Skokie.
        │                                I need to:
        │                                1. Find Skokie's entity code
        │                                2. Get revenue data for that entity"
        │
T+50ms  Root Agent              Decides to call: search_government_entity("Skokie")
        │
T+60ms  Tool: search_           Receives call from agent
        government_entity       Creates FiscalDataClient instance
        │
T+70ms  API Client              Makes HTTP request:
        │                       GET http://localhost:5000/api/v1/entities/search?q=Skokie
        │
T+80ms  Flask API               Receives request at /api/v1/entities/search
        │                       Checks DATA_SOURCE environment variable
        │
        ├─── IF BigQuery ───────────────────────────────────────────────────
        │    T+90ms   BigQuery Client    Executes:
        │                                SELECT Code, UnitName, Description, County
        │                                FROM `project.dataset.UnitData`
        │                                WHERE LOWER(UnitName) LIKE '%skokie%'
        │    T+200ms  BigQuery           Returns results
        │
        └─── IF MS Access ──────────────────────────────────────────────────
             T+90ms   pyodbc             Opens ODBC connection
                                         Executes:
                                         SELECT TOP 10 Code, UnitName, Description, County
                                         FROM UnitData
                                         WHERE UnitName LIKE '%Skokie%'
             T+150ms  MS Access          Returns results
        │
T+210ms Flask API               Returns JSON:
        │                       {
        │                         "status": "success",
        │                         "count": 1,
        │                         "entities": [{
        │                           "Code": "016/020/32",
        │                           "UnitName": "Skokie",
        │                           "EntityType": "Village",
        │                           "County": "Cook"
        │                         }]
        │                       }
        │
T+220ms API Client              Receives JSON response
        │
T+230ms Tool                    Stores entity in tool_context.state
        │                       Returns result to agent
        │
T+240ms Root Agent              Receives search results
        │                       Thought: "Found Skokie with code 016/020/32.
        │                                Now I need to get revenue data."
        │
T+250ms Root Agent              Decides to call: get_revenue_data("016/020/32")
        │
T+260ms Tool: get_revenue_data  Makes HTTP request:
        │                       GET http://localhost:5000/api/v1/entities/016/020/32/revenues
        │
T+270ms Flask API               Queries revenue data from database
        │
T+400ms Flask API               Returns JSON with revenue breakdown:
        │                       {
        │                         "status": "success",
        │                         "total_revenue": 180000000,
        │                         "by_category": [
        │                           {"Category": "201t", "CategoryName": "Property Taxes",
        │                            "GeneralFund": 45000000, "Total": 45000000},
        │                           ...
        │                         ]
        │                       }
        │
T+410ms Tool                    Enhances data with category names
        │                       Returns to agent
        │
T+420ms Root Agent              Receives revenue data
        │                       Thought: "I have all the data. Property tax (201t) is $45M.
        │                                Let me format a nice response."
        │
T+500ms Root Agent              Generates response:
        │                       "The Village of Skokie's property tax revenue is $45,000,000.
        │                        This represents about 25% of their total revenue of $180,000,000.
        │                        Property taxes are their largest single revenue source."
        │
T+510ms ADK Runner              Sends response to ADK Web UI
        │
T+520ms ADK Web UI              Displays response to user
        │
T+520ms User                    Sees the answer!
```

---

## Data Flow Diagrams

### Comparison: Direct BigQuery vs API-Based

```
DIRECT BIGQUERY (Original):
─────────────────────────────────────────────────────────────────────────────

User ──▶ ADK Agent ──▶ fiscal_tools.py ──▶ bigquery_utils.py ──▶ BigQuery
                            │                     │
                            │                     └── from google.cloud import bigquery
                            │                         client.query(sql)
                            │
                            └── Tool directly imports and uses BigQuery client


API-BASED (New):
─────────────────────────────────────────────────────────────────────────────

User ──▶ ADK Agent ──▶ fiscal_tools_api.py ──▶ api_client.py ──▶ Flask API ──┬──▶ BigQuery
                            │                      │               │          │
                            │                      │               │          └──▶ MS Access
                            │                      │               │
                            │                      │               └── Abstracts data source
                            │                      │
                            │                      └── requests.get(url)
                            │                          HTTP calls only
                            │
                            └── Tool doesn't know about databases
                                Only knows about HTTP endpoints
```

### Complete Request/Response Cycle

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  User   │    │   ADK   │    │  Tool   │    │  Flask  │    │Database │
│         │    │  Agent  │    │         │    │   API   │    │         │
└────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘
     │              │              │              │              │
     │  Question    │              │              │              │
     │─────────────▶│              │              │              │
     │              │              │              │              │
     │              │ Tool Call    │              │              │
     │              │─────────────▶│              │              │
     │              │              │              │              │
     │              │              │ HTTP GET     │              │
     │              │              │─────────────▶│              │
     │              │              │              │              │
     │              │              │              │ SQL Query    │
     │              │              │              │─────────────▶│
     │              │              │              │              │
     │              │              │              │ Result Set   │
     │              │              │              │◀─────────────│
     │              │              │              │              │
     │              │              │ JSON Response│              │
     │              │              │◀─────────────│              │
     │              │              │              │              │
     │              │ Tool Result  │              │              │
     │              │◀─────────────│              │              │
     │              │              │              │              │
     │  Answer      │              │              │              │
     │◀─────────────│              │              │              │
     │              │              │              │              │
```

---

## Summary

### Key Takeaways

1. **The Flask API is the bridge** between your ADK agent and your data, whether that data is in BigQuery or MS Access.

2. **Tools don't touch databases** - They only make HTTP requests. This means you can change your database without touching your agent code.

3. **Sub-agents are optional** - The root agent can call tools directly. Sub-agents help organize complex agents but add complexity.

4. **MS Access works via ODBC** - The pyodbc library + Microsoft Access ODBC driver enables Python to query Access databases.

5. **The architecture is flexible** - You can run everything on one machine, or deploy the API and agent separately.

### When to Use Which Approach

| Scenario | Recommendation |
|----------|----------------|
| Quick prototyping | Direct BigQuery (simpler) |
| Need MS Access support | API-based (required) |
| Multiple applications need data | API-based (share the API) |
| Production deployment | API-based (better separation) |
| Just learning ADK | Direct BigQuery (fewer components) |
