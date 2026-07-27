WITH rfm_raw AS (
    SELECT 
        customer_id,
        MAX(transaction_date) AS last_purchase,
        COUNT(*) AS frequency,
        SUM(amount) AS monetary,
        JULIANDAY((SELECT MAX(transaction_date) FROM transactions)) - JULIANDAY(MAX(transaction_date)) AS recency
    FROM transactions
    GROUP BY customer_id
),
rfm_scores AS (
    SELECT 
        customer_id,
        NTILE(5) OVER (ORDER BY recency DESC) AS r_score,
        NTILE(5) OVER (ORDER BY frequency ASC) AS f_score,
        NTILE(5) OVER (ORDER BY monetary ASC) AS m_score
    FROM rfm_raw
)
SELECT 
    customer_id,
    (r_score || f_score || m_score) AS rfm_segment,
    CASE 
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Loyal'
        WHEN r_score <= 2 AND f_score >= 3 AND m_score >= 3 THEN 'At Risk'
        ELSE 'Others'
    END AS segment_name
FROM rfm_scores;