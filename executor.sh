#!/bin/bash

# all_new_cbot - Codex Executor (OAuth Optimized for macOS)

ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG="$ROOT/execution.log"
CODEX_EXE=$(which codex)

cd "$ROOT"

# 1. 프로세스 중복 실행 체크
if pgrep -f "codex.*all_new_cbot" > /dev/null; then
    echo "[SKIP] Codex busy: $(date)" >> "$LOG"
    exit 0
fi

echo "--- START: $(date) ---" >> "$LOG"

# 2. 코덱스 가동 (v0.77.0 이상: --full-auto, --skip-git-repo-check 사용)
# --full-auto: 중단 없는 작업 수행
# --skip-git-repo-check: 보안 체크 건너뛰기
$CODEX_EXE resume --last --all --full-auto --skip-git-repo-check \
  --config developer_instructions_file="$ROOT/codex.md" \
  "Check messages.json and process any 'processed: false' entries using core.py." >> "$LOG" 2>&1

if [ $? -ne 0 ]; then
    # 세션이 없을 경우 새로 시작
    $CODEX_EXE exec --full-auto --skip-git-repo-check --search \
      --config developer_instructions_file="$ROOT/codex.md" \
      "Check messages.json and process any 'processed: false' entries using core.py." >> "$LOG" 2>&1
fi
