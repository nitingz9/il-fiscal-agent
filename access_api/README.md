# Illinois Fiscal Data Agent (API-Based Architecture)

This is an enhanced version of the Illinois Local Government Financial Data Agent that uses a **3-layer architecture** with a REST API between the data source and the AI agent.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          User Query                                      │
│         "What is the property tax revenue for Naperville?"              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    LAYER 3: AI Layer (ADK Agent)                        │
│  • Processes natural language queries                                   │
│  • Uses Gemini model for reasoning                                      │
│  • Maintains conversation state                                         │
│  • Coordinates tool calls                                               │
│  Location: agents/root_agent_api.py                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                 LAYER 2: Application Layer (API Tools)                  │
│  • ADK tools that call the REST API                                     │
│  • Handles data formatting and enrichment                               │
│  • Manages state between calls                                          │
│  Location: tools/fiscal_tools_api.py                                    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  LAYER 1: Data Layer (Flask REST API)                   │
│  • Exposes data via HTTP/JSON endpoints                                 │
│  • Abstracts data source (BigQuery OR MS Access)                        │
│  • Handles query construction and execution                             │
│  Location: api/fiscal_data_api.py                                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCE                                      │
│  Option A: Google BigQuery (project-zion-454116)                        │
│  Option B: MS Access via ODBC (data2024.accdb)                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 🎯 Why This Architecture?

### Benefits Over Direct BigQuery Access

| Aspect | Direct BigQuery | API-Based |
|--------|-----------------|-----------|
| **Data Source** | BigQuery only | BigQuery OR MS Access |
| **Coupling** | Agent code tied to BigQuery | Decoupled via API |
| **Scalability** | Single deployment | API can scale independently |
| **Reusability** | Agent-specific | API serves multiple clients |
| **Testing** | Requires BigQuery | Can mock API responses |
| **Security** | GCP credentials in agent | Credentials in API only |

### When to Use This Approach

- ✅ Need to support multiple data sources (cloud + legacy)
- ✅ Multiple applications need the same data
- ✅ Want to deploy API and agent separately
- ✅ Need to add caching layer
- ✅ Want clearer separation of concerns

## 📁 Project Structure

```
il_fiscal_agent_api/
├── agent.py                    # ADK entry point
├── run.py                      # Runner script (API + Agent)
├── requirements.txt            # Dependencies
├── .env.example               # Environment template
│
├── api/
│   ├── __init__.py
│   └── fiscal_data_api.py     # Flask REST API server
│
├── utils/
│   ├── __init__.py
│   └── api_client.py          # Python client for the API
│
├── tools/
│   ├── __init__.py
│   └── fiscal_tools_api.py    # ADK tools (call API)
│
├── agents/
│   ├── __init__.py
│   └── root_agent_api.py      # Main ADK agent
│
└── config/
    └── __init__.py
```

## 🚀 Quick Start

### Prerequisites

1. **Python 3.9+**
2. **Google Cloud Project** with BigQuery
3. **GCP Authentication** configured
4. **ADK installed**: `pip install google-adk`

### Step 1: Install Dependencies

```bash
cd il_fiscal_agent_api
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### Step 3: Start the System

**Option A: Run both API and Agent together**
```bash
python run.py both
```

**Option B: Run separately (recommended for development)**
```bash
# Terminal 1: Start API
python run.py api

# Terminal 2: Start Agent
python run.py agent
```

### Step 4: Test

Open http://localhost:8000 and try:
- "Find information about Skokie"
- "What is the property tax revenue for Naperville?"
- "Compare Chicago vs Aurora"

## 📡 API Endpoints

### Health Check
```
GET /api/v1/health
```

### Entity Operations
```
GET /api/v1/entities/search?q={name}&limit={n}
GET /api/v1/entities/{code}
GET /api/v1/entities/compare?codes={code1},{code2}
GET /api/v1/entities/rank?metric={metric}&entity_type={type}
```

### Financial Data
```
GET /api/v1/entities/{code}/revenues
GET /api/v1/entities/{code}/expenditures
GET /api/v1/entities/{code}/debt
GET /api/v1/entities/{code}/pensions
```

### Geographic
```
GET /api/v1/counties/{county}/entities?entity_type={type}
GET /api/v1/counties/{county}/summary
```

## 🔧 Configuration Options

### Using BigQuery (Default)

```env
DATA_SOURCE=bigquery
GOOGLE_CLOUD_PROJECT=project-zion-454116
BQ_DATASET=comp_financial_insights_2024
```

### Using MS Access (Legacy)

```env
DATA_SOURCE=access
ACCESS_DRIVER={Microsoft Access Driver (*.mdb, *.accdb)}
ACCESS_DB_PATH=C:\path\to\data2024.accdb
```

**Note:** MS Access requires the ODBC driver installed on the server.

## 🧪 Testing

```bash
# Run all tests
python run.py test

# Test API directly
curl http://localhost:5000/api/v1/health
curl http://localhost:5000/api/v1/entities/search?q=Skokie
```

## 🔄 Migration from Direct BigQuery

If you have the original `il_fiscal_agent` with direct BigQuery access:

1. Keep your existing BigQuery setup and data
2. Start the Flask API pointing to the same BigQuery dataset
3. Update your agent to use the API-based tools
4. Test side-by-side to ensure parity

The API uses the same SQL queries as the original agent, just exposed over HTTP.

## 📊 Comparison: Original vs API-Based

### Original (Direct BigQuery)

```python
# In fiscal_tools.py
from utils.bigquery_utils import search_entities

def search_government_entity(search_term: str, tool_context):
    results = search_entities(search_term)  # Direct BigQuery call
    return results
```

### New (API-Based)

```python
# In fiscal_tools_api.py
from utils.api_client import FiscalDataClient

def search_government_entity(search_term: str, tool_context):
    client = FiscalDataClient()
    results = client.search_entities(search_term)  # HTTP API call
    return results
```

## 🚢 Deployment Options

### Option 1: Local Development
- API and Agent on same machine
- Good for testing and development

### Option 2: Separate Deployments
- API on Cloud Run/App Engine
- Agent on separate service
- Better for production

### Option 3: Containerized
```dockerfile
# Dockerfile.api
FROM python:3.11-slim
COPY api/ /app/api/
COPY utils/ /app/utils/
WORKDIR /app
RUN pip install flask google-cloud-bigquery
ENV DATA_SOURCE=bigquery
EXPOSE 5000
CMD ["python", "api/fiscal_data_api.py"]
```

## 🔒 Security Considerations

1. **API Authentication**: Consider adding API keys or JWT
2. **Rate Limiting**: Protect against abuse
3. **CORS**: Configure for your frontend domains
4. **Credentials**: Keep BigQuery credentials only in API layer

## 📚 Additional Resources

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [BigQuery Python Client](https://cloud.google.com/python/docs/reference/bigquery/latest)

## 📄 License

This project is provided for educational purposes. The underlying data is public information from Illinois Comptroller's Office.
