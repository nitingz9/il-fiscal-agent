-- =============================================================================
-- Illinois Local Government Financial Data - BigQuery Setup Script
-- =============================================================================
-- 
-- This script creates the necessary views for the fiscal data agent.
-- Run this in BigQuery Console or using bq command line tool.
--
-- Prerequisites:
-- 1. Create a BigQuery dataset: bq mk --dataset YOUR_PROJECT:il_local_gov_finance
-- 2. Export Access tables to CSV and upload to GCS
-- 3. Load CSVs into BigQuery tables using bq load
-- =============================================================================

-- =============================================================================
-- STEP 1: Load base tables from CSV files
-- =============================================================================
-- Run these commands from terminal (adjust paths):
-- 
-- bq load --autodetect --source_format=CSV \
--   your-project:il_local_gov_finance.UnitData \
--   gs://your-bucket/UnitData.csv
--
-- bq load --autodetect --source_format=CSV \
--   your-project:il_local_gov_finance.UnitStats \
--   gs://your-bucket/UnitStats.csv
--
-- bq load --autodetect --source_format=CSV \
--   your-project:il_local_gov_finance.Revenues \
--   gs://your-bucket/Revenues.csv
--
-- (Repeat for all 15 tables)
-- =============================================================================

-- =============================================================================
-- STEP 2: Create Entity Summary View
-- =============================================================================
-- This view joins the core entity tables for quick lookups

CREATE OR REPLACE VIEW `${PROJECT_ID}.${DATASET_ID}.vw_EntitySummary` AS
SELECT 
    ud.Code,
    ud.UnitName,
    ud.Description AS EntityType,
    ud.C4 AS EntityTypeCode,
    ud.County,
    
    -- Contact Info
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
    us.Debt AS HasDebt,
    us.BondedDebt AS HasBondedDebt,
    
    -- Funding Sources
    us.AmtState AS StateFunding,
    us.AmtLocal AS LocalFunding,
    us.AmtFederal AS FederalFunding,
    
    -- Accounting
    us.AccountingMethod

FROM `${PROJECT_ID}.${DATASET_ID}.UnitData` ud
LEFT JOIN `${PROJECT_ID}.${DATASET_ID}.UnitStats` us ON ud.Code = us.Code;


-- =============================================================================
-- STEP 3: Create Revenue Totals View
-- =============================================================================

CREATE OR REPLACE VIEW `${PROJECT_ID}.${DATASET_ID}.vw_RevenueTotals` AS
SELECT 
    Code,
    SUM(COALESCE(GN, 0)) AS GeneralFund_Revenue,
    SUM(COALESCE(SR, 0)) AS SpecialRevenue_Revenue,
    SUM(COALESCE(CP, 0)) AS CapitalProjects_Revenue,
    SUM(COALESCE(DS, 0)) AS DebtService_Revenue,
    SUM(COALESCE(EP, 0)) AS Enterprise_Revenue,
    SUM(COALESCE(TS, 0)) AS Trust_Revenue,
    SUM(COALESCE(FD, 0)) AS Fiduciary_Revenue,
    SUM(COALESCE(DP, 0)) AS DebtPrincipal_Revenue,
    SUM(
        COALESCE(GN, 0) + COALESCE(SR, 0) + COALESCE(CP, 0) + 
        COALESCE(DS, 0) + COALESCE(EP, 0) + COALESCE(TS, 0) + 
        COALESCE(FD, 0) + COALESCE(DP, 0)
    ) AS Total_Revenue
FROM `${PROJECT_ID}.${DATASET_ID}.Revenues`
GROUP BY Code;


-- =============================================================================
-- STEP 4: Create Expenditure Totals View
-- =============================================================================

CREATE OR REPLACE VIEW `${PROJECT_ID}.${DATASET_ID}.vw_ExpenditureTotals` AS
SELECT 
    Code,
    SUM(COALESCE(GN, 0)) AS GeneralFund_Expenditure,
    SUM(COALESCE(SR, 0)) AS SpecialRevenue_Expenditure,
    SUM(COALESCE(CP, 0)) AS CapitalProjects_Expenditure,
    SUM(COALESCE(DS, 0)) AS DebtService_Expenditure,
    SUM(COALESCE(EP, 0)) AS Enterprise_Expenditure,
    SUM(COALESCE(TS, 0)) AS Trust_Expenditure,
    SUM(COALESCE(FD, 0)) AS Fiduciary_Expenditure,
    SUM(COALESCE(DP, 0)) AS DebtPrincipal_Expenditure,
    SUM(
        COALESCE(GN, 0) + COALESCE(SR, 0) + COALESCE(CP, 0) + 
        COALESCE(DS, 0) + COALESCE(EP, 0) + COALESCE(TS, 0) + 
        COALESCE(FD, 0) + COALESCE(DP, 0)
    ) AS Total_Expenditure
