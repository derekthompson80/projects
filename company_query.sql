-- Query to find companies with more than 1000 employees
-- Returns company IDs in ascending order

SELECT id
FROM companies
WHERE employees > 1000
ORDER BY id ASC;