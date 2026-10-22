# -*- coding: utf-8 -*-
"""Mo hinh du lieu thuan (dataclass) — khong logic I/O."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional


# ---- Trang thai tong hop cua mot ten mien ----
STATUS_UP = "up"              # moi may chu quoc gia deu tra loi tot
STATUS_DEGRADED = "degraded"  # mot so tra loi, mot so khong
STATUS_DOWN = "down"          # khong may chu nao tra loi/giai duoc
STATUS_UNKNOWN = "unknown"    # chua kiem tra


@dataclass
class NameServer:
    """Mot may chu ten mien quoc gia VNNIC (du lieu thuan)."""
    host: str            # vd a.dns-servers.vn
    ipv4: str            # dia chi IPv4
    ipv6: str = ""       # dia chi IPv6 (neu co)

    def address(self, prefer_ipv6: bool = False) -> str:
        if prefer_ipv6 and self.ipv6:
            return self.ipv6
        return self.ipv4


@dataclass
class ServerProbe:
    """Ket qua truy van toi MOT may chu cho MOT loai ban ghi."""
    server: str          # host cua NameServer
    address: str         # dia chi IP da truy van
    qtype: str           # A / AAAA / NS / SOA
    ok: bool             # co cau tra loi dung khong
    rcode: str = ""      # NOERROR / NXDOMAIN / SERVFAIL / ...
    answers: int = 0     # so ban ghi answer
    authority: int = 0   # so ban ghi authority (delegation)
    rtt_ms: int = 0      # thoi gian phan hoi (ms); -1 neu that bai
    records: List[str] = field(default_factory=list)  # noi dung tom tat
    error: str = ""      # mo ta loi neu that bai


@dataclass
class CheckResult:
    """Ket qua tong hop cua mot lan kiem tra mot ten mien."""
    domain: str
    ts: int
    status: str
    servers_total: int
    servers_ok: int
    rtt_ms: int                 # trung binh thoi gian phan hoi cac server OK
    probes: List[ServerProbe] = field(default_factory=list)

    @property
    def ratio(self) -> float:
        if self.servers_total == 0:
            return 0.0
        return self.servers_ok / self.servers_total


@dataclass
class Domain:
    """Mot ban ghi ten mien trong danh sach giam sat."""
    id: int
    domain: str
    descr: str = ""
    status: str = STATUS_UNKNOWN
    enabled: bool = True
    create_date: Optional[int] = None
    update_date: Optional[int] = None
    last_check: Optional[int] = None


@dataclass
class UptimeStat:
    """Thong ke uptime cua mot ten mien trong khoang thoi gian."""
    domain: str
    window_sec: int
    total_checks: int
    up_checks: int
    degraded_checks: int
    down_checks: int
    avg_rtt_ms: int

    @property
    def uptime_pct(self) -> float:
        if self.total_checks == 0:
            return 0.0
        # degraded tinh 1/2 diem — van giai duoc nhung khong tron ven
        score = self.up_checks + 0.5 * self.degraded_checks
        return round(100.0 * score / self.total_checks, 2)