FROM `${PROJECT_ID}.${DATASET_ID}.Expenditures`
GROUP BY Code;


-- =============================================================================
-- STEP 5: Create Fiscal Health View (Pre-computed Metrics)
-- =============================================================================

CREATE OR REPLACE VIEW `${PROJECT_ID}.${DATASET_ID}.vw_FiscalHealth` AS
WITH revenue_totals AS (
    SELECT * FROM `${PROJECT_ID}.${DATASET_ID}.vw_RevenueTotals`
),
expenditure_totals AS (
    SELECT * FROM `${PROJECT_ID}.${DATASET_ID}.vw_ExpenditureTotals`
),
fund_balances AS (
    SELECT 
        Code,
        SUM(CASE WHEN Category = '307t' THEN COALESCE(GN, 0) ELSE 0 END) AS Unassigned_FundBalance,
        SUM(CASE WHEN Category = '308t' THEN COALESCE(GN, 0) ELSE 0 END) AS Total_FundBalance
    FROM `${PROJECT_ID}.${DATASET_ID}.FundBalances`
    GROUP BY Code
),
debt_totals AS (
    SELECT 
        Code,
        COALESCE(t404, 0) + COALESCE(t410, 0) AS Total_Debt
    FROM `${PROJECT_ID}.${DATASET_ID}.Indebtedness`
),
pension_data AS (
    SELECT 
        Code,
        -- Get lowest funded ratio across all systems
        LEAST(
            COALESCE(NULLIF(IMRF_t504_3, 0), 100),
            COALESCE(NULLIF(Police_t504_3, 0), 100),
            COALESCE(NULLIF(Fire_t504_3, 0), 100)
        ) AS Lowest_Pension_FundedRatio,
        -- Total net pension liability
        COALESCE(IMRF_t503_3, 0) + COALESCE(Police_t503_3, 0) + COALESCE(Fire_t503_3, 0) AS Total_Net_Pension_Liability
    FROM `${PROJECT_ID}.${DATASET_ID}.Pensions`
)
SELECT 
    es.Code,
    es.UnitName,
    es.EntityType,
    es.County,
    es.Population,
    es.EquitalizedAssessedValue AS EAV,
    
    -- Raw Financial Totals
    COALESCE(rt.Total_Revenue, 0) AS Total_Revenue,
    COALESCE(et.Total_Expenditure, 0) AS Total_Expenditure,
    COALESCE(fb.Unassigned_FundBalance, 0) AS Unassigned_FundBalance,
    COALESCE(fb.Total_FundBalance, 0) AS Total_FundBalance,
    COALESCE(dt.Total_Debt, 0) AS Total_Debt,
    COALESCE(pd.Total_Net_Pension_Liability, 0) AS Total_Net_Pension_Liability,
    
    -- Calculated Metrics
    -- Operating Margin
    SAFE_DIVIDE(
        COALESCE(rt.Total_Revenue, 0) - COALESCE(et.Total_Expenditure, 0),
        NULLIF(rt.Total_Revenue, 0)
    ) AS Operating_Margin,
    
    -- Fund Balance Ratio (months of reserves)
    SAFE_DIVIDE(
        COALESCE(fb.Unassigned_FundBalance, 0),
        NULLIF(et.Total_Expenditure, 0)
    ) AS Fund_Balance_Ratio,
    
    -- Per Capita Metrics
    SAFE_DIVIDE(COALESCE(rt.Total_Revenue, 0), NULLIF(es.Population, 0)) AS Revenue_Per_Capita,
    SAFE_DIVIDE(COALESCE(et.Total_Expenditure, 0), NULLIF(es.Population, 0)) AS Expenditure_Per_Capita,
    SAFE_DIVIDE(COALESCE(dt.Total_Debt, 0), NULLIF(es.Population, 0)) AS Debt_Per_Capita,
    
    -- EAV Metrics
    SAFE_DIVIDE(COALESCE(rt.Total_Revenue, 0), NULLIF(es.EquitalizedAssessedValue, 0)) * 1000 AS Revenue_Per_1000_EAV,
    
    -- Pension Metrics
    pd.Lowest_Pension_FundedRatio AS Pension_Funded_Ratio,
    
    -- Health Ratings
    CASE 
        WHEN SAFE_DIVIDE(rt.Total_Revenue - et.Total_Expenditure, NULLIF(rt.Total_Revenue, 0)) >= 0.05 THEN 'Excellent'
        WHEN SAFE_DIVIDE(rt.Total_Revenue - et.Total_Expenditure, NULLIF(rt.Total_Revenue, 0)) >= 0 THEN 'Good'
        WHEN SAFE_DIVIDE(rt.Total_Revenue - et.Total_Expenditure, NULLIF(rt.Total_Revenue, 0)) >= -0.05 THEN 'Fair'
        ELSE 'Poor'
    END AS Operating_Margin_Rating,
    
    CASE 
        WHEN SAFE_DIVIDE(fb.Unassigned_FundBalance, NULLIF(et.Total_Expenditure, 0)) >= 0.25 THEN 'Excellent'
        WHEN SAFE_DIVIDE(fb.Unassigned_FundBalance, NULLIF(et.Total_Expenditure, 0)) >= 0.15 THEN 'Good'
        WHEN SAFE_DIVIDE(fb.Unassigned_FundBalance, NULLIF(et.Total_Expenditure, 0)) >= 0.08 THEN 'Fair'
        ELSE 'Poor'
    END AS Fund_Balance_Rating,
    
    CASE 
        WHEN SAFE_DIVIDE(dt.Total_Debt, NULLIF(es.Population, 0)) <= 1000 THEN 'Low'
        WHEN SAFE_DIVIDE(dt.Total_Debt, NULLIF(es.Population, 0)) <= 2500 THEN 'Moderate'
        WHEN SAFE_DIVIDE(dt.Total_Debt, NULLIF(es.Population, 0)) <= 5000 THEN 'High'
        ELSE 'Very High'
    END AS Debt_Rating,
    
    CASE 
        WHEN pd.Lowest_Pension_FundedRatio >= 80 THEN 'Excellent'
        WHEN pd.Lowest_Pension_FundedRatio >= 60 THEN 'Good'
        WHEN pd.Lowest_Pension_FundedRatio >= 40 THEN 'Fair'
        ELSE 'Critical'
    END AS Pension_Rating

