-- ============================================================
-- Olist E-Commerce: SQL Analysis
-- Dataset: Brazilian marketplace, 2016-2018
-- ============================================================

-- ─────────────────────────────────────────────
-- 1. BUSINESS OVERVIEW
-- ─────────────────────────────────────────────
-- Total revenue, orders, customers, avg order value
SELECT
    COUNT(DISTINCT o.order_id)                          AS total_orders,
    COUNT(DISTINCT o.customer_id)                       AS total_customers,
    COUNT(DISTINCT i.seller_id)                         AS total_sellers,
    ROUND(SUM(i.price + i.freight_value), 2)            AS total_revenue,
    ROUND(AVG(i.price + i.freight_value), 2)            AS avg_order_value,
    ROUND(SUM(i.freight_value) / SUM(i.price) * 100, 1) AS freight_pct_of_revenue
FROM orders o
JOIN order_items i ON o.order_id = i.order_id
WHERE o.order_status = 'delivered';


-- ─────────────────────────────────────────────
-- 2. MONTHLY REVENUE TREND WITH GROWTH RATE
-- ─────────────────────────────────────────────
WITH monthly AS (
    SELECT
        STRFTIME('%Y-%m', o.order_purchase_timestamp)   AS month,
        ROUND(SUM(i.price + i.freight_value), 2)        AS revenue,
        COUNT(DISTINCT o.order_id)                      AS orders
    FROM orders o
    JOIN order_items i ON o.order_id = i.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp >= '2017-01-01'
    GROUP BY month
)
SELECT
    month,
    revenue,
    orders,
    ROUND(revenue - LAG(revenue) OVER (ORDER BY month), 2)          AS revenue_change,
    ROUND((revenue - LAG(revenue) OVER (ORDER BY month))
          / LAG(revenue) OVER (ORDER BY month) * 100, 1)            AS growth_pct
FROM monthly
ORDER BY month;


-- ─────────────────────────────────────────────
-- 3. ORDER STATUS BREAKDOWN
-- ─────────────────────────────────────────────
SELECT
    order_status,
    COUNT(*)                                            AS orders,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS pct
FROM orders
GROUP BY order_status
ORDER BY orders DESC;


-- ─────────────────────────────────────────────
-- 4. TOP 10 PRODUCT CATEGORIES BY REVENUE
-- ─────────────────────────────────────────────
SELECT
    p.product_category_name                             AS category,
    COUNT(DISTINCT o.order_id)                          AS orders,
    ROUND(SUM(i.price), 2)                              AS revenue,
    ROUND(AVG(i.price), 2)                              AS avg_price,
    ROUND(SUM(i.price) * 100.0 / SUM(SUM(i.price)) OVER (), 2) AS revenue_share_pct
FROM order_items i
JOIN orders o      ON i.order_id = o.order_id
JOIN products p    ON i.product_id = p.product_id
WHERE o.order_status = 'delivered'
GROUP BY category
ORDER BY revenue DESC
LIMIT 10;


-- ─────────────────────────────────────────────
-- 5. DELIVERY PERFORMANCE BY STATE
-- ─────────────────────────────────────────────
SELECT
    c.customer_state                                                AS state,
    COUNT(o.order_id)                                              AS deliveries,
    ROUND(AVG(
        JULIANDAY(o.order_delivered_customer_date)
        - JULIANDAY(o.order_purchase_timestamp)
    ), 1)                                                           AS avg_delivery_days,
    ROUND(AVG(
        JULIANDAY(o.order_estimated_delivery_date)
        - JULIANDAY(o.order_delivered_customer_date)
    ), 1)                                                           AS avg_days_early,
    SUM(CASE WHEN o.order_delivered_customer_date
                  > o.order_estimated_delivery_date
             THEN 1 ELSE 0 END)                                     AS late_orders,
    ROUND(SUM(CASE WHEN o.order_delivered_customer_date
                        > o.order_estimated_delivery_date
                   THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)      AS late_pct
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
GROUP BY state
HAVING deliveries > 100
ORDER BY late_pct DESC;


-- ─────────────────────────────────────────────
-- 6. PAYMENT METHOD ANALYSIS
-- ─────────────────────────────────────────────
SELECT
    payment_type,
    COUNT(DISTINCT order_id)                                        AS orders,
    ROUND(SUM(payment_value), 2)                                    AS total_value,
    ROUND(AVG(payment_value), 2)                                    AS avg_value,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)             AS pct_of_orders
FROM payments
GROUP BY payment_type
ORDER BY total_value DESC;


