from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.models.search_log import SearchLog
from app.models.quotation import QuotationHistory

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


def _bracket_samples(db: Session, condition_sql: str) -> list:
    """Fetch real tile samples for a stock-aging bracket. Empty list if none."""
    try:
        q = text(f"""
            SELECT
                t.id,
                t.name,
                t.sku,
                COALESCE(
                    (SELECT ti.image_url FROM tile_images ti
                     WHERE ti.tile_id = t.id
                     ORDER BY ti.is_primary DESC, ti.id ASC
                     LIMIT 1),
                    ''
                ) AS img,
                COALESCE(i.quantity, 0) AS stock_qty,
                COALESCE(i.restocked_at::date, CURRENT_DATE) AS batch_dt
            FROM tiles t
            INNER JOIN inventory i ON i.tile_id = t.id
            WHERE {condition_sql}
            ORDER BY i.quantity DESC
            LIMIT 4
        """)
        rows = db.execute(q).fetchall()
        return [
            {
                "id": r[0],
                "name": str(r[1]),
                "sku": str(r[2]),
                "image_url": str(r[3] or ""),
                "quantity": int(r[4] or 0),
                "date": str(r[5]),
            }
            for r in rows
        ]
    except Exception as e:
        print(f"[ANALYTICS SAMPLES]: {e}")
        db.rollback()
        return []


@router.get("/summary")
def get_factory_analytics(db: Session = Depends(get_db)):
    aging_query = text("""
        SELECT
            COALESCE(SUM(CASE WHEN COALESCE(restocked_at, CURRENT_TIMESTAMP) >= CURRENT_TIMESTAMP - INTERVAL '90 days' THEN quantity ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN restocked_at < CURRENT_TIMESTAMP - INTERVAL '90 days' AND restocked_at >= CURRENT_TIMESTAMP - INTERVAL '180 days' THEN quantity ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN restocked_at < CURRENT_TIMESTAMP - INTERVAL '180 days' THEN quantity ELSE 0 END), 0),
            COALESCE(SUM(quantity), 0)
        FROM inventory
    """)
    aging_res = db.execute(aging_query).fetchone()

    fresh_samples = _bracket_samples(
        db, "i.restocked_at >= CURRENT_TIMESTAMP - INTERVAL '90 days'"
    )
    medium_samples = _bracket_samples(
        db,
        "i.restocked_at < CURRENT_TIMESTAMP - INTERVAL '90 days' "
        "AND i.restocked_at >= CURRENT_TIMESTAMP - INTERVAL '180 days'",
    )
    aged_samples = _bracket_samples(
        db, "i.restocked_at < CURRENT_TIMESTAMP - INTERVAL '180 days'"
    )

    # Production vs sales from live inventory + quotations
    inv_stats = db.execute(text("""
        SELECT
            COALESCE(SUM(
                CASE WHEN i.unit = 'sqm' THEN i.quantity
                     ELSE i.quantity * COALESCE(t.width_cm, 0) * COALESCE(t.height_cm, 0) / 10000.0
                END
            ), 0),
            COALESCE(SUM(i.quantity * COALESCE(t.price_per_sqm, 0)), 0)
        FROM inventory i
        JOIN tiles t ON t.id = i.tile_id
    """)).fetchone()
    stock_sqm = float(inv_stats[0] or 0)

    sold_row = db.execute(text("""
        SELECT COALESCE(SUM(total_amount), 0), COUNT(*)
        FROM quotations_history
    """)).fetchone()
    quote_revenue = float(sold_row[0] or 0)
    quote_count = int(sold_row[1] or 0)

    # Approximate sold sqm from order_items when present; else leave 0
    sold_sqm = 0.0
    try:
        sold_sqm = float(db.execute(text("""
            SELECT COALESCE(SUM(
                oi.quantity * COALESCE(t.width_cm, 0) * COALESCE(t.height_cm, 0) / 10000.0
            ), 0)
            FROM order_items oi
            JOIN tiles t ON t.id = oi.tile_id
        """)).scalar() or 0)
    except Exception:
        db.rollback()

    total_handled = stock_sqm + sold_sqm
    efficiency = round((sold_sqm / total_handled) * 100, 1) if total_handled > 0 else 0.0

    # Top materials by current stock value / volume
    top_materials = []
    try:
        rows = db.execute(text("""
            SELECT
                m.name,
                ROUND(SUM(
                    CASE WHEN i.unit = 'sqm' THEN i.quantity
                         ELSE i.quantity * COALESCE(t.width_cm, 0) * COALESCE(t.height_cm, 0) / 10000.0
                    END
                )::numeric, 1) AS volume_sqm,
                ROUND(SUM(i.quantity * COALESCE(t.price_per_sqm, 0))::numeric, 2) AS revenue
            FROM inventory i
            JOIN tiles t ON t.id = i.tile_id
            JOIN materials m ON m.id = t.material_id
            GROUP BY m.name
            HAVING SUM(i.quantity) > 0
            ORDER BY volume_sqm DESC
            LIMIT 5
        """)).fetchall()
        top_materials = [
            {
                "material": str(r[0]),
                "volume_sqm": float(r[1] or 0),
                "revenue": float(r[2] or 0),
            }
            for r in rows
        ]
    except Exception as e:
        print(f"[ANALYTICS TOP MATERIALS]: {e}")
        db.rollback()

    return {
        "stock_aging": {
            "fresh_under_90": int(aging_res[0] or 0),
            "medium_90_180": int(aging_res[1] or 0),
            "aged_over_180": int(aging_res[2] or 0),
            "total_inventory_pieces": int(aging_res[3] or 0),
            "samples": {
                "fresh": fresh_samples,
                "medium": medium_samples,
                "aged": aged_samples,
            },
        },
        "production_vs_sales": {
            "total_produced_sqm": round(stock_sqm + sold_sqm, 1),
            "total_sold_sqm": round(sold_sqm, 1),
            "efficiency_ratio": f"{efficiency}%",
            "quotation_revenue": quote_revenue,
            "quotation_count": quote_count,
        },
        "top_selling_materials": top_materials,
    }


