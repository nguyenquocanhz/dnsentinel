# -*- coding: utf-8 -*-
"""
Quan ly ket noi SQLite + schema. CHI lo ket noi/schema (Single Responsibility);
truy van nghiep vu nam o cac repository. Mot file SQLite la nguon du lieu duy
nhat (quyen 600).
"""
import os
import sqlite3
import threading
from pathlib import Path


class Database:
    def __init__(self, path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        new = not os.path.exists(self.path)
        self._local = threading.local()
        self._init_schema()
        if new:
            try:
                os.chmod(self.path, 0o600)   # file co the chua du lieu rieng
            except OSError:
                pass

    def conn(self) -> sqlite3.Connection:
        c = getattr(self._local, "conn", None)
        if c is None:
            c = sqlite3.connect(self.path, timeout=15, check_same_thread=False)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA synchronous=NORMAL")
            c.execute("PRAGMA foreign_keys=ON")
            self._local.conn = c
        return c

    def _init_schema(self):
        with self.conn() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS settings(
                key TEXT PRIMARY KEY,
                value TEXT);

            CREATE TABLE IF NOT EXISTS domains(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT UNIQUE NOT NULL,
                descr TEXT DEFAULT '',
                status TEXT DEFAULT 'unknown',
                enabled INTEGER DEFAULT 1,
                createDate INTEGER,
                updateDate INTEGER,
                lastCheck INTEGER);

            CREATE TABLE IF NOT EXISTS checks(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain_id INTEGER NOT NULL,
                ts INTEGER NOT NULL,
                status TEXT NOT NULL,
                servers_total INTEGER DEFAULT 0,
                servers_ok INTEGER DEFAULT 0,
                rtt_ms INTEGER DEFAULT 0,
                FOREIGN KEY(domain_id) REFERENCES domains(id) ON DELETE CASCADE);

            CREATE TABLE IF NOT EXISTS probes(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                check_id INTEGER NOT NULL,
                server TEXT,
                address TEXT,
                qtype TEXT,
                ok INTEGER DEFAULT 0,
                rcode TEXT DEFAULT '',
                answers INTEGER DEFAULT 0,
                authority INTEGER DEFAULT 0,
                rtt_ms INTEGER DEFAULT 0,
                error TEXT DEFAULT '',
                FOREIGN KEY(check_id) REFERENCES checks(id) ON DELETE CASCADE);

            CREATE INDEX IF NOT EXISTS idx_checks_domain_ts
                ON checks(domain_id, ts);
            CREATE INDEX IF NOT EXISTS idx_probes_check
                ON probes(check_id);
            """)
