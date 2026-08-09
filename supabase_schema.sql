-- PostgreSQL Migration Schema for Hostel Laundry Management Application
-- Target: Supabase (PostgreSQL)

-- 1. Setup tables
CREATE TABLE IF NOT EXISTS machines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK (status IN ('available', 'in_use', 'idle_full')) DEFAULT 'available'
);

CREATE TABLE IF NOT EXISTS bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    machine_id UUID NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    estimated_end_at TIMESTAMPTZ NOT NULL,
    cleared_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    machine_id UUID NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    position INT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('waiting', 'notified', 'expired')) DEFAULT 'waiting',
    UNIQUE (machine_id, user_id, status)
);

-- 2. Enable Realtime Publications for these tables
-- Supabase Realtime requires publication membership to broadcast changes via WebSockets.
BEGIN;
  -- If the publication doesn't exist, we create it. In Supabase, it usually exists as 'supabase_realtime'.
  -- To be safe, we try to create it or handle it.
  CREATE PUBLICATION supabase_realtime;
EXCEPTION
  WHEN duplicate_object THEN NULL;
END;

ALTER PUBLICATION supabase_realtime ADD TABLE machines;
ALTER PUBLICATION supabase_realtime ADD TABLE bookings;
ALTER PUBLICATION supabase_realtime ADD TABLE queue;

-- 3. Seed initial laundry machines
INSERT INTO machines (name, status) VALUES
('Washer 1', 'available'),
('Washer 2', 'available'),
('Washer 3', 'available'),
('Washer 4', 'available'),
('Dryer 1', 'available'),
('Dryer 2', 'available'),
('Dryer 3', 'available'),
('Dryer 4', 'available')
ON CONFLICT (name) DO NOTHING;
