# -*- coding: utf-8 -*-
"""
CLI DNSentinel — quan ly danh sach ten mien .vn va xem trang thai phan giai
qua cum may chu quoc gia VNNIC.

  dnsentinel add chinhphu.vn -d "Cong TTDT Chinh phu"
  dnsentinel list
  dnsentinel check vnnic.vn
  dnsentinel check            # kiem tra tat ca
  dnsentinel status
  dnsentinel uptime vnnic.vn --days 7
  dnsentinel servers
  dnsentinel config list
"""
from __future__ import annotations
import argparse
import sys
from datetime import datetime

from .. import __version__
from ..container import Container
from ..core.exceptions import DomainInvalid, DomainExists, DomainNotFound
from . import render


def _fmt_ts(ts):
    if not ts:
        return "-"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


# ---------------- domain management ----------------
def cmd_add(k: Container, args):
    try:
        d = k.domains.add(args.domain, args.desc or "")
    except (DomainInvalid, DomainExists) as e:
        render.echo(f"[red]Loi:[/] {e}"); return 1
    render.echo(f"[green]Da them:[/] {d.domain}")
    if not args.no_check:
        _check_one(k, d.domain)
    return 0


def cmd_rm(k: Container, args):
    try:
        ok = k.domains.remove(args.domain)
    except DomainInvalid as e:
        render.echo(f"[red]Loi:[/] {e}"); return 1
    render.echo("[green]Da xoa.[/]" if ok else "[yellow]Khong tim thay.[/]")
    return 0 if ok else 1


def cmd_edit(k: Container, args):
    enabled = None
    if args.enable:
        enabled = True
    elif args.disable:
        enabled = False
    try:
        d = k.domains.update_meta(args.domain, descr=args.desc, enabled=enabled)
    except (DomainInvalid, DomainNotFound) as e:
        render.echo(f"[red]Loi:[/] {e}"); return 1
    render.echo(f"[green]Da cap nhat:[/] {d.domain} "
                f"(bat={d.enabled}, mo ta={d.descr!r})")
    return 0


def cmd_list(k: Container, args):
    doms = k.domains.list()
    if not doms:
        render.echo("[dim]Chua co ten mien nao. Them: dnsentinel add <ten>.vn[/]")
        return 0
    rows = [(d.domain, render.status_text(d.status),
             "co" if d.enabled else "tat",
             _fmt_ts(d.last_check), d.descr) for d in doms]
    render.table(f"Ten mien giam sat ({len(doms)})",
                 ["Domain", "Status", "Bat", "Kiem tra cuoi", "Mo ta"], rows)
    return 0


# ---------------- checking ----------------
def _check_one(k: Container, domain: str, qtype=None, detail=False):
    res = k.watch.check_domain(domain, qtype=qtype, persist=True)
    render.echo(f"{domain}: {render.status_text(res.status)}  "
                f"({res.servers_ok}/{res.servers_total} may chu, "
                f"~{res.rtt_ms}ms)")
    if detail:
        rows = [(p.server, p.qtype, "OK" if p.ok else "x", p.rcode or "-",
                 p.answers, p.authority,
                 f"{p.rtt_ms}ms" if p.rtt_ms >= 0 else "-",
                 (p.records[0] if p.records else "") or p.error)
                for p in res.probes]
        render.table("Chi tiet tung may chu VNNIC",
                     ["Server", "Type", "OK", "Rcode", "Ans", "Auth",
                      "RTT", "Ghi chu/Loi"], rows)
    return res


def cmd_check(k: Container, args):
    if args.domain:
        try:
            _check_one(k, args.domain, qtype=args.type, detail=not args.quiet)
        except (DomainInvalid,) as e:
            render.echo(f"[red]Loi:[/] {e}"); return 1
        return 0
    doms = k.domains.list(enabled_only=True)
    if not doms:
        render.echo("[dim]Chua co ten mien nao duoc bat.[/]"); return 0
    for d in doms:
        _check_one(k, d.domain, qtype=args.type, detail=False)
    return 0


