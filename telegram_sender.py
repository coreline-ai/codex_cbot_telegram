"""
텔레그램 응답 전송기 (Sender) - Cross-Platform

역할:
- core.py의 async 전송 함수를 sync로 래핑
- 텍스트 메시지, 사진, 파일 전송
- 이벤트 루프 충돌 방지 (ThreadPoolExecutor 폴백)

사용법:
    from telegram_sender import send_message_sync, send_photo_sync, send_files_sync

    send_message_sync(chat_id, "메시지 내용")
    send_photo_sync(chat_id, "photo.png", "캡션")
    send_files_sync(chat_id, "메시지", ["file1.txt", "file2.png"])
"""

import os
import asyncio
import core


def run_async_safe(coro):
    """이벤트 루프가 이미 실행 중이면 별도 스레드에서 실행"""
    try:
        asyncio.get_running_loop()
        # 루프가 실행 중 → 별도 스레드에서 새 루프 생성
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    except RuntimeError:
        # 실행 중인 루프 없음 → 직접 실행
        return asyncio.run(coro)


def send_message_sync(chat_id, text, parse_mode="Markdown"):
    """
    동기 방식 메시지 전송

    메시지 전송 성공 시 working.json의 last_activity도 갱신합니다.
    """
    try:
        result = run_async_safe(core.send_message(chat_id, text, parse_mode))
    except Exception as e:
        print(f"❌ [SENDER] Error sending message: {e}")
        return False

    # 메시지 전송 성공 시 활동 시각 갱신
    if result:
        try:
            core.set_working(status=True)
        except Exception:
            pass

    return result


def send_photo_sync(chat_id, photo_path, caption=None):
    """동기 방식 사진 전송"""
    try:
        return run_async_safe(core.send_photo(chat_id, photo_path, caption))
    except Exception as e:
        print(f"❌ [SENDER] Error sending photo: {e}")
        return False


def send_file_sync(chat_id, file_path, caption=None):
    """동기 방식 파일(문서) 전송"""
    try:
        return run_async_safe(core.send_document(chat_id, file_path, caption))
    except Exception as e:
        print(f"❌ [SENDER] Error sending file: {e}")
        return False


def send_files_sync(chat_id, text, file_paths):
    """
    동기 방식 메시지 + 여러 파일 전송

    Args:
        chat_id: 채팅 ID
        text: 메시지 내용
        file_paths: 파일 경로 리스트

    Returns:
        bool: 성공 여부
    """
    # 먼저 메시지 전송
    success = send_message_sync(chat_id, text)
    if not success:
        return False

    if not file_paths:
        return True

    # 파일들 전송
    import time
    for i, file_path in enumerate(file_paths):
        if i > 0:
            time.sleep(0.5)  # 연속 전송 시 잠시 대기

        file_name = os.path.basename(file_path)
        print(f"📎 파일 전송 중: {file_name}")

        # 이미지인지 판별
        ext = os.path.splitext(file_path)[1].lower()
        if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
            result = send_photo_sync(chat_id, file_path, caption=f"📎 {file_name}")
        else:
            result = send_file_sync(chat_id, file_path, caption=f"📎 {file_name}")

        if result:
            print(f"✅ 파일 전송 완료: {file_name}")
        else:
            print(f"❌ 파일 전송 실패: {file_name}")

    return True


if __name__ == "__main__":
    # 테스트
    import sys

    if len(sys.argv) < 3:
        print("사용법: python telegram_sender.py <chat_id> <message>")
        print("예: python telegram_sender.py 1234567890 '테스트 메시지'")
        sys.exit(1)

    chat_id = int(sys.argv[1])
    message = sys.argv[2]

    print(f"메시지 전송 중: {chat_id}")
    success = send_message_sync(chat_id, message)

    if success:
        print("✅ 전송 성공!")
    else:
        print("❌ 전송 실패!")
