#!/usr/bin/env python3
"""
Terminal UI launcher for Web Simulator Messenger server.

Features:
- Start/stop/restart uvicorn for simulator_messenger_server:app
- Health/status polling via /api/status
- Quick test message via /api/messages
- Live process log tail inside TUI
"""

import argparse
import curses
import json
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Deque, Dict, Optional


class ServerController:
    def __init__(
        self,
        python_exe: str,
        app_module: str,
        host: str,
        port: int,
        cwd: Path,
        use_reload: bool = False,
    ) -> None:
        self.python_exe = python_exe
        self.app_module = app_module
        self.host = host
        self.port = port
        self.cwd = cwd
        self.use_reload = use_reload
        self.process: Optional[subprocess.Popen] = None
        self.started_at: Optional[float] = None
        self.log_lines: Deque[str] = deque(maxlen=250)
        self._lock = threading.Lock()
        self._reader_thread: Optional[threading.Thread] = None
        self.last_exit_code: Optional[int] = None
        self.last_error: str = ""

    def _cmd(self) -> list:
        cmd = [
            self.python_exe,
            "-m",
            "uvicorn",
            self.app_module,
            "--host",
            self.host,
            "--port",
            str(self.port),
        ]
        if self.use_reload:
            cmd.append("--reload")
        return cmd

    def _append_log(self, line: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        with self._lock:
            self.log_lines.append(f"[{ts}] {line.rstrip()}")

    def _reader(self) -> None:
        proc = self.process
        if not proc or not proc.stdout:
            return
        for line in proc.stdout:
            self._append_log(line)

    def is_running(self) -> bool:
        return bool(self.process and self.process.poll() is None)

    def start(self) -> bool:
        if self.is_running():
            return False

        env = os.environ.copy()
        env.setdefault("MESSAGE_CHANNEL", "webmock")
        env.setdefault("RUN_MODE", "webmock")

        try:
            self.process = subprocess.Popen(
                self._cmd(),
                cwd=str(self.cwd),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except Exception as exc:  # pragma: no cover
            self.last_error = f"Failed to start server: {exc}"
            self._append_log(self.last_error)
            return False

        self.started_at = time.time()
        self.last_exit_code = None
        self.last_error = ""
        self._append_log("Server start requested.")
        self._reader_thread = threading.Thread(target=self._reader, daemon=True)
        self._reader_thread.start()
        return True

    def stop(self) -> bool:
        if not self.process:
            return False
        if self.process.poll() is not None:
            self.last_exit_code = self.process.returncode
            return False

        self._append_log("Stopping server...")
        self.process.terminate()
        try:
            self.process.wait(timeout=4)
        except subprocess.TimeoutExpired:
            self._append_log("Terminate timeout. Killing server.")
            self.process.kill()
            self.process.wait(timeout=2)

        self.last_exit_code = self.process.returncode
        return True

    def restart(self) -> None:
        self.stop()
        self.start()

    def poll(self) -> None:
        if not self.process:
            return
        rc = self.process.poll()
        if rc is not None and self.last_exit_code is None:
            self.last_exit_code = rc
            self._append_log(f"Server exited with code {rc}.")

    def uptime(self) -> str:
        if not self.started_at or not self.is_running():
            return "-"
        sec = int(time.time() - self.started_at)
        return f"{sec // 60:02d}:{sec % 60:02d}"

    def get_logs(self, max_lines: int) -> list:
        with self._lock:
            if max_lines <= 0:
                return []
            return list(self.log_lines)[-max_lines:]


def fetch_status(host: str, port: int, timeout: float = 1.5) -> Dict[str, object]:
    url = f"http://{host}:{port}/api/status"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return {"ok": True, "payload": payload}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def send_test_message(host: str, port: int) -> str:
    url = f"http://{host}:{port}/api/messages"
    text = f"TUI test {datetime.now().strftime('%H:%M:%S')}"
    body = json.dumps({"text": text, "chat_id": 10001, "user": "TUI User"}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        message_id = payload.get("message", {}).get("message_id", "?")
        return f"Test message sent (id={message_id})"
    except urllib.error.HTTPError as exc:
        return f"HTTP {exc.code}: {exc.reason}"
    except Exception as exc:
        return f"Send failed: {exc}"


def render(stdscr, controller: ServerController, health: Dict[str, object], last_action: str) -> None:
    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()

    status = "RUNNING" if controller.is_running() else "STOPPED"
    stdscr.addnstr(0, 0, "Web Simulator TUI", max_x - 1, curses.A_BOLD)
    stdscr.addnstr(
        1,
        0,
        f"Server: {status}  PID: {controller.process.pid if controller.process else '-'}  Uptime: {controller.uptime()}",
        max_x - 1,
    )
    stdscr.addnstr(2, 0, f"Target: http://{controller.host}:{controller.port}", max_x - 1)

    if health.get("ok"):
        payload = health.get("payload", {})
        pending = payload.get("pending_count", "?")
        running = payload.get("executor_running", "?")
        ids = payload.get("pending_ids", [])
        stdscr.addnstr(4, 0, f"API: OK  pending={pending}  executor_running={running}", max_x - 1)
        stdscr.addnstr(5, 0, f"Pending IDs: {ids}", max_x - 1)
    else:
        stdscr.addnstr(4, 0, f"API: ERROR  {health.get('error', '-')}", max_x - 1, curses.A_BOLD)

    stdscr.addnstr(
        7,
        0,
        "Keys: [s] start  [x] stop  [r] restart  [t] send test message  [q] quit",
        max_x - 1,
    )
    stdscr.addnstr(8, 0, f"Last action: {last_action}", max_x - 1)
    stdscr.hline(9, 0, ord("-"), max_x)

    available = max_y - 11
    logs = controller.get_logs(max(0, available))
    stdscr.addnstr(10, 0, "Server Logs:", max_x - 1, curses.A_BOLD)
    for i, line in enumerate(logs):
        row = 11 + i
        if row >= max_y:
            break
        stdscr.addnstr(row, 0, line, max_x - 1)

    stdscr.refresh()


def run_tui(stdscr, controller: ServerController, auto_start: bool) -> None:
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(150)

    if auto_start:
        controller.start()

    last_action = "Ready"
    last_health_at = 0.0
    health: Dict[str, object] = {"ok": False, "error": "not polled yet"}

    while True:
        controller.poll()
        now = time.time()
        if now - last_health_at > 1.0:
            health = fetch_status(controller.host, controller.port)
            last_health_at = now

        render(stdscr, controller, health, last_action)
        key = stdscr.getch()
        if key < 0:
            continue

        if key in (ord("q"), ord("Q")):
            last_action = "Quitting..."
            break
        if key in (ord("s"), ord("S")):
            started = controller.start()
            last_action = "Start requested." if started else "Already running or failed to start."
        elif key in (ord("x"), ord("X")):
            stopped = controller.stop()
            last_action = "Stop requested." if stopped else "Already stopped."
        elif key in (ord("r"), ord("R")):
            controller.restart()
            last_action = "Restart requested."
        elif key in (ord("t"), ord("T")):
            last_action = send_test_message(controller.host, controller.port)

    controller.stop()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Web Simulator Messenger TUI launcher")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--python", dest="python_exe", default="python3")
    parser.add_argument("--module", default="simulator_messenger_server:app")
    parser.add_argument("--no-auto-start", action="store_true")
    parser.add_argument("--reload", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cwd = Path(__file__).resolve().parent.parent
    controller = ServerController(
        python_exe=args.python_exe,
        app_module=args.module,
        host=args.host,
        port=args.port,
        cwd=cwd,
        use_reload=args.reload,
    )
    curses.wrapper(run_tui, controller, not args.no_auto_start)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
