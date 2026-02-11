@echo off
setlocal EnableExtensions

REM 이 배치 파일이 있는 폴더 = E:\CLAUDE_PROJECT\mybot_ver2\
set "BASE=%~dp0"
set "ROOT=%BASE%"
set "SPF=%ROOT%\CLAUDE.md"
set "LOG=%BASE%claude_task.log"
set "LOCKFILE=%ROOT%\mybot_autoexecutor.lock"

REM Claude 실행 파일 경로 자동 탐지 (신형/구형 모두 지원)
set "CLAUDE_EXE="

REM 1. 신버전 (네이티브 설치) - .exe 파일
if exist "%USERPROFILE%\.local\bin\claude.exe" (
    set "CLAUDE_EXE=%USERPROFILE%\.local\bin\claude.exe"
    echo [INFO] Using native Claude CLI: .local\bin\claude.exe>> "%LOG%"
    goto CLAUDE_FOUND
)

REM 2. 구버전 (NPM 설치) - .cmd 파일
if exist "%APPDATA%\npm\claude.cmd" (
    set "CLAUDE_EXE=%APPDATA%\npm\claude.cmd"
    echo [INFO] Using NPM-based Claude CLI: npm\claude.cmd>> "%LOG%"
    goto CLAUDE_FOUND
)

REM 3. 대안 경로들
if exist "%USERPROFILE%\AppData\Local\Programs\claude\claude.exe" (
    set "CLAUDE_EXE=%USERPROFILE%\AppData\Local\Programs\claude\claude.exe"
    echo [INFO] Using alternative Claude CLI: AppData\Local\Programs\claude\claude.exe>> "%LOG%"
    goto CLAUDE_FOUND
)

if exist "%USERPROFILE%\.claude\claude.exe" (
    set "CLAUDE_EXE=%USERPROFILE%\.claude\claude.exe"
    echo [INFO] Using alternative Claude CLI: .claude\claude.exe>> "%LOG%"
    goto CLAUDE_FOUND
)

REM Claude CLI를 찾지 못함
echo [ERROR] Claude CLI not found in any known location:>> "%LOG%"
echo   - %USERPROFILE%\.local\bin\claude.exe (native)>> "%LOG%"
echo   - %APPDATA%\npm\claude.cmd (npm legacy)>> "%LOG%"
echo   - %USERPROFILE%\AppData\Local\Programs\claude\claude.exe>> "%LOG%"
echo   - %USERPROFILE%\.claude\claude.exe>> "%LOG%"
exit /b 99

:CLAUDE_FOUND

echo ===== %date% %time% =====>> "%LOG%"
echo START CWD=%CD%>> "%LOG%"
echo ROOT=%ROOT%>> "%LOG%"

REM ========================================
REM 프로세스 중복 실행 방지 (개선된 이중 안전 장치)
REM ========================================

REM 1. Claude 프로세스 먼저 확인! (실제 진행 중인지 확인)
tasklist /FI "IMAGENAME eq node.exe" 2>NUL | find /I "node.exe" >NUL
if errorlevel 1 goto PROCESS_NOT_FOUND
REM node.exe 있으면 명령줄 확인 (append-system-prompt-file는 autoexecutor 전용 플래그)
wmic process where "name='node.exe'" get commandline 2>NUL | find /I "claude" | find /I "append-system-prompt-file" >NUL
if errorlevel 1 goto PROCESS_NOT_FOUND
REM Claude process found - check if log has been updated in last 10 minutes
powershell -NoProfile -Command "if (Test-Path '%LOG%') { if ((Get-Date) - (Get-Item '%LOG%').LastWriteTime -gt [TimeSpan]::FromMinutes(10)) { exit 1 } else { exit 0 } } else { exit 0 }" >NUL 2>&1
if %ERRORLEVEL% EQU 1 (
    echo [STALE] Claude idle ^>10min. Force-killing...>> "%LOG%"
    wmic process where "name='node.exe' and commandline like '%%claude%%' and commandline like '%%append-system-prompt-file%%'" delete >NUL 2>&1
    if exist "%LOCKFILE%" del "%LOCKFILE%" 2>NUL
    echo [STALE] Cleared stale state. Proceeding...>> "%LOG%"
    goto LOCK_OK
)
echo [BLOCKED] Autoexecutor Claude already running.>> "%LOG%"
exit /b 98
:PROCESS_NOT_FOUND

REM 2. Lock 파일 확인 (프로세스 없는데 Lock 있으면 오류 중단!)
if not exist "%LOCKFILE%" goto LOCK_OK
echo [RECOVERY] Lock file exists but no process running - recovering from error.>> "%LOG%"
del "%LOCKFILE%" 2>NUL
echo [INFO] Stale lock removed.>> "%LOG%"
:LOCK_OK

REM 3. 빠른 메시지 확인 (Python으로 먼저 확인 - 새 메시지 없으면 Claude Code 실행 안 함!)
echo [QUICK_CHECK] Checking for new messages...>> "%LOG%"
pushd "%ROOT%" >NUL 2>&1
python quick_check.py >> "%LOG%" 2>&1
set "CHECK_RESULT=%ERRORLEVEL%"
popd >NUL 2>&1

