"""
all_new_cbot - Real-time Listener (Cross-Platform)

- Poll Telegram updates
- Append messages to messages.json
- Trigger Codex executor
- Send intermediate progress from execution.log
"""

import asyncio
import json
import os
import shutil
import subprocess
import time
from datetime import datetime

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - fallback for missing dependency
    def load_dotenv(*args, **kwargs):  # type: ignore
        return False

try:
    from telegram import Bot
except Exception:  # pragma: no cover - fallback for missing dependency
    Bot = None  # type: ignore

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USERS = [int(u.strip()) for u in os.getenv("TELEGRAM_ALLOWED_USERS", "").split(",") if u.strip()]
HEARTBEAT_INTERVAL = int(os.getenv("TELEGRAM_PROGRESS_HEARTBEAT", "45"))
TASK_TIMEOUT = int(os.getenv("TELEGRAM_TASK_TIMEOUT", "900"))
CODEX_MODEL = os.getenv("CODEX_MODEL", "gpt-5-codex")
ALLOW_NESTED_CODEX = os.getenv("ALLOW_NESTED_CODEX", "0")
MACOS_STRICT_MODE = os.getenv("MACOS_STRICT_MODE", "0")
RUN_MODE = os.getenv("RUN_MODE", "telegram").strip().lower()

_DIR = os.path.dirname(os.path.abspath(__file__))
MESSAGES_FILE = os.path.join(_DIR, "messages.json")
EXEC_LOG = os.path.join(_DIR, "execution.log")
EXECUTOR_SH = os.path.join(_DIR, "executor.sh")
CODEX_MD = os.path.join(_DIR, "codex.md")

_ACTIVE_PROCESS = None


def load_msgs():
    if os.path.exists(MESSAGES_FILE):
        try:
            with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"messages": [], "last_update_id": 0}


def save_msgs(data):
    with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _read_log_increment(log_path, offset):
    if not os.path.exists(log_path):
        return [], offset
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            f.seek(offset)
            chunk = f.read()
            new_offset = f.tell()
        return chunk.splitlines(), new_offset
    except Exception:
        return [], offset


def _tail_log(log_path, max_lines=30):
    if not os.path.exists(log_path):
        return []
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read().splitlines()[-max_lines:]
    except Exception:
        return []


def _append_log(line):
    try:
        with open(EXEC_LOG, "a", encoding="utf-8") as f:
            f.write(line.rstrip() + "\n")
    except Exception:
        pass


def _is_nested_codex_call_blocked():
    # Nested invocation can terminate/disconnect the parent Codex session.
    return bool(os.getenv("CODEX_THREAD_ID")) and ALLOW_NESTED_CODEX != "1"


def _is_enabled(raw_value):
    return str(raw_value).strip().lower() in ("1", "true", "yes", "on")


def _progress_from_line(line):
    l = (line or "").lower()
    if "[recon]" in l:
        return ("recon", "Market/domain analysis in progress.")
    if "[copy]" in l:
        return ("copy", "Copy strategy generation in progress.")
    if "[variator]" in l:
        return ("variator", "Design variation selection in progress.")
    if "[builder]" in l:
        return ("builder", "Building the web package.")
    if "[generate]" in l or "image_gen subprocess" in l:
        return ("assets", "Generating image assets.")
    if "[motion]" in l:
        return ("motion", "Applying motion/animation effects.")
    if "[audit]" in l:
        return ("audit", "Running quality audit.")
    if "[done]" in l or "pipeline complete" in l:
        return ("done", "Generation pipeline completed.")
    if "[skip] codex busy" in l:
        return ("busy", "Codex is currently busy with another task.")
    if "[error]" in l or " failed" in l:
        return ("warn", "Issue detected. Attempting recovery/check.")
    return (None, None)


async def _send_progress(bot, chat_id, text):
    if not chat_id or Bot is None:
        return
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=None)
    except Exception as e:
        print(f"[LISTENER] Progress send failed: {e}")


async def _monitor_codex_progress(chat_id, process, log_offset):
    if not BOT_TOKEN or not chat_id or Bot is None:
        return

    bot = Bot(token=BOT_TOKEN)
    start_time = time.time()
    last_heartbeat = start_time
    seen = set()

    while True:
        rc = process.poll()

        lines, log_offset = _read_log_increment(EXEC_LOG, log_offset)
        for line in lines:
            key, msg = _progress_from_line(line)
            if key and msg and key not in seen:
                await _send_progress(bot, chat_id, msg)
                seen.add(key)
                last_heartbeat = time.time()

        elapsed = time.time() - start_time
        if elapsed > TASK_TIMEOUT:
            try:
                process.kill()
            except Exception:
                pass
            await _send_progress(bot, chat_id, f"Task timeout exceeded ({TASK_TIMEOUT}s).")
            log_file = getattr(process, "_cbot_log_file", None)
            if log_file:
                try:
                    log_file.close()
                except Exception:
                    pass
            return

        if rc is not None:
            break

        if time.time() - last_heartbeat >= HEARTBEAT_INTERVAL:
            await _send_progress(bot, chat_id, f"Task still running... ({int(elapsed)}s)")
            last_heartbeat = time.time()

        await asyncio.sleep(2)

    lines, _ = _read_log_increment(EXEC_LOG, log_offset)
    for line in lines:
        key, msg = _progress_from_line(line)
        if key and msg and key not in seen:
            await _send_progress(bot, chat_id, msg)
            seen.add(key)

    if process.returncode == 0:
        await _send_progress(bot, chat_id, "Automated task completed.")
    else:
        tail = _tail_log(EXEC_LOG, max_lines=30)
        err_line = next((x for x in reversed(tail) if "error" in x.lower() or "failed" in x.lower()), "")
        if not err_line and tail:
            err_line = tail[-1]
        if err_line:
            await _send_progress(bot, chat_id, f"Task failed: {err_line[:180]}")
        else:
            await _send_progress(bot, chat_id, "Task failed. Check execution.log for details.")

    log_file = getattr(process, "_cbot_log_file", None)
    if log_file:
        try:
            log_file.close()
        except Exception:
            pass


