#!/usr/bin/env python3
"""Dashboard 2.0 — 数据引擎"""
import json, subprocess, sys, os, re, urllib.request, yaml
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))
BASE = Path.home() / "Desktop/claude work/hermes-workbench"
ASSISTANT = Path.home() / "Desktop/claude work/wechat-assistant"
VAULT = Path.home() / "Documents/Obsidian Vault"


def load_json(path):
    if not Path(path).exists(): return {}
    with open(path) as f: return json.load(f)


def load_yaml(path):
    if not os.path.exists(path): return {}
    with open(path) as f: return yaml.safe_load(f) or {}


# ─── 伴读 ───
def get_reading():
    data = load_json(ASSISTANT / "data/reading_log.json")
    items = data.get("items", [])
    toread = [i for i in items if i.get("rating", 0) == 0]
    read = [i for i in items if i.get("rating", 0) > 0]
    return {"total": len(items), "toread": toread[-5:], "read": read[-5:], "recent": items[-5:][::-1]}


# ─── 灵感 ───
def get_ideas():
    data = load_json(ASSISTANT / "data/ideas.json")
    active = [i for i in data if not i.get("done")]
    return {"total": len(active), "recent": active[-5:][::-1]}


# ─── 断舍离 ───
def get_declutter():
    data = load_json(ASSISTANT / "data/declutter.json")
    items = data.get("items", [])
    pending = [i for i in items if i.get("status") == "pending"]
    done = [i for i in items if i.get("status") == "done"]
    return {"total": len(items), "pending": pending[-5:], "done_recent": done[-5:]}


# ─── 生词 ───
def get_vocab():
    data = load_json(ASSISTANT / "data/vocabulary.json")
    words = data.get("words", [])
    return {"total": len(words), "new": sum(1 for w in words if w["stage"] == 0),
            "learning": sum(1 for w in words if 0 < w["stage"] < 6 and not w.get("mastered")),
            "mastered": sum(1 for w in words if w.get("mastered"))}


# ─── Cron ───
def get_cron():
    try:
        raw = subprocess.run(["hermes", "cron", "list"], capture_output=True, text=True, timeout=15).stdout
    except: return {"total": 0, "ok": 0, "error": 0, "jobs": []}
    jobs = []; cur = None
    for line in raw.split("\n"):
        m = re.match(r'\s+([0-9a-f]+)\s+\[(\w+)\]', line)
        if m:
            if cur: jobs.append(cur)
            cur = {"id": m.group(1), "state": m.group(2)}
        elif cur:
            if "Name:" in line: cur["name"] = line.split("Name:", 1)[1].strip()
            elif "Schedule:" in line: cur["schedule"] = line.split("Schedule:", 1)[1].strip()
            elif "Last run:" in line:
                rest = line.split("Last run:", 1)[1].strip()
                cur["last_status"] = "error" if "error" in rest.lower() else "ok"
    if cur: jobs.append(cur)
    ok = sum(1 for j in jobs if j.get("last_status") == "ok")
    err = sum(1 for j in jobs if j.get("last_status") == "error")
    return {"total": len(jobs), "ok": ok, "error": err, "jobs": jobs}


# ─── 连线状态 ───
def check_connections():
    conns = []
    for name, url in [("DeepSeek", "https://api.deepseek.com/v1/models"), ("豆瓣", "https://www.douban.com/feed/people/zhengyuzhouliar/interests")]:
        try:
            resp = urllib.request.urlopen(url, timeout=5)
            conns.append({"name": name, "icon": "🧠" if "Deep" in name else "📖", "ok": resp.status == 200})
        except: conns.append({"name": name, "icon": "🧠" if "Deep" in name else "📖", "ok": False})
    cfg = load_yaml(os.path.expanduser("~/.hermes/config.yaml"))
    cfg_str = str(cfg).lower()
    conns.append({"name": "飞书", "icon": "💬", "ok": "feishu" in cfg_str})
    conns.append({"name": "微信", "icon": "💬", "ok": "weixin" in cfg_str})
    return conns


