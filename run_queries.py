import sqlite3
import pandas as pd

DB = r"C:\Users\muza\Projects\olist-analysis\data\olist.db"
conn = sqlite3.connect(DB)
pd.set_option("display.max_columns", 10)
pd.set_option("display.width", 120)

queries = {
    "1. Business Overview": """
        SELECT COUNT(DISTINCT o.order_id) AS total_orders,
               COUNT(DISTINCT o.customer_id) AS total_customers,
               ROUND(SUM(i.price + i.freight_value), 2) AS total_revenue,
               ROUND(AVG(i.price + i.freight_value), 2) AS avg_order_value
        FROM orders o JOIN order_items i ON o.order_id = i.order_id
        WHERE o.order_status = 'delivered'
    """,
    "2. Top 5 Categories": """
        SELECT p.product_category_name AS category,
               COUNT(DISTINCT o.order_id) AS orders,
               ROUND(SUM(i.price), 2) AS revenue
        FROM order_items i
        JOIN orders o ON i.order_id = o.order_id
        JOIN products p ON i.product_id = p.product_id
        WHERE o.order_status = 'delivered'
        GROUP BY category ORDER BY revenue DESC LIMIT 5
    """,
    "3. Payment Methods": """
        SELECT payment_type, COUNT(DISTINCT order_id) AS orders,
               ROUND(SUM(payment_value), 2) AS total_value
        FROM payments GROUP BY payment_type ORDER BY total_value DESC
    """,
    "4. RFM Segments": """
        WITH rfm_base AS (
            SELECT o.customer_id,
                CAST(JULIANDAY('2018-10-01') - JULIANDAY(MAX(o.order_purchase_timestamp)) AS INT) AS recency,
                COUNT(DISTINCT o.order_id) AS frequency,
                ROUND(SUM(i.price + i.freight_value), 2) AS monetary
            FROM orders o JOIN order_items i ON o.order_id = i.order_id
            WHERE o.order_status = 'delivered' GROUP BY o.customer_id
        ),
        rfm_scores AS (
            SELECT *, NTILE(5) OVER (ORDER BY recency DESC) AS r_score,
                NTILE(5) OVER (ORDER BY frequency) AS f_score,
                NTILE(5) OVER (ORDER BY monetary) AS m_score FROM rfm_base
        ),
        segments AS (
            SELECT *, CASE
                WHEN r_score >= 4 AND f_score >= 4 THEN 'Champions'
                WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
                WHEN r_score >= 4 AND f_score <= 2 THEN 'Recent Customers'
                WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
                WHEN r_score <= 2 AND f_score <= 2 THEN 'Lost'
                ELSE 'Potential Loyalists' END AS segment FROM rfm_scores
        )
        SELECT segment, COUNT(*) AS customers,
               ROUND(AVG(monetary), 2) AS avg_ltv,
               ROUND(SUM(monetary), 2) AS total_revenue
        FROM segments GROUP BY segment ORDER BY total_revenue DESC
    """
}

for name, sql in queries.items():
    print(f"\n{'='*60}")
    print(f"  {name}")
    print('='*60)
    print(pd.read_sql(sql, conn).to_string(index=False))

conn.close()
