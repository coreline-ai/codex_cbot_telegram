# Codex System Instructions (macOS)

이 문서는 Codex CLI가 텔레그램 기반 자율 작업 시스템을 이해하고 올바르게 작동하기 위한 지침서입니다.

## 시스템 개요
- **목적**: 텔레그램 메시지를 수신하여 자율적으로 작업을 수행하고 결과를 보고함.
- **핵심 모듈**:
    - `telegram_bot.py`: 통합 봇 엔진 (check_telegram, report_telegram 등)
    - `telegram_sender.py`: 메시지/파일 전송 (send_message_sync, send_files_sync)
    - `telegram_listener.py`: 실시간 메시지 수집 및 트리거

## Codex 작업 가이드라인
1. **자율성**: `--approval-mode full-auto` 환경에서 작동하며, 사용자의 명시적 승인 없이도 파일 수정 및 명령 실행을 완수해야 함.
2. **API 활용**:
    - `telegram_bot.check_telegram()`로 새 메시지 확인.
    - 작업 진행 중에는 `telegram_sender.send_message_sync()`로 중간 상황 보고.
    - 작업 완료 시 `telegram_bot.report_telegram(instruction, result_text, ...)`를 반드시 호출하여 사용자에게 파일과 결과를 전송.
    - 마지막에 `telegram_bot.mark_done_telegram(message_id)`로 처리 완료 마킹.
3. **샌드박스 인식**: macOS Seatbelt 샌드박스 내에서 작동하므로, 부여된 워크스페이스 권한 내에서만 파일을 제어함.
4. **연속성**: `codex resume --last`를 통해 이전 대화 맥락이 유지되므로 불필요한 초기화 없이 작업을 이어감.

## 보안 및 규칙
- `.env` 파일의 토큰을 외부에 노출하지 말 것.
- 모든 작업 결과물은 사용자에게 텔레그램으로 투명하게 보고할 것.
