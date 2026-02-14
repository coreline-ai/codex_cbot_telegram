#!/bin/bash

# codex_cbot_telegram - Codex Executor (macOS/Linux)

ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG="$ROOT/execution.log"
SPF="$ROOT/codex.md"
ROUTER="$ROOT/router.py"
CODEX_EXE=$(which codex)
PYTHON_EXE="${PYTHON_EXE:-python3}"
CODEX_MODEL="${CODEX_MODEL:-gpt-5-codex}"
CODEX_USE_RESUME="${CODEX_USE_RESUME:-0}"
ALLOW_NESTED_CODEX="${ALLOW_NESTED_CODEX:-0}"

cd "$ROOT"

# 0) Safety guard: prevent nested Codex calls from inside an active Codex session.
# This is the most common cause of stream disconnects and "everything died" symptoms.
if [ -n "${CODEX_THREAD_ID:-}" ] && [ "$ALLOW_NESTED_CODEX" != "1" ]; then
  echo "--- START: $(date) ---" >> "$LOG"
  echo "[ERROR] Nested Codex invocation blocked. CODEX_THREAD_ID=$CODEX_THREAD_ID" >> "$LOG"
  echo "[HINT] Run executor.sh from a normal terminal (not inside Codex session), or set ALLOW_NESTED_CODEX=1 if you really need nesting." >> "$LOG"
  echo "--- END: $(date) (exit=21) ---" >> "$LOG"
  exit 21
fi

# 1) Codex CLI existence
if [ -z "$CODEX_EXE" ]; then
  echo "[ERROR] Codex CLI not found. Install: npm install -g @openai/codex" >> "$LOG"
  exit 1
fi

# 2) prevent overlapping runs
# Keep backward compatibility for legacy workspace name while supporting new name.
if pgrep -f "codex.*developer_instructions_file=.*codex.md" > /dev/null || \
   pgrep -f "codex.*all_new_cbot" > /dev/null || \
   pgrep -f "codex.*codex_cbot_telegram" > /dev/null; then
  echo "[SKIP] Codex busy: $(date)" >> "$LOG"
  exit 0
fi

echo "--- START: $(date) ---" >> "$LOG"
export DISABLE_AUTOUPDATER=1

# 3) route from message queue
HAS_TASK="0"
ROUTE="idle"
ROUTE_REASON=""
MESSAGE_ID=""
PROJECT_NAME=""
INSTRUCTION=""
TASK_TYPE=""
TASK_CONFIDENCE=""
DOMAIN_HINT=""
DOMAIN_CONFIDENCE=""
STYLE_HINT=""
DELIVERABLE_HINT=""

if [ -f "$ROUTER" ]; then
  eval "$($PYTHON_EXE "$ROUTER" --format env 2>>"$LOG")"
else
  echo "[WARN] Router not found: $ROUTER" >> "$LOG"
fi

echo "[ROUTER] has_task=$HAS_TASK route=$ROUTE reason=$ROUTE_REASON message_id=$MESSAGE_ID project=$PROJECT_NAME task_type=$TASK_TYPE task_conf=$TASK_CONFIDENCE domain=$DOMAIN_HINT domain_conf=$DOMAIN_CONFIDENCE style=$STYLE_HINT deliverable=$DELIVERABLE_HINT" >> "$LOG"

if [ "$HAS_TASK" != "1" ]; then
  echo "[IDLE] No unprocessed messages. Exit." >> "$LOG"
  echo "--- END: $(date) (exit=0) ---" >> "$LOG"
  exit 0
fi

TASK_PROMPT="Process the first unprocessed message using only core.py APIs and finish with core.mark_as_done."

