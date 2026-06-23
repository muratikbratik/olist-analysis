import sqlite3
import pandas as pd
import os

DB = r"C:\Users\muza\Projects\olist-analysis\data\olist.db"
OUT = r"C:\Users\muza\Projects\olist-analysis\data\powerbi"
os.makedirs(OUT, exist_ok=True)

conn = sqlite3.connect(DB)

# 1. Monthly revenue
monthly = pd.read_sql("""
    SELECT STRFTIME('%Y-%m', o.order_purchase_timestamp) AS month,
           COUNT(DISTINCT o.order_id) AS orders,
           ROUND(SUM(i.price + i.freight_value), 2) AS revenue,
           ROUND(SUM(i.price), 2) AS product_revenue,
           ROUND(SUM(i.freight_value), 2) AS freight_revenue
    FROM orders o JOIN order_items i ON o.order_id = i.order_id
    WHERE o.order_status = 'delivered' AND o.order_purchase_timestamp >= '2017-01-01'
    GROUP BY month ORDER BY month
""", conn)
monthly.to_csv(f"{OUT}/monthly_revenue.csv", index=False)
print(f"✅ monthly_revenue: {len(monthly)} rows")

# 2. Categories
categories = pd.read_sql("""
    SELECT p.product_category_name AS category,
           COUNT(DISTINCT o.order_id) AS orders,
           ROUND(SUM(i.price), 2) AS revenue,
           ROUND(AVG(r.review_score), 2) AS avg_rating
    FROM order_items i
    JOIN orders o ON i.order_id = o.order_id
    JOIN products p ON i.product_id = p.product_id
    LEFT JOIN reviews r ON o.order_id = r.order_id
    WHERE o.order_status = 'delivered' AND p.product_category_name IS NOT NULL
    GROUP BY category ORDER BY revenue DESC
""", conn)
categories.to_csv(f"{OUT}/categories.csv", index=False)
print(f"✅ categories: {len(categories)} rows")

# 3. States
states = pd.read_sql("""
    SELECT c.customer_state AS state,
           COUNT(DISTINCT o.order_id) AS orders,
           ROUND(SUM(i.price + i.freight_value), 2) AS revenue,
           ROUND(AVG(JULIANDAY(o.order_delivered_customer_date)
                 - JULIANDAY(o.order_purchase_timestamp)), 1) AS avg_delivery_days,
           ROUND(SUM(CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
                     THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS late_pct
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN order_items i ON o.order_id = i.order_id
    WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
    GROUP BY state ORDER BY revenue DESC
""", conn)
states.to_csv(f"{OUT}/states.csv", index=False)
print(f"✅ states: {len(states)} rows")

# 4. Payments
payments = pd.read_sql("""
    SELECT payment_type,
           COUNT(DISTINCT order_id) AS orders,
           ROUND(SUM(payment_value), 2) AS total_value,
           ROUND(AVG(payment_value), 2) AS avg_value
    FROM payments GROUP BY payment_type ORDER BY total_value DESC
""", conn)
payments.to_csv(f"{OUT}/payments.csv", index=False)
print(f"✅ payments: {len(payments)} rows")

# 5. RFM segments
rfm = pd.read_sql("""
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
    )
    SELECT *, CASE
        WHEN r_score >= 4 AND f_score >= 4 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
        WHEN r_score >= 4 AND f_score <= 2 THEN 'Recent Customers'
        WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
        WHEN r_score <= 2 AND f_score <= 2 THEN 'Lost'
        ELSE 'Potential Loyalists' END AS segment
    FROM rfm_scores
""", conn)
rfm.to_csv(f"{OUT}/rfm_customers.csv", index=False)
print(f"✅ rfm_customers: {len(rfm)} rows")

# 6. Reviews
reviews = pd.read_sql("""
    SELECT review_score,
           COUNT(*) AS count,
           ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct
    FROM reviews GROUP BY review_score ORDER BY review_score
""", conn)
reviews.to_csv(f"{OUT}/reviews.csv", index=False)
print(f"✅ reviews: {len(reviews)} rows")

conn.close()

# Export все таблицы в один Excel файл — типы данных сохраняются точно
excel_path = f"{OUT}/olist_dashboard.xlsx"
with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
    for fname in os.listdir(OUT):
        if fname.endswith(".csv"):
            df = pd.read_csv(f"{OUT}/{fname}")
            for col in df.select_dtypes(include="float").columns:
                df[col] = df[col].fillna(0).round(0).astype(int)
            sheet = fname.replace(".csv", "")[:31]
            df.to_excel(writer, sheet_name=sheet, index=False)
            print(f"✅ Excel sheet: {sheet}")

print(f"\nExcel file saved to: {excel_path}")