# ─── 连线地图 ───
def get_connection_map():
    return [
        {"from": "训记", "to": "健身数据", "via": "JSON", "icon": "🏋️"},
        {"from": "Exchange", "to": "日历/早报", "via": "icalBuddy", "icon": "💼"},
        {"from": "Apple Health", "to": "健康日报", "via": "XML→JSON", "icon": "🩺"},
        {"from": "豆瓣", "to": "伴读", "via": "RSS", "icon": "📖"},
        {"from": "上金所", "to": "微博", "via": "auto_opossum", "icon": "🥇"},
        {"from": "美团", "to": "每日领券", "via": "Skill", "icon": "🎫"},
        {"from": "多邻国", "to": "打卡记录", "via": "状态文件", "icon": "🟢"},
    ]


# ─── Skills ───
def get_skills():
    skill_dir = Path.home() / ".hermes/skills"
    if not skill_dir.exists(): return []
    skills = []
    for d in sorted(skill_dir.iterdir()):
        if d.is_dir() and (d / "SKILL.md").exists():
            lines = (d / "SKILL.md").read_text().split("\n")[:8]
            desc = " ".join([l.strip("- #")[:80] for l in lines if l.strip() and not l.startswith("---")])
            skills.append({"name": d.name, "desc": desc[:120]})
    return skills


# ─── Obsidian ───
def get_obsidian():
    if not VAULT.exists(): return []
    icon_map = {"伴读":"📖","看板":"📊","项目":"🚀","健康":"❤️","日记":"📓","知识库":"📚","买房资料":"🏡","微信收藏":"💬"}
    folders = []
    for item in sorted(VAULT.iterdir()):
        if item.name.startswith(".") or item.name.startswith("_"): continue
        if item.is_dir():
            md_files = list(item.rglob("*.md"))
            items = []
            for f in md_files[:8]:
                line = f.read_text().split("\n")[0] if f.exists() else ""
                title = line.replace("# ","").strip()[:50] if line.startswith("#") else f.stem
                items.append({"title": title, "path": str(f.relative_to(VAULT))})
            folders.append({"name": item.name, "icon": icon_map.get(item.name,"📁"), "count": len(md_files), "items": items})
    return folders


