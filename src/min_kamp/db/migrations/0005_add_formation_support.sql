-- Legg til støtte for å lagre formasjoner
ALTER TABLE app_innstillinger ADD COLUMN kamp_id INTEGER REFERENCES kamper(id);

-- Indeks for raskere oppslag
CREATE INDEX IF NOT EXISTS idx_app_innstillinger_kamp_id ON app_innstillinger(kamp_id);
