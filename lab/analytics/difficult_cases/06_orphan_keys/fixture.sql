CREATE TABLE items(item_id TEXT PRIMARY KEY, category TEXT);
CREATE TABLE sales(sale_id INTEGER PRIMARY KEY, item_id TEXT, amount_usd REAL);
INSERT INTO items VALUES('M1','food'),('M2','food'),('B1','beer');
INSERT INTO sales VALUES(1,'M1',10),(2,'M2',20),(3,'B1',5),(4,'X9',7),(5,'X9',3),(6,NULL,4);
