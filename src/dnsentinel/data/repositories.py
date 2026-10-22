# -*- coding: utf-8 -*-
"""
Repository — moi lop phu trach MOT nhom bang (Single Responsibility,
Interface Segregation). Deu nhan Database (nha cung cap ket noi).
"""
import re
import time

from ..core.exceptions import DomainInvalid, DomainExists, DomainNotFound
from ..core.models import (
    Domain, CheckResult, UptimeStat,
    STATUS_UP, STATUS_DEGRADED, STATUS_DOWN, STATUS_UNKNOWN,
)

DEFAULT_SETTINGS = {
    "watch.interval": "300",        # giay giua 2 vong kiem tra
    "watch.qtype": "NS",            # loai ban ghi mac dinh kiem tra
    "watch.timeout": "3.0",         # timeout moi truy van (giay)
    "watch.retries": "1",           # so lan thu lai moi server
    "watch.prefer_ipv6": "0",       # uu tien IPv6 khi truy van
    "watch.degraded_ratio": "0.5",  # ty le server OK toi thieu de coi la 'len'
    "retention.days": "90",         # giu lich su kiem tra bao nhieu ngay
}

# Ten mien .vn hop le (ho tro domain cap 2 va cap 3: vd chinhphu.vn, moj.gov.vn)
_DOMAIN_RE = re.compile(
    r"^(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+vn$"
)

_STATUS_COL = {
    STATUS_UP: "up_checks",
    STATUS_DEGRADED: "degraded_checks",
    STATUS_DOWN: "down_checks",
}


def normalize_domain(raw: str) -> str:
    """Chuan hoa + xac thuc ten mien .vn. Nem DomainInvalid neu sai."""
    if raw is None:
        raise DomainInvalid("Ten mien rong")
    d = raw.strip().lower().rstrip(".")
    if d.startswith("http://"):
        d = d[7:]
    elif d.startswith("https://"):
        d = d[8:]
    d = d.split("/")[0]
    if not d:
        raise DomainInvalid("Ten mien rong")
    try:
        d = d.encode("idna").decode("ascii")  # ho tro ten mien tieng Viet
    except (UnicodeError, ValueError):
        pass
    if not d.endswith(".vn"):
        raise DomainInvalid(f"Chi ho tro ten mien .vn: {raw!r}")
    if not _DOMAIN_RE.match(d):
        raise DomainInvalid(f"Ten mien khong hop le: {raw!r}")
    return d


