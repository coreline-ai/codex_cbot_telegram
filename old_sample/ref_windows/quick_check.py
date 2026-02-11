#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
빠른 텔레그램 메시지 확인 (Claude Code 실행 전)

Exit Codes:
  0: 새 메시지 없음 (즉시 종료)
  1: 새 메시지 있음 (Claude Code 실행 필요)
  2: 다른 작업 진행 중 (working.json 잠금)
"""

import os
import sys

# 프로젝트 루트로 이동 (스크립트 위치 기반 - 어디든 작동!)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

from telegram_bot import check_telegram

try:
    # 새 메시지 확인 (working.json도 자동으로 확인됨)
    pending = check_telegram()

    if not pending:
        # 새 메시지 없음 또는 다른 작업 진행 중
        # check_telegram()이 빈 리스트 반환 시 = 새 메시지 없음
        sys.exit(0)

    # 새 메시지 있음
    print(f"📨 새 메시지 {len(pending)}개 발견!")
    sys.exit(1)

except Exception as e:
    print(f"⚠️ 오류: {e}")
    # 오류 발생 시에도 0 반환 (다음 주기에 재시도)
    sys.exit(0)
