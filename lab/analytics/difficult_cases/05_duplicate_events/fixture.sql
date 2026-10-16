CREATE TABLE events(event_id TEXT, order_id TEXT, event_type TEXT, amount_usd REAL, received_at TEXT);
INSERT INTO events VALUES
('e1','O1','placed',0,'2026-05-01T10:00:00'),('e2','O1','completed',40,'2026-05-01T10:30:00'),('e2','O1','completed',40,'2026-05-01T10:31:00'),
('e3','O2','completed',25,'2026-05-01T11:00:00'),('e3','O2','completed',27,'2026-05-01T11:45:00'),
('e4','O3','placed',0,'2026-05-01T12:00:00'),('e5','O4','completed',10,'2026-05-01T13:00:00'),('e5','O4','completed',10,'2026-05-01T13:00:30'),('e5','O4','completed',10,'2026-05-01T13:01:00');
