#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════╗
║         NA XUẤT DƯ — SECTION TOOL v2.0                  ║
║  Tự động cập nhật 3 section:                            ║
║    🔥 Hot Deal  — sản phẩm bán >= X đơn hôm nay        ║
║    🏷️  Xả Kho   — sản phẩm có chữ SALE trong tên       ║
║    ✨ Hàng Mới  — sản phẩm tạo hôm nay                  ║
║  → Git push tự động lên GitHub Pages                    ║
╚══════════════════════════════════════════════════════════╝

Lần đầu: tool hỏi config → lưu vào config.json
Lần sau: double-click là xong!

Yêu cầu: Python 3.7+  |  pip install requests
         Git đã cài và đã clone repo về máy
"""

import requests
import json
import re
import os
import sys
import time
import subprocess
from datetime import datetime, date, timezone, timedelta
from collections import defaultdict

# ══════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════
PANCAKE_BASE  = "https://pos.pages.fm/api/v1"
WEBCAKE_BASE  = "https://api.storecake.io/api/v1/external"
WEBCAKE_DOMAIN = "https://www.naxuatdu.vn"
CONFIG_FILE   = "config.json"

HTML_FILES = {
    "hotdeal": "hotdeal_section.html",
    "sale":    "sale_section.html",
    "new":     "new_section.html",
}

DEFAULT_CONFIG = {
    "pancake_api_key":        "",
    "pancake_shop_id":        "",
    "webcake_api_key":        "",
    "webcake_refresh_token":  "",
    "so_luong_ban_toi_thieu": 50,
    "so_sp_hien_thi":         4,
    "so_sp_hang_moi":         8,
    "github_token":           "",
    "github_username":        "longdat444",
    "github_repo":            "hotdeal-naxuatdu",
}

# ══════════════════════════════════════════
# QUẢN LÝ CONFIG
# ══════════════════════════════════════════
def doc_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        return {**DEFAULT_CONFIG, **saved}
    return dict(DEFAULT_CONFIG)

def luu_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def nhap(prompt, mac_dinh=""):
    if mac_dinh:
        hien_thi = mac_dinh[:8] + "..." if len(mac_dinh) > 11 else mac_dinh
        val = input(f"  {prompt} [{hien_thi}]: ").strip()
    else:
        val = input(f"  {prompt}: ").strip()
    return val if val else mac_dinh

def kiem_tra_config(cfg):
    # Ưu tiên đọc từ environment variables (GitHub Actions Secrets)
    env_map = {
        "pancake_api_key":        "PANCAKE_API_KEY",
        "pancake_shop_id":        "PANCAKE_SHOP_ID",
        "webcake_api_key":        "WEBCAKE_API_KEY",
        "webcake_refresh_token":  "WEBCAKE_REFRESH_TOKEN",
        "github_token":           "GH_TOKEN_PAT",
        "so_luong_ban_toi_thieu": "SO_LUONG_BAN_TOI_THIEU",
        "so_sp_hang_moi":         "SO_SP_HANG_MOI",
    }
    for cfg_key, env_key in env_map.items():
        val = os.environ.get(env_key, "")
        if val:
            if cfg_key in ("so_luong_ban_toi_thieu", "so_sp_hang_moi"):
                cfg[cfg_key] = int(val) if val.isdigit() else cfg[cfg_key]
            else:
                cfg[cfg_key] = val

    thieu = not cfg["pancake_api_key"] or not cfg["pancake_shop_id"]
    if not thieu:
        return cfg

    # Chỉ hỏi khi chạy local (có terminal)
    if not sys.stdin.isatty():
        print("❌ Thiếu config và không có terminal — dừng lại")
        sys.exit(1)

    print("\n⚙️  THIẾT LẬP LẦN ĐẦU\n")
    cfg["pancake_api_key"]        = nhap("Pancake API Key", cfg["pancake_api_key"])
    cfg["pancake_shop_id"]        = nhap("Pancake Shop ID", cfg["pancake_shop_id"])

    so = nhap("Ngưỡng Hot Deal (đơn/ngày)", str(cfg["so_luong_ban_toi_thieu"]))
    cfg["so_luong_ban_toi_thieu"] = int(so) if so.isdigit() else 50

    so_sp = nhap("Số SP hiển thị mỗi section", str(cfg["so_sp_hien_thi"]))
    cfg["so_sp_hien_thi"]         = int(so_sp) if so_sp.isdigit() else 8

    cfg["github_token"]    = nhap("GitHub Token (PAT)", cfg.get("github_token", ""))
    cfg["github_username"] = nhap("GitHub Username",    cfg.get("github_username", "longdat444"))
    cfg["github_repo"]     = nhap("GitHub Repo",        cfg.get("github_repo", "hotdeal-naxuatdu"))

    luu_config(cfg)
    print(f"\n  ✅ Đã lưu config!")
    return cfg

def sua_config(cfg):
    print("\n⚙️  CHỈNH SỬA CẤU HÌNH\n")
    cfg["pancake_api_key"]       = nhap("Pancake API Key",           cfg["pancake_api_key"])
    cfg["pancake_shop_id"]       = nhap("Pancake Shop ID",           cfg["pancake_shop_id"])
    cfg["webcake_api_key"]       = nhap("Webcake Access Token",      cfg.get("webcake_api_key", ""))
    cfg["webcake_refresh_token"] = nhap("Webcake Refresh Token",     cfg.get("webcake_refresh_token", ""))
    cfg["github_token"]          = nhap("GitHub Token (PAT)",        cfg.get("github_token", ""))
    cfg["github_username"]       = nhap("GitHub Username",           cfg.get("github_username", "longdat444"))
    cfg["github_repo"]           = nhap("GitHub Repo",               cfg.get("github_repo", "hotdeal-naxuatdu"))
    so = nhap("Ngưỡng Hot Deal (đơn/ngày)", str(cfg["so_luong_ban_toi_thieu"]))
    cfg["so_luong_ban_toi_thieu"] = int(so) if so.isdigit() else cfg["so_luong_ban_toi_thieu"]
    so_sp = nhap("Số SP hiển thị mỗi section", str(cfg["so_sp_hien_thi"]))
    cfg["so_sp_hien_thi"]        = int(so_sp) if so_sp.isdigit() else cfg["so_sp_hien_thi"]
    luu_config(cfg)
    print(f"\n  ✅ Đã lưu config mới!")
    input("\n  Bấm Enter để thoát...")


# ══════════════════════════════════════════
# HELPER
# ══════════════════════════════════════════
def format_gia(price):
    try:
        return f"{int(float(price)):,}đ".replace(",", ".")
    except:
        return str(price)

# ══════════════════════════════════════════
# WEBCAKE — Lấy slug/ảnh/giá + refresh token
# ══════════════════════════════════════════
def refresh_webcake_token(cfg):
    refresh = cfg.get("webcake_refresh_token", "")
    if not refresh:
        print("  ❌ Chưa có Webcake Refresh Token. Chạy --config để nhập.")
        return None
    try:
        r = requests.post(
            f"{WEBCAKE_BASE}/oauth/token",
            headers={"Content-Type": "application/json",
                     "X-Storecake-Refresh-Token": refresh},
            timeout=10,
        )
        new_token = r.json().get("data", {}).get("access_token")
        if not new_token:
            print(f"  ❌ Refresh thất bại: {r.text[:100]}")
            return None
        cfg["webcake_api_key"] = new_token
        luu_config(cfg)
        print("  ✅ Refresh token thành công!")
        return new_token
    except Exception as e:
        print(f"  ❌ Lỗi refresh: {e}")
        return None

def lay_webcake_products(cfg):
    """Trả về (slug_map, info_map) từ Webcake"""
    print("  🔄 Đang tải sản phẩm từ Webcake...")
    headers = {"X-Storecake-Access-Token": cfg.get("webcake_api_key", "")}

    # Kiểm tra token
    test = requests.get(f"{WEBCAKE_BASE}/product/all", headers=headers,
                        params={"limit": 1, "page": 1}, timeout=10)
    if test.status_code == 401:
        print("  ⚠️  Token hết hạn → đang refresh...")
        new_token = refresh_webcake_token(cfg)
        if not new_token:
            return {}, {}
        headers = {"X-Storecake-Access-Token": new_token}

    slug_map = {}  # SKU → URL đầy đủ
    info_map = {}  # SKU → {name, price, image, slug, is_published, created_at}
    page = 1

    while True:
        try:
            r = requests.get(f"{WEBCAKE_BASE}/product/all", headers=headers,
                             params={"limit": 50, "page": page}, timeout=15)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"  ⚠️  Lỗi trang {page}: {e}")
            break

        products = data.get("products", [])
        if not products:
            break

        for p in products:
            sku  = (p.get("custom_id") or "").strip()
            slug = p.get("slug") or ""
            if not sku:
                continue

            # Ảnh: ưu tiên variation, fallback product
            image = ""
            for v in (p.get("variations") or []):
                imgs = v.get("images") or []
                if imgs:
                    image = imgs[0]
                    break
            if not image and p.get("image"):
                image = p["image"]

            # Giá: lấy variation đầu có retail_price > 0
            price = 0
            for v in (p.get("variations") or []):
                rp = v.get("retail_price") or 0
                if rp > 0:
                    price = rp
                    break

            if slug:
                slug_map[sku] = f"{WEBCAKE_DOMAIN}/products/{slug}"

            info_map[sku] = {
                "name":         p.get("name") or sku,
                "slug":         slug,
                "price":        price,
                "image":        image,
                "is_published": bool(p.get("is_published", False)),
                "created_at":   p.get("inserted_at") or p.get("inserted_at_pos") or "",
            }

        total = data.get("total_product", 0)
        if page * 50 >= total:
            break
        page += 1

    print(f"  ✅ Đã load {len(slug_map)} SP từ Webcake")
    # DEBUG — xoá sau khi kiểm tra xong
    if "--debug" in __import__("sys").argv:
        print("\n  [DEBUG] Tất cả fields của SP đầu tiên trong info_map:")
        for sku, info in info_map.items():
            import pprint
            pprint.pprint(info, indent=4)
            break  # Chỉ in 1 SP thôi
        
        # Đếm bao nhiêu SP có created_at
        co_ngay = sum(1 for info in info_map.values() if info.get("created_at"))
        print(f"\n  [DEBUG] SP có created_at: {co_ngay}/{len(info_map)}")
        
        # In thử raw response của 1 SP từ Webcake để xem đủ field
        print("\n  [DEBUG] Raw fields từ Webcake (SP đầu tiên):")
        headers2 = {"X-Storecake-Access-Token": cfg.get("webcake_api_key", "")}
        r2 = requests.get(f"{WEBCAKE_BASE}/product/all", headers=headers2,
                         params={"limit": 1, "page": 1}, timeout=15)
        raw_products = r2.json().get("products", [])
        if raw_products:
            pprint.pprint(list(raw_products[0].keys()), indent=4)
            print("\n  [DEBUG] Giá trị các field ngày:")
            for field in ["created_at", "created", "published_at", "updated_at", "inserted_at"]:
                print(f"    {field}: {raw_products[0].get(field, '(không có)')}")
    return slug_map, info_map


# ══════════════════════════════════════════
# PANCAKE — Kéo đơn hàng hôm nay → đếm QTY
# ══════════════════════════════════════════
LOAI_BO_STATUS = {4, 5, 6, 7}  # hoàn / huỷ / xoá

def dem_qty_hom_nay(cfg):
    """Kéo toàn bộ đơn hôm nay, đếm QTY từng SKU. Trả về qty_map."""
    VN_TZ    = timezone(timedelta(hours=7))
    today_vn = datetime.now(VN_TZ).date()
    start_ts = int(datetime(today_vn.year, today_vn.month, today_vn.day,
                            0, 0, 0, tzinfo=VN_TZ).timestamp())
    end_ts   = int(datetime(today_vn.year, today_vn.month, today_vn.day,
                            23, 59, 59, tzinfo=VN_TZ).timestamp())

    print(f"  Ngày: {today_vn.strftime('%d/%m/%Y')} | Loại bỏ status: {sorted(LOAI_BO_STATUS)}")

    url      = f"{PANCAKE_BASE}/shops/{cfg['pancake_shop_id']}/orders"
    page     = 1
    qty_map  = defaultdict(int)

    while True:
        params = {
            "api_key":       cfg["pancake_api_key"],
            "page_size":     100,
            "page_number":   page,
            "startDateTime": start_ts,
            "endDateTime":   end_ts,
            "option_sort":   "inserted_at_desc",
        }
        retry = 0
        resp  = None
        while retry < 3:
            try:
                r    = requests.get(url, params=params, timeout=40)
                r.raise_for_status()
                resp = r.json()
                break
            except Exception as e:
                retry += 1
                print(f"  ⚠️  Lỗi trang {page} (lần {retry}/3): {e} — thử lại...")
                time.sleep(2 * retry)
        if resp is None:
            print(f"  ❌ Bỏ qua trang {page} sau 3 lần thử")
            break

        data        = resp.get("data", [])
        total_pages = resp.get("total_pages", 1)
        total_entries = resp.get("total_entries", "?")
        print(f"  Trang {page}/{total_pages} — {(page-1)*100+len(data)}/{total_entries} đơn", end="\r")

        for o in data:
            if o.get("status") in LOAI_BO_STATUS:
                continue
            for item in (o.get("items") or []):
                vi  = item.get("variation_info") or {}
                sku = (vi.get("product_display_id") or "").strip()
                if not sku:
                    continue
                qty_map[sku] += int(item.get("quantity") or 1)

        if page >= total_pages or not data:
            break
        page += 1
        time.sleep(0.3)

    print(f"\n  ✅ Xong — {len(qty_map)} SKU khác nhau hôm nay")
    return qty_map

# ══════════════════════════════════════════
# PANCAKE — Kéo hàng mới tạo hôm nay
# ══════════════════════════════════════════
def lay_hang_moi_tu_pancake(cfg, slug_map):
    """Kéo SP tạo hôm nay từ Pancake. Nếu chưa đủ slot → bổ sung SP mới nhất từ trước hôm nay."""
    VN_TZ    = timezone(timedelta(hours=7))
    today_vn = datetime.now(VN_TZ).date()
    start_ts = int(datetime(today_vn.year, today_vn.month, today_vn.day,
                            0, 0, 0, tzinfo=VN_TZ).timestamp())
    end_ts   = int(datetime(today_vn.year, today_vn.month, today_vn.day,
                            23, 59, 59, tzinfo=VN_TZ).timestamp())

    url     = f"{PANCAKE_BASE}/shops/{cfg['pancake_shop_id']}/products/variations"
    so_hien = cfg["so_sp_hien_thi"]

    def keo_variations(extra_params, max_pages=None, label="", page_size=50):
        """Kéo variations theo params, trả về list variation raw."""
        page = 1
        result = []
        while True:
            params = {
                "api_key":     cfg["pancake_api_key"],
                "page_size":   page_size,
                "page_number": page,
                **extra_params,
            }
            try:
                r    = requests.get(url, params=params, timeout=30)
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                print(f"  ⚠️  Lỗi trang {page}: {e}")
                break
            variations  = data.get("data", [])
            total_pages = data.get("total_pages", 1)
            result.extend(variations)
            if label:
                print(f"  {label} trang {page}/{total_pages} ({len(result)} variations)", end="\r")
            if page >= total_pages or not variations:
                break
            if max_pages and page >= max_pages:
                break
            page += 1
            time.sleep(0.3)
        if label:
            print()  # xuống dòng sau \r
        return result

    def parse_variation(v):
        """Parse 1 variation thành SP dict. Trả về None nếu không hợp lệ."""
        product    = v.get("product", {}) or {}
        sku        = product.get("display_id", "").strip()
        name       = product.get("name", "").strip()
        price      = v.get("retail_price", 0) or 0
        images     = v.get("images", []) or []
        image      = images[0] if images else ""
        product_id = v.get("product_id", "")
        link       = slug_map.get(sku, f"{WEBCAKE_DOMAIN}/products/{sku.lower()}" if sku else "")
        if not sku or not name or not image or price <= 0 or not product_id:
            return None
        if "SALE" in name.upper():
            return None
        return {
            "product_id": product_id,
            "sku":        sku,
            "name":       name,
            "sold_today": 0,
            "price":      price,
            "image":      image,
            "stock":      999,
            "link":       link,
        }

    # ── Bước 1: SP mới hôm nay ──
    print("  🔄 Bước 1: Kéo SP mới hôm nay...")
    seen_ids = {}  # product_id → SP dict
    for v in keo_variations({"startDate": start_ts, "endDate": end_ts}, label="  [Hôm nay]"):
        sp = parse_variation(v)
        if sp and sp["product_id"] not in seen_ids:
            seen_ids[sp["product_id"]] = sp

    today_count = len(seen_ids)

    # ── Bước 2: Bổ sung từ trước hôm nay nếu chưa đủ slot ──
    bo_sung_count = 0
    if today_count < so_hien:
        can_them = so_hien - today_count
        # Lấy SP trước hôm nay (không truyền startDate/endDate)
        # API trả về theo inserted_at giảm dần nên lấy trang đầu là đủ
        print(f"  🔄 Bước 2: Cần bổ sung {can_them} SP — kéo SP gần nhất từ trước hôm nay...")
        raw_all = keo_variations({}, max_pages=max(5, so_hien), label="  [Bổ sung]", page_size=100)
        # Sort theo product_id mới nhất (dùng inserted_at từ product nếu có, fallback product_id)
        candidates = []
        for v in raw_all:
            sp = parse_variation(v)
            if not sp:
                continue
            if sp["product_id"] in seen_ids:
                continue  # đã có từ hôm nay
            # Lấy inserted_at để sort
            product    = v.get("product", {}) or {}
            inserted   = product.get("inserted_at") or v.get("inserted_at") or ""
            candidates.append((inserted, sp))

        # Sort giảm dần theo ngày tạo (mới nhất lên trước), bỏ duplicate product_id
        candidates.sort(key=lambda x: x[0], reverse=True)
        seen_bo_sung = set()
        for inserted, sp in candidates:
            if bo_sung_count >= can_them:
                break
            if sp["product_id"] in seen_bo_sung:
                continue
            seen_ids[sp["product_id"]] = sp
            seen_bo_sung.add(sp["product_id"])
            bo_sung_count += 1

    result = list(seen_ids.values())
    print(f"  ✅ Hàng Mới: {len(result[:so_hien])} SP "
          f"(hôm nay: {today_count}, bổ sung từ trước: {bo_sung_count})")
    return result[:so_hien]
# ══════════════════════════════════════════
# LỌC TỪNG SECTION
# ══════════════════════════════════════════

def loc_hot_deal(qty_map, slug_map, info_map, cfg):
    """Top SP bán >= ngưỡng hôm nay, lấy info từ Webcake"""
    nguong  = cfg["so_luong_ban_toi_thieu"]
    so_hien = cfg["so_sp_hien_thi"]
    top     = sorted(qty_map.items(), key=lambda x: x[1], reverse=True)
    if nguong > 0:
        top = [(s, q) for s, q in top if q >= nguong]

    result   = []
    bi_loai  = []
    rank     = 1

    for sku, qty in top:
        if len(result) >= so_hien:
            break
        info  = info_map.get(sku, {})
        link  = slug_map.get(sku, f"{WEBCAKE_DOMAIN}/products/{sku.lower()}")
        issues = []
        if not info.get("is_published", True):
            issues.append("chưa published")
        if not info.get("image"):
            issues.append("không có ảnh")
        if not info.get("slug"):
            issues.append("không có slug")
        if issues:
            bi_loai.append((sku, qty, issues))
            continue
        result.append({
            "sku": sku, "name": info.get("name", sku),
            "sold_today": qty, "price": info.get("price", 0),
            "image": info.get("image", ""), "stock": 999, "link": link,
        })
        print(f"  #{rank} {sku} — {qty} đã bán")
        rank += 1

    if bi_loai:
        print(f"  ⚠️  Bỏ qua {len(bi_loai)} SP: " +
              ", ".join(f"{s}({','.join(i)})" for s,_,i in bi_loai))
    print(f"  ✅ Hot Deal: {len(result)} SP")
    return result


def loc_sale(slug_map, info_map, cfg):
    """SP có chữ SALE trong tên, đang published, có ảnh.
    Lấy TẤT CẢ SP SALE (không giới hạn so_sp_hien_thi) để carousel
    HTML có đủ dữ liệu hiển thị nhiều trang."""
    result  = []

    for sku, info in info_map.items():
        name = info.get("name", "")
        if "SALE" not in name.upper():
            continue
        if not info.get("is_published", True):
            continue
        if not info.get("image"):
            continue
        link = slug_map.get(sku, f"{WEBCAKE_DOMAIN}/products/{sku.lower()}")
        result.append({
            "sku": sku, "name": name,
            "sold_today": 0, "price": info.get("price", 0),
            "image": info.get("image", ""), "stock": 999, "link": link,
        })

    print(f"  ✅ Xả Kho/SALE: {len(result)} SP")
    return result


def loc_hang_moi(slug_map, info_map, cfg):
    """SP có created_at = hôm nay, published, có ảnh"""
    so_hien  = cfg["so_sp_hien_thi"]
    VN_TZ    = timezone(timedelta(hours=7))
    today_str = datetime.now(VN_TZ).strftime("%Y-%m-%d")
    result   = []

    for sku, info in info_map.items():
        created = info.get("created_at", "")
        if not created:
            continue
        # inserted_at trả về UTC (có chữ Z), convert sang giờ VN (+7) trước khi so sánh
        try:
            created_utc = datetime.fromisoformat(created.replace("Z", "+00:00"))
            created_vn  = created_utc.astimezone(VN_TZ)
            if created_vn.strftime("%Y-%m-%d") != today_str:
                continue
        except Exception:
            continue

        if not info.get("image"):
            continue
        link = slug_map.get(sku, f"{WEBCAKE_DOMAIN}/products/{sku.lower()}")
        result.append({
            "sku": sku, "name": info.get("name", sku),
            "sold_today": 0, "price": info.get("price", 0),
            "image": info.get("image", ""), "stock": 999, "link": link,
        })

    print(f"  ✅ Hàng Mới hôm nay: {len(result[:so_hien])} SP")
    return result[:so_hien]


# ══════════════════════════════════════════
# CẬP NHẬT HTML
# ══════════════════════════════════════════

def cap_nhat_html_file(file_name, section_key, san_pham, expired=False):
    """Ghi data mới vào file HTML tương ứng"""
    VN_TZ = timezone(timedelta(hours=7))
    now   = datetime.now(VN_TZ)
    today = now.date()

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

    data_obj = {
        "updated":  now.strftime("%Y-%m-%dT%H:%M:%S"),
        "expires":  today.strftime("%Y-%m-%d") + "T23:59:59",
        "products": products_list,
    }

    if not os.path.exists(file_name):
        print(f"  ⚠️  Không tìm thấy {file_name} — bỏ qua")
        return False

    with open(file_name, "r", encoding="utf-8") as f:
        html = f.read()

    # Thay thế data variable (hỗ trợ HOT_DEAL_DATA, SALE_DATA, NEW_DATA)
    var_map = {"hotdeal": "HOT_DEAL_DATA", "sale": "SALE_DATA", "new": "NEW_DATA"}
    var_name = var_map.get(section_key, "SECTION_DATA")

    data_json = json.dumps(data_obj, ensure_ascii=False, indent=2)
    pattern   = rf'(var {var_name}\s*=\s*)\{{[\s\S]*?\}}(\s*;)'
    # Dùng lambda để tránh lỗi khi data_json chứa backslash (ví dụ tên SP có \")
    new_html, count = re.subn(pattern, lambda m: m.group(1) + data_json + m.group(2), html)

    if count == 0:
        print(f"  ❌ Không tìm thấy {var_name} trong {file_name}")
        return False

    with open(file_name, "w", encoding="utf-8") as f:
        f.write(new_html)

    print(f"  ✅ Đã cập nhật {file_name} ({len(san_pham)} SP)")
    return True


# ══════════════════════════════════════════
# GIT PUSH
# ══════════════════════════════════════════

def git_push(cfg):
    import base64
    token    = cfg.get("github_token", "").strip()
    username = cfg.get("github_username", "").strip()
    repo     = cfg.get("github_repo", "").strip()

    if not token or not username or not repo:
        print("\n⚠️  Chưa có GitHub Token/Username/Repo — bỏ qua push")
        print("   Chạy: py hotdeal_tool.py --config để nhập")
        return False

    print("\n📤 Đang push lên GitHub Pages...")
    api_base = f"https://api.github.com/repos/{username}/{repo}/contents"
    headers  = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    now_str  = datetime.now().strftime("%d/%m/%Y %H:%M")
    ok_count = 0

    for section_key, file_name in HTML_FILES.items():
        if not os.path.exists(file_name):
            print(f"  ⚠️  Không tìm thấy {file_name} — bỏ qua")
            continue

        with open(file_name, "r", encoding="utf-8") as f:
            content = f.read()
        content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        # Lấy SHA file hiện tại trên GitHub (cần để update)
        r = requests.get(f"{api_base}/{file_name}", headers=headers, timeout=10)
        sha = r.json().get("sha", "") if r.status_code == 200 else ""

        payload = {
            "message": f"Auto update {file_name} {now_str}",
            "content": content_b64,
        }
        if sha:
            payload["sha"] = sha

        r2 = requests.put(f"{api_base}/{file_name}", headers=headers,
                          json=payload, timeout=15)
        if r2.status_code in (200, 201):
            print(f"  ✅ {file_name} — OK")
            ok_count += 1
        else:
            print(f"  ❌ {file_name} — Lỗi {r2.status_code}: {r2.json().get('message','')}")

    if ok_count == len(HTML_FILES):
        print("  🎉 Push xong! GitHub Pages cập nhật sau ~30 giây")
        return True
    return False


# ══════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════
def main():
    import sys

    print("=" * 56)
    print("  🛍️  NA XUẤT DƯ — SECTION TOOL v2.0")
    print(f"  ⏰  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 56)

    try:
        import requests
    except ImportError:
        print("\n❌ Thiếu: pip install requests")
        input("\nBấm Enter để thoát...")
        return

    cfg = doc_config()

    if "--config" in sys.argv:
        sua_config(cfg)
        return

    cfg = kiem_tra_config(cfg)

    print(f"\n  Ngưỡng Hot Deal : {cfg['so_luong_ban_toi_thieu']} đơn/ngày")
    print(f"  Số SP/section   : {cfg['so_sp_hien_thi']} sản phẩm")
    print(f"  (Đổi cấu hình  : py hotdeal_tool.py --config)\n")

    # ── Bước 1: Webcake ──
    print("📡 Bước 1/3 — Kéo sản phẩm từ Webcake...")
    slug_map, info_map = lay_webcake_products(cfg)

    # ── Bước 2: Pancake ──
    print("\n📊 Bước 2/3 — Kéo đơn hàng từ Pancake...")
    qty_map = dem_qty_hom_nay(cfg)

    # ── Bước 3: Lọc ──
    print("\n🔍 Bước 3/3 — Lọc sản phẩm...")
    hot_deal  = loc_hot_deal(qty_map, slug_map, info_map, cfg)
    sale_list = loc_sale(slug_map, info_map, cfg)
    cfg_new       = dict(cfg)
    cfg_new["so_sp_hien_thi"] = cfg.get("so_sp_hang_moi", 8)
    new_list  = lay_hang_moi_tu_pancake(cfg_new, slug_map)

    # ── Cập nhật HTML ──
    print("\n📝 Đang cập nhật HTML...")
    cap_nhat_html_file(HTML_FILES["hotdeal"], "hotdeal", hot_deal)
    cap_nhat_html_file(HTML_FILES["sale"],    "sale",    sale_list)
    cap_nhat_html_file(HTML_FILES["new"],     "new",     new_list)

    # ── Push GitHub ──
    git_push(cfg)

    # ── Tóm tắt ──
    print("\n" + "=" * 56)
    print("  📊 KẾT QUẢ:")
    print(f"     🔥 Hot Deal  : {len(hot_deal)} sản phẩm")
    print(f"     🏷️  Xả Kho   : {len(sale_list)} sản phẩm")
    print(f"     ✨ Hàng Mới  : {len(new_list)} sản phẩm")
    print("=" * 56)
    print("  ✅ Xong!")
    print("=" * 56)
    if sys.stdin.isatty():
        input("\n  Bấm Enter để đóng...")


if __name__ == "__main__":
    main()