FROM `${PROJECT_ID}.${DATASET_ID}.vw_EntitySummary` es
LEFT JOIN revenue_totals rt ON es.Code = rt.Code
LEFT JOIN expenditure_totals et ON es.Code = et.Code
LEFT JOIN fund_balances fb ON es.Code = fb.Code
LEFT JOIN debt_totals dt ON es.Code = dt.Code
LEFT JOIN pension_data pd ON es.Code = pd.Code;


-- =============================================================================
-- STEP 6: Create County Summary View
-- =============================================================================

CREATE OR REPLACE VIEW `${PROJECT_ID}.${DATASET_ID}.vw_CountySummary` AS
SELECT 
    County,
    COUNT(DISTINCT Code) AS Entity_Count,
    COUNT(DISTINCT EntityType) AS Entity_Type_Count,
    SUM(Population) AS Total_Population,
    SUM(EAV) AS Total_EAV,
    SUM(Total_Revenue) AS Total_Revenue,
    SUM(Total_Expenditure) AS Total_Expenditure,
    SUM(Total_Debt) AS Total_Debt,
    AVG(Operating_Margin) AS Avg_Operating_Margin,
    AVG(Fund_Balance_Ratio) AS Avg_Fund_Balance_Ratio,
    AVG(Debt_Per_Capita) AS Avg_Debt_Per_Capita
FROM `${PROJECT_ID}.${DATASET_ID}.vw_FiscalHealth`
GROUP BY County
ORDER BY Total_Population DESC;


-- =============================================================================
-- STEP 7: Create Entity Type Summary View
-- =============================================================================

CREATE OR REPLACE VIEW `${PROJECT_ID}.${DATASET_ID}.vw_EntityTypeSummary` AS
SELECT 
    EntityType,
    COUNT(DISTINCT Code) AS Entity_Count,
    SUM(Population) AS Total_Population,
    SUM(EAV) AS Total_EAV,
    SUM(Total_Revenue) AS Total_Revenue,
    SUM(Total_Expenditure) AS Total_Expenditure,
    AVG(Revenue_Per_Capita) AS Avg_Revenue_Per_Capita,
    AVG(Expenditure_Per_Capita) AS Avg_Expenditure_Per_Capita,
    AVG(Operating_Margin) AS Avg_Operating_Margin,
    AVG(Fund_Balance_Ratio) AS Avg_Fund_Balance_Ratio
FROM `${PROJECT_ID}.${DATASET_ID}.vw_FiscalHealth`
GROUP BY EntityType
ORDER BY Entity_Count DESC;


