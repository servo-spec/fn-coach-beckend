import sqlite3
from datetime import date, datetime

DB = "coach.db"

def init():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, type TEXT, duration INTEGER, result TEXT, notes TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS mistakes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, mistake TEXT, fixed INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS profile (
        key TEXT PRIMARY KEY, value TEXT)""")
    con.commit()
    con.close()

def add_session(type_, duration, result, notes=""):
    con = sqlite3.connect(DB)
    con.execute("INSERT INTO sessions (date,type,duration,result,notes) VALUES (?,?,?,?,?)",
                (date.today().isoformat(), type_, duration, result, notes))
    con.commit()
    con.close()

def add_mistake(text):
    con = sqlite3.connect(DB)
    con.execute("INSERT INTO mistakes (date,mistake) VALUES (?,?)",
                (date.today().isoformat(), text))
    con.commit()
    con.close()

def get_mistakes(only_open=True):
    con = sqlite3.connect(DB)
    q = "SELECT id,mistake,fixed FROM mistakes"
    if only_open:
        q += " WHERE fixed=0"
    rows = con.execute(q).fetchall()
    con.close()
    return rows

def fix_mistake(mid):
    con = sqlite3.connect(DB)
    con.execute("UPDATE mistakes SET fixed=1 WHERE id=?", (mid,))
    con.commit()
    con.close()

def week_stats():
    con = sqlite3.connect(DB)
    rows = con.execute(
        "SELECT type, SUM(duration) FROM sessions WHERE date >= date('now','-7 day') GROUP BY type"
    ).fetchall()
    con.close()
    return rows

def set_profile(key, value):
    con = sqlite3.connect(DB)
    con.execute("INSERT OR REPLACE INTO profile (key,value) VALUES (?,?)", (key, value))
    con.commit()
    con.close()

def get_profile(key, default=None):
    con = sqlite3.connect(DB)
    row = con.execute("SELECT value FROM profile WHERE key=?", (key,)).fetchone()
    con.close()
    return row[0] if row else default