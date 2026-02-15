# codex_cbot_telegram (macOS)  
### Telegram + Codex 자동화 에이전트 with Web Simulator

![Platform](https://img.shields.io/badge/platform-macOS-black)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Mode](https://img.shields.io/badge/mode-telegram%20%7C%20web_simulator-2ea44f)
![Router](https://img.shields.io/badge/router-NL%20intent-orange)
![Status](https://img.shields.io/badge/status-active-success)

<p align="center">
<img width="1300" height="863" alt="스크린샷 2026-02-15 오후 4 52 21" src="https://github.com/user-attachments/assets/f918b0e8-2d05-40b6-84dc-dcab5bf8672e" />
</p>

Telegram 메시지를 받아 Codex 워크플로를 자동 실행하고, 결과를 다시 Telegram(또는 웹 시뮬레이터)로 반환하는 로컬 자동화 프로젝트입니다.  
핵심은 `messages.json` 큐 기반 처리 + `router.py` 자연어 라우팅 + `executor.sh` 단일 실행 계약입니다.

---

## Table of Contents
- [What It Does](#what-it-does)
- [Architecture](#architecture)
- [Quick Start (macOS)](#quick-start-macos)
- [Run Modes](#run-modes)
- [Environment Variables](#environment-variables)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)

---

## What It Does

### Core Capabilities
- Telegram Long Polling 기반 메시지 수집 (`listener.py`)
- 메시지 큐(`messages.json`)의 미처리 작업 자동 실행
- 자연어 의도 기반 라우팅 (`router.py`)
  - `web_master` (랜딩페이지/웹 패키지 생성)
  - `image_gen` (이미지 생성 파이프라인)
  - `codex_general` (일반 작업)
- Codex 실행 오케스트레이션 (`executor.sh`)
- 전송 채널 추상화 (`core.py`)
  - `telegram` 전송
  - `webmock`(웹 시뮬레이터) 전송
- Telegram 없이 웹에서 E2E 테스트 가능한 시뮬레이터
  - FastAPI 서버: `simulator_messenger_server.py`
  - UI: `web_simulator/`
  - TUI 런처: `scripts/web_simulator_tui.py`

### Why This Project
- 반복적인 Telegram 요청 처리 자동화
- 웹/이미지 제작 요청을 라우팅해 표준화된 파이프라인 실행
- 실제 Telegram 없이도 로컬 웹 UI에서 빠른 통합 테스트 가능

---

## Architecture

```text
Telegram or Web UI
        |
        v
  messages.json (queue)
        |
        v
   listener.py / API trigger
        |
        v
     executor.sh
        |
        v
      router.py  ---> route=web_master|image_gen|codex_general
        |
        v
      codex exec
        |
        v
       core.py (send_message/send_photo/send_document/mark_as_done)
        |
        +--> Telegram API
        |
        +--> web_outbox.json -> simulator_messenger_server.py -> Web UI
```

---

## Quick Start (macOS)

### 1) Install
```bash
git clone <your-repo-url>
cd codex_cbot_telegram
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m pip install fastapi uvicorn
python3 -m playwright install chromium
cp .env.example .env
```

또는 스크립트 사용:

```bash
bash setup_macos.sh
```

### 2) Configure `.env`
필수:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_ALLOWED_USERS`

### 3) Run
Telegram 모드:
```bash
python3 listener.py
```

---

## Run Modes

### A) Telegram Mode (default)
- 입력: Telegram
- 출력: Telegram
- 실행:
```bash
python3 listener.py
```

### B) Web Simulator Mode (Telegram 대체 테스트)
`.env` 예시:
```env
MESSAGE_CHANNEL=webmock
RUN_MODE=webmock
```

실행:
```bash
python3 -m uvicorn simulator_messenger_server:app --host 127.0.0.1 --port 8080 --reload
```

접속:
- `http://127.0.0.1:8080`

TUI 런처(권장):
```bash
python3 scripts/web_simulator_tui.py
```

TUI 단축키:
- `s` 서버 시작
- `x` 서버 중지
- `r` 재시작
- `t` 테스트 메시지 전송
- `q` 종료

---

## Environment Variables

주요 변수만 정리했습니다. 전체 목록은 `.env.example` 참고.

| Key | Default | Description |
|---|---:|---|
| `TELEGRAM_BOT_TOKEN` | - | Telegram BotFather 토큰 |
| `TELEGRAM_ALLOWED_USERS` | - | 허용 사용자 ID(쉼표 구분) |
| `TELEGRAM_POLLING_INTERVAL` | `10` | 폴링 간격(초) |
| `RUN_MODE` | `telegram` | `telegram` 또는 `webmock` |
| `MESSAGE_CHANNEL` | `telegram` | 전송 채널(`telegram`, `webmock`) |
| `MACOS_STRICT_MODE` | `0` | `1`이면 bash+executor 경로만 허용 |
| `CODEX_MODEL` | `gpt-5-codex` | Codex 실행 모델 |
| `IMAGE_GEN_PROVIDER` | `auto` | `codex_cli`/`sd_webui`/`stock`/`canvas` |
| `WEB_PREVIEW_BASE_URL` | `http://127.0.0.1:8080/api/files` | 생성 웹 결과 미리보기 base URL |
| `WEB_DIVERSITY_MODE` | `balanced` | 레이아웃/디자인 다양성 강도 |

---

## Testing

### Unit + Integration
```bash
pytest -q
```

웹 시뮬레이터 관련만:
```bash
pytest -q tests/test_web_simulator_messenger.py
```

다양성 라우팅/변형 테스트:
```bash
pytest -q tests/test_web_variator_diversity.py
```

### Realism Smoke (strict photoreal)
```bash
python3 scripts/run_realism_smoke.py \
  --project live-test-shoppingmall-real \
  --brief "쇼핑몰 랜딩 페이지 만들어줘"
```

산출물:
- `test_runs/realism_smoke_*.log`
- `test_runs/realism_smoke_*.json`

---

## Project Structure

```text
.
├── core.py                         # 채널 추상화 + 메시지/파일 전송 + 작업 상태 관리
├── listener.py                     # Telegram long polling 리스너
├── telegram_bot.py                 # 큐 기반 에이전트 루프
├── router.py                       # 자연어 라우터 (task/domain/style)
├── executor.sh                     # Codex 실행 진입점
├── simulator_messenger_server.py   # FastAPI 웹 시뮬레이터 서버
├── web_simulator/                  # 시뮬레이터 프론트엔드
├── skills/                         # web_master, image_gen 등 스킬 파이프라인
├── scripts/
│   ├── web_simulator_tui.py        # TUI 서버 제어기
│   └── run_realism_smoke.py        # 실사 품질 smoke 테스트
├── tests/                          # 라우터/스킬/시뮬레이터 테스트
└── docs/                           # 구현 계획/런북 문서
```

---

## Troubleshooting

### 1) 웹에서 응답이 안 올 때
- `.env`에 `MESSAGE_CHANNEL=webmock`, `RUN_MODE=webmock` 설정 확인
- `execution.log` 마지막 로그 확인
- `working.json`에서 stuck 상태인지 확인

### 2) `codex` 명령을 못 찾을 때
- Codex CLI 설치:
```bash
npm install -g @openai/codex
codex login
```

### 3) Playwright 관련 오류
- 브라우저 재설치:
```bash
python3 -m playwright install chromium
```

### 4) 포트 충돌 (`8080`)
```bash
lsof -i :8080
kill -9 <PID>
```
또는 다른 포트 사용:
```bash
python3 -m uvicorn simulator_messenger_server:app --host 127.0.0.1 --port 8090
```

---

실행 상세 문서:
- `docs/web_simulator_messenger_runbook.md`
- `docs/web_simulator_messenger_implementation_plan.md`
