from fastapi import FastAPI, HTTPException
from pymongo import MongoClient
from datetime import datetime, timedelta
import google.generativeai as genai
import json
import os
import re
import certifi  # <--- Added for SSL Fix

# =========================================================
# CONFIG
# =========================================================

# IMPORTANT:
# - Database name is explicitly included
# - No manual TLS flags (Atlas handles TLS)
MONGO_URI = (
    "mongodb+srv://kvivek1023_db_user:"
    "agevKM97gG9VGRbX"
    "@cluster0.bnksytl.mongodb.net/"
    "shipments_db"
    "?retryWrites=true&w=majority"
)

DB_NAME = "shipments_db"
COLLECTION_NAME = "shipments"


# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY environment variable not set")

genai.configure(api_key=GEMINI_API_KEY)

# =========================================================
# MONGODB CLIENT (CLEAN)
# =========================================================

# SSL FIX: Explicitly tell pymongo where to find the certificate authority
mongo_client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())

db = mongo_client[DB_NAME]
collection = db[COLLECTION_NAME]

# =========================================================
# GEMINI MODEL
# =========================================================

model = genai.GenerativeModel("gemini-2.5-flash")

# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(title="Shipment Natural Language Query API")

# =========================================================
# TIME HELPERS
# =========================================================


def current_month_range():
    now = datetime.now()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, now


# =========================================================
# JSON EXTRACTION (ROBUST)
# =========================================================


def extract_json(text: str) -> dict:
    """
    Extract JSON from Gemini output.
    Handles markdown fences and stray text.
    """
    text = text.strip()

    # Remove markdown fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text)
        text = re.sub(r"```$", "", text)
        text = text.strip()

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON found")

    return json.loads(match.group())


# =========================================================
# GEMINI QUERY PARSER
# =========================================================


def gemini_parse_query(query: str) -> dict:
    prompt = f"""
You are a query parser.

Convert the user query into a JSON object
that STRICTLY follows this schema:

{{
  "operation": "count | sum | group | top | filter",
  "time_range": "current_month | last_7_days | none",
  "group_by": "status | none",
  "field": "discounted_cost | none",
  "limit": number | null
}}

Rules:
- Return ONLY valid JSON
- Do NOT explain anything
- Do NOT wrap in markdown
- Use discounted_cost when cost is mentioned
- If unsure, use "none"

User query:
"{query}"
"""

    response = model.generate_content(prompt)

    try:
        return extract_json(response.text)
    except Exception:
        raise HTTPException(
            status_code=400, detail=f"Gemini returned invalid JSON: {response.text}"
        )


# =========================================================
# EXECUTION ENGINE (DETERMINISTIC)
# =========================================================


def execute_intent(intent: dict):
    operation = intent["operation"]
    time_range = intent["time_range"]
    field = intent["field"]
    group_by = intent["group_by"]
    limit = intent["limit"]

    match_stage = {}

    if time_range == "current_month":
        start, end = current_month_range()
        match_stage["ship_date"] = {"$gte": start, "$lte": end}

    if time_range == "last_7_days":
        cutoff = datetime.utcnow() - timedelta(days=7)
        match_stage["ship_date"] = {"$gte": cutoff}

    # COUNT
    if operation == "count":
        return collection.count_documents(match_stage)

    # SUM
    if operation == "sum":
        pipeline = []
        if match_stage:
            pipeline.append({"$match": match_stage})
        pipeline.append({"$group": {"_id": None, "total": {"$sum": f"${field}"}}})
        return list(collection.aggregate(pipeline))

    # GROUP
    if operation == "group":
        pipeline = []
        if match_stage:
            pipeline.append({"$match": match_stage})
        pipeline.append(
            {
                "$group": {
                    "_id": f"${group_by}",
                    "count": {"$sum": 1},
                    "total_cost": {"$sum": f"${field}"},
                }
            }
        )
        return list(collection.aggregate(pipeline))

    # TOP
    if operation == "top":
        return list(
            collection.find(match_stage, {"_id": 0}).sort(field, -1).limit(limit or 5)
        )

    # FILTER
    if operation == "filter":
        return list(collection.find(match_stage, {"_id": 0}))

    raise HTTPException(status_code=400, detail="Unsupported operation")


# =========================================================
# ROUTES
# =========================================================


@app.get("/")
def health():
    return {"status": "ok", "message": "Shipment API running"}


@app.post("/query")
def query_shipments(payload: dict):
    query = payload.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")

    intent = gemini_parse_query(query)
    result = execute_intent(intent)

    return {"query": query, "intent": intent, "result": result}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)

