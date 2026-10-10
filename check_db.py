import psycopg2
import pandas as pd

SUPABASE_CONN_STRING = "postgresql://postgres.pafsrnguwnpagyytzirx:pacekiosk2027@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres"

def check_database():
    try:
        conn = psycopg2.connect(SUPABASE_CONN_STRING)
        print("✅ SUCCESS: Connected to Supabase Database!\n")
        
        tables = ["patients", "patient_logs", "appointments", "prescriptions"]
        
        for table in tables:
            print(f"=================== TABLE: {table.upper()} ===================")
            try:
                df = pd.read_sql_query(f"SELECT * FROM {table} ORDER BY 1 DESC LIMIT 5", conn)
                if df.empty:
                    print(f"⚠️ Table '{table}' exists but has 0 records.\n")
                else:
                    print(df.to_string(index=False))
                    print("\n")
            except Exception as e:
                print(f"❌ Could not query table '{table}': {e}\n")
                
        conn.close()
    except Exception as e:
        print(f"❌ DATABASE CONNECTION FAILED: {e}")

if __name__ == "__main__":
    check_database()