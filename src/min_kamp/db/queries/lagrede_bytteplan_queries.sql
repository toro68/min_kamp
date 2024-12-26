-- Opprett tabell for lagrede bytteplaner
CREATE TABLE IF NOT EXISTS lagrede_bytteplan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kamp_id INTEGER NOT NULL,
    navn TEXT NOT NULL,
    beskrivelse TEXT,
    opprettet_dato DATETIME DEFAULT CURRENT_TIMESTAMP,
    sist_oppdatert DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (kamp_id) REFERENCES kamper(id)
);

-- Opprett tabell for byttedetaljer
CREATE TABLE IF NOT EXISTS lagrede_bytteplan_detaljer (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bytteplan_id INTEGER NOT NULL,
    spiller_id INTEGER NOT NULL,
    periode INTEGER NOT NULL,
    er_paa BOOLEAN NOT NULL,
    opprettet_dato DATETIME DEFAULT CURRENT_TIMESTAMP,
    sist_oppdatert DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bytteplan_id) REFERENCES lagrede_bytteplan(id),
    FOREIGN KEY (spiller_id) REFERENCES spillere(id)
);

-- Hent alle lagrede bytteplaner for en kamp
SELECT id, navn, beskrivelse, opprettet_dato, sist_oppdatert
FROM lagrede_bytteplan
WHERE kamp_id = ?
ORDER BY sist_oppdatert DESC;

-- Hent detaljer for en spesifikk bytteplan
SELECT spiller_id, periode, er_paa
FROM lagrede_bytteplan_detaljer
WHERE bytteplan_id = ?
ORDER BY periode, spiller_id;

-- Lagre ny bytteplan
INSERT INTO lagrede_bytteplan (kamp_id, navn, beskrivelse)
VALUES (?, ?, ?);

-- Lagre bytteplan detaljer
INSERT INTO lagrede_bytteplan_detaljer (bytteplan_id, spiller_id, periode, er_paa)
VALUES (?, ?, ?, ?);

-- Oppdater sist_oppdatert timestamp
UPDATE lagrede_bytteplan
SET sist_oppdatert = CURRENT_TIMESTAMP
WHERE id = ?;
