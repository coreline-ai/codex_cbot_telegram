#!/usr/bin/env python3
"""
Natural-language aware router for deterministic Codex task dispatch.

This router preserves original instruction text, extracts intent/domain hints,
and outputs shell-friendly env vars for executor.sh.
"""

import argparse
import json
import os
import re
import shlex
from typing import Dict, Tuple

_DIR = os.path.dirname(os.path.abspath(__file__))
MESSAGES_FILE = os.path.join(_DIR, "messages.json")


WEB_KEYWORDS = [
    "웹", "웹사이트", "사이트", "랜딩", "랜딩페이지", "페이지", "홈페이지",
    "website", "web site", "webpage", "web page", "landing", "landing page",
    "html", "css", "프론트", "frontend", "ui",
]

IMAGE_KEYWORDS = [
    "이미지", "그림", "사진", "일러스트", "포스터", "로고", "배너", "썸네일",
    "렌더", "렌더링", "icon", "image", "poster", "logo", "thumbnail",
]

WEB_STRONG = ["웹", "웹사이트", "사이트", "랜딩", "페이지", "홈페이지", "website", "landing", "web", "html"]
IMAGE_STRONG = ["이미지", "그림", "렌더", "렌더링", "포스터", "로고", "image", "render", "poster", "logo"]

DOMAIN_KEYWORDS = {
    "cafe": ["카페", "커피", "coffee", "cafe", "roastery", "brew", "브루", "원두"],
    "fashion": ["패션", "의류", "옷", "fashion", "apparel", "lookbook"],
    "tech": ["테크", "기술", "saas", "ai", "software", "startup", "테크놀로지"],
    "beauty": ["뷰티", "화장품", "스킨케어", "beauty", "cosmetic", "skincare"],
    "food": ["음식", "레스토랑", "food", "restaurant", "menu", "맛집"],
    "realestate": ["부동산", "아파트", "분양", "real estate", "property", "realtor"],
    "education": ["교육", "학원", "강의", "education", "course", "academy"],
    "travel": ["여행", "호텔", "tour", "travel", "resort", "trip"],
    "medical": ["병원", "의원", "클리닉", "medical", "clinic", "health"],
}

STYLE_KEYWORDS = {
    "minimal": ["미니멀", "minimal", "clean", "심플"],
    "dark": ["다크", "dark", "moody", "어두운"],
    "premium": ["고급", "프리미엄", "premium", "luxury", "럭셔리"],
    "playful": ["발랄", "playful", "fun", "귀여운"],
    "modern": ["모던", "modern", "세련", "trendy"],
}


def load_messages() -> Dict:
    if not os.path.exists(MESSAGES_FILE):
        return {"messages": [], "last_update_id": 0}
    try:
        with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"messages": [], "last_update_id": 0}


def first_unprocessed_message() -> Dict:
    data = load_messages()
    for msg in data.get("messages", []):
        if not msg.get("processed"):
            return msg
    return {}


def _contains_any(text: str, words) -> bool:
    return any(w in text for w in words)


def detect_task_type(instruction: str) -> Tuple[str, str, float]:
    text = (instruction or "").strip().lower()
    if not text:
        return "general", "empty_instruction", 0.0

    has_web = _contains_any(text, WEB_KEYWORDS)
    has_image = _contains_any(text, IMAGE_KEYWORDS)

    web_score = sum(1 for w in WEB_KEYWORDS if w in text)
    image_score = sum(1 for w in IMAGE_KEYWORDS if w in text)

    if has_web and not has_image:
        conf = min(0.99, 0.60 + (web_score * 0.05))
        return "web_page", "web_keywords_detected", conf
    if has_image and not has_web:
        conf = min(0.99, 0.60 + (image_score * 0.05))
        return "image_asset", "image_keywords_detected", conf

    if has_web and has_image:
        # In mixed cases prioritize deliverable semantics:
        # if page-like words are present, route to web page generation.
        if _contains_any(text, WEB_STRONG) and not _contains_any(text, ["아이콘", "icon", "로고", "logo"]):
            conf = min(0.95, 0.58 + (web_score * 0.04))
            return "web_page", "mixed_keywords_pref_web", conf
        if _contains_any(text, IMAGE_STRONG):
            conf = min(0.95, 0.58 + (image_score * 0.04))
            return "image_asset", "mixed_keywords_pref_image", conf
        return "web_page", "mixed_keywords_default_web", 0.62

    return "general", "no_route_keyword", 0.35


