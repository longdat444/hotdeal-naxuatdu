#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════╗
║       HOT DEAL TOOL — Na Xuất Dư                    ║
║  Kéo sản phẩm bán chạy từ Pancake                  ║
║  → Tự động cập nhật section Hot Deal trên Webcake   ║
╚══════════════════════════════════════════════════════╝

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

WEBCAKE_DOMAIN = "https://www.naxuatdu.vn"

# Status loại bỏ: hoàn / huỷ / xoá
LOAI_BO_STATUS = {4, 5, 6, 7}

# ══════════════════════════════════════════
# QUẢN LÝ CONFIG
# ══════════════════════════════════════════
DEFAULT_CONFIG = {
    "pancake_api_key":          "2c8f40cee58248a988d0ec569806984a",
    "pancake_shop_id":          "120163355",
    "webcake_api_key":          "eyJhbGci...",
    "webcake_refresh_token":    "",
    "webcake_product_id":       "",
    "so_luong_ban_toi_thieu":   0,
    "so_sp_hien_thi":           4,
    "github_token":             "ghp_...",
    "github_username":          "longdat444",
    "github_repo":              "hotdeal-naxuatdu",
}

def doc_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        return {**DEFAULT_CONFIG, **saved}
    return dict(DEFAULT_CONFIG)

def doc_config_tu_env(cfg):
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

def luu_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def nhap_co_mac_dinh(prompt, mac_dinh=""):
    if mac_dinh:
        hien_thi = mac_dinh[:6] + "..." if len(mac_dinh) > 9 else mac_dinh
        gia_tri = input(f"  {prompt} [{hien_thi}]: ").strip()
    else:
        gia_tri = input(f"  {prompt}: ").strip()
    return gia_tri if gia_tri else mac_dinh

def kiem_tra_va_nhap_config(cfg):
    thieu = not cfg["pancake_api_key"] or not cfg["pancake_shop_id"] or not cfg["webcake_api_key"]
    if not thieu:
        return cfg
    print("\n⚙️  THIẾT LẬP LẦN ĐẦU\n")
    cfg["pancake_api_key"] = nhap_co_mac_dinh("Pancake API Key", cfg["pancake_api_key"])
    cfg["pancake_shop_id"] = nhap_co_mac_dinh("Pancake Shop ID", cfg["pancake_shop_id"])
    cfg["webcake_api_key"] = nhap_co_mac_dinh("Webcake API Key", cfg["webcake_api_key"])
    luu_config(cfg)
    print(f"\n  ✅ Đã lưu config vào {CONFIG_FILE}")
    return cfg

def sua_config(cfg):
    print("\n⚙️  CHỈNH SỬA CẤU HÌNH\n")
    cfg["pancake_api_key"]       = nhap_co_mac_dinh("Pancake API Key",      cfg["pancake_api_key"])
    cfg["pancake_shop_id"]       = nhap_co_mac_dinh("Pancake Shop ID",       cfg["pancake_shop_id"])
    cfg["webcake_api_key"]       = nhap_co_mac_dinh("Webcake Access Token",  cfg["webcake_api_key"])
    cfg["webcake_refresh_token"] = nhap_co_mac_dinh("Webcake Refresh Token", cfg.get("webcake_refresh_token", ""))
    cfg["webcake_product_id"]    = nhap_co_mac_dinh("Webcake Product ID",    cfg["webcake_product_id"])
    so_luong = nhap_co_mac_dinh("Ngưỡng bán tối thiểu (qty/ngày)", str(cfg["so_luong_ban_toi_thieu"]))
    cfg["so_luong_ban_toi_thieu"] = int(so_luong) if so_luong.isdigit() else cfg["so_luong_ban_toi_thieu"]
    so_sp = nhap_co_mac_dinh("Số SP hiển thị tối đa", str(cfg["so_sp_hien_thi"]))
    cfg["so_sp_hien_thi"] = int(so_sp) if so_sp.isdigit() else cfg["so_sp_hien_thi"]
    luu_config(cfg)
    print(f"\n  ✅ Đã lưu config mới")
    input("\n  Bấm Enter để thoát...")


# ══════════════════════════════════════════
# WEBCAKE — Slug map & Token refresh
# ══════════════════════════════════════════
def refresh_webcake_token(cfg):
    refresh = cfg.get("webcake_refresh_token", "")
    if not refresh:
        print("  ❌ Chưa có Refresh Token!")
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

