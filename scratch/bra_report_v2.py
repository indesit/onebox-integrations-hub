import sys
import os
import csv
import json
from sqlmodel import Session, text

# Add project path to sys.path
sys.path.append('/root/.openclaw/workspace/projects/onebox-integrations-hub')
from src.core.database import engine

def get_bra_report_v2(date_from='2026-03-01', date_to='2026-03-15'):
    output_file = '/root/.openclaw/workspace/projects/onebox-integrations-hub/scratch/bra_sales_report_v2.csv'
    with Session(engine) as session:
        # SQL query refined with Anton's feedback
        sql = text("""
        SELECT 
            COALESCE(s.store_name, CAST(f.store_uuid AS TEXT)) as store_name,
            f.receipt_number,
            f.receipt_datetime,
            p.product_name,
            p.characteristic_name,
            p.characteristic_article,
            p."group",
            p.category,
            p.type,
            p.material,
            p.brand,
            p.napolnenie,
            p.razmer_chashki,
            p.obxvat_grudi,
            p.razmer_trusikov,
            p.razmer_swim,
            p.razmer_plavok,
            p.razmer_sleep,
            p.color,
            p.osobennosti,
            f.qty,
            f.price,
            f.line_amount
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
          -- Exclusion 1: No Body (Боді)
          AND p."group" NOT ILIKE '%Боді%'
          AND p.category NOT ILIKE '%Боді%'
          AND p.product_name NOT ILIKE '%Боді%'
        ORDER BY store_name, f.receipt_datetime ASC;
        """)
        
        rows = session.execute(sql, {"d_from": date_from, "d_to": date_to}).all()
        
        if not rows:
            print('NO_DATA_FOUND')
            return

        with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow([
                'Магазин', 'Номер чека', 'Дата', 'Товар', 'Характеристика', 'Артикул', 
                'Група', 'Категорія', 'Тип', 'Матеріал', 'Бренд', 'Наповнення',
                'Розмір чашки', 'Обхват грудей', 'Розмір (S/M/L)', 'Колір', 'Особливості',
                'Кількість', 'Ціна', 'Сума'
            ])
            
            for r in rows:
                # 3. Handle S/M/L for Bustier (Бюстье) or items without Cup sizes
                size_standard = r[12] or r[13] or r[14] or r[15] or r[16] or r[17]
                
                # Anton: Always use 'color' from BAF if available, fallback to parsing char_name
                color = str(r[18]) if r[18] else "" 
                
                if not color:
                    char_name = str(r[4])
                    if "," in char_name:
                        color = char_name.split(",")[0].strip()
                    elif char_name and not size_standard:
                        color = char_name.strip()
                
                if not size_standard:
                    # Attempt to extract from characteristic name (e.g., "(чорний, XS)")
                    char_name = str(r[4])
                    import re
                    match = re.search(r'\b(XS|S|M|L|XL|XXL|2XL)\b', char_name.upper())
                    if match:
                        size_standard = match.group(0)
                    else:
                        # Attempt to extract from Article suffix (e.g., "422-144-SEQ-M")
                        art = str(r[5])
                        match_art = re.search(r'-(XS|S|M|L|XL|XXL|2XL)$', art.upper())
                        if match_art:
                            size_standard = match_art.group(1)
                
                osob_str = ''
                if r[19] and isinstance(r[19], list):
                    parts = []
                    for o in r[19]:
                        if isinstance(o, dict):
                            parts.append(f"{o.get('name')}: {o.get('value')}")
                        elif isinstance(o, str):
                            parts.append(o)
                    osob_str = ', '.join(parts)
                
                dt_str = r[2].strftime('%d.%m.%Y %H:%M:%S')
                
                writer.writerow([
                    r[0], r[1], dt_str, r[3], r[4], r[5],
                    r[6], r[7], r[8], r[9], r[10], r[11],
                    r[12], r[13], size_standard, color, osob_str,
                    str(r[20]).replace('.', ','), 
                    str(r[21]).replace('.', ','), 
                    str(r[22]).replace('.', ',')
                ])
        print(f'REPORT_GENERATED: {output_file}')

if __name__ == "__main__":
    get_bra_report_v2()
