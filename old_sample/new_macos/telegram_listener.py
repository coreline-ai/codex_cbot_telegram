"""
텔레그램 메시지 수집기 (Listener - macOS Optimized)

역할:
- Long Polling (timeout=30)을 통한 실시간 메시지 감지
- 메시지 수신 즉시 mybot_autoexecutor.sh 실행 (Reactive Trigger)
- 중복 실행 방지 및 저전력 설계
"""

import os
import json
import time
import asyncio
import subprocess
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot

# .env 로드
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USERS = [int(uid.strip()) for uid in os.getenv("TELEGRAM_ALLOWED_USERS", "").split(",") if uid.strip()]

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MESSAGES_FILE = os.path.join(_BASE_DIR, "telegram_messages.json")

def load_messages():
    if os.path.exists(MESSAGES_FILE):
        try:
            with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {"messages": [], "last_update_id": 0}

def save_messages(data):
    with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def trigger_autoexecutor(text=""):
    """Claude 또는 Codex 엔진 선택적 실행 (Reactive Trigger)"""
    import subprocess
    import platform
    
    # 메시지에 '/codex'가 포함되어 있으면 코덱스 엔진 사용
    engine = "claude"
    if "/codex" in text.lower():
        engine = "codex"
        
    if platform.system() == "Windows":
        script_name = "mybot_autoexecutor.bat"
    else:
        script_name = "mybot_autoexecutor.sh" if engine == "claude" else "mybot_autoexecutor_codex.sh"
        
    script_path = os.path.join(_BASE_DIR, script_name)
    
    if os.path.exists(script_path):
        print(f"🚀 실시간 {engine.upper()} 트리거 발동: {script_name}")
        # 백그라운드에서 비동기로 실행
        if platform.system() == "Windows":
            subprocess.Popen([script_path], shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            subprocess.Popen(["bash", script_path])
    else:
        print(f"⚠️ 실행 파일을 찾을 수 없음: {script_path}")

async def fetch_new_messages():
    """Long Polling 적용 버전"""
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN이 없습니다.")
        return None

    bot = Bot(token=BOT_TOKEN)
    data = load_messages()
    last_update_id = data.get("last_update_id", 0)

    try:
        # timeout=30으로 실시간 연결 유지
        updates = await bot.get_updates(
            offset=last_update_id + 1,
            timeout=30,
            allowed_updates=["message"]
        )

        new_count = 0
        for update in updates:
            if not update.message: continue
            
            msg = update.message
            if ALLOWED_USERS and msg.from_user.id not in ALLOWED_USERS: continue

            message_data = {
                "message_id": msg.message_id,
                "update_id": update.update_id,
                "user_id": msg.from_user.id,
                "chat_id": msg.chat_id,
                "text": msg.caption or msg.text or "",
                "timestamp": msg.date.strftime("%Y-%m-%d %H:%M:%S"),
                "processed": False
            }

            data["messages"].append(message_data)
            if update.update_id > data["last_update_id"]:
                data["last_update_id"] = update.update_id
            new_count += 1

        if new_count > 0:
            save_messages(data)
            return new_count
        return 0

    except Exception as e:
        print(f"❌ API 오류: {e}")
        return None

async def main():
    print("=" * 60)
    print("🚀 macOS 고속 반응 리스너 가동 중...")
    print("=" * 60)

    while True:
        result = await fetch_new_messages()
        if result and result > 0:
            print(f"✅ {result}개 신규 메시지 수집. 엔진을 호출합니다.")
            # 새 메시지 중 첫 번째 텍스트를 기준으로 엔진 판단 (간소화)
            data = load_messages()
            last_msg_text = data["messages"][-1].get("text", "")
            trigger_autoexecutor(last_msg_text)
        
        # 짧은 대기 후 다시 Long Polling
        await asyncio.sleep(0.1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n종료합니다.")
