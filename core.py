"""
all_new_cbot - Core Engine

Provides stable APIs used by Codex tasks:
- Telegram send helpers (async)
- Message queue check/mark
- Working-state tracking
- Memory index integration
"""

import os
import json
import asyncio
from datetime import datetime
from contextlib import contextmanager

try:
    import fcntl
except Exception:  # pragma: no cover
    fcntl = None  # type: ignore

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    def load_dotenv(*args, **kwargs):  # type: ignore
        return False

try:
    from telegram import Bot
except Exception:  # pragma: no cover
    Bot = None  # type: ignore

try:
    import memory
except Exception:  # pragma: no cover
    from all_new_cbot import memory  # type: ignore

# Load environment
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USERS = [int(u.strip()) for u in os.getenv("TELEGRAM_ALLOWED_USERS", "").split(",") if u.strip()]

_DIR = os.path.dirname(os.path.abspath(__file__))
MESSAGES_FILE = os.path.join(_DIR, "messages.json")
WORKING_FILE = os.path.join(_DIR, "working.json")
WEB_OUTBOX_FILE = os.path.join(_DIR, "web_outbox.json")
MESSAGE_CHANNEL = os.getenv("MESSAGE_CHANNEL", "telegram").strip().lower()


def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def save_json(path, data):
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


@contextmanager
def _file_lock(path):
    lock_path = f"{path}.lock"
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    with open(lock_path, "a+", encoding="utf-8") as lock_file:
        if fcntl is not None:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _normalize_saved_path(path):
    abs_target = os.path.abspath(path)
    try:
        return os.path.relpath(abs_target, _DIR)
    except Exception:
        return abs_target


def _append_webmock_message(entry):
    with _file_lock(WEB_OUTBOX_FILE):
        data = load_json(WEB_OUTBOX_FILE, {"messages": []})
        data.setdefault("messages", []).append(entry)
        save_json(WEB_OUTBOX_FILE, data)
    return True


async def send_message(chat_id, text, parse_mode="Markdown"):
    """Send Telegram message with chunking and markdown fallback."""
    if MESSAGE_CHANNEL == "webmock":
        return _append_webmock_message(
            {
                "type": "message",
                "chat_id": int(chat_id),
                "text": str(text),
                "parse_mode": parse_mode,
                "timestamp": str(datetime.now()),
            }
        )

    if Bot is None:
        print("[CORE] python-telegram-bot not installed. send_message skipped.")
        return False

    if not BOT_TOKEN or BOT_TOKEN in ("your_bot_token_here", "YOUR_BOT_TOKEN"):
        print(f"[CORE][MOCK] BOT_TOKEN not set: {str(text)[:100]}")
        return False

    try:
        bot = Bot(token=BOT_TOKEN)
        text = str(text)

        if len(text) > 4000:
            chunks = [text[i : i + 4000] for i in range(0, len(text), 4000)]
            for i, chunk in enumerate(chunks):
                if i > 0:
                    await asyncio.sleep(0.5)
                await bot.send_message(chat_id=chat_id, text=chunk, parse_mode=parse_mode)
        else:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)

        print(f"[TELEGRAM] Sent to {chat_id}: {text[:80]}")
        return True
    except Exception as e:
        print(f"[TELEGRAM] Send failed: {e}")
        if parse_mode == "Markdown":
            try:
                bot = Bot(token=BOT_TOKEN)
                await bot.send_message(chat_id=chat_id, text=str(text), parse_mode=None)
                return True
            except Exception:
                pass
        return False


