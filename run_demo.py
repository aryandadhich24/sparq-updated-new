import sys
import os
import json

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from fastapi.testclient import TestClient
from app.main import app

def run_walkthrough():
    client = TestClient(app)
    
    print("\n--- 1. Reset Data ---")
    res = client.delete("/api/v1/reset")
    print(res.json())

    print("\n--- 2. Seed Data (Decisions) ---")
    res = client.post("/api/v1/seed")
    print(res.json())
    
    print("\n--- 3. Ingest Data (Mock HubSpot) ---")
    res = client.post("/api/v1/ingest/hubspot")
    print(res.json())
    
    print("\n--- 4. Calculate Attribution ---")
    res = client.post("/api/v1/attribution/calculate")
    print(res.json())
    
    print("\n--- 5. View Decision Ledger ---")
    res = client.get("/api/v1/decisions")
    decisions = res.json()
    
    print(f"Found {len(decisions)} decisions.")
    for d in decisions:
        print(f"[{d['description']}] Type: {d['type']}")
        print(f"  Cost: ${d['total_cost']:,.2f} | Attributed Value: ${d['value']:,.2f}")
        print(f"  ROI: {d['roi']:.2f}x | Action: {d['action']}")
        print("-" * 40)

if __name__ == "__main__":
    run_walkthrough()
