# -*- coding: utf-8 -*-
"""UptimeService — tinh uptime % tu lich su kiem tra (bang checks)."""
from __future__ import annotations
from typing import List

from ..core.models import UptimeStat


class UptimeService:
    def __init__(self, domain_repo, check_repo):
        self.domains = domain_repo
        self.checks = check_repo

    def for_domain(self, domain: str, window_sec: int = 86400) -> UptimeStat:
        dom = self.domains.get_by_name(domain)
        if not dom:
            return UptimeStat(domain, window_sec, 0, 0, 0, 0, 0)
        return self.checks.uptime(dom.domain, dom.id, window_sec)

    def for_all(self, window_sec: int = 86400) -> List[UptimeStat]:
        return [self.checks.uptime(d.domain, d.id, window_sec)
                for d in self.domains.list()]

    def prune(self, keep_days: int = 90) -> int:
        return self.checks.prune(keep_days)
