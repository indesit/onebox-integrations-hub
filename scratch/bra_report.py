import sys
import os
import json
from sqlmodel import Session, text

# Add project path to sys.path
sys.path.append('/root/.openclaw/workspace/projects/onebox-integrations-hub')
from src.core.database import engine

def get_bra_report_detailed(date_from='2026-03-01', date_to='2026-03-15'):
    with Session(engine) as session:
        # SQL query matching the visual structure: Store -> Receipt -> Subtotal
        sql = text("""
        SELECT 
            COALESCE(s.store_name, CAST(f.store_uuid AS TEXT)) as store_name,
            f.receipt_number,
            f.receipt_datetime,
            SUM(f.qty) as qty,
            SUM(f.line_amount) as amount
        FROM fact_sales_receipt_items f
        JOIN dim_product_variants p ON f.product_uuid = p.product_uuid 
            AND (f.characteristic_uuid = p.characteristic_uuid OR (f.characteristic_uuid IS NULL AND p.characteristic_uuid IS NULL))
        LEFT JOIN dim_stores s ON f.store_uuid = s.store_uuid
        WHERE date(f.receipt_datetime) BETWEEN :d_from AND :d_to
          AND (
            p."group" ILIKE '%Бюст%' 
            OR p.category ILIKE '%Бюст%' 
            OR p.product_name ILIKE '%Бюст%'
            OR p."group" ILIKE '%Пуш%'
            OR p."group" ILIKE '%Бра%'
          )
        GROUP BY s.store_name, f.store_uuid, f.receipt_number, f.receipt_datetime, f.receipt_uuid
        ORDER BY store_name, f.receipt_datetime ASC;
        """)
        
        rows = session.execute(sql, {"d_from": date_from, "d_to": date_to}).all()
        
        if not rows:
            print('NO_DATA_FOUND')
            return

        current_store = None
        store_qty = 0
        store_amount = 0
        grand_qty = 0
        grand_amount = 0
        
        print(f"{'Магазин / Чек':<30} | {'Дата':<10} | {'К-сть':>5} | {'Сума':>12}")
        print("-" * 65)
        
        for row in rows:
            store, doc, dt, qty, amount = row
            
            if store != current_store:
                if current_store is not None:
                    print("-" * 65)
                    print(f"{'Разом ' + current_store:<30} | {'':<10} | {store_qty:>5.0f} | {store_amount:>12,.2f}")
                    print("=" * 65)
                current_store = store
                store_qty = 0
                store_amount = 0
                print(f"\n{store}")
            
            date_str = dt.strftime('%d.%m.%y')
            print(f"  {doc:<28} | {date_str:<10} | {qty:>5.0f} | {amount:>12,.2f}")
            
            store_qty += qty
            store_amount += amount
            grand_qty += qty
            grand_amount += amount
            
        # Last store subtotal
        print("-" * 65)
        print(f"{'Разом ' + current_store:<30} | {'':<10} | {store_qty:>5.0f} | {store_amount:>12,.2f}")
        print("=" * 65)
        print(f"{'ВСЬОГО':<30} | {'':<10} | {grand_qty:>5.0f} | {grand_amount:>12,.2f}")

if __name__ == "__main__":
    get_bra_report_detailed()
