"""
codex_cbot_telegram - Memory Management (Indexed)

memory.py:
- Fast task indexing
- Keyword-based retrieval (cleaned tokens)
- Context management
"""

import os
import re
import json
from datetime import datetime

_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_FILE = os.path.join(_DIR, "index.json")
MEM_DIR = os.path.join(_DIR, "memory")

if not os.path.exists(MEM_DIR):
    os.makedirs(MEM_DIR)

def load_index():
    if os.path.exists(INDEX_FILE):
        try:
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {"tasks": []}

def save_index(data):
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _clean_token(word):
    """구두점·따옴표 제거하여 깨끗한 토큰 반환"""
    # Keep Korean/English letters and digits only for stable multilingual tokenization.
    return re.sub(r"[^0-9A-Za-z가-힣]", "", word)

def _extract_keywords(text):
    """텍스트에서 유의미한 키워드를 추출합니다."""
    # Multilingual keyword extraction: Korean/English words and numbers.
    tokens = re.findall(r"[0-9A-Za-z가-힣]{2,}", text or "")
    # 2글자 이상, 중복 제거, 최대 15개
    seen = set()
    keywords = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            keywords.append(t)
        if len(keywords) >= 15:
            break
    return keywords

def update_index(message_id, instruction, result_summary="", files=None):
    """지시사항과 결과를 인덱스에 기록합니다."""
    index = load_index()

    keywords = _extract_keywords(instruction)

    task_entry = {
        "message_id": message_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "instruction": instruction,
        "keywords": keywords,
        "summary": result_summary,
        "files": files or []
    }

    # 기존 항목 업데이트 또는 새 항목 추가
    updated = False
    for i, t in enumerate(index["tasks"]):
        if t["message_id"] == message_id:
            index["tasks"][i] = task_entry
            updated = True
            break

    if not updated:
        index["tasks"].append(task_entry)

    # timestamp 기준 최신순 정렬
    index["tasks"].sort(key=lambda x: x["timestamp"], reverse=True)
    save_index(index)
    return task_entry

def search_memory(query):
    """인덱스에서 쿼리와 매칭되는 과거 기록을 검색합니다."""
    index = load_index()
    query_tokens = [t.lower() for t in re.findall(r"[0-9A-Za-z가-힣]{2,}", query or "")]
    results = []

    # Fallback for edge cases where tokenizer yields nothing (symbols-only input etc.).
    query_fallback = (query or "").strip().lower()

    for task in index["tasks"]:
        score = 0
        # 키워드 완전 일치 (가중치 2)
        task_keywords_lower = [k.lower() for k in task.get("keywords", [])]
        for qt in query_tokens:
            if qt in task_keywords_lower:
                score += 2

        # instruction + summary 내 포함 (가중치 1)
        content = (task["instruction"] + " " + task["summary"]).lower()
        for qt in query_tokens:
            if qt in content:
                score += 1

        if score == 0 and query_fallback and query_fallback in content:
            score += 1

        if score > 0:
            results.append((score, task))

    # 관련성 점수 높은 순으로 반환
    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results[:5]]

def get_recent_context(limit=3):
    """최근 작업 이력을 반환합니다."""
    index = load_index()
    return index["tasks"][:limit]

if __name__ == "__main__":
    # Test
    update_index(999, "날씨 정보 알려줘", "서울은 맑음입니다.")
    print("Search result:", search_memory("날씨"))
