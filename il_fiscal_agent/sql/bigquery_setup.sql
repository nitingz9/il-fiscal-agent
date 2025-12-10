-- =============================================================================
-- Illinois Local Government Financial Data - BigQuery Setup Script
-- =============================================================================
-- 
-- This script creates the necessary tables and views for the fiscal data agent.
-- Run this in BigQuery Console or using bq command line tool.
--
-- Prerequisites:
-- 1. Create a BigQuery dataset: bq mk --dataset YOUR_PROJECT:il_local_gov_finance
-- 2. Export Access tables to CSV and upload to GCS
-- 3. Load CSVs into BigQuery tables
-- =============================================================================

-- =============================================================================
-- STEP 1: Create the dataset (run once)
-- =============================================================================
-- Run in terminal: bq mk --dataset your-project-id:il_local_gov_finance

-- =============================================================================
-- STEP 2: Load CSV files into BigQuery
-- =============================================================================
-- Option A: Using bq command line (recommended for large files)
-- 
-- bq load --autodetect --source_format=CSV \
--   your-project-id:il_local_gov_finance.UnitData \
--   gs://your-bucket/data2024/UnitData.csv
--
-- Option B: Using BigQuery Console
-- 1. Go to BigQuery Console
-- 2. Select your dataset
-- 3. Click "Create Table"
-- 4. Choose "Upload" or "Google Cloud Storage"
-- 5. Select your CSV file
-- 6. Enable "Auto detect" for schema

-- =============================================================================
-- STEP 3: Create Views for Common Queries
-- =============================================================================

-- -----------------------------------------------------------------------------
-- View: Entity Summary (Joins UnitData with UnitStats)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW `your-project-id.il_local_gov_finance.vw_EntitySummary` AS
SELECT 
    ud.Code,
    ud.UnitName,
    ud.Description AS EntityType,
    ud.County,
    ud.C4 AS EntityTypeCode,
    
    -- Contact Information
    CONCAT(ud.CEOFName, ' ', ud.CEOLName) AS CEO_Name,
    ud.CEOTitle AS CEO_Title,
    CONCAT(ud.CFOFName, ' ', ud.CFOLName) AS CFO_Name,
    ud.CFOTitle AS CFO_Title,
    
    -- Statistics
    us.Pop AS Population,
    us.EAV AS EquitalizedAssessedValue,
    us.FULL_EMP AS FullTimeEmployees,
    us.PART_EMP AS PartTimeEmployees,
    
    -- Flags
    us.HomeRule,
    us.Utilities,
    us.TIF_District,
    us.AccountingMethod,
    us.Debt AS HasDebt,
    us.BondedDebt AS HasBondedDebt,
    us.GOBonds AS HasGOBonds,
    us.RevenueBonds AS HasRevenueBonds,
    
    -- Funding Sources
    us.AmtState AS StateFunding,
    us.AmtLocal AS LocalFunding,
    us.AmtFederal AS FederalFunding

FROM `your-project-id.il_local_gov_finance.UnitData` ud
LEFT JOIN `your-project-id.il_local_gov_finance.UnitStats` us 
    ON ud.Code = us.Code;


-- -----------------------------------------------------------------------------
-- View: Revenue Totals by Entity
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW `your-project-id.il_local_gov_finance.vw_RevenueTotals` AS
SELECT 
    Code,
    SUM(COALESCE(GN, 0)) AS GeneralFund_Revenue,
    SUM(COALESCE(SR, 0)) AS SpecialRevenue_Revenue,
    SUM(COALESCE(CP, 0)) AS CapitalProjects_Revenue,
    SUM(COALESCE(DS, 0)) AS DebtService_Revenue,
    SUM(COALESCE(EP, 0)) AS Enterprise_Revenue,
    SUM(COALESCE(TS, 0)) AS Trust_Revenue,
    SUM(COALESCE(FD, 0)) AS Fiduciary_Revenue,
    SUM(COALESCE(GN, 0) + COALESCE(SR, 0) + COALESCE(CP, 0) + 
        COALESCE(DS, 0) + COALESCE(EP, 0) + COALESCE(TS, 0) + 
        COALESCE(FD, 0)) AS Total_Revenue
FROM `your-project-id.il_local_gov_finance.Revenues`
GROUP BY Code;


