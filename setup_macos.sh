#!/bin/bash

# codex_cbot_telegram - macOS 초기 설정 스크립트

echo "🚀 codex_cbot_telegram macOS 설정을 시작합니다."

# 1. 폴더 이동
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# 2. 실행 권한 부여
chmod +x executor.sh
echo "✅ executor.sh 실행 권한 부여 완료."

# 3. Python 의존성 설치
if [ -f "requirements.txt" ]; then
    echo "📦 Python 라이브러리 설치 중..."
    pip3 install -r requirements.txt
    echo "✅ Python 라이브러리 설치 완료."
fi

# 4. Playwright 브라우저 설치 (image_gen, web_recon용)
echo "🌐 Playwright Chromium 설치 중..."
python3 -m playwright install chromium
echo "✅ Playwright Chromium 설치 완료."

# 5. .env 파일 확인
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "⚠️  .env 파일을 생성했습니다."
        echo "   → TELEGRAM_BOT_TOKEN 과 TELEGRAM_ALLOWED_USERS 를 설정해 주세요."
        echo "   → 편집: nano .env"
    fi
else
    echo "✅ .env 파일 이미 존재합니다."
fi

# 6. memory 폴더 확인
mkdir -p memory
echo "✅ memory/ 폴더 확인."

echo ""
echo "🎉 모든 설정이 완료되었습니다!"
echo "================================================"
echo "  리스너 실행: python3 listener.py"
echo "  봇 직접 실행: python3 telegram_bot.py"
echo "================================================"
