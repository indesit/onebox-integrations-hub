import sys
import os
from sqlmodel import Session, text

# Add project path to sys.path
sys.path.append('/root/.openclaw/workspace/projects/onebox-integrations-hub')
from src.core.database import engine

def check_articles():
    with Session(engine) as session:
        print('CHECKING BRA SIZES FOR SPECIFIC ARTICLES:')
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
        FROM dim_product_variants 
        WHERE characteristic_article IN ('422-144-SEQ-M', '193-093-QB4-XS')
        """)
        res = session.execute(sql).all()
        for row in res:
            print(f"Article: {row[0]}")
            print(f"  Name: {row[1]} ({row[2]})")
            print(f"  Sizes: Cup={row[3]}, Underbust={row[4]}, Panty={row[5]}, Swim={row[6]}, Swim_P={row[7]}, Sleep={row[8]}")
            print(f"  Osobennosti: {row[9]}")
            print("-" * 20)

if __name__ == "__main__":
    check_articles()
