-- PostgreSQL Migration Schema v2 for WashQueue Hostel Laundry Management Application
-- Target: Supabase (PostgreSQL)

-- 1. Create smart_plugs table (Hardened Local LAN & Cloud configuration)
CREATE TABLE IF NOT EXISTS smart_plugs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    machine_id UUID UNIQUE REFERENCES machines(id) ON DELETE SET NULL,
    name TEXT,
    mac_address TEXT,
    outlet_index INT NOT NULL DEFAULT 1,
    provider TEXT NOT NULL DEFAULT 'tuya_local',
    device_id TEXT NOT NULL,
    local_key TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    protocol_version TEXT NOT NULL DEFAULT '3.3',
    power_threshold_running REAL NOT NULL DEFAULT 10.0,
    power_threshold_idle REAL NOT NULL DEFAULT 5.0,
    debounce_seconds INT NOT NULL DEFAULT 120,
    is_online BOOLEAN NOT NULL DEFAULT false,
    last_seen_at TIMESTAMPTZ,
    consecutive_failures INT NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_smart_plugs_mac_outlet UNIQUE (mac_address, outlet_index)
);

CREATE INDEX IF NOT EXISTS ix_smart_plugs_device_id ON smart_plugs(device_id);
CREATE INDEX IF NOT EXISTS ix_smart_plugs_mac ON smart_plugs(mac_address);

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

CREATE INDEX IF NOT EXISTS ix_telemetry_plug_recorded_at ON telemetry_readings (plug_id, recorded_at DESC);

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
