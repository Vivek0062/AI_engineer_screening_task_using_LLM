# AI_engineer_screening_task_using_LLM
# **Shipment Analytics - AI-Powered Natural Language Query API**

This project provides an end-to-end solution for ingesting shipment data from Excel into MongoDB Atlas and querying that data using natural language through a FastAPI application integrated with Google Gemini AI.

## **Project Structure**

* 'Import_Data.py': A script to read, normalize, and clean shipment data from shipment_data.xlsx and ingest it into a MongoDB collection.  

* LLMQuery.py: A FastAPI application that uses Google Gemini AI to interpret natural language queries and execute corresponding MongoDB aggregation pipelines.  

* requirements.txt: List of Python dependencies (pandas, pymongo, fastapi, uvicorn, google-generativeai, certifi).  

* shipment_data.xlsx: Source data file containing shipment records.

## **Prerequisites**

* Python 3.8+  
* MongoDB Atlas cluster (URI configured in scripts)  
* Google Gemini API Key (required for natural language parsing)

## **Installation**

1. Clone the repository and navigate to the project directory.  
2. Create a virtual environment (recommended):  
   python -m venv venv  
   source venv/bin/activate  # On Windows: venv\Scripts\activate

3. Install the dependencies:  
   pip install -r requirements.txt

4. Set your Gemini API Key as an environment variable:

   set GEMINI_API_KEY=your_actual_key_here

## **Usage**

### **1. Ingest Data**

Before running the API, populate your MongoDB collection with the shipment data.

Run the ingestion script:

python Import_Data.py

This will:

* Read shipment_data.xlsx.  
* Normalize headers (e.g., "Ship Date" becomes ship_date).  
* Clean data by converting NaN and NaT values to None for database compatibility.  
* Insert records into the MongoDB shipments collection.

### **2. Run the API**

Start the FastAPI server:

python LLMQuery.py

The API will be available at http://127.0.0.1:8000.

## **How it Works: LLMQuery Logic**

The LLMQuery.py script acts as an intelligent bridge between the user and the database. Here is the internal workflow:

1. **AI Parsing (gemini_parse_query)**: When a user submits a question, the script sends it to the **Google Gemini AI** model with a strict system prompt. The AI acts as a translator, converting the English sentence into a structured **JSON Intent** (identifying the operation, fields, and time ranges).  

2. **Intent Mapping**: The script validates the AI's output using a robust JSON extractor that strips away any markdown formatting to ensure data integrity.  

3. **Dynamic Query Construction**: The execute_intent function takes the AI's "plan" and builds the actual database query.  
   * It handles **Time Arithmetic** (e.g., calculating the start of the current month).  
   * It constructs **MongoDB Aggregation Pipelines** for complex tasks like grouping data by status or summing up costs. 

4. **Data Retrieval**: The final query is executed against the MongoDB Atlas cluster using pymongo, and the results are formatted for the user.

## **API Endpoints**

### **Health Check**

* **URL**: /  
* **Method**: GET  
* **Response**: {"status": "ok", "message": "Shipment API running"}

### **Query Shipments**

* **URL**: /query  
* **Method**: POST  
* **Body**:  
  {  
    "query": "total cost of shipments this month"  
  }

* **Supported Query Patterns**:  
  * "how many shipments..." (Counts documents)  
  * "total cost / sum of cost..." (Calculates sum of discounted_cost)  
  * "group by status..." (Aggregates count and cost per status)  
  * "top 5 expensive shipments..." (Retrieves highest cost records)  
  * "last 7 days..." (Filters by recent ship_date)

## **Notes**

* **AI Engine**: This project uses gemini-1.5-flash to convert text to structured JSON intents, which are then mapped to deterministic MongoDB queries.  

* **Security**: The MONGO_URI is currently embedded for demonstration. For production, it is recommended to use environment variables.
  
* **Connectivity**: The script uses certifi to ensure secure TLS/SSL connections to MongoDB Atlas.
