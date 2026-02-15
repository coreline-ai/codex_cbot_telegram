import json
import os
import subprocess
import hashlib
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import quote
from contextlib import contextmanager

try:
    import fcntl
except Exception:  # pragma: no cover
    fcntl = None  # type: ignore

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent
MESSAGES_FILE = ROOT / "messages.json"
WORKING_FILE = ROOT / "working.json"
OUTBOX_FILE = ROOT / "web_outbox.json"
HISTORY_FILE = ROOT / "web_chat_history.json"
EXEC_LOG = ROOT / "execution.log"
EXECUTOR_SH = ROOT / "executor.sh"
WEB_DIR = ROOT / "web_simulator"

_ACTIVE_PROCESS = None
_PROCESS_LOCK = threading.Lock()


class IncomingMessage(BaseModel):
    text: str
    chat_id: int = 10001
    user: str = "Web User"


class QuickTestMessage(BaseModel):
    text: str = "Web control test ping"
    chat_id: int = 10001
    user: str = "Web Control"


def _load_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


@contextmanager
def _file_lock(path: Path):
    lock_path = Path(f"{path}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        if fcntl is not None:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _save_json(path: Path, data: Dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def _next_message_id(messages: List[Dict[str, Any]]) -> int:
    numeric_ids = []
    for m in messages:
        try:
            numeric_ids.append(int(m.get("message_id", 0)))
        except Exception:
            continue
    return (max(numeric_ids) + 1) if numeric_ids else 1


def _has_pending_messages() -> bool:
    queued = _load_json(MESSAGES_FILE, {"messages": [], "last_update_id": 0}).get("messages", [])
    return any(not m.get("processed") for m in queued)


def _spawn_executor_locked() -> Dict[str, Any]:
    global _ACTIVE_PROCESS

    if not EXECUTOR_SH.exists():
        return {"ok": False, "error": "executor.sh not found"}

    env = os.environ.copy()
    # Ensure child worker is not treated as a nested Codex session.
    env.pop("CODEX_THREAD_ID", None)
    env.pop("CODEX_SESSION_ID", None)
    env.pop("CODEX_RUN_ID", None)
    env.setdefault("MESSAGE_CHANNEL", "webmock")
    env.setdefault("RUN_MODE", "webmock")
    proc = subprocess.Popen(["bash", str(EXECUTOR_SH)], cwd=str(ROOT), env=env)
    _ACTIVE_PROCESS = proc
    watcher = threading.Thread(target=_watch_executor, args=(proc,), daemon=True)
    watcher.start()
    return {"ok": True, "triggered": True, "pid": proc.pid}


def _watch_executor(proc: subprocess.Popen) -> None:
    global _ACTIVE_PROCESS
    exit_code = proc.wait()

    with _PROCESS_LOCK:
        if _ACTIVE_PROCESS is proc:
            _ACTIVE_PROCESS = None

    # Prevent hot-loop retries when the executor failed.
    if exit_code != 0:
        return

    if not _has_pending_messages():
        return

    with _PROCESS_LOCK:
        if _ACTIVE_PROCESS and _ACTIVE_PROCESS.poll() is None:
            return
        _spawn_executor_locked()


def _trigger_executor() -> Dict[str, Any]:
    with _PROCESS_LOCK:
        if _ACTIVE_PROCESS and _ACTIVE_PROCESS.poll() is None:
            return {"ok": True, "triggered": False, "reason": "already_running"}
        return _spawn_executor_locked()


def _stop_executor() -> Dict[str, Any]:
    global _ACTIVE_PROCESS

    with _PROCESS_LOCK:
        proc = _ACTIVE_PROCESS
        if not proc or proc.poll() is not None:
            _ACTIVE_PROCESS = None
            return {"ok": True, "stopped": False, "reason": "not_running"}

    pid = proc.pid
    try:
        proc.terminate()
        proc.wait(timeout=4)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=2)
    except Exception as exc:
        return {"ok": False, "stopped": False, "error": str(exc), "pid": pid}

    with _PROCESS_LOCK:
        if _ACTIVE_PROCESS is proc:
            _ACTIVE_PROCESS = None
    return {"ok": True, "stopped": True, "pid": pid}


