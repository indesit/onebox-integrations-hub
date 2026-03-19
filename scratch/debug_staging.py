import sys
import os
from sqlmodel import Session, text

# Add project path to sys.path
sys.path.append('/root/.openclaw/workspace/projects/onebox-integrations-hub')
from src.core.database import engine

def debug_staging_article():
    with Session(engine) as session:
        print('DIAGNOSING STAGING DATA FOR 422-144-SEQ-M:')
        sql = text("""
        SELECT 
            characteristic_article, 
            product_name, 
            characteristic_name,
            razmer_chashki, 
            obxvat_grudi,
            razmer_trusikov,
            razmer_swim,
            razmer_plavok,
            razmer_sleep,
            osobennosti
        FROM stg_baf_product_catalog 
        WHERE characteristic_article = '422-144-SEQ-M'
        LIMIT 1;
        """)
        res = session.execute(sql).all()
        if res:
            r = res[0]
            print(f"Article: {r[0]}")
            print(f"Name: {r[1]} / {r[2]}")
            print(f"Sizes in Staging: Cup='{r[3]}', Underbust='{r[4]}', Panty='{r[5]}', Swim='{r[6]}', Swim_P='{r[7]}', Sleep='{r[8]}'")
            print(f"Features: {r[9]}")
        else:
            print("Article NOT FOUND in stg_baf_product_catalog")

if __name__ == "__main__":
    debug_staging_article()
