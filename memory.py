"""
all_new_cbot - Memory Management (Indexed)

memory.py:
- Fast task indexing
- Keyword-based retrieval
- Context management
"""

import os
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

def update_index(message_id, instruction, result_summary="", files=None):
    """지시사항과 결과를 인덱스에 기록합니다."""
    index = load_index()
    
    # 키워드 추출 (간이)
    keywords = list(set([word for word in instruction.split() if len(word) >= 2]))[:10]
    
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
        
    # 최신순 정렬
    index["tasks"].sort(key=lambda x: x["message_id"], reverse=True)
    save_index(index)
    return task_entry

def search_memory(query):
    """인덱스에서 쿼리와 매칭되는 과거 기록을 검색합니다."""
    index = load_index()
    query_words = query.lower().split()
    results = []
    
    for task in index["tasks"]:
        score = 0
        content = (task["instruction"] + " " + task["summary"]).lower()
        for word in query_words:
            if word in content:
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
    # Test update and search
    update_index(999, "날씨 정보 알려줘", "서울은 맑음입니다.")
    print("Search result:", search_memory("날씨"))
