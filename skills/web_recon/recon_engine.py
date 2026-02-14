import os
import sys
import json
import argparse
import time

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - graceful degradation when Playwright is missing
    sync_playwright = None


class ReconEngine:
    def __init__(self):
        self.niche_keywords = {
            "Luxury": ["watch", "jewelry", "luxury", "premium", "\uc8fc\uc5bc\ub9ac", "\uc2dc\uacc4", "\uace0\uae09"],
            "Cafe": ["cafe", "coffee", "latte", "espresso", "roastery", "\uce74\ud398", "\ucee4\ud53c", "\ub77c\ub5bc"],
            "Tech": ["tech", "startup", "saas", "software", "ai", "dashboard", "\ud14c\ud06c", "\uae30\uc220"],
            "Fashion": ["fashion", "style", "lookbook", "apparel", "\ud328\uc158", "\uc758\ub958"],
            "Travel": ["travel", "hotel", "resort", "trip", "tour", "\uc5ec\ud589", "\ud638\ud154"],
            "Medical": ["medical", "clinic", "hospital", "health", "\ubcd1\uc6d0", "\ud074\ub9ac\ub2c9"],
        }

    def analyze(self, input_data):
        """
        Analyze input URL or free-form brief.
        - URL: browser-based structure/screenshot analysis.
        - Brief: niche classification and design guidance.
        """
        if (input_data or "").startswith("http"):
            return self._analyze_site(input_data, "recon_output")
        return self._simulate_market_research(input_data or "")

    def _simulate_market_research(self, topic):
        print(f"[RECON] Simulating market research for: '{topic}'")

        lower = topic.lower()
        niche = "General"
        best_score = 0
        for candidate, words in self.niche_keywords.items():
            score = sum(1 for w in words if w.lower() in lower)
            if score > best_score:
                best_score = score
                niche = candidate

        palette_map = {
            "Luxury": ["#101010", "#f5f3eb", "#b79b53"],
            "Cafe": ["#2f1d15", "#f0e2cc", "#a36a43"],
            "Tech": ["#0b1020", "#d6e7ff", "#3f7ef7"],
            "Fashion": ["#261b23", "#f8e9f2", "#d35f8d"],
            "Travel": ["#133a53", "#e7f6ff", "#2fa5c6"],
            "Medical": ["#143546", "#eaf8ff", "#31a2c9"],
            "General": ["#1a1a1a", "#f2f2f2", "#666666"],
        }

        typography = "Playfair Display" if niche in ("Luxury", "Cafe", "Fashion") else "Inter"
        layout = self._infer_layout(topic, niche)

        print(f"[RECON] Identified market niche: {niche}")

        return {
            "niche": niche,
            "palette": palette_map.get(niche, palette_map["General"]),
            "typography": typography,
            "layout": layout,
        }

    def _infer_layout(self, topic, niche):
        lower = (topic or "").lower()

        if any(k in lower for k in ["split", "좌우", "two column", "2 column"]):
            return "split_showcase"
        if any(k in lower for k in ["editorial", "magazine", "스토리", "story"]):
            return "editorial_stack"
        if any(k in lower for k in ["catalog", "grid", "list", "상품목록", "목록"]):
            return "catalog_grid"
        if any(k in lower for k in ["hero", "fullscreen", "full screen"]):
            return "hero_centered"

        niche_defaults = {
            "Tech": "split_showcase",
            "Fashion": "editorial_stack",
            "Cafe": "hero_centered",
            "Travel": "catalog_grid",
            "Medical": "split_showcase",
            "Luxury": "hero_centered",
        }
        return niche_defaults.get(niche, "hero_centered")

    def _analyze_site(self, url, output_dir):
        """Analyze a website structure and save metadata + screenshot."""
        if sync_playwright is None:
            raise RuntimeError("Playwright is required for live site analysis but is not installed")

        os.makedirs(output_dir, exist_ok=True)

        with sync_playwright() as p:
            try:
                print(f"[RECON] Launching browser for: {url}")
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1280, "height": 800})

                page.goto(url)
                page.wait_for_load_state("networkidle")
                time.sleep(2)

                screenshot_path = os.path.join(output_dir, "screenshot.png")
                page.screenshot(path=screenshot_path, full_page=True)
                print(f"[RECON] Screenshot saved: {screenshot_path}")

                structure = page.evaluate(
                    """() => {
                    const getBestText = (el) => (el.innerText || "").split('\n')[0].trim().substring(0, 50);

                    const sections = [];
                    const header = document.querySelector('header, #header, .header');
                    if (header) sections.push({ type: 'header', text: getBestText(header), tag: header.tagName });

                    const mainSections = document.querySelectorAll('section, [role="main"] > div, .section');
                    mainSections.forEach(s => {
                        sections.push({ type: 'section', text: getBestText(s), tag: s.tagName, id: s.id, classes: s.className });
                    });

                    const footer = document.querySelector('footer, #footer, .footer');
                    if (footer) sections.push({ type: 'footer', text: getBestText(footer), tag: footer.tagName });

                    const colors = Array.from(new Set(
                        Array.from(document.querySelectorAll('*'))
                        .slice(0, 100)
                        .map(el => window.getComputedStyle(el).color)
                        .filter(c => c && c.startsWith('rgb'))
                    )).slice(0, 10);

                    return {
                        url: window.location.href,
                        title: document.title,
                        sections: sections,
                        colors: colors
                    };
                }"""
                )

                meta_path = os.path.join(output_dir, "structure.json")
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(structure, f, indent=2, ensure_ascii=False)

                print(f"[RECON] Metadata saved: {meta_path}")
                print(f"[RECON] Found {len(structure['sections'])} major sections.")

                browser.close()
                return structure
            except Exception as e:
                print(f"[ERROR] Recon failed: {e}")
                return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Web Reconnaissance Engine")
    parser.add_argument("--url", help="URL to analyze")
    parser.add_argument("--brief", help="Brief to analyze")
    parser.add_argument("--output_dir", default="recon_output", help="Directory to save results")

    args = parser.parse_args()

    engine = ReconEngine()
    if args.url:
        engine.analyze(args.url)
    elif args.brief:
        engine.analyze(args.brief)
    else:
        print("Please provide --url or --brief")


if __name__ == "__main__":
    main()
