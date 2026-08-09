-- PostgreSQL Migration Schema v2 for WashQueue Hostel Laundry Management Application
-- Target: Supabase (PostgreSQL)

-- 1. Create smart_plugs table (Local LAN configuration)
CREATE TABLE IF NOT EXISTS smart_plugs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    machine_id UUID REFERENCES machines(id) ON DELETE SET NULL,
    provider TEXT NOT NULL DEFAULT 'tuya_local',
    device_id TEXT NOT NULL UNIQUE,
    local_key TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    protocol_version TEXT NOT NULL DEFAULT '3.3',
    power_threshold_running REAL NOT NULL DEFAULT 10.0,
    power_threshold_idle REAL NOT NULL DEFAULT 5.0,
    debounce_seconds INT NOT NULL DEFAULT 120,
    is_online BOOLEAN NOT NULL DEFAULT false,
    last_seen_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Create telemetry_readings table
CREATE TABLE IF NOT EXISTS telemetry_readings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plug_id UUID NOT NULL REFERENCES smart_plugs(id) ON DELETE CASCADE,
    voltage_v REAL,
    current_ma REAL,
    power_w REAL,
    energy_kwh REAL,
    switch_on BOOLEAN,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Create users table with admin support
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    is_admin BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enable Realtime Publications for new tables
BEGIN;
  ALTER PUBLICATION supabase_realtime ADD TABLE smart_plugs;
  ALTER PUBLICATION supabase_realtime ADD TABLE telemetry_readings;
EXCEPTION
  WHEN OTHERS THEN NULL;
END;

-- Seed default test users
INSERT INTO users (id, name, email, is_admin) VALUES
('11111111-1111-1111-1111-111111111111', 'Alex (User A)', 'alex@hostel.edu', false),
('22222222-2222-2222-2222-222222222222', 'Blake (User B)', 'blake@hostel.edu', false),
('33333333-3333-3333-3333-333333333333', 'Charlie (User C)', 'charlie@hostel.edu', false),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'Hostel Admin', 'admin@hostel.edu', true)
ON CONFLICT (id) DO NOTHING;
