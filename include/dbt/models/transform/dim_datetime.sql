-- Create a CTE to extract date and time components as strings
WITH datetime_cte AS (
  SELECT DISTINCT
    CAST(InvoiceDate AS STRING) AS datetime_id,
    FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%S', InvoiceDate) AS date_part
  FROM {{ source('retail', 'raw_invoices') }}
  WHERE InvoiceDate IS NOT NULL
)
SELECT
  datetime_id,
  CAST(date_part as datetime) AS datetime,
  SUBSTR(date_part, 9, 2) AS day,
  SUBSTR(date_part, 6, 2) AS month,
  SUBSTR(date_part, 1, 4) AS year,
  SUBSTR(date_part, 12, 2) AS hour,
  SUBSTR(date_part, 15, 2) AS minute,
  EXTRACT(DAYOFWEEK FROM TIMESTAMP(date_part)) AS weekday
FROM datetime_cte
