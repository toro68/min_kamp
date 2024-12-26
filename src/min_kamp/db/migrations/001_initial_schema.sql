-- Aktiver foreign key constraints
PRAGMA foreign_keys = ON;

-- Opprett brukere-tabell (basis for alle relasjoner)
CREATE TABLE IF NOT EXISTS brukere (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brukernavn TEXT NOT NULL UNIQUE,
    passord_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    opprettet_dato DATETIME DEFAULT CURRENT_TIMESTAMP,
    sist_innlogget DATETIME,
    sist_oppdatert DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Opprett app_innstillinger-tabell
CREATE TABLE IF NOT EXISTS app_innstillinger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bruker_id INTEGER NOT NULL,
    nokkel TEXT NOT NULL,
    verdi TEXT,
    opprettet_dato DATETIME DEFAULT CURRENT_TIMESTAMP,
    sist_oppdatert DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bruker_id) REFERENCES brukere(id) ON DELETE CASCADE
);

-- Opprett kamper-tabell
CREATE TABLE IF NOT EXISTS kamper (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bruker_id INTEGER NOT NULL,
    motstander TEXT NOT NULL,
    dato DATE NOT NULL,
    hjemmebane BOOLEAN NOT NULL,
    resultat_hjemme INTEGER,
    resultat_borte INTEGER,
    opprettet_dato DATETIME DEFAULT CURRENT_TIMESTAMP,
    sist_oppdatert DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bruker_id) REFERENCES brukere(id) ON DELETE CASCADE
);

-- Opprett spillere-tabell
CREATE TABLE IF NOT EXISTS spillere (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bruker_id INTEGER NOT NULL,
    navn TEXT NOT NULL,
    posisjon TEXT NOT NULL,
    opprettet_dato DATETIME DEFAULT CURRENT_TIMESTAMP,
    sist_oppdatert DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bruker_id) REFERENCES brukere(id) ON DELETE CASCADE,
    UNIQUE(bruker_id, navn)
);

-- Opprett kamptropp-tabell
CREATE TABLE IF NOT EXISTS kamptropp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kamp_id INTEGER NOT NULL,
    spiller_id INTEGER NOT NULL,
    er_med BOOLEAN NOT NULL DEFAULT 0,
    opprettet_dato DATETIME DEFAULT CURRENT_TIMESTAMP,
    sist_oppdatert DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (kamp_id) REFERENCES kamper(id) ON DELETE CASCADE,
    FOREIGN KEY (spiller_id) REFERENCES spillere(id) ON DELETE CASCADE,
    UNIQUE(kamp_id, spiller_id)
);

-- Opprett bytteplan-tabell
CREATE TABLE IF NOT EXISTS bytteplan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kamp_id INTEGER NOT NULL,
    spiller_id INTEGER NOT NULL,
    periode INTEGER NOT NULL,
    er_paa BOOLEAN NOT NULL DEFAULT 0,
    opprettet_dato DATETIME DEFAULT CURRENT_TIMESTAMP,
    sist_oppdatert DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (kamp_id) REFERENCES kamper(id) ON DELETE CASCADE,
    FOREIGN KEY (spiller_id) REFERENCES spillere(id) ON DELETE CASCADE
);

-- Opprett spilletid-tabell
CREATE TABLE IF NOT EXISTS spilletid (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kamp_id INTEGER NOT NULL,
    spiller_id INTEGER NOT NULL,
    minutter INTEGER NOT NULL,
    opprettet_dato DATETIME DEFAULT CURRENT_TIMESTAMP,
    sist_oppdatert DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (kamp_id) REFERENCES kamper(id) ON DELETE CASCADE,
    FOREIGN KEY (spiller_id) REFERENCES spillere(id) ON DELETE CASCADE,
    UNIQUE(kamp_id, spiller_id)
);

-- Opprett indekser for brukere
CREATE INDEX IF NOT EXISTS idx_brukere_brukernavn ON brukere(brukernavn);

-- Opprett indekser for app_innstillinger
CREATE INDEX IF NOT EXISTS idx_app_innstillinger_bruker_id ON app_innstillinger(bruker_id);
CREATE INDEX IF NOT EXISTS idx_app_innstillinger_nokkel ON app_innstillinger(nokkel);

-- Opprett indekser for kamper
CREATE INDEX IF NOT EXISTS idx_kamper_bruker_id ON kamper(bruker_id);
CREATE INDEX IF NOT EXISTS idx_kamper_dato ON kamper(dato);

-- Opprett indekser for spillere
CREATE INDEX IF NOT EXISTS idx_spillere_bruker_id ON spillere(bruker_id);
CREATE INDEX IF NOT EXISTS idx_spillere_posisjon ON spillere(posisjon);
CREATE INDEX IF NOT EXISTS idx_spillere_navn ON spillere(navn COLLATE NOCASE);
CREATE UNIQUE INDEX IF NOT EXISTS idx_spillere_bruker_navn ON spillere(bruker_id, navn);

-- Opprett indekser for kamptropp
CREATE INDEX IF NOT EXISTS idx_kamptropp_kamp_id ON kamptropp(kamp_id);
CREATE INDEX IF NOT EXISTS idx_kamptropp_spiller_id ON kamptropp(spiller_id);
CREATE INDEX IF NOT EXISTS idx_kamptropp_er_med ON kamptropp(er_med);

-- Opprett indekser for bytteplan
CREATE INDEX IF NOT EXISTS idx_bytteplan_kamp_id ON bytteplan(kamp_id);
CREATE INDEX IF NOT EXISTS idx_bytteplan_spiller_id ON bytteplan(spiller_id);
CREATE INDEX IF NOT EXISTS idx_bytteplan_periode ON bytteplan(periode);

-- Opprett indekser for spilletid
CREATE INDEX IF NOT EXISTS idx_spilletid_kamp_id ON spilletid(kamp_id);
CREATE INDEX IF NOT EXISTS idx_spilletid_spiller_id ON spilletid(spiller_id);