def detect_domain(instruction: str) -> Tuple[str, str, float]:
    text = (instruction or "").strip().lower()
    if not text:
        return "general", "empty_instruction", 0.0

    best_domain = "general"
    best_score = 0
    for domain, words in DOMAIN_KEYWORDS.items():
        score = sum(1 for w in words if w in text)
        if score > best_score:
            best_domain = domain
            best_score = score

    if best_domain == "general":
        return "general", "no_domain_keyword", 0.2

    conf = min(0.98, 0.55 + (best_score * 0.08))
    return best_domain, "domain_keywords_detected", conf


def detect_style(instruction: str) -> str:
    text = (instruction or "").strip().lower()
    for style, words in STYLE_KEYWORDS.items():
        if _contains_any(text, words):
            return style
    return "auto"


def map_task_to_route(task_type: str) -> str:
    if task_type == "web_page":
        return "web_master"
    if task_type == "image_asset":
        return "image_gen"
    return "codex_general"


def slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return slug[:max_len] or "project"


def build_route_payload(msg: Dict) -> Dict[str, str]:
    if not msg:
        return {
            "HAS_TASK": "0",
            "ROUTE": "idle",
            "ROUTE_REASON": "no_unprocessed_message",
            "MESSAGE_ID": "",
            "CHAT_ID": "",
            "PROJECT_NAME": "",
            "INSTRUCTION": "",
            "TASK_TYPE": "",
            "TASK_CONFIDENCE": "",
            "DOMAIN_HINT": "",
            "DOMAIN_CONFIDENCE": "",
            "STYLE_HINT": "",
            "DELIVERABLE_HINT": "",
        }

    instruction = (msg.get("text") or "").strip()
    task_type, reason, task_conf = detect_task_type(instruction)
    domain_hint, _, domain_conf = detect_domain(instruction)
    style_hint = detect_style(instruction)
    route = map_task_to_route(task_type)
    message_id = str(msg.get("message_id", ""))

    base_name = slugify(instruction)
    domain_tag = domain_hint if domain_hint and domain_hint != "general" else "project"
    project_name = f"msg-{message_id}-{domain_tag}-{base_name}" if message_id else f"msg-{domain_tag}-{base_name}"
    deliverable_hint = "web_page" if route == "web_master" else ("image_asset" if route == "image_gen" else "general")

    return {
        "HAS_TASK": "1",
        "ROUTE": route,
        "ROUTE_REASON": reason,
        "MESSAGE_ID": message_id,
        "CHAT_ID": str(msg.get("chat_id", "")),
        "PROJECT_NAME": project_name,
        "INSTRUCTION": instruction,
        "TASK_TYPE": task_type,
        "TASK_CONFIDENCE": f"{task_conf:.2f}",
        "DOMAIN_HINT": domain_hint,
        "DOMAIN_CONFIDENCE": f"{domain_conf:.2f}",
        "STYLE_HINT": style_hint,
        "DELIVERABLE_HINT": deliverable_hint,
    }


def print_env(payload: Dict[str, str]) -> None:
    for key, value in payload.items():
        print(f"{key}={shlex.quote(str(value))}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Route first unprocessed message.")
    parser.add_argument("--format", choices=["env", "json"], default="env")
    parser.add_argument("--text", help="Optional direct text for dry-run routing")
    parser.add_argument("--message-id", default="0", help="Optional message id for --text mode")
    args = parser.parse_args()

    if args.text is not None:
        task_type, reason, task_conf = detect_task_type(args.text)
        domain_hint, _, domain_conf = detect_domain(args.text)
        style_hint = detect_style(args.text)
        route = map_task_to_route(task_type)
        payload = {
            "HAS_TASK": "1",
            "ROUTE": route,
            "ROUTE_REASON": reason,
            "MESSAGE_ID": str(args.message_id),
            "CHAT_ID": "",
            "PROJECT_NAME": f"msg-{args.message_id}-{domain_hint if domain_hint != 'general' else 'project'}-{slugify(args.text)}",
            "INSTRUCTION": args.text.strip(),
            "TASK_TYPE": task_type,
            "TASK_CONFIDENCE": f"{task_conf:.2f}",
            "DOMAIN_HINT": domain_hint,
            "DOMAIN_CONFIDENCE": f"{domain_conf:.2f}",
            "STYLE_HINT": style_hint,
            "DELIVERABLE_HINT": "web_page" if route == "web_master" else ("image_asset" if route == "image_gen" else "general"),
        }
    else:
        payload = build_route_payload(first_unprocessed_message())

    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print_env(payload)


if __name__ == "__main__":
    main()
