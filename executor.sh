#!/bin/bash

# all_new_cbot - Codex Executor (macOS/Linux)

ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG="$ROOT/execution.log"
SPF="$ROOT/codex.md"
CODEX_EXE=$(which codex)

cd "$ROOT"

# 1. Codex CLI 존재 확인
if [ -z "$CODEX_EXE" ]; then
    echo "[ERROR] Codex CLI를 찾을 수 없습니다. 'npm install -g @openai/codex' 명령어로 설치해 주세요." >> "$LOG"
    exit 1
fi

# 2. 프로세스 중복 실행 체크
if pgrep -f "codex.*all_new_cbot" > /dev/null; then
    echo "[SKIP] Codex busy: $(date)" >> "$LOG"
    exit 0
fi

echo "--- START: $(date) ---" >> "$LOG"

# 환경변수 설정
export DISABLE_AUTOUPDATER=1

# 3. 코덱스 가동 (resume → exec fallback)
# --approval-mode full-auto: 중단 없는 작업 수행
$CODEX_EXE resume --last --all --approval-mode full-auto \
  --config developer_instructions_file="$SPF" \
  "Check messages.json and process any 'processed: false' entries using core.py." >> "$LOG" 2>&1

EC=$?

if [ $EC -ne 0 ]; then
    # 세션이 없을 경우 새로 시작
    echo "[INFO] No previous session, starting fresh..." >> "$LOG"
    $CODEX_EXE exec --approval-mode full-auto --search \
      --config developer_instructions_file="$SPF" \
      "Check messages.json and process any 'processed: false' entries using core.py." >> "$LOG" 2>&1
    EC=$?
fi

echo "--- END: $(date) (exit=$EC) ---" >> "$LOG"
exit $EC
