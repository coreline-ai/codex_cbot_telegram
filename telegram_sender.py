"""
?붾젅洹몃옩 ?묐떟 ?꾩넚湲?(Sender) - Cross-Platform

??븷:
- core.py??async ?꾩넚 ?⑥닔瑜?sync濡??섑븨
- ?띿뒪??硫붿떆吏, ?ъ쭊, ?뚯씪 ?꾩넚
- ?대깽??猷⑦봽 異⑸룎 諛⑹? (ThreadPoolExecutor ?대갚)

?ъ슜踰?
    from telegram_sender import send_message_sync, send_photo_sync, send_files_sync

    send_message_sync(chat_id, "硫붿떆吏 ?댁슜")
    send_photo_sync(chat_id, "photo.png", "罹≪뀡")
    send_files_sync(chat_id, "硫붿떆吏", ["file1.txt", "file2.png"])
"""

import os
import asyncio
try:
    import core
except Exception:  # pragma: no cover
    from all_new_cbot import core  # type: ignore


def run_async_safe(coro):
    """?대깽??猷⑦봽媛 ?대? ?ㅽ뻾 以묒씠硫?蹂꾨룄 ?ㅻ젅?쒖뿉???ㅽ뻾"""
    try:
        asyncio.get_running_loop()
        # 猷⑦봽媛 ?ㅽ뻾 以???蹂꾨룄 ?ㅻ젅?쒖뿉????猷⑦봽 ?앹꽦
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    except RuntimeError:
        # ?ㅽ뻾 以묒씤 猷⑦봽 ?놁쓬 ??吏곸젒 ?ㅽ뻾
        return asyncio.run(coro)


def send_message_sync(chat_id, text, parse_mode="Markdown"):
    """
    ?숆린 諛⑹떇 硫붿떆吏 ?꾩넚

    硫붿떆吏 ?꾩넚 ?깃났 ??working.json??last_activity??媛깆떊?⑸땲??
    """
    try:
        result = run_async_safe(core.send_message(chat_id, text, parse_mode))
    except Exception as e:
        print(f"??[SENDER] Error sending message: {e}")
        return False

    # 硫붿떆吏 ?꾩넚 ?깃났 ???쒕룞 ?쒓컖 媛깆떊
    if result:
        try:
            core.set_working(status=True)
        except Exception:
            pass

    return result


def send_photo_sync(chat_id, photo_path, caption=None):
    """?숆린 諛⑹떇 ?ъ쭊 ?꾩넚"""
    try:
        return run_async_safe(core.send_photo(chat_id, photo_path, caption))
    except Exception as e:
        print(f"??[SENDER] Error sending photo: {e}")
        return False


def send_file_sync(chat_id, file_path, caption=None):
    """?숆린 諛⑹떇 ?뚯씪(臾몄꽌) ?꾩넚"""
    try:
        return run_async_safe(core.send_document(chat_id, file_path, caption))
    except Exception as e:
        print(f"??[SENDER] Error sending file: {e}")
        return False


def send_files_sync(chat_id, text, file_paths):
    """
    ?숆린 諛⑹떇 硫붿떆吏 + ?щ윭 ?뚯씪 ?꾩넚

    Args:
        chat_id: 梨꾪똿 ID
        text: 硫붿떆吏 ?댁슜
        file_paths: ?뚯씪 寃쎈줈 由ъ뒪??

    Returns:
        bool: ?깃났 ?щ?
    """
    # 癒쇱? 硫붿떆吏 ?꾩넚
    success = send_message_sync(chat_id, text)
    if not success:
        return False

    if not file_paths:
        return True

    # ?뚯씪???꾩넚
    import time
    for i, file_path in enumerate(file_paths):
        if i > 0:
            time.sleep(0.5)  # ?곗냽 ?꾩넚 ???좎떆 ?湲?

        file_name = os.path.basename(file_path)
        print(f"?뱨 ?뚯씪 ?꾩넚 以? {file_name}")

        # ?대?吏?몄? ?먮퀎
        ext = os.path.splitext(file_path)[1].lower()
        if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
            result = send_photo_sync(chat_id, file_path, caption=f"?뱨 {file_name}")
        else:
            result = send_file_sync(chat_id, file_path, caption=f"?뱨 {file_name}")

        if result:
            print(f"???뚯씪 ?꾩넚 ?꾨즺: {file_name}")
        else:
            print(f"???뚯씪 ?꾩넚 ?ㅽ뙣: {file_name}")

    return True


if __name__ == "__main__":
    # ?뚯뒪??
    import sys

    if len(sys.argv) < 3:
        print("?ъ슜踰? python telegram_sender.py <chat_id> <message>")
        print("?? python telegram_sender.py 1234567890 '?뚯뒪??硫붿떆吏'")
        sys.exit(1)

    chat_id = int(sys.argv[1])
    message = sys.argv[2]

    print(f"硫붿떆吏 ?꾩넚 以? {chat_id}")
    success = send_message_sync(chat_id, message)

    if success:
        print("???꾩넚 ?깃났!")
    else:
        print("???꾩넚 ?ㅽ뙣!")

