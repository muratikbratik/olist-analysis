import pandas as pd
import sqlite3
import os

DOCS = r"C:\Users\muza\Documents"
DB = r"C:\Users\muza\Projects\olist-analysis\data\olist.db"

files = {
    "orders":     "olist_orders_dataset.csv",
    "customers":  "olist_customers_dataset.csv",
    "order_items":"olist_order_items_dataset.csv",
    "payments":   "olist_order_payments_dataset.csv",
    "reviews":    "olist_order_reviews_dataset.csv",
    "products":   "olist_products_dataset.csv",
    "sellers":    "olist_sellers_dataset.csv",
}

conn = sqlite3.connect(DB)

for table, filename in files.items():
    path = os.path.join(DOCS, filename)
    df = pd.read_csv(path)
    df.to_sql(table, conn, if_exists="replace", index=False)
    print(f"✅ {table}: {len(df):,} rows loaded")

conn.close()
print(f"\nDatabase saved to: {DB}")
