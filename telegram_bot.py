import os
import time
import subprocess
from datetime import datetime

try:
    import core
except Exception:  # pragma: no cover
    try:
        from codex_cbot_telegram import core  # type: ignore
    except Exception:
        from all_new_cbot import core  # type: ignore

try:
    import telegram_sender as sender
except Exception:  # pragma: no cover
    try:
        from codex_cbot_telegram import telegram_sender as sender  # type: ignore
    except Exception:
        from all_new_cbot import telegram_sender as sender  # type: ignore

# Configuration
POLL_INTERVAL = int(os.getenv("TELEGRAM_POLLING_INTERVAL", "10"))
POST_WORK_WAIT = int(os.getenv("TELEGRAM_POST_WORK_WAIT", "180"))
LOCK_FILE = "working.lock"
HEARTBEAT_INTERVAL = int(os.getenv("TELEGRAM_PROGRESS_HEARTBEAT", "45"))
TASK_TIMEOUT = int(os.getenv("TELEGRAM_TASK_TIMEOUT", "900"))
CODEX_MODEL = os.getenv("CODEX_MODEL", "gpt-5-codex")
ALLOW_NESTED_CODEX = os.getenv("ALLOW_NESTED_CODEX", "0")
MACOS_STRICT_MODE = os.getenv("MACOS_STRICT_MODE", "0")


def check_telegram():
    """Step 1: Check for new messages via core."""
    return core.check_messages()


def combine_tasks(messages):
    """Step 2: Select one task (FIFO)."""
    if not messages:
        return None
    return messages[0]


def create_working_lock(message_id=None):
    """Step 4: Create lock file + set working status."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    lock_path = os.path.join(base_dir, LOCK_FILE)
    with open(lock_path, "w", encoding="utf-8") as f:
        f.write(str(datetime.now()))
    core.set_working(True, message_id=message_id)


def remove_working_lock():
    """Step 10: Remove lock file + clear working status."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    lock_path = os.path.join(base_dir, LOCK_FILE)
    if os.path.exists(lock_path):
        os.remove(lock_path)
    core.set_working(False)


def _is_nested_codex_call_blocked():
    # Nested Codex call from inside an active Codex session can break the parent stream.
    return bool(os.getenv("CODEX_THREAD_ID")) and ALLOW_NESTED_CODEX != "1"


def _is_enabled(raw_value):
    return str(raw_value).strip().lower() in ("1", "true", "yes", "on")


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


def _tail_log(log_path, max_lines=40):
    if not os.path.exists(log_path):
        return []
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read().splitlines()[-max_lines:]
    except Exception:
        return []


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


def _build_executor_command(base_dir):
    executor_sh = os.path.join(base_dir, "executor.sh")
    codex_md = os.path.join(base_dir, "codex.md")
    strict_mode = _is_enabled(MACOS_STRICT_MODE)

    # Prefer shared executor when bash is available.
    if os.path.exists(executor_sh) and _which("bash"):
        return ["bash", executor_sh], "bash"

    if strict_mode:
        # macOS strict mode: do not allow direct fallback.
        return None, "strict_bash_only"

    # Windows-safe fallback.
    if _which("codex"):
        prompt = "Check messages.json and process the first 'processed: false' item using only core.py APIs, then mark as done."
        return [
            "codex",
            "exec",
            "--full-auto",
            "-m",
            CODEX_MODEL,
            "--config",
            f"developer_instructions_file={codex_md}",
            prompt,
        ], "direct"

    return None, "none"


def _which(name):
    paths = os.environ.get("PATH", "").split(os.pathsep)
    exts = [""]
    if os.name == "nt":
        exts.extend(os.environ.get("PATHEXT", ".EXE;.BAT;.CMD").split(";"))
    for p in paths:
        for ext in exts:
            candidate = os.path.join(p, name + ext)
            if os.path.isfile(candidate):
                return candidate
    return None


