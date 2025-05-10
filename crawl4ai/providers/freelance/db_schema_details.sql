-- Schema für die neue Detailtabelle für Freelance.de Projektdetails

CREATE TABLE IF NOT EXISTS freelance_project_details (
    id SERIAL PRIMARY KEY,
    project_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    
    -- Basisdaten
    company_url TEXT,
    logo_url TEXT,
    
    -- Zusätzliche Projektdaten
    start_date TEXT,
    project_duration TEXT,
    reference_number TEXT,
    hourly_rate TEXT,
    
    -- Statistiken
    company_active_since TEXT,
    view_count INTEGER,
    application_count INTEGER,
    
    -- Detaillierte Beschreibung
    full_description TEXT,
    
    -- Kontaktdaten
    contact_person TEXT,
    contact_address TEXT,
    contact_email TEXT,
    contact_phone TEXT,
    
    -- Kategorien und Skills als JSON
    categories JSONB DEFAULT '[]'::jsonb,
    
    -- Ähnliche Projekte als JSON
    related_projects JSONB DEFAULT '[]'::jsonb,
    
    -- Metadaten
    details_last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Verbindung zur Haupttabelle
    FOREIGN KEY (project_id, provider) REFERENCES freelance_projects (project_id, provider) ON DELETE CASCADE,
    UNIQUE(project_id, provider)
);

-- Indizes
CREATE INDEX IF NOT EXISTS idx_freelance_project_details_project_id ON freelance_project_details (project_id);
CREATE INDEX IF NOT EXISTS idx_freelance_project_details_provider ON freelance_project_details (provider); 