-- -----------------------------------------------------------------------------
-- View: Expenditure Totals by Entity
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW `your-project-id.il_local_gov_finance.vw_ExpenditureTotals` AS
SELECT 
    Code,
    SUM(COALESCE(GN, 0)) AS GeneralFund_Expenditure,
    SUM(COALESCE(SR, 0)) AS SpecialRevenue_Expenditure,
    SUM(COALESCE(CP, 0)) AS CapitalProjects_Expenditure,
    SUM(COALESCE(DS, 0)) AS DebtService_Expenditure,
    SUM(COALESCE(EP, 0)) AS Enterprise_Expenditure,
    SUM(COALESCE(TS, 0)) AS Trust_Expenditure,
    SUM(COALESCE(FD, 0)) AS Fiduciary_Expenditure,
    SUM(COALESCE(GN, 0) + COALESCE(SR, 0) + COALESCE(CP, 0) + 
        COALESCE(DS, 0) + COALESCE(EP, 0) + COALESCE(TS, 0) + 
        COALESCE(FD, 0)) AS Total_Expenditure
FROM `your-project-id.il_local_gov_finance.Expenditures`
GROUP BY Code;


-- -----------------------------------------------------------------------------
-- View: Fiscal Health Indicators
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW `your-project-id.il_local_gov_finance.vw_FiscalHealth` AS
WITH revenue_totals AS (
    SELECT Code, Total_Revenue
    FROM `your-project-id.il_local_gov_finance.vw_RevenueTotals`
),
expenditure_totals AS (
    SELECT Code, Total_Expenditure
    FROM `your-project-id.il_local_gov_finance.vw_ExpenditureTotals`
),
unassigned_balance AS (
    SELECT 
        Code,
        COALESCE(GN, 0) AS UnassignedFundBalance
    FROM `your-project-id.il_local_gov_finance.FundBalances`
    WHERE Category = '307t'
),
debt_totals AS (
    SELECT 
        Code,
        COALESCE(t404, 0) + COALESCE(t410, 0) AS TotalDebt
    FROM `your-project-id.il_local_gov_finance.Indebtedness`
),
pension_funded AS (
    SELECT 
        Code,
        -- Get the lowest funded ratio among all pension systems
        LEAST(
            COALESCE(NULLIF(IMRF_t504_3, 0), 100),
            COALESCE(NULLIF(Police_t504_3, 0), 100),
            COALESCE(NULLIF(Fire_t504_3, 0), 100)
        ) AS LowestFundedRatio
    FROM `your-project-id.il_local_gov_finance.Pensions`
)

SELECT 
    es.Code,
    es.UnitName,
    es.EntityType,
    es.County,
    es.Population,
    es.EquitalizedAssessedValue,
    
    -- Raw values
    COALESCE(r.Total_Revenue, 0) AS TotalRevenue,
    COALESCE(e.Total_Expenditure, 0) AS TotalExpenditure,
    COALESCE(ub.UnassignedFundBalance, 0) AS UnassignedFundBalance,
    COALESCE(d.TotalDebt, 0) AS TotalDebt,
    
    -- Calculated metrics
    CASE 
        WHEN COALESCE(r.Total_Revenue, 0) > 0 
        THEN ROUND((COALESCE(r.Total_Revenue, 0) - COALESCE(e.Total_Expenditure, 0)) / r.Total_Revenue * 100, 2)
        ELSE NULL 
    END AS OperatingMargin_Pct,
    
    CASE 
        WHEN COALESCE(e.Total_Expenditure, 0) > 0 
        THEN ROUND(COALESCE(ub.UnassignedFundBalance, 0) / e.Total_Expenditure * 100, 2)
        ELSE NULL 
    END AS FundBalanceRatio_Pct,
    
    CASE 
        WHEN COALESCE(es.Population, 0) > 0 
        THEN ROUND(COALESCE(d.TotalDebt, 0) / es.Population, 2)
        ELSE NULL 
    END AS DebtPerCapita,
    
    CASE 
        WHEN COALESCE(es.Population, 0) > 0 
        THEN ROUND(COALESCE(r.Total_Revenue, 0) / es.Population, 2)
        ELSE NULL 
    END AS RevenuePerCapita,
    
    CASE 
        WHEN COALESCE(es.Population, 0) > 0 
        THEN ROUND(COALESCE(e.Total_Expenditure, 0) / es.Population, 2)
        ELSE NULL 
    END AS ExpenditurePerCapita,
    
    pf.LowestFundedRatio AS PensionFundedRatio_Pct,
    
    -- Rating categories
    CASE 
        WHEN (COALESCE(r.Total_Revenue, 0) - COALESCE(e.Total_Expenditure, 0)) / NULLIF(r.Total_Revenue, 0) >= 0.05 THEN 'Excellent'
        WHEN (COALESCE(r.Total_Revenue, 0) - COALESCE(e.Total_Expenditure, 0)) / NULLIF(r.Total_Revenue, 0) >= 0 THEN 'Good'
        WHEN (COALESCE(r.Total_Revenue, 0) - COALESCE(e.Total_Expenditure, 0)) / NULLIF(r.Total_Revenue, 0) >= -0.05 THEN 'Fair'
        ELSE 'Poor'
    END AS OperatingMargin_Rating,
    
    CASE 
        WHEN COALESCE(ub.UnassignedFundBalance, 0) / NULLIF(e.Total_Expenditure, 0) >= 0.25 THEN 'Excellent'
        WHEN COALESCE(ub.UnassignedFundBalance, 0) / NULLIF(e.Total_Expenditure, 0) >= 0.15 THEN 'Good'
        WHEN COALESCE(ub.UnassignedFundBalance, 0) / NULLIF(e.Total_Expenditure, 0) >= 0.08 THEN 'Fair'
        ELSE 'Poor'
    END AS FundBalance_Rating,
    
    CASE 
        WHEN pf.LowestFundedRatio >= 80 THEN 'Excellent'
        WHEN pf.LowestFundedRatio >= 60 THEN 'Good'
        WHEN pf.LowestFundedRatio >= 40 THEN 'Fair'
        ELSE 'Critical'
    END AS Pension_Rating

