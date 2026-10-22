# -*- coding: utf-8 -*-
"""
Cac phep kiem tra theo loai ban ghi (Open/Closed). Them loai moi = them lop,
khong sua WatchService. Moi lop quyet dinh khi nao mot probe coi la 'giai duoc'.
"""
from __future__ import annotations
from typing import Dict

from ..core.interfaces import RecordCheck
from ..core.models import ServerProbe


class NSCheck(RecordCheck):
    """Hoi NS cua ten mien — may chu .vn tra ve uy quyen/delegation."""
    qtype = "NS"

    def ok(self, probe: ServerProbe) -> bool:
        return probe.ok and (probe.answers > 0 or probe.authority > 0)


class SOACheck(RecordCheck):
    """Hoi SOA — co ban ghi SOA (answer hoac authority) la dat."""
    qtype = "SOA"

    def ok(self, probe: ServerProbe) -> bool:
        return probe.ok and (probe.answers > 0 or probe.authority > 0)


class ACheck(RecordCheck):
    """Hoi A — can co ban ghi dia chi trong answer (truy van uy quyen)."""
    qtype = "A"

    def ok(self, probe: ServerProbe) -> bool:
        return probe.ok and (probe.answers > 0 or probe.authority > 0)


class AAAACheck(ACheck):
    qtype = "AAAA"


_REGISTRY: Dict[str, RecordCheck] = {
    c.qtype: c for c in (NSCheck(), SOACheck(), ACheck(), AAAACheck())
}


def get_check(qtype: str) -> RecordCheck:
    """Lay phep kiem tra theo loai ban ghi (mac dinh NS neu khong ro)."""
    return _REGISTRY.get((qtype or "NS").upper(), _REGISTRY["NS"])
