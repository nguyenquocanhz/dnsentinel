# -*- coding: utf-8 -*-
"""
Lop hien thi — dung 'rich' neu co, neu khong tu dong fallback ra text thuan.
Nho the CLI chay duoc ngay tren box chua cai gi (khong phu thuoc bat buoc).
"""
from __future__ import annotations
from typing import List, Sequence

try:
    from rich.console import Console
    from rich.table import Table
    from rich import box
    _RICH = True
    _C = Console()
except Exception:  # rich chua cai -> fallback
    _RICH = False
    _C = None

# Mau trang thai (chi dung khi co rich)
_STATUS_STYLE = {
    "up": "green", "degraded": "yellow", "down": "red", "unknown": "dim",
}


def echo(msg: str = ""):
    if _RICH:
        _C.print(msg)
    else:
        # bo cac the mau don gian [..]
        import re
        print(re.sub(r"\[/?[a-z0-9 =#]*\]", "", msg))


def status_text(status: str) -> str:
    if _RICH:
        style = _STATUS_STYLE.get(status, "white")
        return f"[{style}]{status}[/]"
    return status


def table(title: str, columns: Sequence[str], rows: List[Sequence]):
    if _RICH:
        t = Table(title=title, box=box.SIMPLE, expand=False)
        for col in columns:
            t.add_column(col)
        for r in rows:
            t.add_row(*[str(x) for x in r])
        _C.print(t)
        return
    # ---- fallback text ----
    widths = [len(c) for c in columns]
    srows = [[str(x) for x in r] for r in rows]
    for r in srows:
        for i, cell in enumerate(r):
            widths[i] = max(widths[i], len(cell))
    if title:
        print(f"\n{title}")
    line = "  ".join(c.ljust(widths[i]) for i, c in enumerate(columns))
    print(line)
    print("  ".join("-" * widths[i] for i in range(len(columns))))
    for r in srows:
        print("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(r)))
