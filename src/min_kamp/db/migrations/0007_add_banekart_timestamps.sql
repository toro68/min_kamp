-- Legg til tidsstempel-kolonner i banekart-tabellen hvis de ikke finnes
CREATE TABLE IF NOT EXISTS temp_table AS SELECT * FROM banekart;
DROP TABLE banekart;

CREATE TABLE banekart (
    kamp_id INTEGER,
    periode_id INTEGER,
    spillerposisjoner TEXT,
    opprettet_dato DATETIME DEFAULT CURRENT_TIMESTAMP,
    sist_oppdatert DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (kamp_id, periode_id)
);

INSERT INTO banekart (kamp_id, periode_id, spillerposisjoner)
SELECT kamp_id, periode_id, spillerposisjoner FROM temp_table;

DROP TABLE temp_table;

-- Opprett indeks
CREATE INDEX IF NOT EXISTS idx_banekart_kamp_periode ON banekart(kamp_id, periode_id);

-- Oppdater trigger for å håndtere sist_oppdatert
DROP TRIGGER IF EXISTS update_banekart_timestamp;
CREATE TRIGGER update_banekart_timestamp
AFTER UPDATE ON banekart
BEGIN
    UPDATE banekart SET sist_oppdatert = CURRENT_TIMESTAMP
    WHERE kamp_id = NEW.kamp_id AND periode_id = NEW.periode_id;
END;
