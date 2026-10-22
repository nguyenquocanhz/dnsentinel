# -*- coding: utf-8 -*-
"""
Ma hoa/giai ma goi tin DNS theo RFC 1035 — PYTHON THUAN (khong phu thuoc).
Chi lam dung viec can cho giam sat: dung truy van, doc rcode + dem ban ghi +
giai ma vai loai RDATA pho bien (A/AAAA/NS/SOA/CNAME) de hien thi.
"""
from __future__ import annotations
import struct
from typing import Dict, List, Tuple

# Loai ban ghi ho tro
QTYPES: Dict[str, int] = {
    "A": 1, "NS": 2, "CNAME": 5, "SOA": 6, "AAAA": 28,
}
_TYPE_NAME = {v: k for k, v in QTYPES.items()}

RCODES = {
    0: "NOERROR", 1: "FORMERR", 2: "SERVFAIL", 3: "NXDOMAIN",
    4: "NOTIMP", 5: "REFUSED",
}


class DNSFormatError(Exception):
    """Goi tin DNS khong hop le / khong giai ma duoc."""


def _encode_name(name: str) -> bytes:
    out = bytearray()
    name = name.rstrip(".")
    if name:
        for label in name.split("."):
            b = label.encode("ascii", "ignore")
            if len(b) > 63:
                raise DNSFormatError("Label qua dai (>63)")
            out.append(len(b))
            out.extend(b)
    out.append(0)
    return bytes(out)


def build_query(qname: str, qtype: str, qid: int, rd: bool = False) -> bytes:
    """
    Tao goi truy van. rd=False (khong de quy) vi ta hoi truc tiep may chu uy
    quyen; chung se tra loi uy quyen hoac referral (delegation).
    """
    if qtype not in QTYPES:
        raise DNSFormatError(f"Loai ban ghi khong ho tro: {qtype}")
    flags = 0x0100 if rd else 0x0000  # standard query
    header = struct.pack(">HHHHHH", qid & 0xFFFF, flags, 1, 0, 0, 0)
    question = _encode_name(qname) + struct.pack(">HH", QTYPES[qtype], 1)  # IN
    return header + question


def _read_name(data: bytes, offset: int) -> Tuple[str, int]:
    """Doc ten co nen (compression pointer). Tra (ten, offset_sau_khi_doc)."""
    labels: List[str] = []
    jumped = False
    orig_offset = offset
    steps = 0
    while True:
        if offset >= len(data):
            raise DNSFormatError("Vuot gioi han khi doc ten")
        length = data[offset]
        if length & 0xC0 == 0xC0:  # pointer 2 byte
            if offset + 1 >= len(data):
                raise DNSFormatError("Pointer hong")
            ptr = ((length & 0x3F) << 8) | data[offset + 1]
            if not jumped:
                orig_offset = offset + 2
            offset = ptr
            jumped = True
            steps += 1
            if steps > 128:
                raise DNSFormatError("Vong lap pointer")
            continue
        offset += 1
        if length == 0:
            break
        labels.append(data[offset:offset + length].decode("ascii", "ignore"))
        offset += length
    name = ".".join(labels)
    return name, (orig_offset if jumped else offset)


def _read_rdata(data: bytes, rtype: int, rdlength: int, offset: int) -> str:
    """Giai ma RDATA vai loai pho bien thanh chuoi de hien thi."""
    end = offset + rdlength
    try:
        if rtype == 1 and rdlength == 4:            # A
            return ".".join(str(b) for b in data[offset:end])
        if rtype == 28 and rdlength == 16:          # AAAA
            parts = [f"{data[i] << 8 | data[i+1]:x}"
                     for i in range(offset, end, 2)]
            return ":".join(parts)
        if rtype in (2, 5):                         # NS / CNAME
            name, _ = _read_name(data, offset)
            return name
        if rtype == 6:                              # SOA
            mname, off = _read_name(data, offset)
            rname, _ = _read_name(data, off)
            return f"{mname} {rname}"
    except DNSFormatError:
        pass
    return ""  # loai khac: bo qua noi dung, chi can dem


def parse_response(data: bytes) -> Dict:
    """Giai ma goi tra loi. Tra dict: rcode, counts, answers[], authority[]."""
    if len(data) < 12:
        raise DNSFormatError("Goi tra loi qua ngan")
    (qid, flags, qdcount, ancount, nscount,
     arcount) = struct.unpack(">HHHHHH", data[:12])
    rcode = RCODES.get(flags & 0x0F, str(flags & 0x0F))
    offset = 12
    # bo qua phan question
    for _ in range(qdcount):
        _, offset = _read_name(data, offset)
        offset += 4  # QTYPE + QCLASS

    def read_rrset(count):
        nonlocal offset
        out = []
        for _ in range(count):
            name, offset = _read_name(data, offset)
            if offset + 10 > len(data):
                raise DNSFormatError("RR header hong")
            rtype, rclass, ttl, rdlength = struct.unpack(
                ">HHIH", data[offset:offset + 10])
            offset += 10
            rdata = _read_rdata(data, rtype, rdlength, offset)
            offset += rdlength
            out.append({
                "name": name, "type": _TYPE_NAME.get(rtype, str(rtype)),
                "ttl": ttl, "data": rdata,
            })
        return out

    answers = read_rrset(ancount)
    authority = read_rrset(nscount)
    # bo qua additional (arcount) — khong can
    return {
        "qid": qid, "rcode": rcode, "aa": bool(flags & 0x0400),
        "tc": bool(flags & 0x0200),
        "ancount": ancount, "nscount": nscount, "arcount": arcount,
        "answers": answers, "authority": authority,
    }
