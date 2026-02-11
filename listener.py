"""
all_new_cbot - Real-time Listener (macOS/Codex Only)

listener.py:
- Long Polling (timeout=30)
- Reactive Trigger for executor.sh
"""

import os
import json
import asyncio
import subprocess
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USERS = [int(u.strip()) for u in os.getenv("TELEGRAM_ALLOWED_USERS", "").split(",") if u.strip()]

_DIR = os.path.dirname(os.path.abspath(__file__))
MESSAGES_FILE = os.path.join(_DIR, "messages.json")

def load_msgs():
    if os.path.exists(MESSAGES_FILE):
        try:
            with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {"messages": [], "last_update_id": 0}

def save_msgs(data):
    with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def trigger_codex():
    """즉시 코덱스 엔진 실행"""
    script = os.path.join(_DIR, "executor.sh")
    if os.path.exists(script):
        print(f"🚀 Codex Trigger: {datetime.now().strftime('%H:%M:%S')}")
        subprocess.Popen(["/bin/bash", script])

async def fetch_updates():
    if not BOT_TOKEN: return 0
    bot = Bot(token=BOT_TOKEN)
    data = load_msgs()
    
    try:
        updates = await bot.get_updates(offset=data["last_update_id"]+1, timeout=30)
        new_count = 0
        for u in updates:
            if not u.message: continue
            if ALLOWED_USERS and u.message.from_user.id not in ALLOWED_USERS: continue
            
            msg_data = {
                "message_id": u.message.message_id,
                "chat_id": u.message.chat_id,
                "user": u.message.from_user.first_name,
                "text": u.message.text or u.message.caption or "",
                "timestamp": str(datetime.now()),
                "processed": False
            }
            data["messages"].append(msg_data)
            data["last_update_id"] = u.update_id
            new_count += 1
            
        if new_count > 0:
            save_msgs(data)
            return new_count
    except Exception as e:
        print(f"⚠️ Polling Error: {e}")
    return 0

async def main():
    print("="*40)
    print("🔥 all_new_cbot High-Speed Listener")
    print("="*40)
    
    while True:
        count = await fetch_updates()
        if count > 0:
            trigger_codex()
        await asyncio.sleep(0.1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
