#!/usr/bin/env python3
"""
💬 对话记忆引擎 — 从 state.db 提取关键信息
输出: dialogue_memory.json
"""
import sqlite3, json, os, re
from datetime import datetime
from pathlib import Path

DB = os.path.expanduser("~/.hermes/state.db")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dialogue_memory.json")


def extract_from_db(days=3):
    """从 state.db 提取最近几天的对话"""
    if not os.path.exists(DB):
        return {"recent": [], "extracted": [], "updated": datetime.now().isoformat()}

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    sql = """
    SELECT m.id, m.role, m.content, m.timestamp, s.source
    FROM messages m
    JOIN sessions s ON m.session_id = s.id
    WHERE m.role IN ('user', 'assistant')
      AND m.timestamp > unixepoch() - ?
      AND s.source != 'cron'
    ORDER BY m.timestamp DESC
    LIMIT 200
    """
    rows = conn.execute(sql, (days * 86400,)).fetchall()
    conn.close()

    extracted = []
    recent = []

    for row in rows:
        content = row["content"] or ""
        # 跳过太短的、工具调用的
        if len(content) < 15:
            continue

        recent.append({
            "role": row["role"],
            "text": content[:200],
            "time": datetime.fromtimestamp(row["timestamp"]).strftime("%m/%d %H:%M"),
            "source": row["source"],
        })

        # 提取：待办 → 如果包含「帮我记」「提醒我」「要做」「明天」「待办」
        if row["role"] == "user" and re.search(r'帮我记|提醒我|要做|待办|明天.*做|写上|日程|写进去|修改简历|改简历', content):
            extracted.append({
                "type": "todo",
                "from": content[:80],
                "time": datetime.fromtimestamp(row["timestamp"]).strftime("%m/%d %H:%M"),
            })
        # 提取：决策 → 「不用了」「删掉」「固定」「锁定」
        elif row["role"] == "user" and re.search(r'不用了|删掉|固定|锁定|决定了|不续|清除|移除', content):
            extracted.append({
                "type": "decision",
                "from": content[:80],
                "time": datetime.fromtimestamp(row["timestamp"]).strftime("%m/%d %H:%M"),
            })
        # 提取：灵感 → 「想」「试试」「探索」「做|搞一下」
        elif row["role"] == "user" and re.search(r'想要|试试|探索|搞一下|做一个|加一个|弄一个|搭一个|要不要', content):
            extracted.append({
                "type": "idea",
                "from": content[:80],
                "time": datetime.fromtimestamp(row["timestamp"]).strftime("%m/%d %H:%M"),
            })

        if len(extracted) >= 20:
            break

    # 去重
    seen = set()
    unique = []
    for e in extracted:
        key = (e["type"], e["from"][:40])
        if key not in seen:
            seen.add(key)
            unique.append(e)

    return {
        "recent": recent[:30],
        "extracted": unique[:15],
        "updated": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    data = extract_from_db(days=3)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ {len(data['recent'])} recent · {len(data['extracted'])} extracted → {OUT}")
