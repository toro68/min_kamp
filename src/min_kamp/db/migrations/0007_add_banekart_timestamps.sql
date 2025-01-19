-- Legg til tidsstempel-kolonner i banekart-tabellen
ALTER TABLE banekart ADD COLUMN opprettet_dato DATETIME DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE banekart ADD COLUMN sist_oppdatert DATETIME DEFAULT CURRENT_TIMESTAMP;

-- Oppdater trigger for å håndtere sist_oppdatert
DROP TRIGGER IF EXISTS update_banekart_timestamp;
CREATE TRIGGER update_banekart_timestamp
AFTER UPDATE ON banekart
BEGIN
    UPDATE banekart SET sist_oppdatert = CURRENT_TIMESTAMP
    WHERE kamp_id = NEW.kamp_id AND periode_id = NEW.periode_id;
END;
