"""Database utilities for SPECTER"""
import requests
import json
from config import SUPABASE_URL, SUPABASE_KEY

def get_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }

def insert_records(table_name, records, batch_size=100):
    """Insert records into Supabase table in batches"""
    url = f"{SUPABASE_URL}/rest/v1/{table_name}"
    headers = get_headers()

    inserted = 0
    errors = []

    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        try:
            response = requests.post(url, headers=headers, json=batch)
            if response.status_code in (200, 201):
                inserted += len(batch)
            else:
                errors.append(f"Batch {i//batch_size}: {response.status_code} - {response.text[:200]}")
        except Exception as e:
            errors.append(f"Batch {i//batch_size}: {str(e)}")

    return inserted, errors

def query_table(table_name, select="*", filters=None, limit=1000):
    """Query Supabase table"""
    url = f"{SUPABASE_URL}/rest/v1/{table_name}?select={select}"
    if filters:
        url += f"&{filters}"
    url += f"&limit={limit}"

    headers = get_headers()
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Query error: {response.status_code} - {response.text}")
        return []

def execute_rpc(function_name, params=None):
    """Execute a Supabase RPC function"""
    url = f"{SUPABASE_URL}/rest/v1/rpc/{function_name}"
    headers = get_headers()

    response = requests.post(url, headers=headers, json=params or {})
    return response.json() if response.status_code == 200 else None