def _build_executor_command():
    strict_mode = _is_enabled(MACOS_STRICT_MODE)

    # Preferred route: executor.sh through bash
    if os.path.exists(EXECUTOR_SH) and shutil.which("bash"):
        return ["bash", EXECUTOR_SH], "bash"

    if strict_mode:
        # macOS strict mode: do not allow direct fallback.
        return None, "strict_bash_only"

    # Windows-safe fallback route: direct codex exec
    if shutil.which("codex"):
        prompt = "Check messages.json and process the first 'processed: false' item using only core.py APIs, then mark as done."
        return [
            "codex", "exec",
            "--full-auto",
            "-m", CODEX_MODEL,
            "--config", f"developer_instructions_file={CODEX_MD}",
            prompt,
        ], "direct"

    return None, "none"


async def trigger_codex(chat_id=None, text=""):
    """Trigger Codex worker + progress reporting."""
    global _ACTIVE_PROCESS

    if _is_nested_codex_call_blocked():
        msg = "[ERROR] Nested Codex invocation blocked in listener (CODEX_THREAD_ID detected)."
        _append_log(msg)
        print(f"[LISTENER] {msg}")
        if BOT_TOKEN and chat_id:
            bot = Bot(token=BOT_TOKEN)
            await _send_progress(
                bot,
                chat_id,
                "Nested Codex call blocked. Run automation in a normal terminal or set ALLOW_NESTED_CODEX=1.",
            )
        return

    if _ACTIVE_PROCESS and _ACTIVE_PROCESS.poll() is None:
        print("[LISTENER] Codex worker already running. Skip duplicate trigger.")
        return

    cmd, mode = _build_executor_command()
    if not cmd:
        if mode == "strict_bash_only":
            msg = "[ERROR] macOS strict mode enabled: bash+executor.sh is required, direct fallback is disabled."
        else:
            msg = "[ERROR] Executor unavailable: bash/codex not found."
        print(f"[LISTENER] {msg}")
        _append_log(msg)
        return

    print(f"[LISTENER] Codex trigger mode={mode} at {datetime.now().strftime('%H:%M:%S')}")
    log_offset = os.path.getsize(EXEC_LOG) if os.path.exists(EXEC_LOG) else 0
    popen_kwargs = {}
    if mode == "direct":
        # Direct codex mode must write to execution.log for progress/error monitoring.
        log_file = open(EXEC_LOG, "a", encoding="utf-8")
        popen_kwargs["stdout"] = log_file
        popen_kwargs["stderr"] = subprocess.STDOUT
    proc = subprocess.Popen(cmd, cwd=_DIR, **popen_kwargs)
    if mode == "direct":
        setattr(proc, "_cbot_log_file", log_file)
    _ACTIVE_PROCESS = proc
    if BOT_TOKEN and chat_id:
        asyncio.create_task(_monitor_codex_progress(chat_id, proc, log_offset))


async def fetch_updates():
    if Bot is None:
        print("[LISTENER] python-telegram-bot is not installed. Skipping Telegram polling.")
        return 0
    if not BOT_TOKEN or BOT_TOKEN in ("your_bot_token_here", "YOUR_BOT_TOKEN"):
        print("[LISTENER] BOT_TOKEN not set. Check .env")
        return 0

    bot = Bot(token=BOT_TOKEN)
    data = load_msgs()

    try:
        updates = await bot.get_updates(
            offset=data["last_update_id"] + 1,
            timeout=30,
            allowed_updates=["message"],
        )

        new_count = 0
        for u in updates:
            if not u.message:
                continue
            if ALLOWED_USERS and u.message.from_user.id not in ALLOWED_USERS:
                continue

            msg_data = {
                "message_id": u.message.message_id,
                "chat_id": u.message.chat_id,
                "user": u.message.from_user.first_name,
                "text": u.message.text or u.message.caption or "",
                "timestamp": str(datetime.now()),
                "processed": False,
            }
            data["messages"].append(msg_data)
            if u.update_id > data["last_update_id"]:
                data["last_update_id"] = u.update_id
            new_count += 1

        if new_count > 0:
            save_msgs(data)
            return new_count
    except Exception as e:
        print(f"[LISTENER] Polling error: {e}")

    return 0


async def main():
    if RUN_MODE == "webmock":
        print("[LISTENER] RUN_MODE=webmock. Telegram listener is disabled for this mode.")
        return

    print("=" * 50)
    print("all_new_cbot Listener")
    print("=" * 50)

    while True:
        count = await fetch_updates()
        if count > 0:
            print(f"[LISTENER] New messages: {count}. Triggering Codex...")
            data = load_msgs()
            last_msg = data["messages"][-1] if data["messages"] else {}
            await trigger_codex(last_msg.get("chat_id"), last_msg.get("text", ""))
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
