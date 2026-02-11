#!/bin/bash

# macOS 전용 Claude Code 실행기 (new_macos)

ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SPF="$ROOT/CLAUDE.md"
LOG="$ROOT/claude_task.log"
LOCKFILE="$ROOT/mybot_autoexecutor.lock"
CLAUDE_EXE=$(which claude)

# 1. 실행 경로 및 종속성 체크
if [ -z "$CLAUDE_EXE" ]; then
    echo "[ERROR] Claude CLI를 찾을 수 없습니다." >> "$LOG"
    exit 1
fi

# 2. 프로세스 중복 실행 방지
if pgrep -f "claude.*new_macos" > /dev/null; then
    echo "[SKIP] 이미 클로드가 작업 중입니다." >> "$LOG"
    exit 0
fi

echo "--- START: $(date) ---" >> "$LOG"

# 3. 명령 실행 (macOS 최적화)
cd "$ROOT"
export DISABLE_AUTOUPDATER=1

# 세션 유지(-c) 모드로 실행
$CLAUDE_EXE -p -c --dangerously-skip-permissions \
  --append-system-prompt-file "$SPF" \
  "텔레그램 메시지를 확인하고 처리할 것. (new_macos 버전)" >> "$LOG" 2>&1

exit $?