async def send_photo(chat_id, photo_path, caption=None):
    """Send Telegram photo."""
    if MESSAGE_CHANNEL == "webmock":
        if not os.path.exists(photo_path):
            print(f"[WEBMOCK] File missing: {photo_path}")
            return False
        return _append_webmock_message(
            {
                "type": "photo",
                "chat_id": int(chat_id),
                "photo_path": _normalize_saved_path(photo_path),
                "caption": caption or "",
                "timestamp": str(datetime.now()),
            }
        )

    if Bot is None:
        print("[CORE] python-telegram-bot not installed. send_photo skipped.")
        return False

    if not BOT_TOKEN or BOT_TOKEN in ("your_bot_token_here", "YOUR_BOT_TOKEN"):
        print(f"[CORE][MOCK] BOT_TOKEN not set: photo={photo_path}")
        return False

    if not os.path.exists(photo_path):
        print(f"[TELEGRAM] File missing: {photo_path}")
        return False

    try:
        bot = Bot(token=BOT_TOKEN)
        with open(photo_path, "rb") as photo_file:
            await bot.send_photo(chat_id=chat_id, photo=photo_file, caption=caption)
        print(f"[TELEGRAM] Photo sent to {chat_id}: {photo_path}")
        return True
    except Exception as e:
        print(f"[TELEGRAM] Photo send failed: {e}")
        return False


async def send_document(chat_id, file_path, caption=None):
    """Send Telegram document."""
    if MESSAGE_CHANNEL == "webmock":
        if not os.path.exists(file_path):
            print(f"[WEBMOCK] File missing: {file_path}")
            return False
        return _append_webmock_message(
            {
                "type": "document",
                "chat_id": int(chat_id),
                "file_path": _normalize_saved_path(file_path),
                "caption": caption or "",
                "timestamp": str(datetime.now()),
            }
        )

    if Bot is None:
        print("[CORE] python-telegram-bot not installed. send_document skipped.")
        return False

    if not BOT_TOKEN or BOT_TOKEN in ("your_bot_token_here", "YOUR_BOT_TOKEN"):
        print(f"[CORE][MOCK] BOT_TOKEN not set: doc={file_path}")
        return False

    if not os.path.exists(file_path):
        print(f"[TELEGRAM] File missing: {file_path}")
        return False

    file_size = os.path.getsize(file_path)
    if file_size > 50 * 1024 * 1024:
        print(f"[TELEGRAM] File too large (>50MB): {file_size / 1024 / 1024:.1f}MB")
        return False

    try:
        bot = Bot(token=BOT_TOKEN)
        with open(file_path, "rb") as doc_file:
            await bot.send_document(
                chat_id=chat_id,
                document=doc_file,
                caption=caption,
                filename=os.path.basename(file_path),
            )
        print(f"[TELEGRAM] Document sent to {chat_id}: {file_path}")
        return True
    except Exception as e:
        print(f"[TELEGRAM] Document send failed: {e}")
        return False


def check_messages():
    """Return unprocessed messages from messages.json."""
    with _file_lock(MESSAGES_FILE):
        data = load_json(MESSAGES_FILE, {"messages": [], "last_update_id": 0})
    return [m for m in data.get("messages", []) if not m.get("processed")]


def mark_as_done(message_id, instruction=None, result_summary="", summary=None):
    """Mark message as processed and update memory index."""
    if summary is not None and not result_summary:
        result_summary = summary

    with _file_lock(MESSAGES_FILE):
        data = load_json(MESSAGES_FILE, {"messages": [], "last_update_id": 0})
        target_msg = None
        for m in data.get("messages", []):
            if m.get("message_id") == message_id:
                m["processed"] = True
                target_msg = m
                break
        save_json(MESSAGES_FILE, data)

    if target_msg:
        memory.update_index(
            message_id=message_id,
            instruction=instruction or target_msg.get("text", ""),
            result_summary=result_summary,
        )


def get_past_memory(query):
    """Search indexed memory by query."""
    return memory.search_memory(query)


def get_recent_history(limit=3):
    """Get recent memory summary context."""
    return memory.get_recent_context(limit)


def set_working(status=True, message_id=None):
    """Persist working state."""
    save_json(
        WORKING_FILE,
        {
            "active": bool(status),
            "message_id": message_id,
            "time": str(datetime.now()),
        },
    )


def is_working():
    """Return True when agent is marked as busy."""
    data = load_json(WORKING_FILE, {"active": False})
    return bool(data.get("active", False))


if __name__ == "__main__":
    print("Core module loaded. BOT_TOKEN:", "SET" if BOT_TOKEN else "NOT SET")
