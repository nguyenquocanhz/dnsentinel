# DNSentinel

**Giám sát uptime phân giải DNS cho tên miền `.vn`** thông qua cụm **máy chủ tên
miền quốc gia Việt Nam (VNNIC)** — `a.dns-servers.vn` … `h.dns-servers.vn`.

Với mỗi tên miền `.vn` trong danh sách, DNSentinel truy vấn phân giải
(`NS`/`SOA`/`A`/`AAAA`) **trực tiếp tới từng máy chủ quốc gia**, ghi nhận máy
chủ nào trả lời, thời gian phản hồi (RTT) và tổng hợp trạng thái
`up` / `degraded` / `down`, rồi tính **uptime %** theo lịch sử.

> Viết **Python thuần, SOLID/OOP**. **Core không phụ thuộc gì** ngoài thư viện
> chuẩn (giao thức DNS được hiện thực thuần bằng `socket`). **Một SQLite** là
> nguồn dữ liệu duy nhất (quyền `600`). `rich` chỉ là tùy chọn để CLI đẹp hơn —
> thiếu vẫn chạy (tự fallback ra text thuần). Nhẹ, hợp box yếu.

---

## 1. Vì sao truy vấn thẳng máy chủ VNNIC?

Cụm `*.dns-servers.vn` là các máy chủ **uỷ quyền cho vùng `.vn`**. Hỏi `NS`/`SOA`
của một tên miền `.vn` tới các máy chủ này cho biết **đường phân giải `.vn` có
khỏe không** ở tầng quốc gia — độc lập với cache của resolver công cộng
(8.8.8.8, 1.1.1.1…). Nếu một/nhiều máy chủ VNNIC không trả lời, ta phát hiện
sớm sự cố phân giải ở cấp hạ tầng.

