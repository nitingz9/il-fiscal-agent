# Illinois Local Government Financial Data Agent

A conversational AI agent built with Google's Agent Development Kit (ADK) that enables natural language queries against financial data from 4,000+ Illinois local governments.

## 🎯 Features

- **Entity Lookup**: Search for cities, villages, townships, fire districts by name
- **Financial Queries**: Get revenue, expenditure, debt, and pension data
- **Fiscal Health Analysis**: Assess financial stability with calculated metrics
- **Peer Benchmarking**: Compare entities against similar governments
- **Geographic Analysis**: Explore all entities within a county
- **Natural Language Interface**: Ask questions in plain English

## 📁 Project Structure

```
il_fiscal_agent/
├── agent.py                    # Main entry point (ADK requirement)
├── .env.example                # Environment configuration template
├── requirements.txt            # Python dependencies
├── test_agent.py              # Test script
│
├── config/
│   ├── __init__.py
│   └── settings.py            # Configuration, constants, mappings
│
├── utils/
│   ├── __init__.py
│   └── bigquery_utils.py      # BigQuery database operations
│
├── tools/
│   ├── __init__.py
│   └── fiscal_tools.py        # All agent tools (13 tools)
│
├── agents/
│   ├── __init__.py
│   ├── sub_agents.py          # Specialized sub-agents (6 agents)
│   └── root_agent.py          # Main orchestrator agent
│
└── sql/
    └── bigquery_setup.sql     # BigQuery table/view creation
```

## 🚀 Quick Start

### Prerequisites

