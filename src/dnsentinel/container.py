# -*- coding: utf-8 -*-
"""
Container — diem rap noi (composition root). Rap resolver + repository +
service lai voi nhau tu cau hinh trong SQLite. Giu Dependency Inversion:
tang tren chi thay interface, viec chon hien thuc nam o day.
"""
from __future__ import annotations

from .paths import db_path
from .data.database import Database
from .data.repositories import (
    SettingsRepository, DomainRepository, CheckRepository,
)
from .resolve.resolver import StdlibDnsResolver
from .resolve.servers import default_servers
from .services.watch_service import WatchService
from .services.uptime_service import UptimeService


class Container:
    def __init__(self, path=None):
        self.db = Database(path or db_path())
        self.settings = SettingsRepository(self.db)
        self.settings.seed_defaults()
        self.domains = DomainRepository(self.db)
        self.checks = CheckRepository(self.db)

        self.servers = default_servers()
        self.resolver = StdlibDnsResolver(
            timeout=self.settings.get_float("watch.timeout", 3.0),
            retries=self.settings.get_int("watch.retries", 1),
        )
        self.watch = WatchService(
            self.resolver, self.servers,
            self.domains, self.checks, self.settings)
        self.uptime = UptimeService(self.domains, self.checks)

    @property
    def interval(self) -> int:
        return self.settings.get_int("watch.interval", 300)
