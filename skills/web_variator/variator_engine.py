class VariatorEngine:
    def __init__(self):
        # Tailwind-safe class presets (all classes exist in default Tailwind palette).
        self.themes = {
            "Minimal": {
                "font": "Inter",
                "bg": "bg-white",
                "text": "text-slate-900",
                "accent": "bg-slate-900",
            },
            "Bold": {
                "font": "Oswald",
                "bg": "bg-amber-300",
                "text": "text-zinc-900",
                "accent": "bg-zinc-900",
            },
            "Premium": {
                "font": "Playfair Display",
                "bg": "bg-stone-900",
                "text": "text-amber-100",
                "accent": "bg-amber-500",
            },
            "NeoTech": {
                "font": "Space Grotesk",
                "bg": "bg-slate-950",
                "text": "text-cyan-100",
                "accent": "bg-cyan-500",
            },
            "WarmCafe": {
                "font": "Merriweather",
                "bg": "bg-amber-950",
                "text": "text-amber-100",
                "accent": "bg-amber-600",
            },
        }

    def generate_variations(self, niche):
        """Return multiple design configurations."""
        print(f"[VARIATOR] Generating design conceptualizations for '{niche}'...")
        return [
            {"name": "Minimal", "config": self.themes["Minimal"]},
            {"name": "Bold", "config": self.themes["Bold"]},
            {"name": "Premium", "config": self.themes["Premium"]},
            {"name": "NeoTech", "config": self.themes["NeoTech"]},
            {"name": "WarmCafe", "config": self.themes["WarmCafe"]},
        ]

    def select_best_variation(self, variations, niche):
        """Select a variation based on inferred niche."""
        lower = (niche or "").lower()

        preferred = "Premium"
        if "tech" in lower:
            preferred = "NeoTech"
        elif "fashion" in lower:
            preferred = "Bold"
        elif "cafe" in lower:
            preferred = "WarmCafe"
        elif "travel" in lower:
            preferred = "Minimal"
        elif "medical" in lower:
            preferred = "Minimal"

        selected = next((v for v in variations if v["name"] == preferred), variations[0])
        print(f"[VARIATOR] AI Selection: '{selected['name']}' is the optimal fit for '{niche}'.")
        return selected


if __name__ == "__main__":
    engine = VariatorEngine()
    v = engine.generate_variations("Cafe")
    print(engine.select_best_variation(v, "Cafe"))
