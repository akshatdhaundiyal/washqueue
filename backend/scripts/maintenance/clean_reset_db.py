import sqlite3
import uuid
import os

def clean_reset():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_path = os.path.join(base_dir, 'washqueue.db')
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Clear dynamic transactional & telemetry data
    cur.execute('DELETE FROM telemetry_readings')
    cur.execute('DELETE FROM bookings')
    cur.execute('DELETE FROM queue')

    # 2. Clean machines: keep only Washer 1, delete all others
    cur.execute("SELECT id FROM machines WHERE name = 'Washer 1'")
    w1 = cur.fetchone()
    if not w1:
        w1_id = uuid.uuid4().hex
        cur.execute("INSERT INTO machines (id, name, status) VALUES (?, 'Washer 1', 'available')", (w1_id,))
    else:
        w1_id = w1[0]
        cur.execute("UPDATE machines SET status = 'available' WHERE id = ?", (w1_id,))

    # Delete all machines except Washer 1
    cur.execute("DELETE FROM machines WHERE id != ?", (w1_id,))

    # 3. Clean smart plugs: keep only Washer 1 Smart Plug (d7fa4d27a2883bb4feqvhl)
    cur.execute("DELETE FROM smart_plugs WHERE device_id != 'd7fa4d27a2883bb4feqvhl'")
    cur.execute("""
        UPDATE smart_plugs 
        SET machine_id = ?,
            name = 'Washer 1 Smart Plug',
            power_threshold_running = 10.0,
            power_threshold_idle = 5.0,
            debounce_seconds = 120,
            consecutive_failures = 0,
            last_error = NULL,
            is_online = 1
        WHERE device_id = 'd7fa4d27a2883bb4feqvhl'
    """, (w1_id,))

    # 4. Clean users: keep only Hostel Admin
    cur.execute("DELETE FROM users WHERE email != 'admin@hostel.edu'")
    cur.execute("SELECT count(*) FROM users WHERE email = 'admin@hostel.edu'")
    if cur.fetchone()[0] == 0:
        admin_id = uuid.UUID('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa').hex
        cur.execute("""
            INSERT INTO users (id, name, email, role, is_admin)
            VALUES (?, 'Hostel Admin', 'admin@hostel.edu', 'admin', 1)
        """, (admin_id,))

    conn.commit()
    cur.execute('VACUUM')
    conn.close()
    print("Clean reset completed successfully!")

if __name__ == '__main__':
    clean_reset()
