# Web Simulator Messenger 실행 가이드

## 1) 설치
```bash
python3 -m pip install -r requirements.txt
```

## 2) 환경 변수
`.env`에 아래 값을 설정합니다.

```env
MESSAGE_CHANNEL=webmock
RUN_MODE=webmock
```

기존 Telegram 모드로 복귀하려면:

```env
MESSAGE_CHANNEL=telegram
RUN_MODE=telegram
```

## 3) 서버 실행
```bash
uvicorn simulator_messenger_server:app --host 127.0.0.1 --port 8080 --reload
```

브라우저에서 `http://127.0.0.1:8080` 접속.

### TUI 런처(권장)
```bash
python3 scripts/web_simulator_tui.py
```

- `s`: 서버 시작
- `x`: 서버 중지
- `r`: 서버 재시작
- `t`: 테스트 메시지 전송(`/api/messages`)
- `q`: 종료(서버도 함께 정리)

## 4) 동작 흐름
1. 웹 UI에서 메시지 전송
2. `messages.json`에 `processed: false`로 저장
3. `executor.sh` 트리거
4. Codex 작업 결과를 `core.py`가 `web_outbox.json`에 기록
5. UI가 `/api/messages` 폴링으로 결과 표시

### 웹 제어 버튼
- `재처리`: `/api/control/retrigger` 호출로 워커 재트리거
- `테스트 메시지`: `/api/control/test-message` 호출
- `워커 중지`: `/api/control/stop-worker` 호출

## 5) 트러블슈팅
- 포트 충돌: `--port` 값을 변경하세요.
- 결과가 안 보임: `MESSAGE_CHANNEL=webmock`인지 확인하세요.
- 작업이 멈춤: `working.json`, `execution.log` 마지막 줄을 확인하세요.
- 실행 파일 오류: `executor.sh` 실행 권한과 `codex` 설치 상태를 확인하세요.