def _run_with_progress_updates(cmd, base_dir, chat_id, timeout_sec=TASK_TIMEOUT):
    """Run subprocess and stream intermediate progress based on execution.log."""
    log_path = os.path.join(base_dir, "execution.log")
    log_offset = os.path.getsize(log_path) if os.path.exists(log_path) else 0
    seen_progress = set()
    start_time = time.time()
    last_heartbeat = start_time

    log_file = open(log_path, "a", encoding="utf-8")
    proc = subprocess.Popen(
        cmd,
        cwd=base_dir,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    try:
        while True:
            rc = proc.poll()

            new_lines, log_offset = _read_log_increment(log_path, log_offset)
            for line in new_lines:
                key, msg = _progress_from_line(line)
                if key and msg and key not in seen_progress:
                    sender.send_message_sync(chat_id, msg)
                    seen_progress.add(key)
                    last_heartbeat = time.time()

            elapsed = time.time() - start_time
            if elapsed > timeout_sec:
                try:
                    proc.kill()
                except Exception:
                    pass
                return False, f"Codex timeout ({timeout_sec}s exceeded)"

            if rc is not None:
                break

            if time.time() - last_heartbeat >= HEARTBEAT_INTERVAL:
                sender.send_message_sync(chat_id, f"Task still running... ({int(elapsed)}s)")
                last_heartbeat = time.time()

            time.sleep(2)

        new_lines, _ = _read_log_increment(log_path, log_offset)
        for line in new_lines:
            key, msg = _progress_from_line(line)
            if key and msg and key not in seen_progress:
                sender.send_message_sync(chat_id, msg)
                seen_progress.add(key)

        if rc == 0:
            return True, "Codex skill execution successful"

        tail = _tail_log(log_path, max_lines=30)
        err_line = next((x for x in reversed(tail) if "error" in x.lower() or "failed" in x.lower()), "")
        if not err_line and tail:
            err_line = tail[-1]
        if err_line:
            return False, f"Codex failed: {err_line[:200]}"
        return False, "Codex failed: unknown error"
    finally:
        try:
            log_file.close()
        except Exception:
            pass


def execute_task(message):
    """Step 7: Execute one task via shared executor (or direct fallback)."""
    text = message.get("text", "")
    chat_id = message.get("chat_id")

    sender.send_message_sync(chat_id, f"[Codex CLI] request received: '{text}'")

    if _is_nested_codex_call_blocked():
        msg = (
            "Nested Codex call blocked (CODEX_THREAD_ID detected). "
            "Run this worker in a normal terminal or set ALLOW_NESTED_CODEX=1."
        )
        sender.send_message_sync(chat_id, msg)
        return False, msg

    base_dir = os.path.dirname(os.path.abspath(__file__))
    cmd, mode = _build_executor_command(base_dir)
    if not cmd:
        if mode == "strict_bash_only":
            msg = "macOS strict mode is enabled: bash+executor.sh is required and direct fallback is disabled."
        else:
            msg = "Executor unavailable: bash/codex not found in PATH"
        sender.send_message_sync(chat_id, msg)
        return False, msg

    sender.send_message_sync(chat_id, f"Starting Codex execution mode={mode}...")

    try:
        success, summary = _run_with_progress_updates(cmd, base_dir, chat_id, timeout_sec=TASK_TIMEOUT)
        print(f"[BOT] Codex Result: success={success}, summary={summary}")
        return success, summary
    except Exception as e:
        return False, f"CLI execution exception: {e}"


def run_agent_loop():
    print(f"--- Telegram Bot Agent Started ({datetime.now()}) ---")
    print(f"--- Policies: poll={POLL_INTERVAL}s, post_work_wait={POST_WORK_WAIT}s ---")

    while True:
        try:
            messages = check_telegram()

            if messages:
                print(f"[BOT] Found {len(messages)} new messages.")

                task_msg = combine_tasks(messages)
                if not task_msg:
                    time.sleep(POLL_INTERVAL)
                    continue

                raw_allowed = os.getenv("TELEGRAM_ALLOWED_USERS", "").split(",")
                fallback_chat = next((x for x in raw_allowed if x.strip()), "")
                chat_id = task_msg.get("chat_id", fallback_chat)

                create_working_lock(message_id=task_msg.get("message_id"))

                success, summary = execute_task(task_msg)

                status_icon = "OK" if success else "FAIL"
                sender.send_message_sync(chat_id, f"[{status_icon}] Task summary: {summary}")

                core.mark_as_done(
                    task_msg["message_id"],
                    instruction=task_msg.get("text", ""),
                    result_summary=summary,
                )

                remove_working_lock()

                sender.send_message_sync(
                    chat_id,
                    "Current task is complete. If you have another request, send it now. Polling will continue.",
                )

                print(f"[BOT] Entered cooldown: {POST_WORK_WAIT}s")
                time.sleep(POST_WORK_WAIT)
                print("[BOT] Cooldown finished. Resuming poll.")
            else:
                time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print("\n[BOT] Stopping agent...")
            remove_working_lock()
            break
        except Exception as e:
            print(f"\n[BOT] Error in loop: {e}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run_agent_loop()
