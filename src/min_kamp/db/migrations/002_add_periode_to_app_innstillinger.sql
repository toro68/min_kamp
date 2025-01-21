-- Legg til indeks for raskere søk på periode
CREATE INDEX IF NOT EXISTS idx_app_innstillinger_periode ON app_innstillinger(periode);

-- Legg til indeks for kombinert søk på kamp_id og periode
CREATE INDEX IF NOT EXISTS idx_app_innstillinger_kamp_periode ON app_innstillinger(kamp_id, periode);