1. **Python 3.9+** installed
2. **Google Cloud Project** with BigQuery enabled
3. **Gemini API Key** from [Google AI Studio](https://aistudio.google.com/app/apikey)
4. **Illinois fiscal data** loaded into BigQuery

### Step 1: Clone and Setup Environment

```bash
# Create project directory
mkdir il_fiscal_agent && cd il_fiscal_agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env  # or use your preferred editor
```

Set these values in `.env`:
```
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_API_KEY=your-gemini-api-key
BQ_DATASET=il_local_gov_finance
```

### Step 3: Setup BigQuery Data

See detailed instructions in [BigQuery Setup](#bigquery-setup) below.

### Step 4: Run the Agent

```bash
# Option 1: Web Interface (recommended for testing)
adk web

# Option 2: Command Line Interface
adk run il_fiscal_agent

# Option 3: API Server (for integration)
adk api_server
```

Open http://localhost:8000 and select `il_fiscal_agent` from the dropdown.

---

## 📊 BigQuery Setup

### Step 1: Create Dataset

```bash
# Using gcloud CLI
bq mk --dataset your-project-id:il_local_gov_finance
```

### Step 2: Export Access Database to CSV

The source data is in Microsoft Access format. Export each table:

```bash
# If you have mdbtools installed (Linux/Mac)
mdb-export data2024.accdb UnitData > UnitData.csv
mdb-export data2024.accdb UnitStats > UnitStats.csv
mdb-export data2024.accdb Revenues > Revenues.csv
mdb-export data2024.accdb Expenditures > Expenditures.csv
mdb-export data2024.accdb FundBalances > FundBalances.csv
mdb-export data2024.accdb Assets > Assets.csv
mdb-export data2024.accdb Indebtedness > Indebtedness.csv
mdb-export data2024.accdb Pensions > Pensions.csv
mdb-export data2024.accdb CapitalOutlay > CapitalOutlay.csv
mdb-export data2024.accdb Audits > Audits.csv
mdb-export data2024.accdb AFRNotes > AFRNotes.csv
mdb-export data2024.accdb FundsUsed > FundsUsed.csv
mdb-export data2024.accdb Component > Component.csv
mdb-export data2024.accdb GovernmentalEntities > GovernmentalEntities.csv
mdb-export data2024.accdb Reporting > Reporting.csv
```

### Step 3: Upload CSVs to Cloud Storage

```bash
# Create a bucket
gsutil mb gs://your-bucket-il-fiscal-data

# Upload CSV files
gsutil cp *.csv gs://your-bucket-il-fiscal-data/data2024/
```

### Step 4: Load into BigQuery

```bash
# Load each table (repeat for all 15 tables)
bq load --autodetect --source_format=CSV \
  your-project-id:il_local_gov_finance.UnitData \
  gs://your-bucket-il-fiscal-data/data2024/UnitData.csv

bq load --autodetect --source_format=CSV \
  your-project-id:il_local_gov_finance.UnitStats \
  gs://your-bucket-il-fiscal-data/data2024/UnitStats.csv

bq load --autodetect --source_format=CSV \
  your-project-id:il_local_gov_finance.Revenues \
  gs://your-bucket-il-fiscal-data/data2024/Revenues.csv

# ... repeat for all tables
```

### Step 5: Create Views

Run the SQL in `sql/bigquery_setup.sql` in BigQuery Console to create:
- `vw_EntitySummary` - Joined entity + stats data
- `vw_RevenueTotals` - Aggregated revenues by entity
- `vw_ExpenditureTotals` - Aggregated expenditures by entity  
- `vw_FiscalHealth` - Calculated fiscal health metrics
- `vw_CountySummary` - County-level aggregations

### Step 6: Verify Setup

```sql
-- Check row counts
SELECT 'UnitData' as tbl, COUNT(*) as cnt FROM `your-project.il_local_gov_finance.UnitData`
UNION ALL SELECT 'Revenues', COUNT(*) FROM `your-project.il_local_gov_finance.Revenues`
UNION ALL SELECT 'Expenditures', COUNT(*) FROM `your-project.il_local_gov_finance.Expenditures`;
```

Expected counts:
- UnitData: 4,140 rows
- Revenues: 29,550 rows
- Expenditures: 26,805 rows

---

## 🤖 Agent Architecture

### Root Agent
The main orchestrator that routes queries to specialized sub-agents.

### Sub-Agents

| Agent | Purpose | Tools |
|-------|---------|-------|
| `entity_lookup_agent` | Find/identify government entities | `search_government_entity`, `get_entity_details` |
| `fiscal_query_agent` | Financial data queries | `get_revenue_data`, `get_expenditure_data`, `get_fund_balance_data`, `get_debt_data`, `get_pension_data` |
| `comparison_agent` | Benchmarking and rankings | `compare_entities`, `find_peer_entities`, `rank_entities` |
| `fiscal_health_agent` | Financial health assessment | `calculate_fiscal_health_score` |
| `geographic_agent` | County-level analysis | `get_county_entities`, `get_county_financial_summary` |
| `greeting_agent` | Conversation handling | `greet_user`, `say_goodbye`, `provide_help` |

### Tools (13 Total)

**Entity Lookup:**
- `search_government_entity` - Fuzzy search by name
- `get_entity_details` - Full entity information

**Financial Data:**
- `get_revenue_data` - Revenue breakdown by category/fund
- `get_expenditure_data` - Expenditure breakdown
- `get_fund_balance_data` - GASB 54 fund classifications
- `get_debt_data` - Debt by type
- `get_pension_data` - Pension fund status

**Analysis:**
- `calculate_fiscal_health_score` - Compute fiscal metrics

**Comparison:**
- `compare_entities` - Side-by-side comparison
- `find_peer_entities` - Find similar entities
- `rank_entities` - Create rankings

**Geographic:**
- `get_county_entities` - List entities in county
- `get_county_financial_summary` - County aggregates

### Safety Callbacks

- **Input Guardrail** (`before_model_callback`): Filters out-of-scope requests
- **Tool Guardrail** (`before_tool_callback`): Validates tool arguments

---

## 💬 Example Queries

### Basic Lookups
```
"Find information about Springfield"
"What is the entity code for Naperville?"
"Search for fire districts in Lake County"
```

### Financial Data
```
"What is the property tax revenue for Chicago?"
"Show me Skokie's expenditure breakdown"
"What is the pension funding status for Evanston?"
"How much debt does Peoria have?"
```

### Comparisons
```
"Compare Chicago vs Naperville vs Aurora"
"Find cities similar to Skokie for benchmarking"
"Top 10 villages by population"
"Rank fire districts in Cook County by budget"
```

### Fiscal Health
```
"Is Springfield financially healthy?"
"Assess the fiscal condition of Rockford"
"What are the key financial indicators for Champaign?"
```

### Geographic
```
"What governments are in DuPage County?"
"List all park districts in Kane County"
"Give me a summary of Cook County"
```

---

## ⚙️ Configuration Reference

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_CLOUD_PROJECT` | GCP project ID | Yes |
| `GOOGLE_API_KEY` | Gemini API key | Yes* |
| `GOOGLE_GENAI_USE_VERTEXAI` | Use Vertex AI instead | No |
| `GOOGLE_CLOUD_LOCATION` | GCP region | No |
| `BQ_DATASET` | BigQuery dataset name | Yes |

*Not required if using Vertex AI authentication

### Fiscal Health Thresholds

| Metric | Excellent | Good | Fair | Poor |
|--------|-----------|------|------|------|
| Operating Margin | ≥5% | 0-5% | -5-0% | <-5% |
| Fund Balance Ratio | ≥25% | 15-25% | 8-15% | <8% |
| Pension Funded Ratio | ≥80% | 60-80% | 40-60% | <40% |
| Debt Per Capita | <$1K | $1-2.5K | $2.5-5K | >$5K |

---

## 🧪 Testing

### Test Configuration
```bash
python test_agent.py --config
```

### Test Agent Conversation
```bash
python test_agent.py --agent
```

### Run Both
```bash
python test_agent.py
```

---

## 🚢 Deployment

### Deploy to Cloud Run

```bash
# Build container
gcloud builds submit --tag gcr.io/YOUR_PROJECT/il-fiscal-agent

# Deploy
gcloud run deploy il-fiscal-agent \
  --image gcr.io/YOUR_PROJECT/il-fiscal-agent \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Deploy to Vertex AI Agent Engine

```bash
# Package the agent
adk deploy vertex-ai \
  --project YOUR_PROJECT \
  --location us-central1 \
  --agent-name il-fiscal-agent
```

---

## 📚 Data Dictionary Summary

### Key Tables

| Table | Records | Description |
|-------|---------|-------------|
| UnitData | 4,140 | Entity master registry |
| UnitStats | 4,140 | Annual statistics |
| Revenues | 29,550 | Revenue line items |
| Expenditures | 26,805 | Expenditure line items |
| FundBalances | 7,314 | GASB 54 fund classifications |
| Indebtedness | 1,791 | Debt lifecycle tracking |
| Pensions | 1,401 | Pension fund data |

### Fund Type Codes

| Code | Fund Type |
|------|-----------|
| GN | General Fund |
| SR | Special Revenue |
| CP | Capital Projects |
| DS | Debt Service |
| EP | Enterprise/Proprietary |
| TS | Trust |
| FD | Fiduciary |

### Entity Types (Common)

| Code | Type | Count |
|------|------|-------|
| 1 | Township | 1,224 |
| 32 | Village | 696 |
| 6 | Fire Protection District | 665 |
| 10 | Library District | 327 |
| 12 | Park District | 218 |
| 30 | City | 206 |

---

## 🔧 Troubleshooting

### "Module not found" errors
```bash
# Ensure you're in the project directory
cd il_fiscal_agent

# Reinstall dependencies
pip install -r requirements.txt
```

### BigQuery permission errors
```bash
# Authenticate with gcloud
gcloud auth application-default login

# Verify access
bq show your-project:il_local_gov_finance
```

### Agent not appearing in ADK web UI
```bash
# Run from the parent directory of il_fiscal_agent
cd ..
adk web
```

### Tool execution errors
Check the `--- Tool: xxx called ---` log messages to see which tool failed and with what arguments.

---

## 📝 License

This project is provided for educational purposes. The underlying data is public information from Illinois Comptroller's Office.

---

## 🙏 Acknowledgments

- Data source: [Illinois Comptroller's Local Government Division](https://illinoiscomptroller.gov/)
- Built with [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/)
- Powered by [Google Gemini](https://ai.google.dev/)
