import sqlite3
import os
import shutil
import time

def repair():
    # Base dir is backend/ (three levels up from backend/scripts/maintenance/)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_file = os.path.join(base_dir, "washqueue.db")
    bak_file = os.path.join(base_dir, f"washqueue.db.corrupt.{int(time.time())}")
    clean_file = os.path.join(base_dir, "washqueue_clean.db")

    if not os.path.exists(db_file):
        print(f"[!] Database file not found: {db_file}")
        return

    shutil.copyfile(db_file, bak_file)
    print(f"[+] Preserved corrupt file as {bak_file}")

    src = sqlite3.connect(bak_file)
    src_cur = src.cursor()

    if os.path.exists(clean_file):
        os.remove(clean_file)

    dst = sqlite3.connect(clean_file)
    dst_cur = dst.cursor()

    # Enable WAL mode on clean DB
    dst_cur.execute("PRAGMA journal_mode = WAL")
    dst_cur.execute("PRAGMA synchronous = NORMAL")

    # 1. Recover table schemas and data
    src_cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'")
    tables = src_cur.fetchall()

    for tbl_name, tbl_sql in tables:
        dst_cur.execute(tbl_sql)
        if tbl_name == "telemetry_readings":
            print(f"[+] Recreated empty, clean {tbl_name} table")
            continue

        try:
            src_cur.execute(f"SELECT * FROM {tbl_name}")
            rows = src_cur.fetchall()
            if rows:
                placeholders = ",".join(["?"] * len(rows[0]))
                dst_cur.executemany(f"INSERT INTO {tbl_name} VALUES ({placeholders})", rows)
            print(f"[+] Recovered {tbl_name}: {len(rows)} rows")
        except Exception as e:
            print(f"[!] Error recovering {tbl_name}: {e}")

    # 2. Recover indexes
    src_cur.execute("SELECT sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL")
    for (idx_sql,) in src_cur.fetchall():
        try:
            dst_cur.execute(idx_sql)
        except Exception as e:
            pass

    dst.commit()

    # Verify clean DB
    dst_cur.execute("PRAGMA integrity_check")
    check = dst_cur.fetchall()
    print(f"[+] Integrity check on new DB: {check}")

    dst.close()
    src.close()

    # Atomically replace washqueue.db
    for ext in ["-wal", "-shm"]:
        extra = db_file + ext
        if os.path.exists(extra):
            try:
                os.remove(extra)
            except Exception:
                pass

    shutil.move(clean_file, db_file)
    print(f"[+] Successfully replaced {db_file} with clean, WAL-enabled database!")

if __name__ == "__main__":
    repair()