@router.get("/funnel-and-clients")
def get_funnel_and_clients(db: Session = Depends(get_db)):
    try:
        search_count = db.query(SearchLog).count()
    except Exception as e:
        print("[ANALYTICS ERROR - SearchLog count]:", e)
        db.rollback()
        search_count = 0

    try:
        quote_count = db.query(QuotationHistory).count()
    except Exception as e:
        print("[ANALYTICS ERROR - Quotations count]:", e)
        db.rollback()
        quote_count = 0

    search_to_quote_rate = (
        round((quote_count / search_count) * 100, 1) if search_count > 0 else 0.0
    )
    # Without a separate orders-closed flag, closed orders ≈ quotations for now
    closed_orders = quote_count
    quote_to_sale_rate = 100.0 if quote_count > 0 else 0.0

    top_clients = []
    try:
        clients_query = text("""
            SELECT company_name, client_name, COUNT(id) AS total_orders,
                   SUM(total_amount) AS revenue
            FROM quotations_history
            GROUP BY company_name, client_name
            ORDER BY revenue DESC
            LIMIT 5
        """)
        for r in db.execute(clients_query).fetchall():
            top_clients.append({
                "company": str(r[0]),
                "contact": str(r[1]),
                "total_orders": int(r[2]),
                "revenue": float(r[3] or 0),
            })
    except Exception as e:
        print("[ANALYTICS ERROR - Top Clients]:", e)
        db.rollback()

    return {
        "sales_funnel": {
            "total_visual_searches": search_count,
            "quotations_generated": quote_count,
            "orders_closed": closed_orders,
            "search_to_quote_conversion": f"{search_to_quote_rate}%",
            "quote_to_sale_conversion": f"{quote_to_sale_rate}%",
            "overall_conversion": f"{search_to_quote_rate}%",
        },
        "top_corporate_clients": top_clients,
    }