case "$ROUTE" in
  web_master)
    TASK_PROMPT=$(cat <<EOF
Router selected route=web_master for message_id=$MESSAGE_ID.
Original instruction: "$INSTRUCTION"
Routing hints: task_type=$TASK_TYPE (conf=$TASK_CONFIDENCE), domain=$DOMAIN_HINT (conf=$DOMAIN_CONFIDENCE), style=$STYLE_HINT, deliverable=$DELIVERABLE_HINT.
Use only current contract APIs from core.py:
- allowed: core.check_messages, core.send_message, core.send_photo, core.send_document, core.get_past_memory, core.get_recent_history, core.mark_as_done
- forbidden: telegram_bot.reserve_memory_telegram, telegram_bot.report_telegram, telegram_bot.mark_done_telegram

Transaction contract (mandatory):
1. call core.check_messages and pick the first unprocessed message only
2. send quick ACK via core.send_message
3. understand the natural-language instruction first, then execute:
   python3 skills/web_master/master_orchestrator.py --project "$PROJECT_NAME" --brief "<instruction text with domain/style clarification>"
   - If domain hint exists, preserve it explicitly in brief.
   - For Korean domain terms, add short English anchor words so downstream niche detection is reliable.
   - Example for domain=cafe: include "cafe coffee roastery" in brief context.
4. if long-running, send concise progress updates via core.send_message
5. check generated result aligns with inferred domain intent; if mismatch is visible, regenerate once with corrected brief
6. send major outputs via core.send_document/core.send_photo if files exist
7. call core.mark_as_done(message_id=$MESSAGE_ID, instruction, summary)

Be robust: prioritize semantic intent over literal keyword matching.
Keep output concise and operational.
EOF
)
    ;;
  image_gen)
    TASK_PROMPT=$(cat <<EOF
Router selected route=image_gen for message_id=$MESSAGE_ID.
Original instruction: "$INSTRUCTION"
Routing hints: task_type=$TASK_TYPE (conf=$TASK_CONFIDENCE), domain=$DOMAIN_HINT (conf=$DOMAIN_CONFIDENCE), style=$STYLE_HINT, deliverable=$DELIVERABLE_HINT.
Use only current contract APIs from core.py:
- allowed: core.check_messages, core.send_message, core.send_photo, core.send_document, core.get_past_memory, core.get_recent_history, core.mark_as_done
- forbidden: telegram_bot.reserve_memory_telegram, telegram_bot.report_telegram, telegram_bot.mark_done_telegram

Transaction contract (mandatory):
1. call core.check_messages and pick the first unprocessed message only
2. send quick ACK via core.send_message
3. understand the natural-language instruction first, then execute:
   python3 skills/image_gen/image_gen.py "<instruction text>"
4. if long-running, send concise progress updates via core.send_message
5. if image generation succeeds, send image via core.send_photo with short caption
6. call core.mark_as_done(message_id=$MESSAGE_ID, instruction, summary)

If image_gen execution fails, perform a safe local fallback with canvas_render workflow.
EOF
)
    ;;
  *)
    TASK_PROMPT=$(cat <<EOF
Route=codex_general.
Original instruction: "$INSTRUCTION"
Routing hints: task_type=$TASK_TYPE (conf=$TASK_CONFIDENCE), domain=$DOMAIN_HINT (conf=$DOMAIN_CONFIDENCE), style=$STYLE_HINT.
Use only current contract APIs from core.py and process only the first unprocessed message.
Mandatory sequence: check -> ack -> execute -> progress(optional) -> result send -> core.mark_as_done.
Forbidden API names: telegram_bot.reserve_memory_telegram, telegram_bot.report_telegram, telegram_bot.mark_done_telegram.
Prioritize semantic intent understanding over literal keyword matching.
EOF
)
    ;;
esac

# 4) invoke codex
if [ "$CODEX_USE_RESUME" = "1" ]; then
  $CODEX_EXE resume --last --all --full-auto \
    -m "$CODEX_MODEL" \
    --config developer_instructions_file="$SPF" \
    "$TASK_PROMPT" >> "$LOG" 2>&1
  EC=$?

  if [ $EC -ne 0 ]; then
    echo "[INFO] Resume failed, fallback to exec..." >> "$LOG"
    $CODEX_EXE exec --full-auto \
      -m "$CODEX_MODEL" \
      --config developer_instructions_file="$SPF" \
      "$TASK_PROMPT" >> "$LOG" 2>&1
    EC=$?
  fi
else
  echo "[INFO] Using exec mode (CODEX_USE_RESUME=0)." >> "$LOG"
  $CODEX_EXE exec --full-auto \
    -m "$CODEX_MODEL" \
    --config developer_instructions_file="$SPF" \
    "$TASK_PROMPT" >> "$LOG" 2>&1
  EC=$?
fi

# 5) one-pass domain feedback retry
if [ "$EC" -eq 0 ] && [ "$ROUTE" = "web_master" ] && [ -n "$DOMAIN_HINT" ] && [ "$DOMAIN_HINT" != "general" ]; then
  LAST_NICHE=$(tail -n 400 "$LOG" | grep -i "Identified Niche:" | tail -n 1 | sed -E 's/.*Identified Niche:[[:space:]]*([A-Za-z가-힣-]+).*/\1/')
  EXPECTED=""
  case "$DOMAIN_HINT" in
    cafe) EXPECTED="cafe" ;;
    tech) EXPECTED="tech" ;;
    fashion) EXPECTED="fashion" ;;
    beauty) EXPECTED="beauty" ;;
    food) EXPECTED="food" ;;
    travel) EXPECTED="travel" ;;
    medical) EXPECTED="medical" ;;
    education) EXPECTED="education" ;;
  esac

  if [ -n "$LAST_NICHE" ] && [ -n "$EXPECTED" ]; then
    LAST_NICHE_LC=$(echo "$LAST_NICHE" | tr '[:upper:]' '[:lower:]')
    if [[ "$LAST_NICHE_LC" != *"$EXPECTED"* ]]; then
      echo "[ROUTER_FEEDBACK] Domain mismatch detected. expected=$DOMAIN_HINT detected_niche=$LAST_NICHE. Retrying once..." >> "$LOG"
      RETRY_PROMPT=$(cat <<EOF
Domain-alignment retry requested.
Original instruction: "$INSTRUCTION"
Expected domain hint: "$DOMAIN_HINT"
Previous detected niche from CLI/log: "$LAST_NICHE"

Re-run web generation once with explicit domain anchors.
For domain=cafe, include anchors like: "cafe coffee roastery menu".
Then send corrected result and finalize with core.mark_as_done(message_id=$MESSAGE_ID, instruction, summary).
EOF
)
      $CODEX_EXE exec --full-auto \
        -m "$CODEX_MODEL" \
        --config developer_instructions_file="$SPF" \
        "$RETRY_PROMPT" >> "$LOG" 2>&1
      EC=$?
    fi
  fi
fi

echo "--- END: $(date) (exit=$EC) ---" >> "$LOG"
exit $EC
