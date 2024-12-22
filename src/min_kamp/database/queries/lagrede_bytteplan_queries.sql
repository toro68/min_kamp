-- Opprett tabell for lagrede bytteplaner
CREATE TABLE IF NOT EXISTS lagrede_bytteplan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kamp_id TEXT NOT NULL,
    navn TEXT NOT NULL,
    beskrivelse TEXT,
    opprettet TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sist_brukt TIMESTAMP,
    FOREIGN KEY (kamp_id) REFERENCES kamp(id)
);

-- Opprett tabell for byttedetaljer
CREATE TABLE IF NOT EXISTS lagrede_bytteplan_detaljer (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bytteplan_id INTEGER NOT NULL,
    spiller_id INTEGER NOT NULL,
    periode_nummer INTEGER NOT NULL,
    er_paa_banen BOOLEAN NOT NULL,
    FOREIGN KEY (bytteplan_id) REFERENCES lagrede_bytteplan(id),
    FOREIGN KEY (spiller_id) REFERENCES spillertropp(id)
);

-- Hent alle lagrede bytteplaner for en kamp
SELECT id, navn, beskrivelse, opprettet, sist_brukt
FROM lagrede_bytteplan
WHERE kamp_id = ?
ORDER BY sist_brukt DESC;

-- Hent detaljer for en spesifikk bytteplan
SELECT spiller_id, periode_nummer, er_paa_banen
FROM lagrede_bytteplan_detaljer
WHERE bytteplan_id = ?
ORDER BY periode_nummer, spiller_id;

-- Lagre ny bytteplan
INSERT INTO lagrede_bytteplan (kamp_id, navn, beskrivelse)
VALUES (?, ?, ?);

-- Lagre bytteplan detaljer
INSERT INTO lagrede_bytteplan_detaljer (bytteplan_id, spiller_id, periode_nummer, er_paa_banen)
VALUES (?, ?, ?, ?);

-- Oppdater sist_brukt timestamp
UPDATE lagrede_bytteplan
SET sist_brukt = CURRENT_TIMESTAMP
WHERE id = ?;
