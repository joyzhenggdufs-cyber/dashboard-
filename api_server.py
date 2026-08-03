#!/usr/bin/env python3
"""
🔌 Dashboard API Server — localhost:8765
处理: 健康数据 / 删除灵感 / 删除伴读 / 刷新看板
"""
import json, os, sys, re
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ASSISTANT = Path.home() / "Desktop/claude work/wechat-assistant"
HEALTH = ASSISTANT / "data/health_latest.json"
IDEAS = ASSISTANT / "data/ideas.json"
READING = ASSISTANT / "data/reading_log.json"
DECLUTTER = ASSISTANT / "data/declutter.json"


def load_json(path):
    if not path.exists(): return {}
    with open(path) as f: return json.load(f)

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f: json.dump(data, f, ensure_ascii=False, indent=2)


class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        if path == "/health":
            d = load_json(HEALTH)
            result = {"sleep": d.get("sleep", {}), "heart": d.get("heart", {}),
                      "weight": d.get("weight", {}), "hrv": d.get("hrv", {}),
                      "health_score": d.get("health_score", 0), "today": d.get("today", ""),
                      "export_date": d.get("export_date", "")}
        elif path == "/ping":
            result = {"ok": True}
        else:
            result = {"error": "unknown endpoint"}
        self.wfile.write(json.dumps(result, ensure_ascii=False).encode())

    def do_DELETE(self):
        path = urlparse(self.path).path
        qs = parse_qs(urlparse(self.path).query)
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        try:
            if path.startswith("/ideas/"):
                idx = int(path.split("/")[-1])
                data = load_json(IDEAS)
                if isinstance(data, list) and 0 <= idx < len(data):
                    del data[idx]
                    save_json(IDEAS, data)
                    self.wfile.write(json.dumps({"ok": True, "deleted": idx}).encode())
                else:
                    self.wfile.write(json.dumps({"ok": False, "error": "index out of range"}).encode())

            elif path.startswith("/reading/"):
                idx = int(path.split("/")[-1])
                data = load_json(READING)
                items = data.get("items", [])
                if 0 <= idx < len(items):
                    del items[idx]
                    data["items"] = items
                    data["stats"]["total"] = len(items)
                    save_json(READING, data)
                    self.wfile.write(json.dumps({"ok": True, "deleted": idx}).encode())
                else:
                    self.wfile.write(json.dumps({"ok": False, "error": "index out of range"}).encode())

            elif path.startswith("/declutter/"):
                idx = int(path.split("/")[-1])
                data = load_json(DECLUTTER)
                items = data.get("items", [])
                if 0 <= idx < len(items):
                    del items[idx]
                    data["items"] = items
                    save_json(DECLUTTER, data)
                    self.wfile.write(json.dumps({"ok": True, "deleted": idx}).encode())
                else:
                    self.wfile.write(json.dumps({"ok": False, "error": "index out of range"}).encode())

            elif path == "/refresh":
                os.system(f'/usr/bin/python3 {Path.home()}/Desktop/claude\\ work/hermes-workbench/refresh.py 2>/dev/null &')
                self.wfile.write(json.dumps({"ok": True, "refreshing": True}).encode())

            else:
                self.wfile.write(json.dumps({"ok": False, "error": f"unknown endpoint: {path}"}).encode())
        except Exception as e:
            self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())

    def log_message(self, format, *args):
        pass  # 安静模式


if __name__ == "__main__":
    port = 8765
    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"🔌 Dashboard API → http://localhost:{port}")
    print(f"   GET  /health — 健康数据")
    print(f"   DELETE /ideas/0 — 删灵感")
    print(f"   DELETE /reading/0 — 删伴读")
    print(f"   DELETE /declutter/0 — 删断舍离")
    print(f"   GET  /refresh — 刷新看板")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