def _tail_log(lines: int = 40) -> List[str]:
    if not EXEC_LOG.exists():
        return []
    try:
        with EXEC_LOG.open("r", encoding="utf-8", errors="replace") as f:
            return f.read().splitlines()[-lines:]
    except Exception:
        return []


def _hash_payload(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _to_inbound_timeline(m: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "direction": "in",
        "kind": "message",
        "chat_id": m.get("chat_id"),
        "user": m.get("user", "Web User"),
        "text": m.get("text", ""),
        "timestamp": m.get("timestamp", ""),
        "message_id": m.get("message_id"),
    }
    key = _hash_payload(payload)
    return {
        "id": f"in-{key[:12]}",
        "history_key": f"in-{key}",
        **payload,
        "processed": bool(m.get("processed", False)),
    }


def _to_outbound_timeline(m: Dict[str, Any]) -> Dict[str, Any]:
    kind = m.get("type", "message")
    file_path = m.get("photo_path") or m.get("file_path")
    file_url = f"/api/files/{quote(file_path)}" if file_path else None
    payload = {
        "direction": "out",
        "kind": kind,
        "chat_id": m.get("chat_id"),
        "text": m.get("text", ""),
        "caption": m.get("caption", ""),
        "file_path": file_path,
        "timestamp": m.get("timestamp", ""),
    }
    key = _hash_payload(payload)
    return {
        "id": f"out-{key[:12]}",
        "history_key": f"out-{key}",
        **payload,
        "file_url": file_url,
    }


def _history_key_for_item(item: Dict[str, Any]) -> str:
    if item.get("history_key"):
        return str(item["history_key"])
    payload = {
        "direction": item.get("direction"),
        "kind": item.get("kind"),
        "chat_id": item.get("chat_id"),
        "user": item.get("user"),
        "text": item.get("text", ""),
        "caption": item.get("caption", ""),
        "file_path": item.get("file_path"),
        "timestamp": item.get("timestamp", ""),
        "id": item.get("id"),
    }
    direction = "in" if item.get("direction") == "in" else "out"
    return f"{direction}-{_hash_payload(payload)}"


def _append_history_item(item: Dict[str, Any]) -> None:
    with _file_lock(HISTORY_FILE):
        data = _load_json(HISTORY_FILE, {"messages": []})
        messages = data.setdefault("messages", [])
        key = _history_key_for_item(item)
        if any(_history_key_for_item(existing) == key for existing in messages if isinstance(existing, dict)):
            return
        normalized = dict(item)
        normalized["history_key"] = key
        messages.append(normalized)
        messages.sort(key=lambda x: x.get("timestamp", ""))
        _save_json(HISTORY_FILE, data)


def _to_timeline() -> List[Dict[str, Any]]:
    inbound = _load_json(MESSAGES_FILE, {"messages": []}).get("messages", [])
    outbox = _load_json(OUTBOX_FILE, {"messages": []}).get("messages", [])

    source_items = [_to_inbound_timeline(m) for m in inbound] + [_to_outbound_timeline(m) for m in outbox]

    with _file_lock(HISTORY_FILE):
        history_data = _load_json(HISTORY_FILE, {"messages": []})
        existing = history_data.get("messages", [])
        normalized: List[Dict[str, Any]] = []
        seen = set()
        key_to_index: Dict[str, int] = {}
        changed = False

        for item in existing:
            if not isinstance(item, dict):
                changed = True
                continue
            entry = dict(item)
            key = _history_key_for_item(entry)
            if entry.get("history_key") != key:
                entry["history_key"] = key
                changed = True
            if key in seen:
                changed = True
                continue
            seen.add(key)
            key_to_index[key] = len(normalized)
            normalized.append(entry)

        for item in source_items:
            key = _history_key_for_item(item)
            if key in seen:
                idx = key_to_index.get(key)
                if idx is not None:
                    merged = dict(normalized[idx])
                    for field, value in item.items():
                        if merged.get(field) != value:
                            merged[field] = value
                            changed = True
                    normalized[idx] = merged
                continue
            entry = dict(item)
            entry["history_key"] = key
            key_to_index[key] = len(normalized)
            normalized.append(entry)
            seen.add(key)
            changed = True

        normalized.sort(key=lambda x: x.get("timestamp", ""))
        if changed:
            _save_json(HISTORY_FILE, {"messages": normalized})

    timeline = []
    for item in normalized:
        payload = dict(item)
        payload.pop("history_key", None)
        timeline.append(payload)
    return timeline


def _safe_file_path(raw_path: str) -> Path:
    candidate = (ROOT / raw_path).resolve()
    if not str(candidate).startswith(str(ROOT.resolve())):
        raise HTTPException(status_code=403, detail="Forbidden path")
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return candidate


app = FastAPI(title="Web Simulator Messenger", version="1.0.0")
app.mount("/web", StaticFiles(directory=str(WEB_DIR)), name="web")


@app.get("/")
def root() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/messages")
def get_messages() -> Dict[str, Any]:
    return {"ok": True, "messages": _to_timeline()}


@app.post("/api/messages")
def post_message(payload: IncomingMessage) -> Dict[str, Any]:
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    with _file_lock(MESSAGES_FILE):
        data = _load_json(MESSAGES_FILE, {"messages": [], "last_update_id": 0})
        message_id = _next_message_id(data.get("messages", []))
        msg = {
            "message_id": message_id,
            "chat_id": payload.chat_id,
            "user": payload.user,
            "text": text,
            "timestamp": str(datetime.now()),
            "processed": False,
        }
        data.setdefault("messages", []).append(msg)
        _save_json(MESSAGES_FILE, data)
    _append_history_item(_to_inbound_timeline(msg))

    trigger_result = _trigger_executor()
    return {"ok": True, "message": msg, "trigger": trigger_result}


@app.post("/api/control/retrigger")
def retrigger_executor() -> Dict[str, Any]:
    trigger_result = _trigger_executor()
    return {"ok": True, "trigger": trigger_result}


@app.post("/api/control/stop-worker")
def stop_worker() -> Dict[str, Any]:
    result = _stop_executor()
    return {"ok": result.get("ok", False), "result": result}


@app.post("/api/control/test-message")
def send_test_message(payload: QuickTestMessage) -> Dict[str, Any]:
    incoming = IncomingMessage(text=payload.text, chat_id=payload.chat_id, user=payload.user)
    return post_message(incoming)


@app.get("/api/status")
def get_status() -> Dict[str, Any]:
    working = _load_json(WORKING_FILE, {"active": False, "message_id": None, "time": ""})
    queued = _load_json(MESSAGES_FILE, {"messages": [], "last_update_id": 0}).get("messages", [])
    pending = [m for m in queued if not m.get("processed")]
    running = bool(_ACTIVE_PROCESS and _ACTIVE_PROCESS.poll() is None)
    return {
        "ok": True,
        "working": working,
        "executor_running": running,
        "executor_pid": (_ACTIVE_PROCESS.pid if running and _ACTIVE_PROCESS else None),
        "pending_count": len(pending),
        "pending_ids": [m.get("message_id") for m in pending],
        "log_tail": _tail_log(200),
    }


@app.get("/api/files/{file_path:path}")
def get_file(file_path: str) -> FileResponse:
    safe_path = _safe_file_path(file_path)
    return FileResponse(safe_path)


@app.post("/api/reset")
def reset_data() -> Dict[str, Any]:
    _save_json(OUTBOX_FILE, {"messages": []})
    return {"ok": True}


@app.post("/api/debug/clear")
def clear_debug_log() -> Dict[str, Any]:
    try:
        EXEC_LOG.write_text("", encoding="utf-8")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"failed to clear debug log: {exc}")
    return {"ok": True}
