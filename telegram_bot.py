
import os
import sys
import time
import json
import subprocess
from datetime import datetime
import core
import telegram_sender as sender

# Configuration
POLL_INTERVAL = int(os.getenv("TELEGRAM_POLLING_INTERVAL", "10"))
POST_WORK_WAIT = 180  # 3 minutes wait after finishing work
LOCK_FILE = "working.lock"

def check_telegram():
    """Step 1: Check for new messages via Core."""
    return core.check_messages()

def combine_tasks(messages):
    """Step 2: Combine/Select tasks. For now, FIFO."""
    if not messages:
        return None
    return messages[0]

def create_working_lock():
    """Step 4: Create lock file."""
    _dir = os.path.dirname(os.path.abspath(__file__))
    lock_path = os.path.join(_dir, LOCK_FILE)
    with open(lock_path, "w") as f:
        f.write(str(datetime.now()))
    core.set_working(True)

def remove_working_lock():
    """Step 10: Remove lock file."""
    _dir = os.path.dirname(os.path.abspath(__file__))
    lock_path = os.path.join(_dir, LOCK_FILE)
    if os.path.exists(lock_path):
        os.remove(lock_path)
    core.set_working(False)

def execute_task(message):
    """Step 7: Execute the task (Cross-Platform Codex CLI Dispatch)."""
    text = message.get("text", "")
    chat_id = message.get("chat_id")

    sender.send_message_sync(chat_id, f"🤖 [Codex CLI] 명령 접수: '{text}'\nSkills 분석 중...")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    codex_md = os.path.join(base_dir, "codex.md")

    # macOS/Linux: bash를 통해 codex CLI 호출
    executor_sh = os.path.join(base_dir, "executor.sh")
    if os.path.exists(executor_sh):
        cmd = ["bash", executor_sh]
    else:
        # Fallback: 직접 codex exec 호출
        safe_text = text.replace("'", "'\\''")
        cmd = [
            "codex", "exec",
            "--approval-mode", "full-auto",
            "--config", f"developer_instructions_file={codex_md}",
            safe_text
        ]

    sender.send_message_sync(chat_id, f"🚀 Codex CLI를 가동합니다 (skill-based execution)...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=base_dir,
            timeout=600  # 10분 타임아웃
        )

        if result.returncode == 0:
            print(f"[BOT] Codex Success: {result.stdout[:200]}")
            return True, "Codex Skill Execution Successful"
        else:
            print(f"[BOT] Codex Error: {result.stderr[:200]}")
            return False, f"Codex Failed: {result.stderr[:200]}"

    except subprocess.TimeoutExpired:
        return False, "Codex Timeout (10min exceeded)"
    except Exception as e:
        return False, f"CLI Execution Exception: {e}"

def run_agent_loop():
    print(f"--- 🤖 Telegram Bot Agent Started ({datetime.now()}) ---")
    print(f"--- Policies: Poll {POLL_INTERVAL}s, Wait {POST_WORK_WAIT}s ---")

    while True:
        try:
            # 1. Check
            messages = check_telegram()

            if messages:
                print(f"[BOT] Found {len(messages)} new messages.")

                # 2. Combine
                task_msg = combine_tasks(messages)
                if not task_msg:
                    time.sleep(POLL_INTERVAL)
                    continue

                chat_id = task_msg.get("chat_id", os.getenv("TELEGRAM_ALLOWED_USERS", "").split(",")[0])

                # 4. Lock
                create_working_lock()

                # 7. Execute
                success, summary = execute_task(task_msg)

                # 8. Report
                status_icon = "✅" if success else "❌"
                sender.send_message_sync(chat_id, f"{status_icon} 작업 완료 보고: {summary}")

                # 9. Mark Done
                core.mark_as_done(task_msg["message_id"], instruction=task_msg["text"], result_summary=summary)

                # 10. Unlock
                remove_working_lock()

                # Ask for next task
                sender.send_message_sync(chat_id, "🏁 작업을 마쳤습니다. 추가 요청 사항이 있으신가요?\n(3분 대기 모드 진입)")

                # Wait Cycle
                print(f"[BOT] Entered {POST_WORK_WAIT}s cooldown...")
                time.sleep(POST_WORK_WAIT)
                print("[BOT] Cooldown finished. Resuming poll.")

            else:
                time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print("\n[BOT] Stopping Agent...")
            remove_working_lock()
            break
        except Exception as e:
            print(f"\n[BOT] Error in loop: {e}")
            time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    run_agent_loop()
