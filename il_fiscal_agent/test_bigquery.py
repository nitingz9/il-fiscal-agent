"""
BigQuery Connection Test Script

Run this to verify your BigQuery setup and see available tables.

Usage:
    python test_bigquery.py
"""
from google.cloud import bigquery

# Your BigQuery configuration
PROJECT_ID = "project-zion-454116"
DATASET_ID = "comp_financial_insights_2024"

def main():
    print("=" * 60)
    print("BigQuery Connection Test")
    print("=" * 60)
    print(f"\nProject: {PROJECT_ID}")
    print(f"Dataset: {DATASET_ID}\n")
    
    try:
        client = bigquery.Client(project=PROJECT_ID)
        print("✅ BigQuery client created successfully\n")
    except Exception as e:
        print(f"❌ Failed to create BigQuery client: {e}")
        print("\nMake sure you've authenticated:")
        print("  gcloud auth application-default login")
        return
    
    # List tables
    print("Tables in dataset:")
    print("-" * 40)
    
    try:
        dataset_ref = client.dataset(DATASET_ID)
        tables = list(client.list_tables(dataset_ref))
        
        if not tables:
            print("  (No tables found)")
        else:
            for table in tables:
                # Get row count
                table_ref = dataset_ref.table(table.table_id)
                full_table = client.get_table(table_ref)
                print(f"  {table.table_id}: {full_table.num_rows:,} rows")
                
        print(f"\nTotal: {len(tables)} tables")
        
    except Exception as e:
        print(f"❌ Error listing tables: {e}")
        return
    
    # Test a simple query
    print("\n" + "-" * 40)
    print("Testing sample query...")
    
    try:
        query = f"""
        SELECT COUNT(*) as count 
        FROM `{PROJECT_ID}.{DATASET_ID}.UnitData`
        """
        result = client.query(query).result()
        for row in result:
            print(f"✅ UnitData has {row.count:,} rows")
    except Exception as e:
        print(f"❌ Query failed: {e}")
        print("\nThe table might have a different name. Check the table list above.")

    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
