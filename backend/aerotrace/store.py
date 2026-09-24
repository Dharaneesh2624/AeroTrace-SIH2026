"""Transactional persistence, idempotent replay, independent engine/session/ECU state."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
from .monitor import process, empty_state

class Conflict(ValueError):
    pass

class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as con:
            con.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS streams (
                    engine TEXT, session TEXT, source TEXT, mode TEXT NOT NULL, last_time TEXT,
                    state TEXT NOT NULL, PRIMARY KEY(engine,session,source));
                CREATE TABLE IF NOT EXISTS samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, engine TEXT, session TEXT, source TEXT,
                    time TEXT, input_hash TEXT, result TEXT,
                    UNIQUE(engine,session,source,time));
                CREATE INDEX IF NOT EXISTS stream_samples ON samples(engine,session,source,id);
            """)

    def connect(self):
        con = sqlite3.connect(self.path, timeout=20)
        con.row_factory = sqlite3.Row
        return con

    def ingest(self, record, source, mode, model, input_payload):
        key = (record.engine, record.session, source)
        digest = hashlib.sha256(json.dumps(input_payload, sort_keys=True, allow_nan=False).encode()).hexdigest()
        time = record.time.isoformat()
        with closing(self.connect()) as con, con:
            con.execute("BEGIN IMMEDIATE")
            existing = con.execute("SELECT input_hash,result,id FROM samples WHERE engine=? AND session=? AND source=? AND time=?", (*key, time)).fetchone()
            if existing:
                if existing["input_hash"] != digest:
                    raise Conflict("Conflicting payload at an existing stream timestamp")
                return dict(json.loads(existing["result"]), sample_id=existing["id"], duplicate=True)
            stream = con.execute("SELECT * FROM streams WHERE engine=? AND session=? AND source=?", key).fetchone()
            if stream and stream["mode"] != mode:
                raise Conflict("A stream cannot mix live and replay modes")
            if stream and time <= stream["last_time"]:
                raise Conflict("Out-of-order packet; start a distinct replay session to reprocess history")
            state = json.loads(stream["state"]) if stream else empty_state()
            result, state = process(record, model, state)
            result.update(source_id=source, mode=mode)
            cursor = con.execute("INSERT INTO samples(engine,session,source,time,input_hash,result) VALUES (?,?,?,?,?,?)",
                                 (*key, time, digest, json.dumps(result, allow_nan=False)))
            con.execute("INSERT INTO streams VALUES(?,?,?,?,?,?) ON CONFLICT(engine,session,source) DO UPDATE SET last_time=excluded.last_time,state=excluded.state",
                        (*key, mode, time, json.dumps(state, allow_nan=False)))
            return dict(result, sample_id=cursor.lastrowid, duplicate=False)

    def history(self, engine, session, source, after=0, limit=100):
        with closing(self.connect()) as con:
            rows = con.execute("SELECT id,result FROM samples WHERE engine=? AND session=? AND source=? AND id>? ORDER BY id LIMIT ?",
                               (engine, session, source, after, limit)).fetchall()
        return [dict(json.loads(r["result"]), sample_id=r["id"]) for r in rows]

    def latest(self, engine, session, source):
        with closing(self.connect()) as con:
            row = con.execute("SELECT id,result FROM samples WHERE engine=? AND session=? AND source=? ORDER BY id DESC LIMIT 1",
                              (engine, session, source)).fetchone()
        return dict(json.loads(row["result"]), sample_id=row["id"]) if row else None

    def streams(self):
        with closing(self.connect()) as con:
            rows = con.execute("SELECT engine,session,source,mode,last_time FROM streams ORDER BY last_time DESC LIMIT 1000").fetchall()
        return [dict(r) for r in rows]

