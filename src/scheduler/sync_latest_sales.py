import sys
from datetime import datetime
import httpx
from sqlmodel import Session
from src.core.database import engine
from src.core.etl import ETLLayer
from src.config.settings import settings

sys.path.append('/root/.openclaw/workspace/projects/onebox-integrations-hub')

def sync_latest_sales():
    url = "http://91.202.6.56/SecretShopBAS/hs/reports/receipt_lines"
    auth = (settings.baf_user, settings.baf_password)
    
    d_from = "2026-03-14"
    d_to = "2026-03-17" # Cover today and tomorrow
    
    print(f"Fetching sales from {d_from} to {d_to}...")
    
    with httpx.Client(timeout=180.0) as client:
        response = client.get(url, params={"date_from": d_from, "date_to": d_to}, auth=auth)
        
        if response.status_code == 200:
            data = response.json()
            rows = data if isinstance(data, list) else data.get("rows", [])
            print(f"Received {len(rows)} rows from BAF.")
            
            if rows:
                with Session(engine) as session:
                    etl = ETLLayer(session)
                    load_id = etl.stage_receipt_lines(rows)
                    print(f"Staged with load_id: {load_id}")
                    etl.process_fact_sales(load_id)
                    print(f"Processing complete.")
            else:
                print("No rows returned.")
        else:
            print(f"API Error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    sync_latest_sales()