def lay_slug_map_tu_webcake(cfg):
    """Trả về dict {SKU: URL} từ Webcake — dùng để build link sản phẩm."""
    print("  🔄 Đang tải slug map từ Webcake...")
    headers = {"X-Storecake-Access-Token": cfg["webcake_api_key"]}
    test = requests.get(f"{WEBCAKE_BASE}/product/all", headers=headers,
                        params={"limit": 1, "page": 1}, timeout=10)
    if test.status_code == 401:
        print("  ⚠️  Token hết hạn → refresh...")
        new_token = refresh_webcake_token(cfg)
        if not new_token:
            return {}
        headers = {"X-Storecake-Access-Token": new_token}
    slug_map = {}
    # Lấy thêm thông tin tên, ảnh, giá từ Webcake
    info_map = {}   # SKU → {name, image, price}
    page = 1
    while True:
        try:
            r = requests.get(f"{WEBCAKE_BASE}/product/all", headers=headers,
                             params={"limit": 50, "page": page}, timeout=15)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"  ⚠️  Lỗi slug map trang {page}: {e}")
            break
        products = data.get("products", [])
        if not products:
            break
        if page == 1 and products:
            print("\n🔍 DEBUG — field của sản phẩm đầu tiên từ Webcake:")
            print(json.dumps(products[0], ensure_ascii=False, indent=2))
            print("─" * 60)
        for p in products:
            sku = p.get("custom_id", "")
            slug = p.get("slug", "")
            name = p.get("name", "")
            price = p.get("price", 0) or p.get("sale_price", 0) or 0
            if not price:
                variants = p.get("variants") or p.get("product_variants") or []
                for v in variants:
                    vp = v.get("price") or v.get("sale_price") or 0
                    if vp:
                        price = vp
                        break
            imgs = p.get("images", []) or []
            if imgs and isinstance(imgs[0], dict):
                image = imgs[0].get("url") or imgs[0].get("src") or imgs[0].get("path") or ""
            else:
                image = imgs[0] if imgs else ""
            if sku and slug:
                slug_map[sku]  = f"{WEBCAKE_DOMAIN}/products/{slug}"
                info_map[sku]  = {"name": name, "price": price, "image": image}
        if page * 50 >= data.get("total_product", 0):
            break
        page += 1
    print(f"  ✅ Đã load {len(slug_map)} SP từ Webcake")
    return slug_map, info_map


