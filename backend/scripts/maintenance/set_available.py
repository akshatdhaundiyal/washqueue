import sqlite3
import os

def set_washer_available():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_path = os.path.join(base_dir, 'washqueue.db')
    if not os.path.exists(db_path) and os.path.exists('/app/washqueue.db'):
        db_path = '/app/washqueue.db'

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("UPDATE machines SET status = 'available' WHERE name = 'Washer 1'")
    con.commit()
    print("Updated rows:", cur.rowcount)
    cur.execute("SELECT name, status FROM machines")
    print("Current machines:", cur.fetchall())
    con.close()

if __name__ == '__main__':
    set_washer_available()
