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
    """Au99.99 上金所实时金价（新浪 gds_AU9999）
    
    字段布局: 当前价,0,卖价,开盘,最高,最低,时间,昨收,...
    涨跌幅 = (当前价 − 开盘) / 开盘 × 100
    """
    import urllib.request
    try:
        req = urllib.request.Request('https://hq.sinajs.cn/list=gds_AU9999',
            headers={"Referer": "https://finance.sina.com.cn", "User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = r.read().decode('gbk')
        
        if '=""' in data or len(data.split('"')[1]) == 0:
            # 盘后无数据，尝试 ETF 518880 兜底
            req2 = urllib.request.Request('https://hq.sinajs.cn/list=sh518880',
                headers={"Referer": "https://finance.sina.com.cn", "User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req2, timeout=5) as r2:
                data2 = r2.read().decode('gbk')
            parts = data2.split('"')[1].split(',')
            current = float(parts[3])  # ETF 当前价
            open_price = float(parts[1])  # ETF 开盘
            price = round(current * 100, 2)  # 换算克价
            change_pct = round((current - open_price) / open_price * 100, 2)
            return {"current_price": price, "day_change_pct": change_pct}
        
        parts = data.split('"')[1].split(',')
        current = float(parts[0])   # 当前价（元/克）
        open_price = float(parts[3])  # 今日开盘
        change_pct = round((current - open_price) / open_price * 100, 2)
        return {"current_price": current, "day_change_pct": change_pct}
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
