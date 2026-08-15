"""RF Imperium — Signal Database (SQLite)"""
import sqlite3, json, csv
from datetime import datetime
from pathlib import Path

DB_PATH = Path.home() / ".rf_imperium" / "signals.db"


class SignalDB:
    def __init__(self):
        DB_PATH.parent.mkdir(exist_ok=True)
        self.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._init()

    def _init(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT, freq_hz REAL, bandwidth_hz REAL, power_dbm REAL,
                protocol TEXT, bits TEXT, decoded TEXT, raw_iq_file TEXT,
                fingerprint TEXT, tags TEXT, notes TEXT
            );
            CREATE TABLE IF NOT EXISTS fingerprints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, freq_hz REAL, features TEXT, created TEXT
            );
            CREATE INDEX IF NOT EXISTS i_freq ON signals(freq_hz);
            CREATE INDEX IF NOT EXISTS i_proto ON signals(protocol);
            CREATE INDEX IF NOT EXISTS i_ts ON signals(timestamp);
        """)
        self.conn.commit()

    def insert_signal(self, freq_hz, bw=0, power=0, protocol="",
                      bits="", decoded="", iq_file="", fp="", tags="", notes=""):
        ts = datetime.utcnow().isoformat()
        cur = self.conn.execute(
            "INSERT INTO signals VALUES(NULL,?,?,?,?,?,?,?,?,?,?,?)",
            (ts, freq_hz, bw, power, protocol, bits, decoded, iq_file, fp, tags, notes))
        self.conn.commit()
        return cur.lastrowid

    def search(self, freq_min=None, freq_max=None, protocol=None,
               keyword=None, limit=500, offset=0):
        q = "SELECT * FROM signals WHERE 1=1"
        p = []
        if freq_min is not None:
            q += " AND freq_hz>=?"; p.append(freq_min)
        if freq_max is not None:
            q += " AND freq_hz<=?"; p.append(freq_max)
        if protocol:
            q += " AND protocol LIKE ?"; p.append(f"%{protocol}%")
        if keyword:
            q += " AND(decoded LIKE? OR bits LIKE? OR notes LIKE?)"; p += [f"%{keyword}%"]*3
        q += f" ORDER BY id DESC LIMIT {limit} OFFSET {offset}"
        return self.conn.execute(q, p).fetchall()

    def columns(self):
        return [d[0] for d in self.conn.execute("PRAGMA table_info(signals)").fetchall()]

    def export_csv(self, path):
        rows = self.search(limit=999999)
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(self.columns()); w.writerows(rows)

    def export_json(self, path):
        rows = self.search(limit=999999); cols = self.columns()
        with open(path, "w", encoding="utf-8") as f:
            json.dump([dict(zip(cols, r)) for r in rows], f, indent=2, ensure_ascii=False)

    def stats(self):
        return self.conn.execute("""
            SELECT protocol, COUNT(*) cnt, ROUND(AVG(power_dbm),1),
                   ROUND(MIN(freq_hz)/1e6,3), ROUND(MAX(freq_hz)/1e6,3)
            FROM signals GROUP BY protocol ORDER BY cnt DESC
        """).fetchall()

    def count(self):
        return self.conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]

    def delete(self, sig_id):
        self.conn.execute("DELETE FROM signals WHERE id=?", (sig_id,))
        self.conn.commit()

    def save_fingerprint(self, name, freq_hz, features):
        ts = datetime.utcnow().isoformat()
        self.conn.execute("INSERT INTO fingerprints VALUES(NULL,?,?,?,?)",
                          (name, freq_hz, json.dumps(features), ts))
        self.conn.commit()

    def get_fingerprints(self):
        return self.conn.execute("SELECT * FROM fingerprints").fetchall()

    def close(self):
        self.conn.close()