# ══════════════════════════════════════════
# BƯỚC 1: Kéo TẤT CẢ đơn hôm nay → đếm QTY từng SKU
# Khung giờ: 0h00 → 23h59 hôm nay (giờ VN) — giống nút "Hôm nay" Pancake UI
# ══════════════════════════════════════════
def lay_info_tu_pancake(cfg, ds_sku):
    """Lấy ảnh + giá từ Pancake API sản phẩm cho danh sách SKU."""
    print("  🔄 Đang lấy ảnh/giá từ Pancake...")
    result = {}  # SKU gốc (vd: A122) → {image, price}
    url = f"{PANCAKE_BASE}/shops/{cfg['pancake_shop_id']}/products"
    page = 1
    found = set()
    while len(found) < len(ds_sku):
        try:
            r = requests.get(url, params={
                "api_key": cfg["pancake_api_key"],
                "page_size": 50,
                "page_number": page,
            }, timeout=30)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"  ⚠️ Lỗi Pancake products trang {page}: {e}")
            break
        products = data.get("data", [])
        if not products:
            break
        for p in products:
            sku_goc = str(p.get("custom_id") or p.get("code") or "").strip()
            if sku_goc not in ds_sku:
                continue
            found.add(sku_goc)
            # Lấy ảnh đầu tiên
            imgs = p.get("images") or []
            image = imgs[0].get("url", "") if imgs and isinstance(imgs[0], dict) else (imgs[0] if imgs else "")
            # Lấy giá từ variation đầu tiên
            price = 0
            for v in (p.get("product_variations") or p.get("variations") or []):
                price = (v.get("retail_price") or v.get("price")
                         or v.get("sale_price") or 0)
                if price:
                    break
            result[sku_goc] = {"image": image, "price": price}
            print(f"    ✅ {sku_goc}: giá={price} | ảnh={'có' if image else 'không'}")
        if page * 50 >= data.get("total_entries", 0):
            break
        page += 1
        time.sleep(0.2)
    return result

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
    print(f"  Loại bỏ   : status {sorted(LOAI_BO_STATUS)} (hoàn/huỷ/xoá)\n")

    url  = f"{PANCAKE_BASE}/shops/{cfg['pancake_shop_id']}/orders"
    page = 1
    qty_map = defaultdict(int)   # SKU → tổng QTY
    pancake_img_map = {}         # SKU → ảnh từ Pancake
    pancake_price_map = {}       # SKU → giá từ Pancake
    pancake_img_map = {}          # SKU → ảnh từ Pancake (fallback)

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

        data        = resp.get("data", [])
        total_pages = resp.get("total_pages", 1)
        total_entries = resp.get("total_entries", "?")

        print(f"  Trang {page}/{total_pages} — {(page-1)*100 + len(data)}/{total_entries} đơn", end="\r")

        for o in data:
            if o.get("status") in LOAI_BO_STATUS:
                continue
            for item in (o.get("items") or []):
                vi  = item.get("variation_info") or {}
                sku = (vi.get("product_display_id") or "").strip()
                if not sku:
                    continue
                qty = int(item.get("quantity") or 1)
                qty_map[sku] += qty
                if sku not in pancake_img_map:
                    img = (vi.get("image") or vi.get("product_image")
                           or vi.get("thumbnail") or "")
                    if img:
                        pancake_img_map[sku] = img
                        print(f"   📷 Pancake img [{sku}]: {img[:60]}")
                if sku not in pancake_price_map:
                    price_raw = (item.get("price") or item.get("origin_price")
                                 or vi.get("retail_price") or 0)
                    if price_raw:
                        pancake_price_map[sku] = int(float(price_raw))
                        

        if page >= total_pages or not data:
            break
        page += 1
        time.sleep(0.3)

    print(f"\n  ✅ Đã xử lý xong — tìm thấy {len(qty_map)} SKU khác nhau\n")

    # Sắp xếp theo QTY giảm dần → lấy top N
    so_hien_thi = cfg["so_sp_hien_thi"]
    nguong      = cfg["so_luong_ban_toi_thieu"]

    top_skus = sorted(qty_map.items(), key=lambda x: x[1], reverse=True)
    if nguong > 0:
        top_skus = [(sku, qty) for sku, qty in top_skus if qty >= nguong]
    top_skus = top_skus[:so_hien_thi]

    if not top_skus:
        print("  ⚠️  Không có SP nào đủ ngưỡng hôm nay")
        return []

    # Lấy ảnh + giá từ Pancake cho top SKU
    ds_sku_can_lay = {sku for sku, _ in top_skus}
    pancake_info = lay_info_tu_pancake(cfg, ds_sku_can_lay)

    san_pham = []
    for i, (sku, qty) in enumerate(top_skus, 1):
        info = info_map.get(sku, {})
        pk = pancake_info.get(sku, {})
        link = slug_map.get(sku, f"{WEBCAKE_DOMAIN}/products/{sku.lower()}")
        print(f"  #{i} {sku} — {qty} đã bán | {info.get('name', sku)}")
        san_pham.append({
            "sku": sku,
            "name": info.get("name", sku),
            "sold_today": qty,
            "price": info.get("price", 0) or pk.get("price", 0),
            "image": info.get("image", "") or pk.get("image", ""),
            "stock": 999,
            "link": link,
        })

    return san_pham


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
    VN_TZ = timezone(timedelta(hours=7))
    today = date.today()

    products_list = [
        {
            "rank":       i,
            "sku":        sp["sku"],
            "name":       sp["name"],
            "price":      format_gia(sp["price"]),
            "sold_today": sp["sold_today"],
            "stock":      sp["stock"],
            "image":      sp["image"],
            "link":       sp["link"],
        }
        for i, sp in enumerate(san_pham, 1)
    ]

    hot_deal_data = {
        "updated":  datetime.now(VN_TZ).strftime("%Y-%m-%dT%H:%M:%S"),
        "expires":  today.strftime("%Y-%m-%d") + "T23:59:59+07:00",
        "products": products_list,
    }

    if not os.path.exists(HTML_FILE):
        print(f"  ❌ Không tìm thấy {HTML_FILE}!")
        return None

    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    data_json      = json.dumps(hot_deal_data, ensure_ascii=False, indent=2)
    pattern        = r'(var HOT_DEAL_DATA\s*=\s*)\{[\s\S]*?\}(\s*;)'
    new_html, count = re.subn(pattern, r'\g<1>' + data_json + r'\2', html)

    if count == 0:
        print("  ❌ Không tìm thấy HOT_DEAL_DATA trong HTML!")
        return None

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(new_html)

    print(f"  ✅ Đã cập nhật HTML ({len(san_pham)} sản phẩm)")
    return new_html