-- =============================================================================
-- STEP 8: Create Peer Comparison View
-- =============================================================================

CREATE OR REPLACE VIEW `${PROJECT_ID}.${DATASET_ID}.vw_PeerPercentiles` AS
SELECT 
    EntityType,
    
    -- Population percentiles
    PERCENTILE_CONT(Population, 0.25) OVER (PARTITION BY EntityType) AS Population_P25,
    PERCENTILE_CONT(Population, 0.50) OVER (PARTITION BY EntityType) AS Population_P50,
    PERCENTILE_CONT(Population, 0.75) OVER (PARTITION BY EntityType) AS Population_P75,
    
    -- Revenue per capita percentiles
    PERCENTILE_CONT(Revenue_Per_Capita, 0.25) OVER (PARTITION BY EntityType) AS RevPerCapita_P25,
    PERCENTILE_CONT(Revenue_Per_Capita, 0.50) OVER (PARTITION BY EntityType) AS RevPerCapita_P50,
    PERCENTILE_CONT(Revenue_Per_Capita, 0.75) OVER (PARTITION BY EntityType) AS RevPerCapita_P75,
    
    -- Operating margin percentiles
    PERCENTILE_CONT(Operating_Margin, 0.25) OVER (PARTITION BY EntityType) AS OpMargin_P25,
    PERCENTILE_CONT(Operating_Margin, 0.50) OVER (PARTITION BY EntityType) AS OpMargin_P50,
    PERCENTILE_CONT(Operating_Margin, 0.75) OVER (PARTITION BY EntityType) AS OpMargin_P75,
    
    -- Fund balance ratio percentiles
    PERCENTILE_CONT(Fund_Balance_Ratio, 0.25) OVER (PARTITION BY EntityType) AS FBRatio_P25,
    PERCENTILE_CONT(Fund_Balance_Ratio, 0.50) OVER (PARTITION BY EntityType) AS FBRatio_P50,
    PERCENTILE_CONT(Fund_Balance_Ratio, 0.75) OVER (PARTITION BY EntityType) AS FBRatio_P75

FROM `${PROJECT_ID}.${DATASET_ID}.vw_FiscalHealth`
WHERE Population > 0;


-- =============================================================================
-- STEP 9: Create Rankings View
-- =============================================================================

CREATE OR REPLACE VIEW `${PROJECT_ID}.${DATASET_ID}.vw_EntityRankings` AS
SELECT 
    Code,
    UnitName,
    EntityType,
    County,
    Population,
    EAV,
    Total_Revenue,
    Total_Expenditure,
    
    -- Statewide rankings
    RANK() OVER (ORDER BY Population DESC) AS Rank_Population_Statewide,
    RANK() OVER (ORDER BY EAV DESC) AS Rank_EAV_Statewide,
    RANK() OVER (ORDER BY Total_Revenue DESC) AS Rank_Revenue_Statewide,
    
    -- Rankings within entity type
    RANK() OVER (PARTITION BY EntityType ORDER BY Population DESC) AS Rank_Population_ByType,
    RANK() OVER (PARTITION BY EntityType ORDER BY Total_Revenue DESC) AS Rank_Revenue_ByType,
    
    -- Rankings within county
    RANK() OVER (PARTITION BY County ORDER BY Population DESC) AS Rank_Population_ByCounty,
    RANK() OVER (PARTITION BY County ORDER BY Total_Revenue DESC) AS Rank_Revenue_ByCounty

FROM `${PROJECT_ID}.${DATASET_ID}.vw_FiscalHealth`
WHERE Population > 0;


-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================

-- Verify data loaded correctly
-- SELECT COUNT(*) as entity_count FROM `${PROJECT_ID}.${DATASET_ID}.UnitData`;
-- SELECT COUNT(*) as stats_count FROM `${PROJECT_ID}.${DATASET_ID}.UnitStats`;
-- SELECT COUNT(*) as revenue_rows FROM `${PROJECT_ID}.${DATASET_ID}.Revenues`;

-- Test Entity Summary View
-- SELECT * FROM `${PROJECT_ID}.${DATASET_ID}.vw_EntitySummary` LIMIT 10;

-- Test Fiscal Health View
-- SELECT * FROM `${PROJECT_ID}.${DATASET_ID}.vw_FiscalHealth` WHERE Population > 50000 ORDER BY Population DESC LIMIT 10;

-- Test County Summary
-- SELECT * FROM `${PROJECT_ID}.${DATASET_ID}.vw_CountySummary` ORDER BY Total_Population DESC LIMIT 10;
