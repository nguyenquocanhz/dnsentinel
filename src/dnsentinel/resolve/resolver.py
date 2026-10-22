# -*- coding: utf-8 -*-
"""
StdlibDnsResolver — truy van DNS toi MOT may chu cu the qua socket thuan
(UDP, fallback TCP khi bi cat ngan). Hien thuc cua interface DnsResolver.
"""
from __future__ import annotations
import os
import socket
import struct
import time

from ..core.interfaces import DnsResolver
from ..core.models import NameServer, ServerProbe
from . import message


class StdlibDnsResolver(DnsResolver):
    def __init__(self, timeout: float = 3.0, retries: int = 1,
                 max_records: int = 4):
        self.timeout = timeout
        self.retries = max(1, retries)
        self.max_records = max_records

    # ---- UDP (co fallback TCP khi TC=1) ----
    def _udp(self, address: str, family: int, packet: bytes) -> bytes:
        s = socket.socket(family, socket.SOCK_DGRAM)
        s.settimeout(self.timeout)
        try:
            s.sendto(packet, (address, 53))
            data, _ = s.recvfrom(4096)
            return data
        finally:
            s.close()

    def _tcp(self, address: str, family: int, packet: bytes) -> bytes:
        s = socket.socket(family, socket.SOCK_STREAM)
        s.settimeout(self.timeout)
        try:
            s.connect((address, 53))
            s.sendall(struct.pack(">H", len(packet)) + packet)
            head = self._recv_n(s, 2)
            (ln,) = struct.unpack(">H", head)
            return self._recv_n(s, ln)
        finally:
            s.close()

    @staticmethod
    def _recv_n(s: socket.socket, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = s.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("Ket noi dong som")
            buf += chunk
        return buf

    def query(self, server: NameServer, qname: str, qtype: str,
              prefer_ipv6: bool = False) -> ServerProbe:
        address = server.address(prefer_ipv6)
        family = socket.AF_INET6 if ":" in address else socket.AF_INET
        qid = int.from_bytes(os.urandom(2), "big")
        packet = message.build_query(qname, qtype, qid, rd=False)

        last_err = ""
        for _ in range(self.retries):
            t0 = time.monotonic()
            try:
                data = self._udp(address, family, packet)
                parsed = message.parse_response(data)
                if parsed.get("tc"):   # bi cat ngan -> thu lai qua TCP
                    data = self._tcp(address, family, packet)
                    parsed = message.parse_response(data)
                rtt = int((time.monotonic() - t0) * 1000)
                return self._to_probe(server, address, qtype, parsed, rtt)
            except socket.timeout:
                last_err = "timeout"
            except (OSError, message.DNSFormatError, ConnectionError) as e:
                last_err = f"{type(e).__name__}: {e}"
        return ServerProbe(
            server=server.host, address=address, qtype=qtype, ok=False,
            rcode="", answers=0, authority=0, rtt_ms=-1,
            records=[], error=last_err or "khong phan hoi")

    def _to_probe(self, server, address, qtype, parsed, rtt) -> ServerProbe:
        recs = []
        for rr in (parsed["answers"] + parsed["authority"]):
            if rr["data"]:
                recs.append(f"{rr['type']} {rr['data']}")
            if len(recs) >= self.max_records:
                break
        # 'ok' = co phan hoi NOERROR va co du lieu (answer hoac delegation)
        ok = (parsed["rcode"] == "NOERROR"
              and (parsed["ancount"] > 0 or parsed["nscount"] > 0))
        return ServerProbe(
            server=server.host, address=address, qtype=qtype, ok=ok,
            rcode=parsed["rcode"], answers=parsed["ancount"],
            authority=parsed["nscount"], rtt_ms=rtt, records=recs, error="")