FROM `your-project-id.il_local_gov_finance.vw_EntitySummary` es
LEFT JOIN revenue_totals r ON es.Code = r.Code
LEFT JOIN expenditure_totals e ON es.Code = e.Code
LEFT JOIN unassigned_balance ub ON es.Code = ub.Code
LEFT JOIN debt_totals d ON es.Code = d.Code
LEFT JOIN pension_funded pf ON es.Code = pf.Code;


-- -----------------------------------------------------------------------------
-- View: County Summary
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW `your-project-id.il_local_gov_finance.vw_CountySummary` AS
SELECT 
    County,
    COUNT(DISTINCT Code) AS EntityCount,
    COUNT(DISTINCT EntityType) AS EntityTypeCount,
    SUM(Population) AS TotalPopulation,
    SUM(EquitalizedAssessedValue) AS TotalEAV,
    SUM(FullTimeEmployees) AS TotalFullTimeEmployees,
    SUM(PartTimeEmployees) AS TotalPartTimeEmployees,
    COUNTIF(HomeRule = 'Y') AS HomeRuleCount,
    COUNTIF(HasDebt = 'Y') AS EntitiesWithDebt
FROM `your-project-id.il_local_gov_finance.vw_EntitySummary`
GROUP BY County
ORDER BY TotalPopulation DESC;


-- -----------------------------------------------------------------------------
-- View: Entity Type Summary
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW `your-project-id.il_local_gov_finance.vw_EntityTypeSummary` AS
SELECT 
    EntityType,
    EntityTypeCode,
    COUNT(DISTINCT Code) AS EntityCount,
    SUM(Population) AS TotalPopulation,
    AVG(Population) AS AvgPopulation,
    SUM(EquitalizedAssessedValue) AS TotalEAV,
    AVG(EquitalizedAssessedValue) AS AvgEAV
FROM `your-project-id.il_local_gov_finance.vw_EntitySummary`
GROUP BY EntityType, EntityTypeCode
ORDER BY EntityCount DESC;


-- =============================================================================
-- STEP 4: Create Indexes for Performance (optional)
-- =============================================================================
-- BigQuery doesn't use traditional indexes, but you can:
-- 1. Partition tables by date if you have multi-year data
-- 2. Cluster tables by frequently filtered columns

-- Example: Cluster UnitData by County for faster county-based queries
-- CREATE OR REPLACE TABLE `your-project-id.il_local_gov_finance.UnitData_Clustered`
-- CLUSTER BY County
-- AS SELECT * FROM `your-project-id.il_local_gov_finance.UnitData`;


-- =============================================================================
-- STEP 5: Verify Setup
-- =============================================================================

-- Check row counts
SELECT 'UnitData' AS table_name, COUNT(*) AS row_count 
FROM `your-project-id.il_local_gov_finance.UnitData`
UNION ALL
SELECT 'UnitStats', COUNT(*) FROM `your-project-id.il_local_gov_finance.UnitStats`
UNION ALL
SELECT 'Revenues', COUNT(*) FROM `your-project-id.il_local_gov_finance.Revenues`
UNION ALL
SELECT 'Expenditures', COUNT(*) FROM `your-project-id.il_local_gov_finance.Expenditures`
UNION ALL
SELECT 'FundBalances', COUNT(*) FROM `your-project-id.il_local_gov_finance.FundBalances`
UNION ALL
SELECT 'Indebtedness', COUNT(*) FROM `your-project-id.il_local_gov_finance.Indebtedness`
UNION ALL
SELECT 'Pensions', COUNT(*) FROM `your-project-id.il_local_gov_finance.Pensions`;

-- Test the entity summary view
SELECT * FROM `your-project-id.il_local_gov_finance.vw_EntitySummary` LIMIT 10;

-- Test fiscal health view
SELECT * FROM `your-project-id.il_local_gov_finance.vw_FiscalHealth` 
WHERE Population > 50000
ORDER BY DebtPerCapita DESC
LIMIT 20;
