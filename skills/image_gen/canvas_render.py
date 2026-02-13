import sys
import os
import time
from playwright.sync_api import sync_playwright

def render_canvas(html_path, output_path, selector="#canvas-container", wait_time=2):
    """
    HTML 파일을 브라우저로 열어 특정 영역을 스크린샷으로 저장합니다.
    """
    if not os.path.exists(html_path):
        print(f"[ERROR] {html_path} not found.")
        return False

    output_dir = os.path.dirname(os.path.abspath(output_path))
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    abs_html_path = os.path.abspath(html_path)
    file_url = f"file:///{abs_html_path}".replace("\\", "/")

    with sync_playwright() as p:
        browser = None
        try:
            browser = p.chromium.launch(headless=True)
            # 고해상도 지원을 위해 뷰포트 크게 설정
            page = browser.new_page(viewport={'width': 1200, 'height': 1200})
            
            print(f"[INFO] Rendering: {file_url}")
            page.goto(file_url)
            
            # 네트워크가 안정될 때까지 대기
            page.wait_for_load_state('networkidle')
            
            # JS 애니메이션이나 렌더링 시간을 위해 추가 대기
            if wait_time > 0:
                time.sleep(wait_time)
            
            # 스크린샷 대상 확인
            target = page.locator(selector)
            if target.count() == 0:
                print(f"[WARN] Selector '{selector}' not found. Taking full page screenshot.")
                page.screenshot(path=output_path)
            else:
                target.screenshot(path=output_path)
            
            print(f"[OK] Image saved to {output_path}")
            return True
        except Exception as e:
            print(f"[ERROR] Rendering failed: {e}")
            return False
        finally:
            if browser:
                browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python canvas_render.py <html_path> <output_path> [selector] [wait_time]")
        sys.exit(1)
    
    h_path = sys.argv[1]
    o_path = sys.argv[2]
    sel = sys.argv[3] if len(sys.argv) > 3 else "#canvas-container"
    try:
        wait = float(sys.argv[4]) if len(sys.argv) > 4 else 2.0
    except ValueError:
        print("[ERROR] wait_time must be a number.")
        sys.exit(1)

    ok = render_canvas(h_path, o_path, sel, wait)
    sys.exit(0 if ok else 1)
