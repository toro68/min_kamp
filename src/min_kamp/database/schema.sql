-- Schema versjon
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Brukere
CREATE TABLE IF NOT EXISTS brukere (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brukernavn TEXT NOT NULL UNIQUE,
    passord_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    opprettet TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Spillere
CREATE TABLE IF NOT EXISTS spillere (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    navn TEXT NOT NULL UNIQUE,
    posisjon TEXT NOT NULL,
    aktiv BOOLEAN DEFAULT 1,
    opprettet TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Kamper
CREATE TABLE IF NOT EXISTS kamper (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dato TIMESTAMP NOT NULL,
    motstander TEXT NOT NULL,
    hjemmebane BOOLEAN NOT NULL,
    antall_perioder INTEGER NOT NULL,
    spillere_per_periode INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    opprettet TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES brukere(id)
);

-- Bytteplan
CREATE TABLE IF NOT EXISTS bytteplan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kamp_id INTEGER NOT NULL,
    spiller_id INTEGER NOT NULL,
    periode_nummer INTEGER NOT NULL,
    er_paa_banen BOOLEAN NOT NULL DEFAULT 0,
    opprettet TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (kamp_id) REFERENCES kamper(id),
    FOREIGN KEY (spiller_id) REFERENCES spillere(id)
);

-- Kamptropp
CREATE TABLE IF NOT EXISTS kamptropp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kamp_id INTEGER NOT NULL,
    spiller_id INTEGER NOT NULL,
    opprettet TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (kamp_id) REFERENCES kamper(id),
    FOREIGN KEY (spiller_id) REFERENCES spillere(id),
    UNIQUE(kamp_id, spiller_id)
);

-- Tilstand
CREATE TABLE IF NOT EXISTS state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL,
    opprettet TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    oppdatert TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sett initial schema versjon hvis den ikke finnes
INSERT OR IGNORE INTO schema_version (version) VALUES (1);

-- Opprett admin-bruker hvis den ikke finnes
-- Passord: admin
-- Salt: admin_salt
-- Hash: 8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918
INSERT OR IGNORE INTO brukere (brukernavn, passord_hash, salt)
VALUES ('admin', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'admin_salt');

-- Legg til noen testspillere hvis de ikke finnes
INSERT OR IGNORE INTO spillere (navn, posisjon) VALUES
('Ole Hansen', 'Keeper'),
('Per Jensen', 'Forsvar'),
('Lars Olsen', 'Forsvar'),
('Erik Nilsen', 'Midtbane'),
('Thomas Berg', 'Midtbane'),
('Anders Pedersen', 'Midtbane'),
('Magnus Karlsen', 'Angrep'),
('Kristian Andersen', 'Angrep'),
('Martin Larsen', 'Keeper'),
('Jonas Bakken', 'Forsvar'),
('Stian Iversen', 'Midtbane'),
('Fredrik Moen', 'Angrep');
