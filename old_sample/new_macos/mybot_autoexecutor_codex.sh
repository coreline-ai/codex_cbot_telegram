#!/bin/bash

# macOS 전용 Codex CLI 실행기 (new_macos)

ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SPF="$ROOT/CODEX.md"
LOG="$ROOT/codex_task.log"
LOCKFILE="$ROOT/mybot_autoexecutor_codex.lock"
CODEX_EXE=$(which codex)

# 1. 실행 경로 및 종속성 체크
if [ -z "$CODEX_EXE" ]; then
    echo "[ERROR] Codex CLI를 찾을 수 없습니다. 'npm install -g @openai/codex' 명령어로 설치해 주세요." >> "$LOG"
    exit 1
fi

# 2. 프로세스 중복 실행 방지
if pgrep -f "codex.*new_macos" > /dev/null; then
    echo "[SKIP] 이미 코덱스가 작업 중입니다." >> "$LOG"
    exit 0
fi

echo "--- CODEX START: $(date) ---" >> "$LOG"

# 3. 명령 실행 (macOS/Codex 최적화)
cd "$ROOT"
export DISABLE_AUTOUPDATER=1

# - resume --last: 이전 세션 이어하기
# - --approval-mode full-auto: 완전 자율 모드
# - --config developer_instructions: 시스템 프롬프트 주입
$CODEX_EXE resume --last --all --approval-mode full-auto \
  --config developer_instructions="$(cat "$SPF")" \
  "텔레그램 메시지를 확인하고 처리할 것. (Codex 엔진)" >> "$LOG" 2>&1

EC=$?

# 만약 resume 할 세션이 없으면 새로 시작 (Fallback)
if [ $EC -ne 0 ]; then
    echo "[INFO] No previous session, starting fresh..." >> "$LOG"
    $CODEX_EXE exec --approval-mode full-auto --search \
      --config developer_instructions="$(cat "$SPF")" \
      "텔레그램 메시지를 확인하고 처리할 것. (Codex 엔진)" >> "$LOG" 2>&1
    EC=$?
fi

exit $EC
