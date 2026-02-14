# macOS Native Codex & Telegram Bot Integration Plan

현재 윈도우 기반의 '주기적 폴링' 방식을 개선하여, macOS에서 최적화된 작동을 보장하면서 **실시간 응답(Long Polling)**이 가능한 시스템으로 정교화합니다.

## 핵심 개선 전략

1. **macOS 네이티브 최적화**: PowerShell 의존성을 완전히 제거하고 standard POSIX shell (`sh`)과 `codex` CLI 직접 호출 방식으로 전환.
2. **실시간 텔레그램 연동 (Long Polling)**: `getUpdates` API의 `timeout` 옵션을 활용하여 메시지 발생 즉시 캐치.
3. **이벤트 기반 핸들러**: `telegram_bot.py`가 메시지를 수신하면 `subprocess`를 통해 `codex`를 즉시 기동하여 응답 지연 최소화.
4. **서비스 상주 (Launchd)**: macOS의 `launchd`를 통해 백그라운드 서비스로 등록하여 자동 재시작 및 안정성 확보.

---

## Proposed Changes

### [Component 1] 텔레그램 봇 리스너 (Bot Listener Refinement)

#### [MODIFY] [telegram_bot.py](file:///d:/project_new/cbot_desktop/cbot/codex_cbot_telegram/telegram_bot.py)
- **플랫폼 독립적 실행**: Windows 전용 `powershell` 명령어를 삭제하고 `codex exec`를 직접 호출하도록 수정.
- **실시간성 강화**: 폴링 간격을 최적화하거나 `python-telegram-bot`의 `Updater` 패턴을 고려하여 즉시 응답 체계 구축.
- **에러 핸들링**: macOS 환경에서의 권한 문제나 CLI 연결 실패 시 재시도 로직 강화.

### [Component 2] macOS 전용 실행기 (Shell Executor)

#### [MODIFY] [executor.sh](file:///d:/project_new/cbot_desktop/cbot/codex_cbot_telegram/executor.sh)
- **환경 변수 준수**: `APPDATA`, `USERPROFILE` 등 윈도우 전용 변수 배제 및 macOS 표준 경로 사용.
- **프로세스 제어**: `pgrep`을 활용하여 중복 실행 방지 및 효율적인 상주 관리.
- **Codex Mandate**: `codex.md`의 지침을 엄격히 준수하도록 실행 인자 최적화.

### [Component 3] 시스템 자동화 (macOS Automation)

#### [NEW] `setup_macos.sh`
- macOS 환경에서의 실행 권한(`chmod +x`) 부여, 환경 변수(`.env`) 설정 및 `codex` CLI 연결 확인을 수행하는 통합 설치 스크립트.

#### [NEW] `com.cbot.agent.plist` (Template)
- macOS의 `launchd`를 위한 설정 파일로, 부팅 시 자동 실행 및 장애 시 자동 복구 기능을 제공.

---

## Verification Plan

### Automated Tests
1. **CLI 직접 실행 테스트**: `sh executor.sh` 실행 시 `codex`가 정상적으로 `messages.json`을 읽고 처리하는지 확인.
2. **Dispatch 속도 테스트**: 텔레그램 메시지 인식 후 `codex exec` 시작까지의 지연 시간 측정 (목표 0.5초 이내).

### Manual Verification
- macOS 터미널에서 `top` 또는 `ps` 명령어로 봇 프로세스가 안정적으로 상주하고 있는지 확인.
- 실시간 텔레그램 전송을 통해 명령어가 즉각적으로 Codex CLI로 전달되는지 확인.