Danh sách máy chủ (xác minh tại
<https://vnnic.vn/en/dns/dns-system/vietnam-national-domain-name-server-system>):

```
dnsentinel servers
```

## 2. Kiến trúc (SOLID/OOP phân tầng)

```
src/dnsentinel/
  core/        models (dataclass) · interfaces (ABC) · exceptions   # không I/O
  data/        database (kết nối + schema) · repositories (theo bảng)
  resolve/     servers (dữ liệu VNNIC) · message (DNS wire thuần)
               resolver (socket) · checks (mỗi loại bản ghi = 1 lớp, Open/Closed)
  services/    watch_service (kiểm tra + tổng hợp) · uptime_service (uptime %)
  cli/         tui (argparse) · render (rich-hoặc-text)
  container.py composition root (ráp nối tầng)
  __main__.py  daemon vòng lặp định kỳ
```

- **SRP**: `Database` chỉ lo kết nối/schema; mỗi repository một nhóm bảng.
- **DIP**: service phụ thuộc `DnsResolver` (ABC), không phụ thuộc `socket` cụ thể.
- **OCP**: thêm loại bản ghi mới = thêm một lớp trong `resolve/checks.py`, không
  sửa `WatchService`.

**Bảng SQLite**: `domains` (danh sách tên miền + `status` + `lastCheck` +
`createDate`/`updateDate`), `checks` (lịch sử mỗi lần kiểm tra — phục vụ uptime
%), `probes` (chi tiết từng máy chủ mỗi lần — chẩn đoán), `settings` (cấu hình).

## 3. Cài đặt

### Cách A — chạy trực tiếp từ mã nguồn (không cài gì)

```bash
cd /opt/dnsentinel
python3 -m dnsentinel.cli.tui servers        # thử ngay, không cần rich
# hoặc đặt biến môi trường để chọn nơi lưu DB:
DNSENTINEL_DB=/opt/dnsentinel/dnsentinel.db python3 -m dnsentinel.cli.tui list
```

> Chạy module cần `src/` trong `PYTHONPATH`. Tiện nhất là cài ở chế độ editable
> (cách B) hoặc dùng gói `.deb` (cách C).

### Cách B — cài bằng venv (có lệnh `dnsentinel`)

```bash
cd /opt/dnsentinel
python3 -m venv venv
./venv/bin/pip install -e ".[cli]"     # kèm rich
./venv/bin/dnsentinel servers
```

### Cách C — gói `.deb` + APT repo tự host

```bash
cd /opt/dnsentinel
bash packaging/build-deb.sh            # tạo ../dnsentinel_1.0.0_all.deb
sudo apt install ../dnsentinel_1.0.0_all.deb
# tự tạo venv, lệnh dnsentinel/dnsentinel-watch, bật systemd service
```

Tự host APT repo (ví dụ sau Nginx):

```bash
bash packaging/make-apt-repo.sh /var/www/dnsentinel
# client:
echo 'deb [trusted=yes] http://<host>/dnsentinel ./' | sudo tee /etc/apt/sources.list.d/dnsentinel.list
sudo apt update && sudo apt install dnsentinel
```

## 4. Sử dụng (CLI)

```bash
dnsentinel add chinhphu.vn -d "Cổng TTĐT Chính phủ"   # thêm + kiểm tra ngay
dnsentinel add vnnic.vn
dnsentinel list                      # liệt kê tên miền + trạng thái
dnsentinel check vnnic.vn            # kiểm tra 1 tên miền (in chi tiết từng máy chủ)
dnsentinel check                     # kiểm tra tất cả tên miền đang bật
dnsentinel check vnnic.vn -t SOA     # chọn loại bản ghi (NS/SOA/A/AAAA)
dnsentinel status --days 7           # bảng trạng thái + uptime 7 ngày
dnsentinel uptime vnnic.vn --days 30 # uptime chi tiết
dnsentinel edit vnnic.vn --disable   # tạm dừng giám sát 1 tên miền
dnsentinel rm vnnic.vn               # xóa
dnsentinel servers                   # danh sách máy chủ VNNIC
dnsentinel config list               # xem cấu hình
dnsentinel config set watch.interval 600
```

## 5. Chạy giám sát định kỳ (daemon)

Khi cài bằng `.deb`, service `dnsentinel` tự bật. Thủ công:

```bash
dnsentinel-watch                     # vòng lặp foreground
# hoặc qua systemd (sau khi cài .deb):
sudo systemctl status dnsentinel
journalctl -u dnsentinel -f
```

Vòng lặp đọc `watch.interval` (giây) từ SQLite, kiểm tra mọi tên miền đang bật,
cập nhật `status` + `lastCheck`, lưu lịch sử vào `checks` để tính uptime, và dọn
lịch sử cũ hơn `retention.days` mỗi ngày một lần.

## 6. Cấu hình (`dnsentinel config`)

| Key | Mặc định | Ý nghĩa |
|---|---|---|
| `watch.interval` | `300` | Giây giữa 2 vòng kiểm tra |
| `watch.qtype` | `NS` | Loại bản ghi kiểm tra mặc định |
| `watch.timeout` | `3.0` | Timeout mỗi truy vấn (giây) |
| `watch.retries` | `1` | Số lần thử lại mỗi máy chủ |
| `watch.prefer_ipv6` | `0` | Ưu tiên truy vấn qua IPv6 |
| `watch.degraded_ratio` | `0.5` | Tỉ lệ máy chủ OK tối thiểu để coi là `degraded` (thay vì `down`) |
| `retention.days` | `90` | Giữ lịch sử kiểm tra bao nhiêu ngày |

## 7. Trạng thái tổng hợp

- **up** — tất cả máy chủ VNNIC trả lời tốt (NOERROR + có bản ghi/ủy quyền).
- **degraded** — một số trả lời, một số không (≥ `watch.degraded_ratio`).
- **down** — không máy chủ nào trả lời / dưới ngưỡng.
- **unknown** — chưa kiểm tra lần nào.

**Uptime %** = `(số lần up + 0.5 × số lần degraded) / tổng số lần × 100`.

## 8. Ghi chú tài nguyên (box yếu)

- Core không phụ thuộc nặng; truy vấn tuần tự, mỗi truy vấn có timeout.
- systemd giới hạn `MemoryMax=120M`, `CPUQuota=40%`, siết quyền ghi.
- SQLite ở chế độ WAL, một file, quyền `600`.

## 9. Giấy phép

MIT — xem [LICENSE](LICENSE).
