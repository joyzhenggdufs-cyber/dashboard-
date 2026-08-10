#!/usr/bin/env python3
"""
实时市价抓取 — A股/ETF/黄金
每5分钟刷新 data.json 中的 current_price
"""
import json, re, subprocess, sys
from pathlib import Path

DATA_FILE = Path.home() / "Desktop/claude work/hermes-workbench/data.json"
HOLDINGS = {
    "半导体ETF鹏华": "sz159813",  # 鹏华半导体ETF
    "黄金": "AU9999",              # 上海金交所
}

def fetch_sina(code):
    """Sina finance API for A-shares/ETFs"""
    import urllib.request
    try:
        url = f"http://hq.sinajs.cn/list={code}"
        req = urllib.request.Request(url, headers={"Referer":"http://finance.sina.com.cn"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = r.read().decode('gbk')
        parts = data.split('"')[1].split(',')
        if len(parts) > 3:
            return {
                "current_price": float(parts[3]),  # 当前价
                "day_change_pct": round((float(parts[3])/float(parts[2]) - 1)*100, 2),
            }
    except Exception as e:
        print(f"  ⚠️ {code} fetch error: {e}", file=sys.stderr)
    return None

def fetch_gold():
    """Gold price: USD/oz → CNY/gram"""
    import urllib.request
    try:
        # Gold spot price in USD/oz
        req = urllib.request.Request('https://api.gold-api.com/price/XAU',
            headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
        usd_per_oz = data["price"]

        # USD/CNY rate (Sina)
        req2 = urllib.request.Request('http://hq.sinajs.cn/list=fx_susdcny',
            headers={"Referer":"http://finance.sina.com.cn"})
        with urllib.request.urlopen(req2, timeout=5) as r2:
            fx = r2.read().decode('gbk').split('"')[1].split(',')
            usd_cny = float(fx[1]) if len(fx) > 1 else 7.2

        # Convert: USD/oz ÷ 31.1035 × USDCNY
        cny_per_gram = round(usd_per_oz / 31.1035 * usd_cny, 2)
        return {"current_price": cny_per_gram, "day_change_pct": None}
    except Exception as e:
        print(f"  ⚠️ gold fetch error: {e}", file=sys.stderr)
    return None

def main():
    with open(DATA_FILE) as f:
        data = json.load(f)

    tr = data.get("trades", {})
    updated = False

    for name, code in HOLDINGS.items():
        if name not in tr.get("top_line", {}):
            continue

        if code == "AU9999":
            price = fetch_gold()
        else:
            price = fetch_sina(code)

        if price and price.get("current_price"):
            old = tr["top_line"][name].get("current_price")
            tr["top_line"][name]["current_price"] = price["current_price"]
            if price.get("day_change_pct") is not None:
                tr["top_line"][name]["day_change_pct"] = price["day_change_pct"]
            updated = True
            print(f"  {name}: {old} → {price['current_price']}")

    if updated:
        data["trades"] = tr
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("[OK] prices updated")
    else:
        print("[skip] no changes")

if __name__ == "__main__":
    main()
