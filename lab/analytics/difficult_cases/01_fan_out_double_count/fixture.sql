CREATE TABLE orders(order_id TEXT PRIMARY KEY, site TEXT, total_usd REAL);
CREATE TABLE order_lines(order_id TEXT, line_no INTEGER, item TEXT, qty INTEGER);
INSERT INTO orders VALUES('O1','A',100),('O2','A',50),('O3','A',80),('O4','B',40),('O5','B',25);
INSERT INTO order_lines VALUES('O1',1,'x',1),('O1',2,'y',1),('O1',3,'z',2),('O2',1,'x',1),('O3',1,'y',1),('O3',2,'z',1),('O4',1,'x',1),('O4',2,'y',1);
