-- Legg til støtte for å lagre formasjoner
-- Indeks for raskere oppslag på formasjoner
CREATE INDEX IF NOT EXISTS idx_app_innstillinger_formasjon ON app_innstillinger(nokkel) WHERE nokkel = 'formasjon';
