# -*- coding: utf-8 -*-
"""
Interface (ABC) — tru cot cho Dependency Inversion. Service tang tren phu
thuoc vao truu tuong nay, khong phu thuoc hien thuc cu the (socket thuan,
dnspython...). De thay the / test / mo rong.
"""
from __future__ import annotations
from abc import ABC, abstractmethod

from .models import NameServer, ServerProbe


class DnsResolver(ABC):
    """Truy van DNS toi MOT may chu cu the (khong de quy qua resolver he thong)."""
    @abstractmethod
    def query(self, server: NameServer, qname: str, qtype: str,
              prefer_ipv6: bool = False) -> ServerProbe: ...


class RecordCheck(ABC):
    """
    Mot 'phep kiem tra' cho mot loai ban ghi. Mo rong bang cach them lop moi
    (Open/Closed) — khong sua WatchService.
    """
    qtype: str = "NS"

    @abstractmethod
    def ok(self, probe: ServerProbe) -> bool:
        """Dua tren ket qua probe, may chu nay co coi la 'giai duoc' khong."""
        ...


class Clock(ABC):
    """Nguon thoi gian — tach ra de test de dang."""
    @abstractmethod
    def now(self) -> int: ...
