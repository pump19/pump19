CREATE TABLE IF NOT EXISTS quotes
(
  qid SERIAL PRIMARY KEY,
  quote TEXT NOT NULL,
  attrib_name TEXT,
  attrib_date DATE,
  deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS quote_ratings
(
  quote INTEGER REFERENCES quotes,
  voter TEXT,
  good BOOLEAN NOT NULL,

  PRIMARY KEY (quote, voter)
);

CREATE OR REPLACE FUNCTION
  merge_quote_rating(_quote INTEGER, _voter TEXT, _good BOOLEAN)
  RETURNS VOID
  LANGUAGE plpgsql
  AS $$
    BEGIN
      LOOP
        -- first try to update the key
        UPDATE quote_ratings
          SET good = _good
          WHERE quote = _quote AND voter = _voter;
        IF found THEN
          RETURN;
        END IF;
        -- not there, so try to insert the key
        -- if someone else inserts the same key concurrently, we could get a unique-key failure
        BEGIN
          INSERT INTO quote_ratings VALUES(_quote, _voter, _good);
          RETURN;
        EXCEPTION
          WHEN unique_violation THEN
            -- do nothing, and loop to try the UPDATE again
          WHEN foreign_key_violation THEN
            -- return, can't do anything with an invalid quote
            RETURN;
        END;
      END LOOP;
    END;
  $$;
