"""Sales Analytics & P&L Draft (HUB-010)."""

from sqlmodel import Session, select, func
from src.core.database import engine
from src.core.models_db import Receipt, ReceiptItem, Product
import json

class SalesAnalytics:
    @staticmethod
    def get_daily_sales_summary():
        """Returns total revenue and receipt count per day."""
        with Session(engine) as session:
            # Query: Group by date (ignoring time), sum total_sum, count receipts
            # Note: PostgreSQL specific date truncation
            statement = select(
                func.date_trunc('day', Receipt.cdate).label('day'),
                func.sum(Receipt.total_sum).label('revenue'),
                func.count(Receipt.id).label('count')
            ).group_by('day').order_by('day')
            
            results = session.exec(statement).all()
            return [{"date": str(r.day.date()), "revenue": float(r.revenue), "receipts": r.count} for r in results]

    @staticmethod
    def get_top_selling_characteristics(limit: int = 5):
        """Analyze JSONB characteristics (Size, Cup, Color) to find bestsellers."""
        # This is a raw SQL query because JSONB extraction is complex in ORM
        query = """
            SELECT 
                variant_characteristics->>'size' as size,
                variant_characteristics->>'cup' as cup,
                variant_characteristics->>'color' as color,
                SUM(count) as units_sold
            FROM receiptitem
            GROUP BY size, cup, color
            ORDER BY units_sold DESC
            LIMIT :limit
        """
        with Session(engine) as session:
            results = session.execute(query, {"limit": limit}).all()
            return [dict(r) for r in results]

    @staticmethod
    def get_category_sales():
        """Group sales by product category."""
        with Session(engine) as session:
            statement = select(
                Product.category,
                func.sum(ReceiptItem.count).label('units'),
                func.sum(ReceiptItem.price * ReceiptItem.count).label('revenue')
            ).join(ReceiptItem).group_by(Product.category).order_by(func.sum(ReceiptItem.count).desc())
            
            results = session.exec(statement).all()
            return [{"category": r.category or "Uncategorized", "units": float(r.units), "revenue": float(r.revenue)} for r in results]

if __name__ == "__main__":
    # Example usage for Anton
    print("--- Daily Sales Summary ---")
    print(SalesAnalytics.get_daily_sales_summary())
    
    print("\n--- Top Characteristics (Bestsellers Matrix) ---")
    print(SalesAnalytics.get_top_selling_characteristics())