# ══════════════════════════════════════════
# BƯỚC 4 & 5: Webcake + GitHub
# ══════════════════════════════════════════
def tim_webcake_product_id(cfg):
    url     = f"{WEBCAKE_BASE}/product/all"
    headers = {"X-Storecake-Access-Token": cfg["webcake_api_key"]}
    try:
        r        = requests.get(url, headers=headers, params={"term": "Hot Deal", "limit": 5}, timeout=15)
        products = r.json().get("products", [])
        if products:
            pid = products[0].get("id", "")
            cfg["webcake_product_id"] = pid
            luu_config(cfg)
            print(f"  💡 Tìm thấy Product ID: {pid}")
            return pid
    except Exception as e:
        print(f"  ⚠️  Không tìm được ID: {e}")
    return ""

def upload_len_webcake(html_content, cfg):
    print("\n🚀 Đang upload lên Webcake...")
    product_id = cfg.get("webcake_product_id", "") or tim_webcake_product_id(cfg)
    if not product_id:
        print("  ❌ Không có Product ID. Chạy: py hotdeal_tool.py --config")
        return False
    url     = f"{WEBCAKE_BASE}/product/{product_id}"
    headers = {"X-Storecake-Access-Token": cfg["webcake_api_key"],
               "Content-Type": "application/json"}
    match   = re.search(r'(<style>[\s\S]*?</script>)', html_content)
    payload = {"description": match.group(1) if match else html_content}
    try:
        r = requests.patch(url, headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        print("  ✅ Upload thành công!")
        return True
    except Exception as e:
        print(f"  ❌ Lỗi upload: {e}")
        return False

def push_len_github(cfg):
    import base64
    token    = cfg.get("github_token", "")
    username = cfg.get("github_username", "")
    repo     = cfg.get("github_repo", "")
    if not (token and username and repo):
        print("\n  ⚠️  Chưa cấu hình GitHub.")
        return False
    print("\n🚀 Đang push lên GitHub...")
    if not os.path.exists(HTML_FILE):
        print(f"  ❌ Không tìm thấy {HTML_FILE}")
        return False
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    api_url = f"https://api.github.com/repos/{username}/{repo}/contents/index.html"
    headers = {"Authorization": f"token {token}",
               "Accept": "application/vnd.github.v3+json"}
    sha = None
    try:
        r = requests.get(api_url, headers=headers, timeout=15)
        if r.status_code == 200:
            sha = r.json().get("sha")
    except Exception:
        pass
    content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    payload = {"message": f"Update Hot Deal {datetime.now().strftime('%d/%m/%Y %H:%M')}",
               "content": content_b64}
    if sha:
        payload["sha"] = sha
    try:
        r = requests.put(api_url, headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        print(f"  ✅ Push thành công!")
        print(f"  🌐 https://{username}.github.io/{repo}/")
        return True
    except Exception as e:
        print(f"  ❌ Lỗi push: {e}")
        return False

def liet_ke_blocks(cfg):
    print("\n🔍 Danh sách blocks Webcake:\n")
    headers = {"X-Storecake-Access-Token": cfg["webcake_api_key"]}
    try:
        r        = requests.get(f"{WEBCAKE_BASE}/product/all", headers=headers,
                                params={"limit": 50}, timeout=15)
        products = r.json().get("products", []) or r.json().get("data", []) or []
        if not products:
            print("  ⚠️  Không có block nào.")
        else:
            print(f"  {'ID':<30} {'Tên'}")
            print("  " + "-"*60)
            for p in products:
                print(f"  {p.get('id','?'):<30} {p.get('name','?')}")
    except Exception as e:
        print(f"  ❌ Lỗi: {e}")
    input("\n  Bấm Enter để thoát...")


# ══════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════
def main():
    import sys
    print("=" * 54)
    print("  🔥 HOT DEAL TOOL — Na Xuất Dư")
    VN_TZ = timezone(timedelta(hours=7))
    print(f"  ⏰  {datetime.now(VN_TZ).strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 54)

    cfg = doc_config()
    if "--auto"   in sys.argv: cfg = doc_config_tu_env(cfg)
    if "--config" in sys.argv: sua_config(cfg); return
    if "--list"   in sys.argv:
        cfg = kiem_tra_va_nhap_config(cfg)
        liet_ke_blocks(cfg)
        return

    cfg = kiem_tra_va_nhap_config(cfg)
    print(f"\n  Số SP hiển thị  : {cfg['so_sp_hien_thi']}")
    print(f"  Ngưỡng tối thiểu: {cfg['so_luong_ban_toi_thieu']} qty/ngày")

    san_pham = lay_san_pham_ban_chay(cfg)
    html     = cap_nhat_html(san_pham if san_pham else [], expired=not san_pham)
    if html:
        push_len_github(cfg)

    print("\n" + "="*54)
    print("  ✅ Xong!")
    print("="*54)
    if "--auto" not in sys.argv:
        input("  Bấm Enter để đóng...")

if __name__ == "__main__":
    main()
