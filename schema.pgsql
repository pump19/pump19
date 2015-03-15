DROP TABLE IF EXISTS quotes;
CREATE TABLE quotes
(
  qid SERIAL PRIMARY KEY,
  quote TEXT NOT NULL,
  attrib_name TEXT,
  attrib_date DATE
);
