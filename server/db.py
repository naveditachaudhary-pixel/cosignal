"""Storage. SQLite for the MVP; the same tables map directly onto Postgres."""
import json
import os
import sqlite3
import threading
import time
import uuid

_lock = threading.Lock()


class Store:
    def __init__(self, path=None):
        self.path = path or os.getenv("COSIGNAL_DB", "cosignal.db")
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS runs(
            id TEXT PRIMARY KEY, workspace TEXT, agent TEXT, started_at INTEGER, status TEXT,
            cost REAL, duration INTEGER, risky INTEGER, body TEXT);
        CREATE INDEX IF NOT EXISTS runs_agent_time ON runs(workspace, agent, started_at);
        CREATE TABLE IF NOT EXISTS approvals(
            id TEXT PRIMARY KEY, workspace TEXT, run_id TEXT, agent TEXT, action TEXT, payload TEXT,
            policies TEXT, reason TEXT, status TEXT, created_at INTEGER, decided_at INTEGER, decided_by TEXT, note TEXT);
        CREATE INDEX IF NOT EXISTS approvals_status ON approvals(workspace, status, created_at);
        CREATE TABLE IF NOT EXISTS audit(
            seq INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER, workspace TEXT, kind TEXT, run_id TEXT, agent TEXT,
            action TEXT, decision TEXT, actor TEXT, detail TEXT);
        """)
        self.conn.commit()

    # ---- runs ----
    def save(self, run):
        with _lock:
            self.conn.execute("INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?,?,?,?)",
                              (run["id"], run["workspace"], run["agent"], run["started_at"], run["status"],
                               run["cost"], run["duration"], run["risky"], json.dumps(run)))
            self.conn.commit()

    def get(self, run_id):
        row = self.conn.execute("SELECT body FROM runs WHERE id=?", (run_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def query(self, workspace="default", agent=None, status=None, since=None, limit=None):
        sql, args = "SELECT body FROM runs WHERE workspace=?", [workspace]
        if agent:
            sql += " AND agent=?"; args.append(agent)
        if status:
            sql += " AND status=?"; args.append(status)
        if since:
            sql += " AND started_at>?"; args.append(since)
        sql += " ORDER BY started_at DESC"
        if limit:
            sql += " LIMIT ?"; args.append(int(limit))
        return [json.loads(r[0]) for r in self.conn.execute(sql, args)]

    # ---- approvals ----
    _COLS = ["id", "workspace", "run_id", "agent", "action", "payload", "policies", "reason", "status",
             "created_at", "decided_at", "decided_by", "note"]

    def _approval(self, row):
        a = dict(zip(self._COLS, row))
        a["payload"], a["policies"] = json.loads(a["payload"] or "{}"), json.loads(a["policies"] or "[]")
        return a

    def create_approval(self, workspace, run_id, agent, action, payload, policies, reason, created_at=None):
        aid = "apr_" + uuid.uuid4().hex[:10]
        with _lock:
            self.conn.execute("INSERT INTO approvals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                              (aid, workspace, run_id, agent, action, json.dumps(payload), json.dumps(policies), reason,
                               "pending", created_at or int(time.time() * 1000), None, None, None))
            self.conn.commit()
        return self.get_approval(aid)

    def get_approval(self, aid):
        row = self.conn.execute(f"SELECT {','.join(self._COLS)} FROM approvals WHERE id=?", (aid,)).fetchone()
        return self._approval(row) if row else None

    def list_approvals(self, workspace="default", status=None, limit=200):
        sql, args = f"SELECT {','.join(self._COLS)} FROM approvals WHERE workspace=?", [workspace]
        if status:
            sql += " AND status=?"; args.append(status)
        sql += " ORDER BY created_at DESC LIMIT ?"; args.append(int(limit))
        return [self._approval(r) for r in self.conn.execute(sql, args)]

    def decide_approval(self, aid, status, by, note):
        with _lock:
            cur = self.conn.execute("UPDATE approvals SET status=?, decided_at=?, decided_by=?, note=? WHERE id=? AND status='pending'",
                                    (status, int(time.time() * 1000), by, note, aid))
            self.conn.commit()
        return cur.rowcount == 1

    # ---- audit trail (append-only) ----
    def audit(self, workspace, kind, run_id, agent, action, decision, actor, detail, ts=None):
        with _lock:
            self.conn.execute("INSERT INTO audit(ts,workspace,kind,run_id,agent,action,decision,actor,detail) VALUES (?,?,?,?,?,?,?,?,?)",
                              (ts or int(time.time() * 1000), workspace, kind, run_id, agent, action, decision, actor, json.dumps(detail)))
            self.conn.commit()

    def list_audit(self, workspace="default", limit=200):
        rows = self.conn.execute("SELECT seq,ts,kind,run_id,agent,action,decision,actor,detail FROM audit WHERE workspace=? ORDER BY seq DESC LIMIT ?",
                                 (workspace, int(limit))).fetchall()
        keys = ["seq", "ts", "kind", "run_id", "agent", "action", "decision", "actor", "detail"]
        return [dict(zip(keys, r[:-1]), detail=json.loads(r[-1] or "{}")) for r in rows]
