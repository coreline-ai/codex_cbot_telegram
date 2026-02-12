import sys
import os
import json
import argparse
import time
from playwright.sync_api import sync_playwright

class ReconEngine:
    def __init__(self):
        pass

    def analyze(self, input_data):
        """
        Analyzes input search query or URL.
        If input is a URL, performs partial crawling (simulated for now if no full recon needed).
        If input is a brief (text), performs 'Trend Simulation'.
        """
        # Simple heuristic: is it a URL?
        if input_data.startswith("http"):
            return self._analyze_site(input_data, "recon_output")
        else:
            return self._simulate_market_research(input_data)

    def _simulate_market_research(self, topic):
        """
        Simulates gathering intelligence on a niche.
        """
        print(f"[RECON] 🕵️‍♂️ Simulating Market Research for: '{topic}'")
        
        # Deduce niche
        niche = "General"
        if "watch" in topic.lower() or "jewelry" in topic.lower():
            niche = "Luxury"
        elif "cafe" in topic.lower() or "coffee" in topic.lower():
            niche = "Cafe"
        elif "tech" in topic.lower() or "startup" in topic.lower():
            niche = "Tech"
        
        print(f"[RECON] Identified Market Niche: {niche}")
        
        return {
            "niche": niche,
            "palette": ["#000000", "#FFFFFF", "#D4AF37"] if niche == "Luxury" else ["#333", "#F4F4F4"],
            "typography": "Serif" if niche == "Luxury" else "Sans-Serif",
            "layout": "Hero-Centric"
        }

    def _analyze_site(self, url, output_dir):
        """
        Analyzes a website structure and saves metadata + screenshot.
        """
        os.makedirs(output_dir, exist_ok=True)
        
        with sync_playwright() as p:
            try:
                print(f"[RECON] Launching browser for: {url}")
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(viewport={'width': 1280, 'height': 800})
                
                # Navigate and wait
                page.goto(url)
                page.wait_for_load_state('networkidle')
                time.sleep(2) # Extra buffer for dynamic content
                
                # 1. Capture Screenshot
                screenshot_path = os.path.join(output_dir, "screenshot.png")
                page.screenshot(path=screenshot_path, full_page=True)
                print(f"[RECON] Screenshot saved: {screenshot_path}")
                
                # 2. Extract Structural Metadata
                structure = page.evaluate("""() => {
                    const getBestText = (el) => (el.innerText || "").split('\\n')[0].trim().substring(0, 50);
                    
                    const sections = [];
                    // Find Header
                    const header = document.querySelector('header, #header, .header');
                    if (header) sections.push({ type: 'header', text: getBestText(header), tag: header.tagName });
                    
                    // Find Main Sections
                    const mainSections = document.querySelectorAll('section, [role="main"] > div, .section');
                    mainSections.forEach(s => {
                        sections.push({ type: 'section', text: getBestText(s), tag: s.tagName, id: s.id, classes: s.className });
                    });
                    
                    // Find Footer
                    const footer = document.querySelector('footer, #footer, .footer');
                    if (footer) sections.push({ type: 'footer', text: getBestText(footer), tag: footer.tagName });
                    
                    // Extract unique colors (sample)
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
                }""")
                
                meta_path = os.path.join(output_dir, "structure.json")
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(structure, f, indent=4)
                
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
