import pandas as pd
from pymongo import MongoClient
import math

# =========================================================
# CONFIG
# =========================================================

MONGO_URI = (
    "mongodb+srv://kvivek1023_db_user:"
"1Vwy8zwYr8EoGjQc"
"@cluster0.bnksytl.mongodb.net/"
"?appname=Cluster0"
)

DB_NAME = "shipments_db"
COLLECTION_NAME = "shipments"
EXCEL_FILE = "shipment_data.xlsx"

# =========================================================
# Helpers
# =========================================================

def normalize_columns(columns):
    return [
        c.strip()
         .lower()
         .replace(" ", "_")
         .replace(".", "_")
         .replace("#", "number")
         .replace("/", "_")
        for c in columns
    ]

def clean_record(record):
    """
    Convert NaT / NaN values to None so MongoDB can store them.
    """
    cleaned = {}
    for k, v in record.items():
        if v is None:
            cleaned[k] = None
        elif isinstance(v, float) and math.isnan(v):
            cleaned[k] = None
        elif pd.isna(v):
            cleaned[k] = None
        else:
            cleaned[k] = v
    return cleaned

# =========================================================
# Main ingestion logic
# =========================================================

def ingest_excel_to_mongodb():
    print("📥 Reading Excel file...")
    df = pd.read_excel(EXCEL_FILE)

    print(f"📊 Found {len(df)} rows and {len(df.columns)} columns")

    # Normalize column names dynamically
    df.columns = normalize_columns(df.columns)

    # Convert date-like columns
    for col in df.columns:
        if "date" in col:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Convert DataFrame to records and clean NaT/NaN
    print("🧹 Cleaning records (NaT → None)...")
    records = [clean_record(r) for r in df.to_dict(orient="records")]

    print("🔌 Connecting to MongoDB Atlas...")
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    # Optional: clear existing data
    collection.delete_many({})

    print("🚀 Inserting records...")
    collection.insert_many(records)

    print(f"✅ Successfully inserted {len(records)} shipment records")
    print(f"📂 Database: {DB_NAME}")
    print(f"📁 Collection: {COLLECTION_NAME}")

# =========================================================

if __name__ == "__main__":
    ingest_excel_to_mongodb()