# ─── Codex 项目 ───
def get_codex():
    codex_dirs = [Path.home() / "Desktop/Codex Work", Path.home() / "Desktop/Codexwork"]
    projects = []
    for codex_dir in codex_dirs:
        if not codex_dir.exists(): continue
        for d in sorted(codex_dir.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                subdirs = [s.name for s in d.iterdir() if s.is_dir()]
                files = list(d.rglob("*"))
                md_files = [f.stem for f in files if f.suffix == ".md"]
                projects.append({
                    "name": d.name,
                    "subdirs": subdirs,
                    "file_count": len(files),
                    "recent": md_files[:5],
                })
    return projects


# ─── 健康数据 ───
def get_health():
    health_path = Path.home() / "Desktop/claude work/knowledge-base/health/health_latest.json"
    if not health_path.exists(): return None
    data = load_json(health_path)
    summary = data.get("summary", {})
    
    sleep_recs = summary.get("sleep", [])
    hrv_recs = summary.get("hrv", [])
    hr_recs = summary.get("resting_hr", [])
    weight_recs = summary.get("weight", [])
    temp_recs = summary.get("wrist_temp", [])
    spo2_recs = summary.get("spo2", [])
    
    latest_hr = hr_recs[0]["value"] if hr_recs else ""
    latest_weight = weight_recs[0]["value"] if weight_recs else ""
    latest_hrv = hrv_recs[0]["value"] if hrv_recs else ""
    latest_temp = temp_recs[0]["value"] if temp_recs else ""
    latest_spo2 = spo2_recs[0]["value"] if spo2_recs else ""
    
    # Sleep: calculate last night total from segments
    from datetime import datetime as dt
    sleep_str = "?"
    if sleep_recs:
        # Find segments from last night (after 8pm previous day)
        latest_date = sleep_recs[0]["start"][:10]
        night = [r for r in sleep_recs if r["start"].startswith(latest_date) or r["start"].startswith(
            str(int(latest_date.split("-")[2])-1).zfill(2) if len(latest_date.split("-")[2])==2 else latest_date
        )]
        if night:
            total_min = len(night) * 2  # rough estimate: ~2min per segment
            hours = total_min // 60
            mins = total_min % 60
            sleep_str = f"{hours}h{mins}m" if hours > 0 else f"{mins}m"
    
    # Score: simple heuristic 0-100
    score = 90
    if latest_hrv and isinstance(latest_hrv, (int, float)) and latest_hrv < 25: score -= 15
    if latest_hr and isinstance(latest_hr, (int, float)) and latest_hr > 65: score -= 10
    
    return {
        "sleep": sleep_str,
        "resting_hr": f"{latest_hr} bpm" if latest_hr else "?",
        "weight": f"{latest_weight} kg" if latest_weight else "?",
        "hrv": f"{latest_hrv} ms" if latest_hrv else "?",
        "wrist_temp": f"{latest_temp}°C" if latest_temp else "?",
        "spo2": f"{int(float(latest_spo2)*100)}%" if latest_spo2 else "?",
        "score": score,
        "date": data.get("export_date", "?"),
    }


# ─── 财务数据 ───
def get_finance():
    fp = Path.home() / "Desktop/Codexwork/CURRENT_FINANCIAL_PROFILE.md"
    if not fp.exists():
        fp = Path.home() / "Desktop/Codex Work/CURRENT_FINANCIAL_PROFILE.md"
    if not fp.exists():
        return None
    text = fp.read_text()
    
    def ex(pattern, text=text):
        m = re.search(pattern, text)
        return m.group(1).strip().replace(',', '') if m else None
    
    r = {}
    r['assets'] = ex(r'总资产.*?¥([\d,]+)') or '0'
    r['net_worth'] = ex(r'净资产.*?¥([\d,]+)') or r['assets']
    r['net_worth'] = ex(r'净资产.*?\*?\*?¥([\d,]+)') or r['assets']
    r['liabilities'] = ex(r'总负债.*?\*?\*?¥([\d,]+)') or '0'
    r['cash'] = ex(r'现金及活期.*?¥([\d,]+)') or '0'
    r['gold'] = ex(r'黄金.*?¥([\d,]+)') or '0'
    r['funds'] = ex(r'基金.*?¥([\d,]+)') or '0'
    r['stocks'] = ex(r'A股.*?¥([\d,]+)') or '0'
    funds = re.findall(r'公积金.*?¥([\d,]+)', text); r['housing_fund'] = str(sum(int(f.replace(',','')) for f in funds)) if funds else '0'
    r['insurance'] = ex(r'寿险.*?¥([\d,]+)') or ex(r'中意寿险.*?¥([\d,]+)') or '0'
    r['pension'] = ex(r'养老.*?¥([\d,]+)') or '0'
    r['income'] = ex(r'税后工资.*?¥([\d,]+)') or '22,498'
    exp_match = re.search(r'月支出.*?¥([\d,]+)(?:-¥?([\d,]+))?', text); exp_raw = exp_match.group(2) or exp_match.group(1) if exp_match else '9000'; r['expense'] = exp_raw.replace(',','')
    r['monthly_expense'] = r['expense']
    inc = int(r['income'].replace(',',''))
    exp = int(r['expense'].replace(',',''))
    r['savings'] = str(inc - exp)
    r['savings_rate'] = round((inc - exp) / inc * 100) if inc else 60
    r['emergency_months'] = round(int(r['cash'].replace(',','')) / exp, 1) if exp else 1.0
    inv = int(r['cash'].replace(',','')) + int(r['gold'].replace(',','')) + int(r['funds'].replace(',','')) + int(r['stocks'].replace(',',''))
    r['invest_total'] = f'{inv:,}'
    r['invest_target'] = '1,000,000'
    r['invest_progress'] = round(inv / 1000000 * 100, 1)
    r['invest_gap'] = f'{1000000 - inv:,}'
    r['investable'] = r['invest_total']
    r['annual_expense'] = f'{exp * 12:,}'
    r['fire_target'] = f'{exp * 12 * 25:,}'
    r['fire_pct'] = round(inv / (exp * 12 * 25) * 100, 1) if exp else 17.6
    r['updated'] = datetime.fromtimestamp(fp.stat().st_mtime).strftime("%Y-%m-%d")
    return r


# ─── 投资网格交易追踪 ───
def get_trades():
    tp = BASE / "trades.json"
    if not tp.exists(): return None
    data = load_json(tp)
    top_line = data.get("top_line", {})
    lots = data.get("lots", [])
    
    # 分类
    holding = [l for l in lots if l.get("status") == "holding"]
    pending_sell = [l for l in lots if l.get("status") == "pending_sell"]
    sold = [l for l in lots if l.get("status") == "sold"]
    
    # 总待卖出
    total_target_amount = sum(l.get("quantity", 0) * (l.get("target_price") or 0) for l in pending_sell if l.get("quantity"))
    
    # Top Line 汇总
    total_unrealized = sum(v.get("unrealized_pnl", 0) or 0 for v in top_line.values())
    total_realized = sum(v.get("realized_pnl", 0) or 0 for v in top_line.values())
    
    return {
        "updated": data.get("updated", "?"),
        "top_line": top_line,
        "total_unrealized": round(total_unrealized, 2),
        "total_realized": round(total_realized, 2),
        "holding_count": len(holding),
        "pending_count": len(pending_sell),
        "pending_sell": pending_sell,
        "holding": holding,
        "sold": sold[-10:][::-1],
        "all_lots": lots[::-1],
    }


# ─── 足迹 ───
def get_footprint():
    return {"countries": 6, "cities_cn": 37, "days": 3053, "date": "2026-08-04"}


# ─── 主函数 ───
def safe_collect(fn, name):
    """Wrap collector to catch errors without crashing the pipeline"""
    try:
        return fn()
    except Exception as e:
        print(f"  ⚠️ {name} failed: {e}", file=sys.stderr)
        return None if name in ("health","finance","footprint") else ({} if name == "dialogue" else [])

def main():
    subprocess.run(["/usr/bin/python3", str(BASE / "dialogue_memory.py")], capture_output=True, timeout=30)
    now = datetime.now(CST).strftime("%Y-%m-%d %H:%M")
    data = {
        "updated": now,
        "reading": safe_collect(get_reading, "reading"),
        "ideas": safe_collect(get_ideas, "ideas"),
        "declutter": safe_collect(get_declutter, "declutter"),
        "vocab": safe_collect(get_vocab, "vocab"),
        "cron": safe_collect(get_cron, "cron"),
        "connections": safe_collect(check_connections, "connections"),
        "connection_map": get_connection_map(),
        "skills": safe_collect(get_skills, "skills"),
        "obsidian": safe_collect(get_obsidian, "obsidian"),
        "codex": safe_collect(get_codex, "codex"),
        "dialogue": safe_collect(lambda: load_json(BASE / "dialogue_memory.json"), "dialogue"),
        "health": safe_collect(get_health, "health"),
        "finance": safe_collect(get_finance, "finance"),
        "trades": safe_collect(get_trades, "trades"),
        "footprint": safe_collect(get_footprint, "footprint"),
    }
    (BASE / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"[OK] {data['cron']['total']} cron | {data['reading']['total']} reading | "
          f"{data['ideas']['total']} ideas | {len(data['skills'])} skills | "
          f"{len(data['obsidian'])} vault | h:{data.get('health',{}).get('score','?')} | f:{'ok' if data.get('finance') else '?'} | {now}")


if __name__ == "__main__":
    main()
