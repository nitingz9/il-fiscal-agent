"""
Configuration settings for Illinois Local Government Financial Data Agent
"""
import os

# =============================================================================
# GOOGLE CLOUD CONFIGURATION
# =============================================================================
GCP_PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "your-project-id")
GCP_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
BQ_DATASET = os.environ.get("BQ_DATASET", "il_local_gov_finance")

# =============================================================================
# MODEL CONFIGURATION
# =============================================================================
# Primary model for complex reasoning tasks
PRIMARY_MODEL = "gemini-2.0-flash"

# Lighter model for simple tasks (greetings, clarifications)
LIGHT_MODEL = "gemini-2.0-flash"

# =============================================================================
# BIGQUERY TABLE NAMES
# =============================================================================
TABLES = {
    "unit_data": f"{GCP_PROJECT_ID}.{BQ_DATASET}.UnitData",
    "unit_stats": f"{GCP_PROJECT_ID}.{BQ_DATASET}.UnitStats",
    "revenues": f"{GCP_PROJECT_ID}.{BQ_DATASET}.Revenues",
    "expenditures": f"{GCP_PROJECT_ID}.{BQ_DATASET}.Expenditures",
    "fund_balances": f"{GCP_PROJECT_ID}.{BQ_DATASET}.FundBalances",
    "assets": f"{GCP_PROJECT_ID}.{BQ_DATASET}.Assets",
    "indebtedness": f"{GCP_PROJECT_ID}.{BQ_DATASET}.Indebtedness",
    "pensions": f"{GCP_PROJECT_ID}.{BQ_DATASET}.Pensions",
    "capital_outlay": f"{GCP_PROJECT_ID}.{BQ_DATASET}.CapitalOutlay",
    "audits": f"{GCP_PROJECT_ID}.{BQ_DATASET}.Audits",
    "afr_notes": f"{GCP_PROJECT_ID}.{BQ_DATASET}.AFRNotes",
    "funds_used": f"{GCP_PROJECT_ID}.{BQ_DATASET}.FundsUsed",
    "component": f"{GCP_PROJECT_ID}.{BQ_DATASET}.Component",
    "governmental_entities": f"{GCP_PROJECT_ID}.{BQ_DATASET}.GovernmentalEntities",
    "reporting": f"{GCP_PROJECT_ID}.{BQ_DATASET}.Reporting",
    # Pre-computed views (you'll create these)
    "entity_summary": f"{GCP_PROJECT_ID}.{BQ_DATASET}.vw_EntitySummary",
    "fiscal_health": f"{GCP_PROJECT_ID}.{BQ_DATASET}.vw_FiscalHealth",
}

# =============================================================================
# FUND TYPE MAPPINGS
# =============================================================================
FUND_TYPES = {
    "GN": "General Fund",
    "SR": "Special Revenue Fund",
    "CP": "Capital Projects Fund",
    "DS": "Debt Service Fund",
    "EP": "Enterprise/Proprietary Fund",
    "TS": "Trust Fund",
    "FD": "Fiduciary Fund",
    "DP": "Debt Principal Fund",
    "OT": "Other Funds"
}

# =============================================================================
# REVENUE CATEGORY MAPPINGS
# =============================================================================
REVENUE_CATEGORIES = {
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
    "235t": "User Fees",
    "236t": "Miscellaneous Revenue"
}

# =============================================================================
# EXPENDITURE CATEGORY MAPPINGS
# =============================================================================
EXPENDITURE_CATEGORIES = {
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
    "280t": "Contingency"
}

# =============================================================================
# ENTITY TYPE MAPPINGS
# =============================================================================
ENTITY_TYPES = {
    0: "County",
    1: "Township",
    3: "Airport Authority",
    4: "Cemetery District",
    5: "Drainage District",
    6: "Fire Protection District",
    7: "Forest Preserve District",
    8: "Hospital District",
    9: "Exposition and Auditorium Authority",
    10: "Public Library District",
    11: "Mosquito Abatement District",
    12: "Park District",
    13: "Public Health District",
    14: "River Conservancy District",
    15: "Road District",
    16: "Sanitary District",
    17: "Soil and Water Conservation District",
    18: "Street Lighting District",
    19: "Water Service District",
    20: "Conservation District",
    22: "Surface Water District",
    23: "Mass Transit District",
    24: "Multi-Township Assessment District",
    25: "Port District",
    27: "Rescue Squad District",
    28: "Special Recreation",
    29: "Electric Agency",
    30: "City",
    31: "Town",
    32: "Village",
    33: "Public Building Commission",
    37: "Public Water District",
    38: "Water Commission",
    39: "Solid Waste Agency",
    40: "Water Reclamation District",
    41: "Water Authority",
    45: "Natural Gas Agency",
    46: "Planning Agency",
    50: "Museum District",
    51: "School District",
    53: "Community College",
    54: "Housing Authority",
    55: "Joint Action Water Agency"
}

# =============================================================================
# FISCAL HEALTH THRESHOLDS
# =============================================================================
FISCAL_HEALTH_THRESHOLDS = {
    "fund_balance_ratio": {
        "excellent": 0.25,  # 25%+ of expenditures
        "good": 0.15,       # 15-25%
        "fair": 0.08,       # 8-15%
        "poor": 0.0         # Below 8%
    },
    "operating_margin": {
        "excellent": 0.05,  # 5%+ surplus
        "good": 0.0,        # 0-5%
        "fair": -0.05,      # 0 to -5%
        "poor": -0.10       # Below -5%
    },
    "pension_funded_ratio": {
        "excellent": 0.80,  # 80%+ funded
        "good": 0.60,       # 60-80%
        "fair": 0.40,       # 40-60%
        "critical": 0.0     # Below 40%
    },
    "debt_per_capita": {
        "low": 1000,        # Under $1,000
        "moderate": 2500,   # $1,000-$2,500
        "high": 5000,       # $2,500-$5,000
        "very_high": 10000  # Above $5,000
    }
}

# =============================================================================
# ILLINOIS COUNTIES (for validation)
# =============================================================================
ILLINOIS_COUNTIES = [
    "Adams", "Alexander", "Bond", "Boone", "Brown", "Bureau", "Calhoun", 
    "Carroll", "Cass", "Champaign", "Christian", "Clark", "Clay", "Clinton",
    "Coles", "Cook", "Crawford", "Cumberland", "Dekalb", "Dewitt", "Douglas",
    "Dupage", "Edgar", "Edwards", "Effingham", "Fayette", "Ford", "Franklin",
    "Fulton", "Gallatin", "Greene", "Grundy", "Hamilton", "Hancock", "Hardin",
    "Henderson", "Henry", "Iroquois", "Jackson", "Jasper", "Jefferson", "Jersey",
    "Jo Daviess", "Johnson", "Kane", "Kankakee", "Kendall", "Knox", "Lake",
    "Lasalle", "Lawrence", "Lee", "Livingston", "Logan", "Macon", "Macoupin",
    "Madison", "Marion", "Marshall", "Mason", "Massac", "Mcdonough", "Mchenry",
    "Mclean", "Menard", "Mercer", "Monroe", "Montgomery", "Morgan", "Moultrie",
    "Ogle", "Peoria", "Perry", "Piatt", "Pike", "Pope", "Pulaski", "Putnam",
    "Randolph", "Richland", "Rock Island", "Saline", "Sangamon", "Schuyler",
    "Scott", "Shelby", "St. Clair", "Stark", "Stephenson", "Tazewell", "Union",
    "Vermilion", "Wabash", "Warren", "Washington", "Wayne", "White", "Whiteside",
    "Will", "Williamson", "Winnebago", "Woodford"
]
