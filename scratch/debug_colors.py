import sys
import os
import httpx
import json
from sqlmodel import Session, text

# Add project path to sys.path
sys.path.append('/root/.openclaw/workspace/projects/onebox-integrations-hub')
from src.core.database import engine
from src.config.settings import settings

def debug_specific_articles():
    articles = [
        '11278298-YEL-36DM',
        '904-528-QD6-34C',
        '398-454-GQT-36C',
        '429-866-QС5-34B'
    ]
    
    # 1. Check in our DB (dim_product_variants)
    print("--- 1. DATABASE CHECK (dim_product_variants) ---")
    with Session(engine) as session:
        for art in articles:
            sql = text("SELECT characteristic_article, color, product_name, characteristic_name FROM dim_product_variants WHERE characteristic_article = :art")
            res = session.execute(sql, {"art": art}).first()
            if res:
                print(f"DB [{art}]: Color='{res.color}', Name='{res.product_name} ({res.characteristic_name})'")
            else:
                print(f"DB [{art}]: NOT FOUND")
    
    # 2. Check in BAF API directly
    print("\n--- 2. BAF API DIRECT CHECK ---")
    url = 'http://91.202.6.56/SecretShopBAS/hs/reports/product_catalog'
    auth = (settings.baf_user, settings.baf_password)
    
    for art in articles:
        try:
            r = httpx.get(url, params={'characteristic_article': art}, auth=auth, timeout=60)
            if r.status_code == 200:
                data = r.json()
                rows = data if isinstance(data, list) else data.get('rows', [])
                found = [row for row in rows if row.get('characteristic_article') == art]
                if found:
                    item = found[0]
                    print(f"BAF [{art}]: Color='{item.get('color')}', Group='{item.get('group')}', Cat='{item.get('category')}'")
                else:
                    print(f"BAF [{art}]: NOT FOUND in result set")
            else:
                print(f"BAF [{art}]: API ERROR {r.status_code}")
        except Exception as e:
            print(f"BAF [{art}]: EXCEPTION {str(e)}")

if __name__ == "__main__":
    debug_specific_articles()
