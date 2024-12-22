-- Opprett brukertabell
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Opprett spillertabell
CREATE TABLE IF NOT EXISTS spillertropp (
    spiller_id INTEGER PRIMARY KEY AUTOINCREMENT,
    navn TEXT UNIQUE NOT NULL,
    posisjon TEXT NOT NULL CHECK (posisjon IN ('Keeper', 'Forsvar', 'Midtbane', 'Angrep')),
    status TEXT DEFAULT 'aktiv' CHECK (status IN ('aktiv', 'inaktiv')),
    sist_oppdatert TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    opprettet_dato TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Opprett kamptabell
CREATE TABLE IF NOT EXISTS kamp (
    kamp_id TEXT PRIMARY KEY,
    motstander TEXT NOT NULL,
    status TEXT DEFAULT 'planlagt' CHECK (status IN ('planlagt', 'pågår', 'ferdig')),
    periode_lengde INTEGER DEFAULT 5,
    antall_perioder INTEGER DEFAULT 12,
    spillere_paa_banen INTEGER DEFAULT 7,
    user_id TEXT NOT NULL,
    dato TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    kamptid INTEGER DEFAULT 60,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Opprett bytteplan-tabell
CREATE TABLE IF NOT EXISTS bytteplan (
    bytteplan_id INTEGER PRIMARY KEY AUTOINCREMENT,
    kamp_id TEXT NOT NULL,
    spiller_id INTEGER NOT NULL,
    periode_nummer INTEGER NOT NULL,
    er_paa_banen BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (kamp_id) REFERENCES kamp(kamp_id),
    FOREIGN KEY (spiller_id) REFERENCES spillertropp(spiller_id),
    UNIQUE(kamp_id, spiller_id, periode_nummer)
);

-- Opprett kamptropp-tabell
CREATE TABLE IF NOT EXISTS kamptropp (
    kamp_id TEXT,
    spiller_id INTEGER,
    er_med BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (kamp_id, spiller_id),
    FOREIGN KEY (kamp_id) REFERENCES kamp(kamp_id),
    FOREIGN KEY (spiller_id) REFERENCES spillertropp(spiller_id)
);

-- Opprett sist brukte kamptropp-tabell
CREATE TABLE IF NOT EXISTS sist_brukte_kamptropp (
    user_id TEXT,
    spiller_id INTEGER,
    er_med BOOLEAN DEFAULT TRUE,
    sist_oppdatert TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, spiller_id),
    FOREIGN KEY (spiller_id) REFERENCES spillertropp(spiller_id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Opprett spilletid-tabell
CREATE TABLE IF NOT EXISTS spilletid (
    spilletid_id INTEGER PRIMARY KEY AUTOINCREMENT,
    kamp_id TEXT NOT NULL,
    spiller_id INTEGER NOT NULL,
    total_spilletid INTEGER DEFAULT 0,
    antall_perioder_spilt INTEGER DEFAULT 0,
    gjennomsnitt_per_periode REAL,
    FOREIGN KEY (kamp_id) REFERENCES kamp(kamp_id),
    FOREIGN KEY (spiller_id) REFERENCES spillertropp(spiller_id)
);

-- Opprett lagrede bytteplan-tabell
CREATE TABLE IF NOT EXISTS lagrede_bytteplan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kamp_id TEXT NOT NULL,
    navn TEXT NOT NULL,
    beskrivelse TEXT,
    opprettet TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sist_brukt TIMESTAMP,
    FOREIGN KEY (kamp_id) REFERENCES kamp(kamp_id)
);

-- Opprett lagrede bytteplan detaljer-tabell
CREATE TABLE IF NOT EXISTS lagrede_bytteplan_detaljer (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bytteplan_id INTEGER NOT NULL,
    spiller_id INTEGER NOT NULL,
    periode_nummer INTEGER NOT NULL,
    er_paa_banen BOOLEAN NOT NULL,
    FOREIGN KEY (bytteplan_id) REFERENCES lagrede_bytteplan(id),
    FOREIGN KEY (spiller_id) REFERENCES spillertropp(spiller_id)
);

-- Opprett migrations-tabell
CREATE TABLE IF NOT EXISTS migrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER NOT NULL DEFAULT 1
);

-- Opprett indekser
CREATE INDEX idx_bytteplan_kamp ON bytteplan(kamp_id);
CREATE INDEX idx_bytteplan_spiller ON bytteplan(spiller_id);
CREATE INDEX idx_kamptropp_kamp ON kamptropp(kamp_id);
CREATE INDEX idx_spilletid_kamp ON spilletid(kamp_id);
CREATE INDEX idx_lagrede_bytteplan_kamp ON lagrede_bytteplan(kamp_id);
