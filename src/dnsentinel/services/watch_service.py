# -*- coding: utf-8 -*-
"""
WatchService — kiem tra phan giai mot ten mien .vn qua TAT CA may chu quoc gia
VNNIC, tong hop trang thai (up/degraded/down), luu lich su va cap nhat domains.
"""
from __future__ import annotations
import time
from typing import List, Optional

from ..core.interfaces import DnsResolver
from ..core.models import (
    CheckResult, NameServer, STATUS_UP, STATUS_DEGRADED, STATUS_DOWN,
)
from ..resolve import checks as checks_mod


class WatchService:
    def __init__(self, resolver: DnsResolver, servers: List[NameServer],
                 domain_repo, check_repo, settings_repo):
        self.resolver = resolver
        self.servers = servers
        self.domains = domain_repo
        self.checks = check_repo
        self.settings = settings_repo

    def _aggregate(self, servers_total, servers_ok, degraded_ratio) -> str:
        if servers_ok == 0:
            return STATUS_DOWN
        if servers_ok == servers_total:
            return STATUS_UP
        if servers_total and (servers_ok / servers_total) >= degraded_ratio:
            return STATUS_DEGRADED
        return STATUS_DOWN

    def check_domain(self, domain: str, qtype: Optional[str] = None,
                     persist: bool = True) -> CheckResult:
        """Kiem tra mot ten mien qua cum VNNIC. Tra CheckResult."""
        qtype = (qtype or self.settings.get("watch.qtype", "NS")).upper()
        check = checks_mod.get_check(qtype)
        prefer_ipv6 = self.settings.get_bool("watch.prefer_ipv6", False)
        degraded_ratio = self.settings.get_float("watch.degraded_ratio", 0.5)

        probes = []
        ok_rtts = []
        for srv in self.servers:
            p = self.resolver.query(srv, domain, check.qtype, prefer_ipv6)
            p.ok = check.ok(p)  # phep kiem tra quyet dinh 'dat' hay khong
            probes.append(p)
            if p.ok and p.rtt_ms >= 0:
                ok_rtts.append(p.rtt_ms)

        servers_ok = sum(1 for p in probes if p.ok)
        status = self._aggregate(len(probes), servers_ok, degraded_ratio)
        result = CheckResult(
            domain=domain, ts=int(time.time()), status=status,
            servers_total=len(probes), servers_ok=servers_ok,
            rtt_ms=int(sum(ok_rtts) / len(ok_rtts)) if ok_rtts else 0,
            probes=probes)

        if persist:
            dom = self.domains.get_by_name(domain)
            if dom:
                cid = self.checks.record(dom.id, result)  # noqa: F841
                self.domains.set_status(dom.id, status, result.ts)
        return result

    def check_all(self, qtype: Optional[str] = None) -> List[CheckResult]:
        """Kiem tra moi ten mien dang bat giam sat."""
        out = []
        for dom in self.domains.list(enabled_only=True):
            out.append(self.check_domain(dom.domain, qtype=qtype, persist=True))
        return out
