#!/usr/bin/env python3
"""Refresh dashboard data from live Hermes cron list + Obsidian stats.
Injects live data directly into dashboard.html so it works on file:// too."""

import json, re, subprocess, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))
DASHBOARD = Path.home() / "Desktop/claude work/hermes-workbench"
VAULT = Path.home() / "Documents/Obsidian Vault"


def get_cron_jobs():
    try:
        raw = subprocess.run(
            ["hermes", "cron", "list"],
            capture_output=True, text=True, timeout=15
        ).stdout
    except Exception as e:
        print(f"[WARN] hermes cron list failed: {e}", file=sys.stderr)
        return []

    jobs = []
    current = None
    for line in raw.split("\n"):
        m = re.match(r'\s+([0-9a-f]+)\s+\[(\w+)\]', line)
        if m:
            if current:
                jobs.append(current)
            current = {"id": m.group(1), "state": m.group(2)}
        elif current is not None:
            if "Name:" in line:
                current["name"] = line.split("Name:", 1)[1].strip()
            elif "Schedule:" in line:
                current["schedule"] = line.split("Schedule:", 1)[1].strip()
            elif "Last run:" in line:
                rest = line.split("Last run:", 1)[1].strip()
                current["last_status"] = "error" if "error" in rest.lower() else ("ok" if " ok" in rest else "unknown")
            elif "Mode:" in line:
                current["mode"] = line.split("Mode:", 1)[1].strip().replace("no-agent (script stdout delivered directly)", "Script")
            elif "Script:" in line:
                current["script"] = line.split("Script:", 1)[1].strip()
    if current:
        jobs.append(current)
    return jobs


def get_obsidian_stats():
    if not VAULT.exists():
        return []
    icon_map = {"日记":"📓","工作":"💼","项目":"🚀","知识库":"📚","健康":"❤️",
                "伴读":"📖","看板":"📊","会议":"📋","微信收藏":"💬","买房资料":"🏡"}
    folders = []
    for item in sorted(VAULT.iterdir()):
        if item.name.startswith(".") or item.name.startswith("_"):
            continue
        if item.is_dir():
            md_count = len(list(item.rglob("*.md")))
            folders.append({"name": item.name, "icon": icon_map.get(item.name, "📁"), "count": md_count})
    return folders


def main():
    now = datetime.now(CST).strftime("%Y-%m-%d %H:%M")

    jobs = get_cron_jobs()
    obsidian = get_obsidian_stats()

    total = len(jobs)
    ok_count = sum(1 for j in jobs if j.get("last_status") == "ok")
    err_count = sum(1 for j in jobs if j.get("last_status") == "error")
    paused_count = sum(1 for j in jobs if j.get("state") == "paused")

    data = {
        "updated": now,
        "cron": {
            "total": total,
            "ok": ok_count,
            "error": err_count,
            "paused": paused_count,
            "jobs": jobs
        },
        "obsidian": obsidian
    }

    # Write data.json (for GitHub Pages fetch fallback)
    (DASHBOARD / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))

    # Inject live data into dashboard.html
    dash_path = DASHBOARD / "dashboard.html"
    if dash_path.exists():
        html = dash_path.read_text()
        data_json = json.dumps(data, ensure_ascii=False)
        # Replace the placeholder with actual data
        html = html.replace(
            'const LIVE_DATA = null;  // placeholder — refresh.py replaces this',
            f'const LIVE_DATA = {data_json};'
        )
        dash_path.write_text(html)

    print(f"[OK] {total} cron ({ok_count} ok, {err_count} err) | {len(obsidian)} vault folders | {now}")


if __name__ == "__main__":
    main()