def cmd_status(k: Container, args):
    doms = k.domains.list()
    if not doms:
        render.echo("[dim]Chua co ten mien nao.[/]"); return 0
    rows = []
    for d in doms:
        st = k.uptime.for_domain(d.domain, window_sec=args.days * 86400)
        rows.append((d.domain, render.status_text(d.status),
                     f"{st.uptime_pct}%", st.total_checks,
                     f"{st.avg_rtt_ms}ms", _fmt_ts(d.last_check)))
    render.table(f"Trang thai & uptime ({args.days} ngay)",
                 ["Domain", "Status", "Uptime", "So lan", "RTT TB",
                  "Kiem tra cuoi"], rows)
    return 0


def cmd_uptime(k: Container, args):
    st = k.uptime.for_domain(args.domain, window_sec=args.days * 86400)
    render.echo(f"[bold]{args.domain}[/] — {args.days} ngay gan nhat")
    render.table("", ["Chi so", "Gia tri"], [
        ("Uptime", f"{st.uptime_pct}%"),
        ("Tong so lan kiem tra", st.total_checks),
        ("Len (up)", st.up_checks),
        ("Suy giam (degraded)", st.degraded_checks),
        ("Chet (down)", st.down_checks),
        ("RTT trung binh", f"{st.avg_rtt_ms}ms"),
    ])
    return 0


def cmd_servers(k: Container, args):
    rows = [(s.host, s.ipv4, s.ipv6 or "-") for s in k.servers]
    render.table("Cum may chu ten mien quoc gia VNNIC",
                 ["Host", "IPv4", "IPv6"], rows)
    return 0


# ---------------- config ----------------
def cmd_config(k: Container, args):
    if args.action == "list":
        rows = sorted(k.settings.all().items())
        render.table("Cau hinh", ["Key", "Value"], rows)
    elif args.action == "get":
        render.echo(str(k.settings.get(args.key, "")))
    elif args.action == "set":
        k.settings.set(args.key, args.value)
        render.echo(f"[green]Da dat[/] {args.key} = {args.value}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dnsentinel",
        description="Giam sat uptime phan giai DNS ten mien .vn qua VNNIC")
    p.add_argument("-V", "--version", action="version",
                   version=f"dnsentinel {__version__}")
    sub = p.add_subparsers(dest="cmd")

    a = sub.add_parser("add", help="Them ten mien .vn")
    a.add_argument("domain")
    a.add_argument("-d", "--desc", default="", help="Mo ta")
    a.add_argument("--no-check", action="store_true",
                   help="Khong kiem tra ngay sau khi them")
    a.set_defaults(func=cmd_add)

    r = sub.add_parser("rm", help="Xoa ten mien")
    r.add_argument("domain"); r.set_defaults(func=cmd_rm)

    e = sub.add_parser("edit", help="Sua mo ta / bat-tat giam sat")
    e.add_argument("domain")
    e.add_argument("-d", "--desc", default=None)
    e.add_argument("--enable", action="store_true")
    e.add_argument("--disable", action="store_true")
    e.set_defaults(func=cmd_edit)

    sub.add_parser("list", help="Liet ke ten mien").set_defaults(func=cmd_list)

    c = sub.add_parser("check", help="Kiem tra phan giai (1 hoac tat ca)")
    c.add_argument("domain", nargs="?")
    c.add_argument("-t", "--type", default=None,
                   help="Loai ban ghi: NS/SOA/A/AAAA (mac dinh NS)")
    c.add_argument("-q", "--quiet", action="store_true",
                   help="Khong in chi tiet tung may chu")
    c.set_defaults(func=cmd_check)

    s = sub.add_parser("status", help="Bang trang thai + uptime")
    s.add_argument("--days", type=int, default=1)
    s.set_defaults(func=cmd_status)

    u = sub.add_parser("uptime", help="Uptime chi tiet mot ten mien")
    u.add_argument("domain")
    u.add_argument("--days", type=int, default=7)
    u.set_defaults(func=cmd_uptime)

    sub.add_parser("servers", help="Danh sach may chu VNNIC").set_defaults(
        func=cmd_servers)

    cf = sub.add_parser("config", help="Xem/sua cau hinh")
    cf.add_argument("action", choices=["list", "get", "set"])
    cf.add_argument("key", nargs="?")
    cf.add_argument("value", nargs="?")
    cf.set_defaults(func=cmd_config)

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not getattr(args, "func", None):
        build_parser().print_help()
        return 0
    k = Container()
    try:
        return args.func(k, args) or 0
    except KeyboardInterrupt:
        render.echo("\n[dim]Huy.[/]")
        return 130


if __name__ == "__main__":
    sys.exit(main())