if %CHECK_RESULT% EQU 0 (
    echo [NO_MESSAGE] No new messages. Exiting.>> "%LOG%"
    echo.>> "%LOG%"
    exit /b 0
)

echo [NEW_MESSAGE] New messages found. Starting Claude Code...>> "%LOG%"

REM 4. Lock 파일 생성 (Claude Code 실행 직전)
echo %date% %time%> "%LOCKFILE%"
echo Lock file created: %LOCKFILE%>> "%LOG%"

pushd "%ROOT%" >> "%LOG%" 2>&1
if errorlevel 1 (
  echo [ERROR] pushd failed.>> "%LOG%"
  exit /b 1
)

echo BEFORE CLAUDE CWD=%CD%>> "%LOG%"

if not exist "%SPF%" (
  echo [ERROR] CLAUDE.md not found: %SPF%>> "%LOG%"
  dir >> "%LOG%" 2>&1
  popd
  exit /b 2
)

call "%CLAUDE_EXE%" --version >> "%LOG%" 2>&1

set DISABLE_AUTOUPDATER=1

REM Try to resume the most recent session first for context continuity
echo [INFO] Attempting to resume most recent session...>> "%LOG%"
call "%CLAUDE_EXE%" -p -c --dangerously-skip-permissions ^
  --append-system-prompt-file "%SPF%" ^
  "텔레그램 메시지를 확인하고 처리할 것. 모든 API는 telegram_bot.py에 있고, 전송은 telegram_sender.py의 send_message_sync()를 사용한다. 새 메시지가 있으면: 1) telegram_bot.check_telegram()으로 확인, 2) telegram_bot.combine_tasks()로 합산, 3) telegram_sender.send_message_sync()로 즉시 답장, 4) telegram_bot.create_working_lock() 호출, 5) telegram_bot.reserve_memory_telegram() 호출, 6) telegram_bot.load_memory()로 메모리 조사, 7) 작업 실행(send_message_sync()로 중간 경과 보고), 8) telegram_bot.report_telegram() 호출, 9) telegram_bot.mark_done_telegram() 호출, 10) telegram_bot.remove_working_lock() 호출. 작업 끝나면, 바로 작업 완료하지 말고, 사용자에게 다음 작업 없는지 물어보고, 물어본 후 카운팅 하여, 3분 후에 텔레그램 새메시지 확인하며, 있으면 그것으로 작업 이어할 것 (이 루틴을 계속하고 사용자가 답변 없거나 종료하자고 하면 즉시 완전 종료) (그리고 텔레그램으로 진행상황 알릴때, 세부적인 진행 방법과 중요 이슈를 함께 알릴 것 (하지만 길지 않게 최대한 요약하여 알릴 것))" ^
  >> "%LOG%" 2>&1

set "EC=%ERRORLEVEL%"

REM If resume fails (no previous session), start a new session
if %EC% NEQ 0 (
  echo [INFO] No previous session found. Starting new session...>> "%LOG%"
  call "%CLAUDE_EXE%" -p --dangerously-skip-permissions ^
    --append-system-prompt-file "%SPF%" ^
    "텔레그램 메시지를 확인하고 처리할 것. 모든 API는 telegram_bot.py에 있고, 전송은 telegram_sender.py의 send_message_sync()를 사용한다. 새 메시지가 있으면: 1) telegram_bot.check_telegram()으로 확인, 2) telegram_bot.combine_tasks()로 합산, 3) telegram_sender.send_message_sync()로 즉시 답장, 4) telegram_bot.create_working_lock() 호출, 5) telegram_bot.reserve_memory_telegram() 호출, 6) telegram_bot.load_memory()로 메모리 조사, 7) 작업 실행(send_message_sync()로 중간 경과 보고), 8) telegram_bot.report_telegram() 호출, 9) telegram_bot.mark_done_telegram() 호출, 10) telegram_bot.remove_working_lock() 호출. 작업 끝나면, 바로 작업 완료하지 말고, 사용자에게 다음 작업 없는지 물어보고, 물어본 후 카운팅 하여, 3분 후에 텔레그램 새메시지 확인하며, 있으면 그것으로 작업 이어할 것 (이 루틴을 계속하고 사용자가 답변 없거나 종료하자고 하면 즉시 완전 종료) (그리고 텔레그램으로 진행상황 알릴때, 세부적인 진행 방법과 중요 이슈를 함께 알릴 것 (하지만 길지 않게 최대한 요약하여 알릴 것))" ^
    >> "%LOG%" 2>&1
  set "EC=%ERRORLEVEL%"
)
echo EXITCODE=%EC%>> "%LOG%"
echo.>> "%LOG%"

REM Lock 파일 삭제
if exist "%LOCKFILE%" (
    del "%LOCKFILE%" 2>NUL
    echo Lock file deleted: %LOCKFILE%>> "%LOG%"
)

popd
exit /b %EC%