CREATE TABLE dim_item(item_key INTEGER PRIMARY KEY, item_id TEXT, item_name TEXT, valid_from TEXT, valid_to TEXT);
CREATE TABLE sales(sale_id INTEGER PRIMARY KEY, item_id TEXT, sale_date TEXT, qty INTEGER);
INSERT INTO dim_item VALUES(1,'M04','Gobi Taco','1900-01-01','2026-04-13'),(2,'M04','Mango Habanero Gobi','2026-04-13','9999-12-31'),(3,'M01','Chicken 65 Totopos','1900-01-01','9999-12-31');
INSERT INTO sales VALUES(1,'M04','2026-04-11',2),(2,'M04','2026-04-12',3),(3,'M04','2026-04-13',4),(4,'M04','2026-04-13',1),(5,'M04','2026-04-14',5),(6,'M01','2026-04-13',9);
