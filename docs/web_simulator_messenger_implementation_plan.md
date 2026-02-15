# Web Simulator Messenger (Telegram-like) 구현 상세 계획

## 상태 표기 규칙
- 진행 전: `- [ ] 작업명`
- 완료 후: `- [x] 작업명 (완료)`
- 이 문서는 작업 진행에 따라 체크박스를 갱신한다.

## 목표
- 실제 Telegram 없이도 기존 파이프라인(`messages.json` -> `router.py` -> `executor.sh` -> `core.py`)을 테스트 가능하게 만든다.
- 웹 UI에서 Telegram과 유사한 UX(메시지 송수신, 진행상황, 파일/이미지 결과)를 제공한다.

## 범위
- 포함:
  - `webmock` 전송 채널 추가
  - 웹 API 서버(FastAPI) 추가
  - Telegram 유사 웹 채팅 UI 추가
  - 상태/결과 파일 조회 API 추가
  - 테스트(단위 + 통합) 추가
- 제외:
  - 실제 Telegram Bot API 대체
  - 인증/권한 고도화(내부 테스트 용도)

## 구현 단계 체크리스트

### 0) 기획/기본 구조
- [x] 구현 상세 계획 문서 생성 (완료)
- [x] 파일/모듈 경로 확정 (`simulator_messenger_server.py`, `web_simulator/`, `web_outbox.json`) (완료)
- [x] 환경변수 설계 확정 (`MESSAGE_CHANNEL`, `RUN_MODE`) (완료)

### 1) 채널 추상화 (`core.py`)
- [x] `MESSAGE_CHANNEL=telegram|webmock` 분기 추가 (완료)
- [x] `send_message`의 `webmock` 저장 구현 (`web_outbox.json`) (완료)
- [x] `send_photo`의 `webmock` 저장 구현 (파일 경로 + caption 기록) (완료)
- [x] `send_document`의 `webmock` 저장 구현 (파일 경로 + caption 기록) (완료)
- [x] 기존 Telegram 동작 회귀 없도록 기본값 `telegram` 유지 (완료)

### 2) 웹 API 서버
- [x] `POST /api/messages`: 웹 입력 메시지를 `messages.json`에 적재 (완료)
- [x] `GET /api/messages`: 인바운드(`messages.json`) + 아웃바운드(`web_outbox.json`) 병합 조회 (완료)
- [x] `GET /api/status`: `working.json` + 최근 로그/진행 상태 반환 (완료)
- [x] `GET /api/files/{name}`: 결과 파일 다운로드/미리보기 제공 (완료)
- [x] 최소 에러 처리(파일 없음, JSON 파싱 실패) 추가 (완료)

### 3) Telegram-like 웹 UI
- [x] `web_simulator/index.html` 채팅 레이아웃 구현 (완료)
- [x] `web_simulator/app.js` 메시지 전송/조회 폴링 구현 (완료)
- [x] 진행 상태 메시지 버블(예: running, step update) 표시 (완료)
- [x] 이미지/문서 결과 카드 렌더링 구현 (완료)
- [x] 모바일/데스크톱 기본 반응형 확인 (완료)

### 4) 실행 모드 연결
- [x] `RUN_MODE=webmock`에서 Telegram polling 없이 처리 루프 동작 연결 (완료)
- [x] `executor.sh` 기반 처리 흐름 유지 확인 (완료)
- [x] 웹 메시지 생성 -> 작업 처리 -> 완료 마킹까지 E2E 연결 (완료)

### 5) 테스트
- [x] 단위 테스트: `core.py` webmock 채널 저장 검증 (완료)
- [x] 단위 테스트: API 엔드포인트 입출력 검증 (완료)
- [x] 통합 테스트: 메시지 적재 -> 처리 -> 결과 반영 검증 (완료)
- [x] 회귀 테스트: 기존 `pytest` 스위트 전부 통과 (완료)

### 6) 문서/운영
- [x] 실행 방법 문서 추가 (`docs/web_simulator_messenger_runbook.md`) (완료)
- [x] `.env.example`에 webmock 관련 변수 추가 (완료)
- [x] 트러블슈팅(포트 충돌, 파일 권한, stale lock) 문서화 (완료)

### 7) 안정성 보강
- [x] 웹 채팅 이력 영속 파일(`web_chat_history.json`) 추가로 소스 큐 초기화/경합 시 대화 이력 보존 (완료)
- [x] `messages.json`/`web_outbox.json` 갱신 경로에 파일 잠금 + 원자 저장 적용 (완료)
- [x] 이력 머지 시 상태 변경(`processed`) 반영되도록 동기화 로직 보강 (완료)

## 완료 기준 (Definition of Done)
- [x] Telegram 토큰 없이 웹에서 메시지 전송/응답 확인 가능 (완료)
- [x] 진행상황과 결과 파일(이미지/문서)이 웹 UI에 표시됨 (완료)
- [x] 기존 Telegram 모드 회귀 없음 (완료)
- [x] 테스트 통과 및 실행 문서 제공 (완료)
