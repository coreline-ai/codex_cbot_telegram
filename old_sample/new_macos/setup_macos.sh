#!/bin/bash

# new_macos 프로젝트 초기 설정 스크립트

echo "🚀 macOS용 소놀봇(new_macos) 설정을 시작합니다."

# 1. 폴더 이동
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# 2. 권한 부여
chmod +x mybot_autoexecutor.sh
echo "✅ 실행 권한 부여 완료."

# 3. Python 의존성 설치
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt
    echo "✅ Python 라이브러리 설치 완료."
fi

# 4. .env 확인
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "⚠️  .env 파일을 생성했습니다. 봇 토큰과 사용자 ID를 설정해 주세요."
    fi
fi

echo ""
echo "🎉 모든 설정이 완료되었습니다!"
echo "실행 방법: python3 telegram_listener.py"
echo "------------------------------------------------"
