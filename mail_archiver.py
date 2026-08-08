#!/usr/bin/env python3
"""
📧 邮件存档器 — 从 Exchange/IMAP 同步历史邮件到外接盘
用法: /usr/bin/python3 mail_archiver.py --full  (首次全量)
      /usr/bin/python3 mail_archiver.py          (增量同步)
"""
import imaplib, email, os, sys, json, time
from datetime import datetime, timedelta
from pathlib import Path

# ─── 配置 ───
EMAIL = "yuzhou.zheng@loreal.com"
IMAP_HOST = "outlook.office365.com"
IMAP_PORT = 993
ARCHIVE_DIR = Path("/Volumes/LENOVO_USB_HDD/Mail_Archive")
STATE_FILE = ARCHIVE_DIR / ".sync_state.json"

# 确保存档目录存在
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

def get_password():
    """从钥匙串或环境变量获取密码"""
    pw = os.environ.get("MAIL_PASSWORD")
    if pw:
        return pw
    
    # 尝试从钥匙串读取
    import subprocess
    try:
        result = subprocess.run(
            ["security", "find-internet-password", "-s", "outlook.office365.com", "-a", EMAIL, "-w"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except:
        pass
    
    # 尝试从文件读取
    pw_file = Path.home() / ".mail_password"
    if pw_file.exists():
        return pw_file.read_text().strip()
    
    return None

def connect():
    """连接 IMAP 服务器"""
    password = get_password()
    if not password:
        print("❌ 未找到密码。请设置 MAIL_PASSWORD 环境变量，或运行:")
        print("   security add-internet-password -s outlook.office365.com -a yuzhou.zheng@loreal.com -w '你的密码'")
        sys.exit(1)
    
    mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    try:
        mail.login(EMAIL, password)
        print(f"✅ 已连接 {EMAIL}")
        return mail
    except imaplib.IMAP4.error as e:
        print(f"❌ 登录失败: {e}")
        print("如果是 MFA 账号，需要生成应用专用密码: https://aka.ms/AppPasswords")
        sys.exit(1)

def load_state():
    """读取已同步状态"""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"last_uid": {}, "last_sync": None}

def save_state(state):
    """保存同步状态"""
    state["last_sync"] = datetime.now().isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2))

def sync_folder(mail, folder_name, state, full=False):
    """同步单个文件夹"""
    print(f"  📂 {folder_name}...", end=" ", flush=True)
    
    try:
        status, _ = mail.select(f'"{folder_name}"', readonly=True)
        if status != "OK":
            print("跳过")
            return 0
    except:
        print("跳过")
        return 0
    
    # 搜索邮件
    last_uid = state["last_uid"].get(folder_name, "0")
    if full:
        result, data = mail.uid("SEARCH", None, "ALL")
    else:
        result, data = mail.uid("SEARCH", None, f"UID {int(last_uid)+1}:*")
    
    if result != "OK" or not data[0]:
        print("无新邮件")
        return 0
    
    uids = data[0].split()
    new_count = len(uids)
    print(f"{new_count} 封新邮件", end=" ", flush=True)
    
    # 保存文件夹
    safe_name = folder_name.replace("/", "_").replace(" ", "_")
    folder_dir = ARCHIVE_DIR / safe_name
    folder_dir.mkdir(parents=True, exist_ok=True)
    
    # 批量下载（每 50 封一批）
    saved = 0
    for i in range(0, len(uids), 50):
        batch = uids[i:i+50]
        uid_str = ",".join(b.decode() for b in batch)
        
        try:
            result, msg_data = mail.uid("FETCH", uid_str, "(RFC822)")
        except:
            continue
        
        for j in range(0, len(msg_data), 2):
            try:
                msg_bytes = msg_data[j][1]
                uid = batch[j//2].decode()
                filepath = folder_dir / f"{uid}.eml"
                if not filepath.exists():
                    filepath.write_bytes(msg_bytes)
                    saved += 1
            except:
                continue
    
    # 更新状态
    if uids:
        state["last_uid"][folder_name] = uids[-1].decode()
    
    print(f"→ 保存 {saved} 封")
    return saved

def main():
    full_sync = "--full" in sys.argv or len(sys.argv) < 2
    
    print(f"{'🔄 全量' if full_sync else '📥 增量'}同步 → {ARCHIVE_DIR}")
    
    mail = connect()
    state = load_state()
    
    # 列出所有文件夹
    status, folders = mail.list()
    total = 0
    
    for folder_line in folders:
        folder_raw = folder_line.decode() if isinstance(folder_line, bytes) else folder_line
        # 提取文件夹名
        parts = folder_raw.split('"')
        if len(parts) >= 4:
            folder_name = parts[-1].strip()
        else:
            folder_name = folder_raw.split(' "/')[-1].strip('"').strip()
        
        # 跳过特殊文件夹
        if any(s in folder_name.lower() for s in ["deleted", "trash", "spam", "junk", "drafts", "rss"]):
            continue
        
        total += sync_folder(mail, folder_name, state, full=full_sync)
    
    save_state(state)
    mail.logout()
    print(f"\n✅ 完成 · 共 {total} 封新邮件 → {ARCHIVE_DIR}")

if __name__ == "__main__":
    main()