class SettingsRepository:
    def __init__(self, db):
        self.db = db

    def seed_defaults(self):
        with self.db.conn() as c:
            for k, v in DEFAULT_SETTINGS.items():
                c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",
                          (k, v))

    def get(self, key, default=None):
        r = self.db.conn().execute(
            "SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        if r is not None:
            return r["value"]
        return DEFAULT_SETTINGS.get(key, default)

    def get_int(self, key, default=0):
        try:
            return int(self.get(key, default))
        except (TypeError, ValueError):
            return default

    def get_float(self, key, default=0.0):
        try:
            return float(self.get(key, default))
        except (TypeError, ValueError):
            return default

    def get_bool(self, key, default=False):
        v = self.get(key, "1" if default else "0")
        return str(v).strip().lower() in ("1", "true", "yes", "on")

    def set(self, key, value):
        with self.db.conn() as c:
            c.execute("INSERT INTO settings(key,value) VALUES(?,?) "
                      "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                      (key, "" if value is None else str(value)))

    def all(self):
        rows = self.db.conn().execute("SELECT key,value FROM settings").fetchall()
        return {r["key"]: r["value"] for r in rows}


class DomainRepository:
    """Bang domains — danh sach ten mien giam sat."""
    def __init__(self, db):
        self.db = db

    @staticmethod
    def _row(r) -> Domain:
        return Domain(
            id=r["id"], domain=r["domain"], descr=r["descr"] or "",
            status=r["status"] or STATUS_UNKNOWN, enabled=bool(r["enabled"]),
            create_date=r["createDate"], update_date=r["updateDate"],
            last_check=r["lastCheck"],
        )

    def add(self, domain: str, descr: str = "") -> Domain:
        d = normalize_domain(domain)
        now = int(time.time())
        try:
            with self.db.conn() as c:
                cur = c.execute(
                    "INSERT INTO domains(domain,descr,status,enabled,"
                    "createDate,updateDate,lastCheck) VALUES(?,?,?,?,?,?,NULL)",
                    (d, descr, STATUS_UNKNOWN, 1, now, now))
                new_id = cur.lastrowid
        except Exception as e:  # sqlite3.IntegrityError -> UNIQUE
            if "UNIQUE" in str(e):
                raise DomainExists(f"Ten mien da ton tai: {d}")
            raise
        return self.get(new_id)

    def get(self, domain_id: int):
        r = self.db.conn().execute(
            "SELECT * FROM domains WHERE id=?", (domain_id,)).fetchone()
        return self._row(r) if r else None

    def get_by_name(self, domain: str):
        d = normalize_domain(domain)
        r = self.db.conn().execute(
            "SELECT * FROM domains WHERE domain=?", (d,)).fetchone()
        return self._row(r) if r else None

    def list(self, enabled_only: bool = False):
        q = "SELECT * FROM domains"
        if enabled_only:
            q += " WHERE enabled=1"
        q += " ORDER BY domain"
        return [self._row(r) for r in self.db.conn().execute(q).fetchall()]

    def update_meta(self, domain: str, descr=None, enabled=None):
        dom = self.get_by_name(domain)
        if not dom:
            raise DomainNotFound(f"Khong tim thay: {domain}")
        sets, args = ["updateDate=?"], [int(time.time())]
        if descr is not None:
            sets.append("descr=?"); args.append(descr)
        if enabled is not None:
            sets.append("enabled=?"); args.append(1 if enabled else 0)
        args.append(dom.id)
        with self.db.conn() as c:
            c.execute(f"UPDATE domains SET {','.join(sets)} WHERE id=?", args)
        return self.get(dom.id)

    def set_status(self, domain_id: int, status: str, last_check: int):
        with self.db.conn() as c:
            c.execute("UPDATE domains SET status=?,lastCheck=?,updateDate=? "
                      "WHERE id=?",
                      (status, last_check, int(time.time()), domain_id))

    def remove(self, domain: str) -> bool:
        d = normalize_domain(domain)
        with self.db.conn() as c:
            cur = c.execute("DELETE FROM domains WHERE domain=?", (d,))
            return cur.rowcount > 0


class CheckRepository:
    """Bang checks + probes — lich su kiem tra, phuc vu tinh uptime %."""
    def __init__(self, db):
        self.db = db

    def record(self, domain_id: int, result: CheckResult):
        with self.db.conn() as c:
            cur = c.execute(
                "INSERT INTO checks(domain_id,ts,status,servers_total,"
                "servers_ok,rtt_ms) VALUES(?,?,?,?,?,?)",
                (domain_id, result.ts, result.status, result.servers_total,
                 result.servers_ok, result.rtt_ms))
            check_id = cur.lastrowid
            c.executemany(
                "INSERT INTO probes(check_id,server,address,qtype,ok,rcode,"
                "answers,authority,rtt_ms,error) VALUES(?,?,?,?,?,?,?,?,?,?)",
                [(check_id, p.server, p.address, p.qtype, 1 if p.ok else 0,
                  p.rcode, p.answers, p.authority, p.rtt_ms, p.error)
                 for p in result.probes])
        return check_id

    def latest_probes(self, domain_id: int):
        """Chi tiet tung server cua lan kiem tra moi nhat (de chan doan)."""
        r = self.db.conn().execute(
            "SELECT id FROM checks WHERE domain_id=? ORDER BY ts DESC LIMIT 1",
            (domain_id,)).fetchone()
        if not r:
            return []
        rows = self.db.conn().execute(
            "SELECT server,address,qtype,ok,rcode,answers,authority,rtt_ms,error "
            "FROM probes WHERE check_id=? ORDER BY server", (r["id"],)).fetchall()
        return [dict(x) for x in rows]

    def uptime(self, domain: str, domain_id: int, window_sec: int) -> UptimeStat:
        since = int(time.time()) - window_sec
        counts = {"up_checks": 0, "degraded_checks": 0, "down_checks": 0}
        total = 0
        rtt_sum = rtt_n = 0
        for row in self.db.conn().execute(
                "SELECT status,servers_ok,rtt_ms FROM checks "
                "WHERE domain_id=? AND ts>=?", (domain_id, since)).fetchall():
            total += 1
            col = _STATUS_COL.get(row["status"])
            if col:
                counts[col] += 1
            if row["servers_ok"]:
                rtt_sum += row["rtt_ms"]; rtt_n += 1
        return UptimeStat(
            domain=domain, window_sec=window_sec, total_checks=total,
            up_checks=counts["up_checks"],
            degraded_checks=counts["degraded_checks"],
            down_checks=counts["down_checks"],
            avg_rtt_ms=int(rtt_sum / rtt_n) if rtt_n else 0,
        )

    def prune(self, keep_days: int = 90) -> int:
        cutoff = int(time.time()) - keep_days * 86400
        with self.db.conn() as c:
            cur = c.execute("DELETE FROM checks WHERE ts<?", (cutoff,))
            return cur.rowcount
