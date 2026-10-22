# -*- coding: utf-8 -*-
"""
Cum may chu ten mien quoc gia Viet Nam (VNNIC) — DU LIEU THUAN.
Nguon: https://vnnic.vn/en/dns/dns-system/vietnam-national-domain-name-server-system
Cap nhat: 2026-10 (xac minh lai dinh ky tai trang tren).

Day la cac may chu uy quyen cho vung .vn; truy van NS/SOA cua mot ten mien .vn
toi day cho biet 'duong phan giai .vn' co khoe manh khong.
"""
from __future__ import annotations
from typing import List

from ..core.models import NameServer

VNNIC_SERVERS: List[NameServer] = [
    NameServer("a.dns-servers.vn", "194.0.1.18",      "2001:678:4::12"),
    NameServer("b.dns-servers.vn", "203.119.73.105",  "2001:dc8:1:2::105"),
    NameServer("c.dns-servers.vn", "203.119.38.105",  "2001:dc8:c000:7::105"),
    NameServer("d.dns-servers.vn", "203.119.44.105",  "2001:dc8:8000:2::105"),
    NameServer("e.dns-servers.vn", "203.119.60.105",  "2001:dc8:1000:2::105"),
    NameServer("f.dns-servers.vn", "203.119.68.105",  "2001:dc8:d000:2::105"),
    NameServer("g.dns-servers.vn", "204.61.216.115",  "2001:500:14:6115:ad::1"),
    NameServer("h.dns-servers.vn", "202.47.142.105",  "2001:dc8:6000::105"),
]


def default_servers() -> List[NameServer]:
    return list(VNNIC_SERVERS)
