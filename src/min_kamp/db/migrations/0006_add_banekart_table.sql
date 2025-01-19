-- Opprett banekart-tabell
CREATE TABLE IF NOT EXISTS banekart (
    kamp_id INTEGER NOT NULL,
    periode_id INTEGER NOT NULL,
    spillerposisjoner TEXT NOT NULL,
    opprettet_dato DATETIME DEFAULT CURRENT_TIMESTAMP,
    sist_oppdatert DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (kamp_id, periode_id),
    FOREIGN KEY (kamp_id) REFERENCES kamper(id) ON DELETE CASCADE
);

-- Legg til indeks for effektiv søking
CREATE INDEX IF NOT EXISTS idx_banekart_kamp_periode ON banekart(kamp_id, periode_id);

-- Legg til trigger for å oppdatere sist_oppdatert
CREATE TRIGGER IF NOT EXISTS update_banekart_timestamp
AFTER UPDATE ON banekart
BEGIN
    UPDATE banekart SET sist_oppdatert = CURRENT_TIMESTAMP
    WHERE kamp_id = NEW.kamp_id AND periode_id = NEW.periode_id;
END;
