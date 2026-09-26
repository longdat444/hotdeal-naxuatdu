#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════╗
║       HOT DEAL TOOL — Na Xuất Dư                    ║
║  Kéo sản phẩm bán chạy từ Pancake                  ║
║  → Tự động cập nhật section Hot Deal trên Webcake   ║
╚══════════════════════════════════════════════════════╝

Lần đầu chạy: tool sẽ hỏi API keys và tự lưu vào config.json
Lần sau: double-click chạy thẳng, không cần nhập gì nữa!

Yêu cầu: Python 3.7+  |  pip install requests
"""

import requests
import json
import re
import os
import time
from datetime import datetime, date, timezone, timedelta
from collections import defaultdict
# ══════════════════════════════════════════
# API URLS
# ══════════════════════════════════════════
PANCAKE_BASE = "https://pos.pages.fm/api/v1"
WEBCAKE_BASE = "https://api.storecake.io/api/v1/external"
CONFIG_FILE  = "config.json"
HTML_FILE    = "hotdeal_section.html"

# ══════════════════════════════════════════
# QUẢN LÝ CONFIG — Tự lưu / tự đọc
# ══════════════════════════════════════════
# ── CODE MỚI ──
DEFAULT_CONFIG = {
    "pancake_api_key":          "2c8f40cee58248a988d0ec569806984a",
    "pancake_shop_id":          "120163355",
    "webcake_api_key":          "eyJhbGci...",
    "webcake_refresh_token":    "",   # ← thêm dòng này
    "webcake_product_id":       "",
    "so_luong_ban_toi_thieu":   50,
    "so_sp_hien_thi":           4,
    "github_token":             "ghp_...",
    "github_username":          "longdat444",
    "github_repo":              "hotdeal-naxuatdu",
}

def doc_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        cfg = {**DEFAULT_CONFIG, **saved}
        return cfg
    return dict(DEFAULT_CONFIG)

def doc_config_tu_env(cfg):
    """Ghi đè config bằng biến môi trường khi chạy trên GitHub Actions"""
    mapping = {
        "PANCAKE_API_KEY":        "pancake_api_key",
        "PANCAKE_SHOP_ID":        "pancake_shop_id",
        "WEBCAKE_API_KEY":        "webcake_api_key",
        "WEBCAKE_REFRESH_TOKEN":  "webcake_refresh_token",
        "GITHUB_TOKEN_PAT":       "github_token",
        "SO_LUONG_BAN_TOI_THIEU": "so_luong_ban_toi_thieu",
        "SO_SP_HIEN_THI":         "so_sp_hien_thi",
    }
    for env_key, cfg_key in mapping.items():
        val = os.environ.get(env_key, "")
        if val:
            if cfg_key in ("so_luong_ban_toi_thieu", "so_sp_hien_thi"):
                cfg[cfg_key] = int(val)
            else:
                cfg[cfg_key] = val
    return cfg
    for env_key, cfg_key in mapping.items():
        val = os.environ.get(env_key, "")
        if val:
            cfg[cfg_key] = val
    return cfg

def luu_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def nhap_co_mac_dinh(prompt, mac_dinh=""):
    """Hỏi người dùng, nếu Enter thì giữ giá trị cũ"""
    if mac_dinh:
        hien_thi = mac_dinh[:6] + "..." if len(mac_dinh) > 9 else mac_dinh
        gia_tri = input(f"  {prompt} [{hien_thi}]: ").strip()
    else:
        gia_tri = input(f"  {prompt}: ").strip()
    return gia_tri if gia_tri else mac_dinh

def kiem_tra_va_nhap_config(cfg):
    """Kiểm tra config, nếu thiếu thì hỏi và lưu lại"""
    thieu = (
        not cfg["pancake_api_key"] or
        not cfg["pancake_shop_id"] or
        not cfg["webcake_api_key"]
    )

    if not thieu:
        return cfg  # Đủ rồi, chạy thẳng

    print("\n⚙️  THIẾT LẬP LẦN ĐẦU")
    print("   (Chỉ cần nhập 1 lần, lần sau tự động dùng lại)\n")

    cfg["pancake_api_key"]    = nhap_co_mac_dinh("Pancake API Key", cfg["pancake_api_key"])
    cfg["pancake_shop_id"]    = nhap_co_mac_dinh("Pancake Shop ID", cfg["pancake_shop_id"])
    cfg["webcake_api_key"]    = nhap_co_mac_dinh("Webcake API Key", cfg["webcake_api_key"])

    print("\n  (Webcake Product ID có thể để trống, tool sẽ tự tìm)")
    cfg["webcake_product_id"] = nhap_co_mac_dinh("Webcake Product ID", cfg["webcake_product_id"])

    so_luong = nhap_co_mac_dinh(f"Ngưỡng bán chạy (đơn/ngày)", str(cfg["so_luong_ban_toi_thieu"]))
    cfg["so_luong_ban_toi_thieu"] = int(so_luong) if so_luong.isdigit() else cfg["so_luong_ban_toi_thieu"]

    so_sp = nhap_co_mac_dinh(f"Số SP hiển thị tối đa", str(cfg["so_sp_hien_thi"]))
    cfg["so_sp_hien_thi"] = int(so_sp) if so_sp.isdigit() else cfg["so_sp_hien_thi"]

    luu_config(cfg)
    print(f"\n  ✅ Đã lưu config vào {CONFIG_FILE}")
    return cfg

def sua_config(cfg):
    print("\n⚙️  CHỈNH SỬA CẤU HÌNH\n")
    cfg["pancake_api_key"]        = nhap_co_mac_dinh("Pancake API Key",        cfg["pancake_api_key"])
    cfg["pancake_shop_id"]        = nhap_co_mac_dinh("Pancake Shop ID",         cfg["pancake_shop_id"])
    cfg["webcake_api_key"]        = nhap_co_mac_dinh("Webcake Access Token",    cfg["webcake_api_key"])
    cfg["webcake_refresh_token"]  = nhap_co_mac_dinh("Webcake Refresh Token",   cfg.get("webcake_refresh_token", ""))  # ← thêm dòng này
    cfg["webcake_product_id"]     = nhap_co_mac_dinh("Webcake Product ID",      cfg["webcake_product_id"])
    so_luong = nhap_co_mac_dinh("Ngưỡng bán chạy (đơn/ngày)", str(cfg["so_luong_ban_toi_thieu"]))
    cfg["so_luong_ban_toi_thieu"] = int(so_luong) if so_luong.isdigit() else cfg["so_luong_ban_toi_thieu"]
    so_sp = nhap_co_mac_dinh("Số SP hiển thị tối đa", str(cfg["so_sp_hien_thi"]))
    cfg["so_sp_hien_thi"]         = int(so_sp) if so_sp.isdigit() else cfg["so_sp_hien_thi"]
    luu_config(cfg)
    print(f"\n  ✅ Đã lưu config mới vào {CONFIG_FILE}")
    input("\n  Bấm Enter để thoát...")

# ══════════════════════════════════════════
# BƯỚC 1: Lấy sản phẩm bán chạy từ Pancake
# ══════════════════════════════════════════
# ══════════════════════════════════════════
# MAP SKU → SLUG THẬT TRÊN WEBSITE
# Pancake không trả slug, phải tự điền tay
# Lấy slug từ tab "Webcake" trong cấu hình SP trên Pancake
# VD: S120 → https://www.naxuatdu.vn/products/set-5-quan-chip-mix-mau-s120
# ══════════════════════════════════════════
# ── CODE MỚI (thay vào) ───────────────────────────────────
WEBCAKE_DOMAIN = "https://www.naxuatdu.vn"

# ── CODE MỚI (thêm vào, không xóa gì) ──
def refresh_webcake_token(cfg):
    """Dùng refresh token để lấy access token mới, tự lưu config"""
    refresh = cfg.get("webcake_refresh_token", "")
    if not refresh:
        print("  ❌ Chưa có Refresh Token trong config!")
        print("     Chạy: py hotdeal_tool.py --config  để nhập vào")
        return None
    try:
        r = requests.post(
            f"{WEBCAKE_BASE}/oauth/token",
            headers={
                "Content-Type": "application/json",
                "X-Storecake-Refresh-Token": refresh,
            },
            timeout=10,
        )
        new_token = r.json().get("data", {}).get("access_token")
        if not new_token:
            print(f"  ❌ Refresh thất bại: {r.text[:100]}")
            return None
        cfg["webcake_api_key"] = new_token
        luu_config(cfg)
        print("  ✅ Refresh token thành công! Đã lưu token mới.")
        return new_token
    except Exception as e:
        print(f"  ❌ Lỗi khi refresh: {e}")
        return None

def lay_slug_map_tu_webcake(cfg):
    """Tự động build {SKU: URL} từ Webcake API — tự refresh token nếu hết hạn"""
    print("  🔄 Đang tải slug map từ Webcake...")
    headers  = {"X-Storecake-Access-Token": cfg["webcake_api_key"]}

    # Thử trước, nếu 401 → refresh rồi thử lại
    test = requests.get(f"{WEBCAKE_BASE}/product/all", headers=headers,
                        params={"limit": 1, "page": 1}, timeout=10)
    if test.status_code == 401:
        print("  ⚠️  Access token hết hạn → đang refresh...")
        new_token = refresh_webcake_token(cfg)
        if not new_token:
            return {}
        headers = {"X-Storecake-Access-Token": new_token}
    slug_map = {}
    page     = 1

    while True:
        try:
            r = requests.get(
                f"{WEBCAKE_BASE}/product/all",
                headers=headers,
                params={"limit": 50, "page": page},
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"  ⚠️  Lỗi lấy slug map trang {page}: {e}")
            break

        products = data.get("products", [])
        if not products:
            break

        for p in products:
            sku  = p.get("custom_id", "")
            slug = p.get("slug", "")
            if sku and slug:
                slug_map[sku] = f"{WEBCAKE_DOMAIN}/products/{slug}"

        total = data.get("total_product", 0)
        if page * 50 >= total:
            break
        page += 1

    info_map = {}
    for sku, url in slug_map.items():
        info_map[sku] = {"name": "", "price": 0, "image": ""}
    print(f"  ✅ Đã load {len(slug_map)} SP vào slug map")
    return slug_map, info_map

def lay_san_pham_ban_chay(cfg):
    print("\n📊 Đang kéo đơn hàng từ Pancake...")

    slug_map, info_map = lay_slug_map_tu_webcake(cfg)

    VN_TZ    = timezone(timedelta(hours=7))
    today_vn = datetime.now(VN_TZ).date()
    start_ts = int(datetime(today_vn.year, today_vn.month, today_vn.day,
                            0, 0, 0, tzinfo=VN_TZ).timestamp())
    end_ts   = int(datetime(today_vn.year, today_vn.month, today_vn.day,
                            23, 59, 59, tzinfo=VN_TZ).timestamp())

    print(f"  Ngày      : {today_vn.strftime('%d/%m/%Y')}")
    print(f"  Khung giờ : 00:00 → 23:59 (giờ VN)")

    url  = f"{PANCAKE_BASE}/shops/{cfg['pancake_shop_id']}/orders"
    page = 1
    qty_map         = defaultdict(int)
    pancake_img_map = {}
    pancake_name_map = {}

    while True:
        params = {
            "api_key":       cfg["pancake_api_key"],
            "page_size":     100,
            "page_number":   page,
            "startDateTime": start_ts,
            "endDateTime":   end_ts,
            "option_sort":   "inserted_at_desc",
        }
        try:
            r    = requests.get(url, params=params, timeout=40)
            r.raise_for_status()
            resp = r.json()
        except Exception as e:
            print(f"  ⚠️  Lỗi trang {page}: {e} — thử lại...")
            time.sleep(2)
            continue

        data          = resp.get("data", [])
        total_pages   = resp.get("total_pages", 1)
        total_entries = resp.get("total_entries", "?")

        print(f"  Trang {page}/{total_pages} — {(page-1)*100 + len(data)}/{total_entries} đơn", end="\r")

        LOAI_BO = {4, 5, 6, 7}
        for o in data:
            if o.get("status") in LOAI_BO:
                continue
            for item in (o.get("items") or []):
                vi  = item.get("variation_info") or {}
                sku = (vi.get("product_display_id") or "").strip()
                if not sku:
                    continue
                qty = int(item.get("quantity") or 1)
                qty_map[sku] += qty
                if sku not in pancake_img_map:
                    imgs = vi.get("images") or []
                    if imgs and isinstance(imgs[0], str):
                        pancake_img_map[sku] = imgs[0]
                if sku not in pancake_name_map:
                    name = vi.get("name") or ""
                    if name:
                        pancake_name_map[sku] = name

        if page >= total_pages or not data:
            break
        page += 1
        time.sleep(0.3)

    print(f"\n  ✅ Đã xử lý xong — tìm thấy {len(qty_map)} SKU\n")

    so_hien_thi = cfg["so_sp_hien_thi"]
    nguong      = cfg["so_luong_ban_toi_thieu"]
    top_skus    = sorted(qty_map.items(), key=lambda x: x[1], reverse=True)
    if nguong > 0:
        top_skus = [(s, q) for s, q in top_skus if q >= nguong]
    top_skus = top_skus[:so_hien_thi]

    if not top_skus:
        print("  ⚠️  Không có SP nào đủ ngưỡng hôm nay")
        return []

    san_pham = []
    for i, (sku, qty) in enumerate(top_skus, 1):
        info = info_map.get(sku, {})
        link = slug_map.get(sku, f"{WEBCAKE_DOMAIN}/products/{sku.lower()}")
        print(f"  #{i} {sku} — {qty} đã bán | {info.get('name', '') or pancake_name_map.get(sku, sku)}")
        san_pham.append({
            "sku":        sku,
            "name":       info.get("name", "") or pancake_name_map.get(sku, sku),
            "sold_today": qty,
            "price":      info.get("price", 0),
            "image":      info.get("image", "") or pancake_img_map.get(sku, ""),
            "stock":      999,
            "link":       link,
        })

    return san_pham


def lay_so_cho_van_chuyen(cfg, sku):
    if not sku:
        return 0
    try:
        VN_TZ    = timezone(timedelta(hours=7))
        today    = datetime.now(VN_TZ).date()
        start_ts = int(datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=VN_TZ).timestamp())
        end_ts   = int(datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=VN_TZ).timestamp())
        url    = f"{PANCAKE_BASE}/shops/{cfg['pancake_shop_id']}/orders"
        params = {
            "api_key":         cfg["pancake_api_key"],
            "search":          sku,
            "filter_status[]": 8,
            "startDateTime":   start_ts,
            "endDateTime":     end_ts,
            "page_size":       1,
        }
        r    = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        return int(data.get("total_entries", 0))
    except Exception as e:
        print(f"    ⚠️  Không lấy được số đóng hàng cho {sku}: {e}")
        return 0


# ══════════════════════════════════════════
# BƯỚC 2: Format giá
# ══════════════════════════════════════════
def format_gia(price):
    try:
        return f"{int(float(price)):,}đ".replace(",", ".")
    except:
        return str(price)


# ══════════════════════════════════════════
# BƯỚC 3: Cập nhật file HTML
# ══════════════════════════════════════════
def cap_nhat_html(san_pham, expired=False):
    print("\n📝 Đang cập nhật file HTML...")
    now   = datetime.now()
    today = date.today()

    products_list = []
    for i, sp in enumerate(san_pham, 1):
        products_list.append({
            "rank":       i,
            "sku":        sp["sku"],
            "name":       sp["name"],
            "price":      format_gia(sp["price"]),
            "sold_today": sp["sold_today"],
            "stock":      sp["stock"],
            "image":      sp["image"],
            "link":       sp["link"],
        })

    VN_TZ = timezone(timedelta(hours=7))
    hot_deal_data = {
        "updated": datetime.now(VN_TZ).strftime("%Y-%m-%dT%H:%M:%S"),
        "expires": today.strftime("%Y-%m-%d") + "T23:59:59+07:00",
        "products": products_list,
    }

    if not os.path.exists(HTML_FILE):
        print(f"  ❌ Không tìm thấy {HTML_FILE} — đặt cùng thư mục với tool!")
        return None

    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    data_json = json.dumps(hot_deal_data, ensure_ascii=False, indent=2)
    pattern   = r'(var HOT_DEAL_DATA\s*=\s*)\{[\s\S]*?\}(\s*;)'
    new_html, count = re.subn(pattern, r'\g<1>' + data_json + r'\2', html)

    if count == 0:
        print("  ❌ Không tìm thấy HOT_DEAL_DATA trong file HTML")
        return None

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(new_html)

    print(f"  ✅ Đã cập nhật HTML ({len(san_pham)} sản phẩm)")
    return new_html


# ══════════════════════════════════════════
# BƯỚC 4: Tìm Webcake Product ID tự động
# ══════════════════════════════════════════
def tim_webcake_product_id(cfg):
    url     = f"{WEBCAKE_BASE}/product/all"
    headers = {"X-Storecake-Access-Token": cfg["webcake_api_key"]}
    params  = {"term": "Hot Deal", "limit": 5}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        products = r.json().get("products", [])
        if products:
            pid = products[0].get("id", "")
            print(f"  💡 Tìm thấy Product ID: {pid}")
            # Tự lưu lại để lần sau không cần tìm nữa
            cfg["webcake_product_id"] = pid
            luu_config(cfg)
            return pid
    except Exception as e:
        print(f"  ⚠️  Không tìm được ID tự động: {e}")
    return ""


# ══════════════════════════════════════════
# BƯỚC 5: Upload lên Webcake
# ══════════════════════════════════════════
def upload_len_webcake(html_content, cfg):
    print("\n🚀 Đang upload lên Webcake...")

    product_id = cfg.get("webcake_product_id", "")
    if not product_id:
        print("  ⚠️  Chưa có Webcake Product ID, đang tìm tự động...")
        product_id = tim_webcake_product_id(cfg)
        if not product_id:
            print("  ❌ Không tìm thấy. Hãy tạo sản phẩm 'Hot Deal' trên Webcake")
            print("     rồi chạy lại tool với tham số: py hotdeal_tool.py --config")
            return False

    url     = f"{WEBCAKE_BASE}/product/{product_id}"
    headers = {"X-Storecake-Access-Token": cfg["webcake_api_key"], "Content-Type": "application/json"}
    match   = re.search(r'(<style>[\s\S]*?</script>)', html_content)
    payload = {"description": match.group(1) if match else html_content}

    try:
        r = requests.patch(url, headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        print("  ✅ Upload thành công lên Webcake!")
        return True
    except Exception as e:
        print(f"  ❌ Lỗi upload Webcake: {e}")
        return False


# ══════════════════════════════════════════
# BƯỚC CUỐI: Push lên GitHub Pages
# ══════════════════════════════════════════
def push_len_github(cfg):
    """Push hotdeal_section.html lên GitHub Pages qua API"""
    import base64

    token    = cfg.get("github_token", "")
    username = cfg.get("github_username", "")
    repo     = cfg.get("github_repo", "")

    if not (token and username and repo):
        print("\n  ⚠️  Chưa cấu hình GitHub. Chạy: py hotdeal_tool.py --config")
        return False

    print("\n🚀 Đang push lên GitHub Pages...")

    if not os.path.exists(HTML_FILE):
        print(f"  ❌ Không tìm thấy {HTML_FILE}")
        return False

    with open(HTML_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    api_url = f"https://api.github.com/repos/{username}/{repo}/contents/index.html"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Kiểm tra file đã tồn tại chưa (cần SHA để update)
    sha = None
    try:
        r = requests.get(api_url, headers=headers, timeout=15)
        if r.status_code == 200:
            sha = r.json().get("sha")
    except Exception:
        pass

    import base64 as b64
    content_b64 = b64.b64encode(content.encode("utf-8")).decode("utf-8")

    payload = {
        "message": f"Update Hot Deal {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "content": content_b64,
    }
    if sha:
        payload["sha"] = sha

    try:
        r = requests.put(api_url, headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        print(f"  ✅ Push thành công!")
        print(f"  🌐 URL: https://{username}.github.io/{repo}/")
        return True
    except Exception as e:
        print(f"  ❌ Lỗi push GitHub: {e}")
        return False


# ══════════════════════════════════════════
# CHẠY CHÍNH
# ══════════════════════════════════════════
def liet_ke_blocks(cfg):
    """Liệt kê tất cả product/block trên Webcake để lấy ID"""
    print("\n🔍 Đang lấy danh sách blocks từ Webcake...\n")
    url     = f"{WEBCAKE_BASE}/product/all"
    headers = {"X-Storecake-Access-Token": cfg["webcake_api_key"]}

    try:
        r = requests.get(url, headers=headers, params={"limit": 50}, timeout=15)
        r.raise_for_status()
        data     = r.json()
        products = data.get("products", []) or data.get("data", []) or []

        if not products:
            print("  ⚠️  Không tìm thấy block nào. Kiểm tra lại Webcake API Key.")
        else:
            print(f"  {'ID':<30} {'Tên'}")
            print("  " + "-" * 60)
            for p in products:
                pid  = p.get("id", "?")
                name = p.get("name", "?")
                print(f"  {pid:<30} {name}")
            print()
            print("  → Copy ID của block Hot Deal rồi chạy:")
            print("     py hotdeal_tool.py --config")
            print("     Dán vào dòng 'Webcake Product ID'")
    except Exception as e:
        print(f"  ❌ Lỗi: {e}")

    input("\n  Bấm Enter để thoát...")


def main():
    import sys

    print("=" * 54)
    print("  🔥 HOT DEAL TOOL — Na Xuất Dư")
    VN_TZ = timezone(timedelta(hours=7))
    print(f"  ⏰  {datetime.now(VN_TZ).strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 54)

    # Kiểm tra thư viện
    try:
        import requests
    except ImportError:
        print("\n❌ Thiếu thư viện 'requests'")
        print("   Chạy: pip install requests")
        input("\nBấm Enter để thoát...")
        return

    # Đọc config
    cfg = doc_config()

    # Nếu chạy trên GitHub Actions → đọc từ env
    if "--auto" in sys.argv:
        cfg = doc_config_tu_env(cfg)

    # Nếu chạy với --config → vào menu sửa config
    if "--config" in sys.argv:
        sua_config(cfg)
        return

    # Nếu chạy với --list → liệt kê blocks
    if "--list" in sys.argv:
        cfg = kiem_tra_va_nhap_config(cfg)
        liet_ke_blocks(cfg)
        return

    # Kiểm tra / nhập config lần đầu
    cfg = kiem_tra_va_nhap_config(cfg)

    print(f"\n  Ngưỡng bán chạy : {cfg['so_luong_ban_toi_thieu']} đơn/ngày")
    print(f"  Số SP hiển thị  : {cfg['so_sp_hien_thi']} sản phẩm")
    print(f"  (Đổi cấu hình   : py hotdeal_tool.py --config)")

    # Kéo data
    san_pham = lay_san_pham_ban_chay(cfg)

    if not san_pham:
        cap_nhat_html([], expired=True)
        push_len_github(cfg)
        print("\n  Website sẽ hiển thị 'Hot Deal mới lúc 8h sáng mai'")
    else:
        cap_nhat_html(san_pham)
        push_len_github(cfg)

    print("\n" + "=" * 54)
    print("  ✅ Xong!")
    print("=" * 54)
    if "--auto" not in sys.argv:
        input("  Bấm Enter để đóng...")


if __name__ == "__main__":
    main()
