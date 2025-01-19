-- Legg til posisjon-kolonne i kamptropp-tabellen
ALTER TABLE kamptropp ADD COLUMN posisjon TEXT;

-- Opprett indeks for raskere oppslag
CREATE INDEX IF NOT EXISTS idx_kamptropp_posisjon ON kamptropp(posisjon);
