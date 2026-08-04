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


# ─── 主函数 ───
def main():
    # 先提取对话记忆
    subprocess.run(["/usr/bin/python3", str(BASE / "dialogue_memory.py")], capture_output=True, timeout=30)
    now = datetime.now(CST).strftime("%Y-%m-%d %H:%M")
    data = {
        "updated": now,
        "reading": get_reading(),
        "ideas": get_ideas(),
        "declutter": get_declutter(),
        "vocab": get_vocab(),
        "cron": get_cron(),
        "connections": check_connections(),
        "connection_map": get_connection_map(),
        "skills": get_skills(),
        "obsidian": get_obsidian(),
        "codex": get_codex(),
        "dialogue": load_json(BASE / "dialogue_memory.json"),
    }
    (BASE / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))
    data_json = json.dumps(data, ensure_ascii=False)
    for fname in ["dashboard.html", "index.html"]:
        path = BASE / fname
        if path.exists():
            html = path.read_text()
            html = re.sub(r'const D = __DATA__;', f'const D = {data_json};', html)
            path.write_text(html)
    print(f"[OK] {data['cron']['total']} cron | {data['reading']['total']} reading | "
          f"{data['ideas']['total']} ideas | {len(data['skills'])} skills | "
          f"{len(data['obsidian'])} vault | {now}")


if __name__ == "__main__":
    main()
