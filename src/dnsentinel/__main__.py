# -*- coding: utf-8 -*-
"""
python -m dnsentinel / dnsentinel-watch — chay vong lap giam sat dinh ky.
Nhe: don luong, timeout moi truy van, ngu giua cac vong theo watch.interval.
Dung voi systemd (xem systemd/dnsentinel.service).
"""
import signal
import sys
import time

from .container import Container

_RUN = True


def _stop(*_):
    global _RUN
    _RUN = False


def main():
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    k = Container()
    keep_days = k.settings.get_int("retention.days", 90)
    print(f"[dnsentinel] bat dau giam sat, interval={k.interval}s", flush=True)

    last_prune = 0
    while _RUN:
        started = time.time()
        try:
            results = k.watch.check_all()
            up = sum(1 for r in results if r.status == "up")
            print(f"[dnsentinel] kiem tra {len(results)} ten mien "
                  f"({up} up) luc {int(started)}", flush=True)
        except Exception as e:  # khong de 1 loi lam chet daemon
            print(f"[dnsentinel] loi vong kiem tra: {e}", flush=True)

        if started - last_prune > 86400:   # don lich su 1 lan/ngay
            try:
                k.uptime.prune(keep_days)
            except Exception:
                pass
            last_prune = started

        # ngu phan con lai cua interval, van phan ung SIGTERM nhanh
        interval = k.interval
        while _RUN and (time.time() - started) < interval:
            time.sleep(min(1.0, interval))

    print("[dnsentinel] dung.", flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
