CREATE TABLE sales(sale_id INTEGER PRIMARY KEY, sale_date TEXT, amount_usd REAL);
CREATE TABLE returns(return_id INTEGER PRIMARY KEY, sale_id INTEGER, return_date TEXT, amount_usd REAL);
INSERT INTO sales VALUES(1,'2026-01-10',300),(2,'2026-01-20',200),(3,'2026-02-05',100);
INSERT INTO returns VALUES(1,2,'2026-01-25',50),(2,2,'2026-02-02',30),(3,1,'2026-03-04',300);
