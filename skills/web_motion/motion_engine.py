import os
from bs4 import BeautifulSoup

class MotionEngine:
    def __init__(self):
        self.animations = {
            "fade_up": "animate-fade-in-up", # user needs custom css for this or tailwind config, using standard classes for now if possible or assuming base css has it
            "pulse": "animate-pulse",
            "bounce": "animate-bounce"
        }
        # Pre-defining some keyframes in a style tag to ensure they work without external config
        self.keyframes = """
        <style>
            @keyframes fadeInUp {
                from { opacity: 0; transform: translate3d(0, 40px, 0); }
                to { opacity: 1; transform: translate3d(0, 0, 0); }
            }
            .animate-fade-in-up {
                animation: fadeInUp 0.8s ease-out forwards;
            }
            .delay-100 { animation-delay: 0.1s; }
            .delay-200 { animation-delay: 0.2s; }
            .delay-300 { animation-delay: 0.3s; }
        </style>
        """

    def inject_motion(self, html_path):
        """
        Parses the HTML file and adds animation classes to key elements.
        """
        if not os.path.exists(html_path):
            print(f"[MOTION] Error: File not found {html_path}")
            return False

        try:
            with open(html_path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f, "html.parser")

            # 1. Inject CSS for custom animations
            if soup.head:
                soup.head.append(BeautifulSoup(self.keyframes, "html.parser"))

            # 2. Animate Hero Section Elements
            hero = soup.find(class_="hero") or soup.find("section") # Fallback to first section
            if hero:
                # Animate Heading
                h1 = hero.find("h1")
                if h1:
                    existing = h1.get("class", [])
                    h1["class"] = existing + ["animate-fade-in-up"]
                
                # Animate Paragraph
                p = hero.find("p")
                if p:
                    existing = p.get("class", [])
                    p["class"] = existing + ["animate-fade-in-up", "delay-100", "opacity-0"] # Start invisible
                
                # Animate Buttons
                btn = hero.find("a") or hero.find("button")
                if btn:
                    existing = btn.get("class", [])
                    btn["class"] = existing + ["animate-fade-in-up", "delay-200", "opacity-0"]

            # 3. Save changes
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(str(soup))
            
            print(f"[MOTION] Successfully injected motion into {os.path.basename(html_path)}")
            return True

        except Exception as e:
            print(f"[MOTION] Injection failed: {e}")
            return False

if __name__ == "__main__":
    # Test stub
    pass
