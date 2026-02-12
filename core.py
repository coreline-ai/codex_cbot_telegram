"""
all_new_cbot - Core Engine (macOS/Cross-Platform)

integrated core.py:
- Telegram API Integration (based on python-telegram-bot)
- Integrated Sender & Messenger
- Task Index & Status Management
"""

import os
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot

import memory  # 메모리 모듈 임포트

# Load Environment
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USERS = [int(u.strip()) for u in os.getenv("TELEGRAM_ALLOWED_USERS", "").split(",") if u.strip()]

_DIR = os.path.dirname(os.path.abspath(__file__))
MESSAGES_FILE = os.path.join(_DIR, "messages.json")
WORKING_FILE = os.path.join(_DIR, "working.json")

# --- UTILS ---
def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- TELEGRAM BOT ACTIONS (REAL API) ---
async def send_message(chat_id, text, parse_mode="Markdown"):
    """통합 메시지 전송 함수 (Real Telegram API)"""
    if not BOT_TOKEN or BOT_TOKEN in ("your_bot_token_here", "YOUR_BOT_TOKEN"):
        print(f"⚠️ [CORE] BOT_TOKEN 미설정 — MOCK 모드: {text[:100]}...")
        return False

    try:
        bot = Bot(token=BOT_TOKEN)

        # 텔레그램 메시지 길이 제한 (4096자)
        if len(text) > 4000:
            chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for i, chunk in enumerate(chunks):
                if i > 0:
                    await asyncio.sleep(0.5)
                await bot.send_message(chat_id=chat_id, text=chunk, parse_mode=parse_mode)
        else:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)

        print(f"📧 [TELEGRAM] Sent to {chat_id}: {text[:80]}...")
        return True

    except Exception as e:
        print(f"❌ [TELEGRAM] Send failed: {e}")
        # Markdown 파싱 실패 시 plain text로 재시도
        if parse_mode == "Markdown":
            try:
                bot = Bot(token=BOT_TOKEN)
                await bot.send_message(chat_id=chat_id, text=text, parse_mode=None)
                return True
            except:
                pass
        return False

async def send_photo(chat_id, photo_path, caption=None):
    """이미지 전송 함수 (Real Telegram API)"""
    if not BOT_TOKEN or BOT_TOKEN in ("your_bot_token_here", "YOUR_BOT_TOKEN"):
        print(f"⚠️ [CORE] BOT_TOKEN 미설정 — MOCK 모드: Photo {photo_path}")
        return False

    if not os.path.exists(photo_path):
        print(f"❌ [TELEGRAM] 파일 없음: {photo_path}")
        return False

    try:
        bot = Bot(token=BOT_TOKEN)
        with open(photo_path, "rb") as photo_file:
            await bot.send_photo(chat_id=chat_id, photo=photo_file, caption=caption)
        print(f"📸 [TELEGRAM] Photo sent to {chat_id}: {photo_path}")
        return True

    except Exception as e:
        print(f"❌ [TELEGRAM] Photo send failed: {e}")
        return False

async def send_document(chat_id, file_path, caption=None):
    """파일(문서) 전송 함수"""
    if not BOT_TOKEN or BOT_TOKEN in ("your_bot_token_here", "YOUR_BOT_TOKEN"):
        print(f"⚠️ [CORE] BOT_TOKEN 미설정 — MOCK 모드: Doc {file_path}")
        return False

    if not os.path.exists(file_path):
        print(f"❌ [TELEGRAM] 파일 없음: {file_path}")
        return False

    # 텔레그램 파일 크기 제한 (50MB)
    file_size = os.path.getsize(file_path)
    if file_size > 50 * 1024 * 1024:
        print(f"⚠️ [TELEGRAM] 파일 50MB 초과: {file_size / 1024 / 1024:.1f}MB")
        return False

    try:
        bot = Bot(token=BOT_TOKEN)
        with open(file_path, "rb") as doc_file:
            await bot.send_document(
                chat_id=chat_id,
                document=doc_file,
                caption=caption,
                filename=os.path.basename(file_path)
            )
        print(f"📎 [TELEGRAM] Document sent to {chat_id}: {file_path}")
        return True

    except Exception as e:
        print(f"❌ [TELEGRAM] Document send failed: {e}")
        return False

def check_messages():
    """읽지 않은 새 메시지 목록 반환 (Codex 호출용)"""
    data = load_json(MESSAGES_FILE, {"messages": [], "last_update_id": 0})
    new_msgs = [m for m in data["messages"] if not m.get("processed")]
    return new_msgs

def mark_as_done(message_id, instruction=None, result_summary=""):
    """메시지 처리 완료 마킹 및 인덱스 업데이트"""
    data = load_json(MESSAGES_FILE, {"messages": [], "last_update_id": 0})
    target_msg = None
    for m in data["messages"]:
        if m["message_id"] == message_id:
            m["processed"] = True
            target_msg = m
            break
    save_json(MESSAGES_FILE, data)

    # 메모리 인덱스 업데이트
    if target_msg:
        memory.update_index(
            message_id=message_id,
            instruction=instruction or target_msg.get("text", ""),
            result_summary=result_summary
        )

def get_past_memory(query):
    """과거 대화 검색 (Codex 호출용)"""
    return memory.search_memory(query)

def get_recent_history(limit=3):
    """최근 대화 요약 (Codex 호출용)"""
    return memory.get_recent_context(limit)

def set_working(status=True, message_id=None):
    """작업 상태 기록 (중복 방지용)"""
    save_json(WORKING_FILE, {"active": status, "message_id": message_id, "time": str(datetime.now())})

def is_working():
    """현재 작업 중인지 확인"""
    data = load_json(WORKING_FILE, {"active": False})
    return data.get("active", False)

if __name__ == "__main__":
    # Test
    print("Core module loaded. BOT_TOKEN:", "SET" if BOT_TOKEN else "NOT SET")
