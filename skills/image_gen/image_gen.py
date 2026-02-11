"""
all_new_cbot Skill - Image Generation (Tool/Browser Based)

API 과금을 피하기 위해 OpenAI API 호출 대신 Codex의 내장 도구 또는 
브라우저 기반 자동화(Playwright 등)를 사용하도록 권장합니다.
"""

import os
import asyncio

_DIR = os.path.dirname(os.path.abspath(__file__))
GEN_DIR = os.path.join(_DIR, "generated")

if not os.path.exists(GEN_DIR):
    os.makedirs(GEN_DIR)

async def generate_image(prompt: str):
    """
    이 함수는 API 키 없이 이미지를 생성하기 위한 인터페이스입니다.
    Codex가 직접 브라우저를 제어하거나 내장 이미지 생성 도구를 사용하도록 지시하세요.
    """
    # 에이전트가 직접 브라우저를 열어 작업하거나, 다른 MCP 도구를 쓰도록 유도
    return {"error": "Use Codex direct tools or browser for non-billed generation."}

if __name__ == "__main__":
    print("Non-API Image generation interface ready.")
