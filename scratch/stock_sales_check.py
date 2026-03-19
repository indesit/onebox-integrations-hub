import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from sqlmodel import Session, select, func, and_
from src.core.database import engine
from src.core.models_db import DimProductVariant, FactSalesReportItem

def get_weekly_sales_by_group(group_name: str):
    """
    Get weekly sales for a specific product group.
    """
    last_week = datetime.utcnow() - timedelta(days=7)
    
    with Session(engine) as session:
        # Join FactSales with DimProductVariant to filter by group
        statement = (
            select(
                DimProductVariant.product_uuid,
                DimProductVariant.characteristic_uuid,
                DimProductVariant.product_name,
                DimProductVariant.characteristic_name,
                DimProductVariant.characteristic_article,
                func.sum(FactSalesReportItem.qty).label("total_sales")
            )
            .join(
                FactSalesReportItem,
                and_(
                    FactSalesReportItem.product_uuid == DimProductVariant.product_uuid,
                    FactSalesReportItem.characteristic_uuid == DimProductVariant.characteristic_uuid
                )
            )
            .where(DimProductVariant.group == group_name)
            .where(FactSalesReportItem.receipt_datetime >= last_week)
            .group_by(
                DimProductVariant.product_uuid,
                DimProductVariant.characteristic_uuid,
                DimProductVariant.product_name,
                DimProductVariant.characteristic_name,
                DimProductVariant.characteristic_article
            )
        )
        
        results = session.exec(statement).all()
        return results

if __name__ == "__main__":
    # Test for "Бюстгальтери" or other group
    group = "Бюстгальтери" 
    print(f"--- Sales for group: {group} (Last 7 days) ---")
    sales = get_weekly_sales_by_group(group)
    for row in sales[:10]: # First 10
        print(f"Article: {row.characteristic_article} | {row.product_name} ({row.characteristic_name}) | Sales: {row.total_sales}")
    
    if not sales:
        print("No sales found for this group in the last 7 days or group name mismatch.")