-- ─────────────────────────────────────────────
-- 7. REVIEW SCORE ANALYSIS BY CATEGORY
-- ─────────────────────────────────────────────
SELECT
    p.product_category_name                                         AS category,
    COUNT(r.review_id)                                              AS reviews,
    ROUND(AVG(r.review_score), 2)                                   AS avg_score,
    SUM(CASE WHEN r.review_score = 5 THEN 1 ELSE 0 END)            AS five_star,
    SUM(CASE WHEN r.review_score <= 2 THEN 1 ELSE 0 END)           AS low_score,
    ROUND(SUM(CASE WHEN r.review_score <= 2 THEN 1 ELSE 0 END)
          * 100.0 / COUNT(*), 1)                                    AS dissatisfied_pct
FROM reviews r
JOIN orders o   ON r.order_id = o.order_id
JOIN order_items i ON o.order_id = i.order_id
JOIN products p ON i.product_id = p.product_id
GROUP BY category
HAVING reviews > 200
ORDER BY avg_score DESC
LIMIT 15;


-- ─────────────────────────────────────────────
-- 8. RFM CUSTOMER SEGMENTATION
-- ─────────────────────────────────────────────
WITH rfm_base AS (
    SELECT
        o.customer_id,
        CAST(JULIANDAY('2018-10-01') - JULIANDAY(MAX(o.order_purchase_timestamp)) AS INT) AS recency,
        COUNT(DISTINCT o.order_id)                                  AS frequency,
        ROUND(SUM(i.price + i.freight_value), 2)                    AS monetary
    FROM orders o
    JOIN order_items i ON o.order_id = i.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY o.customer_id
),
rfm_scores AS (
    SELECT *,
        NTILE(5) OVER (ORDER BY recency DESC)   AS r_score,
        NTILE(5) OVER (ORDER BY frequency)      AS f_score,
        NTILE(5) OVER (ORDER BY monetary)       AS m_score
    FROM rfm_base
),
segments AS (
    SELECT *,
        CASE
            WHEN r_score >= 4 AND f_score >= 4 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
            WHEN r_score >= 4 AND f_score <= 2 THEN 'Recent Customers'
            WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
            WHEN r_score <= 2 AND f_score <= 2 THEN 'Lost'
            ELSE 'Potential Loyalists'
        END AS segment
    FROM rfm_scores
)
SELECT
    segment,
    COUNT(*)                                                        AS customers,
    ROUND(AVG(recency), 0)                                         AS avg_recency_days,
    ROUND(AVG(frequency), 2)                                        AS avg_orders,
    ROUND(AVG(monetary), 2)                                         AS avg_ltv,
    ROUND(SUM(monetary), 2)                                         AS total_revenue
FROM segments
GROUP BY segment
ORDER BY total_revenue DESC;


-- ─────────────────────────────────────────────
-- 9. TOP 10 SELLERS BY REVENUE & RATING
-- ─────────────────────────────────────────────
SELECT
    s.seller_id,
    s.seller_city,
    s.seller_state,
    COUNT(DISTINCT i.order_id)                                      AS orders,
    ROUND(SUM(i.price), 2)                                          AS revenue,
    ROUND(AVG(r.review_score), 2)                                   AS avg_rating,
    ROUND(AVG(
        JULIANDAY(o.order_delivered_customer_date)
        - JULIANDAY(o.order_purchase_timestamp)
    ), 1)                                                           AS avg_delivery_days
FROM sellers s
JOIN order_items i  ON s.seller_id = i.seller_id
JOIN orders o       ON i.order_id = o.order_id
LEFT JOIN reviews r ON o.order_id = r.order_id
WHERE o.order_status = 'delivered'
GROUP BY s.seller_id
HAVING orders > 50
ORDER BY revenue DESC
LIMIT 10;


-- ─────────────────────────────────────────────
-- 10. MONTHLY COHORT RETENTION
-- ─────────────────────────────────────────────
WITH first_order AS (
    SELECT
        customer_id,
        STRFTIME('%Y-%m', MIN(order_purchase_timestamp)) AS cohort_month
    FROM orders
    GROUP BY customer_id
),
cohort_data AS (
    SELECT
        f.cohort_month,
        STRFTIME('%Y-%m', o.order_purchase_timestamp)    AS order_month,
        COUNT(DISTINCT o.customer_id)                    AS customers
    FROM orders o
    JOIN first_order f ON o.customer_id = f.customer_id
    GROUP BY f.cohort_month, order_month
)
SELECT
    cohort_month,
    order_month,
    customers,
    ROUND(customers * 100.0
          / FIRST_VALUE(customers) OVER (
              PARTITION BY cohort_month ORDER BY order_month
          ), 1)                                                      AS retention_pct
FROM cohort_data
ORDER BY cohort_month, order_month;
