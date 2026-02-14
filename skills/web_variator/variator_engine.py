import hashlib
import os
import random


class VariatorEngine:
    def __init__(self):
        # Tailwind-safe theme presets.
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
        self.layout_profiles = {
            "hero_centered": {"hero_height": "min-h-screen", "cards": "3up"},
            "split_showcase": {"hero_height": "min-h-[80vh]", "cards": "2up"},
            "editorial_stack": {"hero_height": "min-h-[75vh]", "cards": "mixed"},
            "catalog_grid": {"hero_height": "min-h-[70vh]", "cards": "grid"},
        }

    def _preferred_theme(self, niche):
        lower = (niche or "").lower()
        if "tech" in lower:
            return "NeoTech"
        if "fashion" in lower:
            return "Bold"
        if "cafe" in lower:
            return "WarmCafe"
        if "travel" in lower or "medical" in lower:
            return "Minimal"
        return "Premium"

    def _preferred_layout(self, niche):
        lower = (niche or "").lower()
        if "tech" in lower:
            return "split_showcase"
        if "fashion" in lower:
            return "editorial_stack"
        if "cafe" in lower:
            return "hero_centered"
        if "travel" in lower:
            return "catalog_grid"
        if "medical" in lower:
            return "split_showcase"
        return "hero_centered"

    def _seed_for(self, niche, suggested_layout):
        override = (os.getenv("WEB_VARIATION_SEED") or "").strip()
        if override:
            try:
                return int(override)
            except ValueError:
                pass
        raw = f"{niche}|{suggested_layout}|{os.getenv('PROJECT_NAME','')}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]
        return int(digest, 16)

    def generate_variations(self, niche, suggested_layout=None):
        """Return mixed theme+layout design configurations."""
        print(f"[VARIATOR] Generating design conceptualizations for '{niche}'...")

        preferred_theme = self._preferred_theme(niche)
        preferred_layout = suggested_layout or self._preferred_layout(niche)
        seed = self._seed_for(niche, suggested_layout or "")
        rng = random.Random(seed)

        theme_names = list(self.themes.keys())
        layout_names = list(self.layout_profiles.keys())
        rng.shuffle(theme_names)
        rng.shuffle(layout_names)

        # Build 6 mixed candidates with guaranteed diversity.
        candidates = []
        for idx in range(6):
            theme_name = theme_names[idx % len(theme_names)]
            layout_name = layout_names[idx % len(layout_names)]
            name = f"{theme_name}-{layout_name}"
            config = dict(self.themes[theme_name])
            config["layout"] = layout_name
            config["layout_profile"] = self.layout_profiles[layout_name]
            candidates.append({"name": name, "theme": theme_name, "layout": layout_name, "config": config})

        # Insert guaranteed preferred candidate at front for quality baseline.
        pref_config = dict(self.themes[preferred_theme])
        pref_config["layout"] = preferred_layout
        pref_config["layout_profile"] = self.layout_profiles[preferred_layout]
        preferred = {
            "name": f"{preferred_theme}-{preferred_layout}",
            "theme": preferred_theme,
            "layout": preferred_layout,
            "config": pref_config,
        }

        merged = [preferred]
        seen = {preferred["name"]}
        for item in candidates:
            if item["name"] in seen:
                continue
            merged.append(item)
            seen.add(item["name"])

        return merged

    def select_best_variation(self, variations, niche, suggested_layout=None):
        """Pick a strong candidate while preserving run-to-run diversity."""
        if not variations:
            raise ValueError("variations list is empty")

        preferred_theme = self._preferred_theme(niche)
        preferred_layout = suggested_layout or self._preferred_layout(niche)
        diversity_mode = (os.getenv("WEB_DIVERSITY_MODE") or "balanced").strip().lower()

        # Exact target match first.
        exact = next(
            (
                v
                for v in variations
                if v.get("theme") == preferred_theme and v.get("layout") == preferred_layout
            ),
            None,
        )
        if exact and diversity_mode != "aggressive":
            print(
                f"[VARIATOR] AI Selection: '{exact['name']}' chosen for niche='{niche}', layout='{preferred_layout}'."
            )
            return exact

        # Weighted selection for diversity. Bias by niche but rotate layouts.
        seed = self._seed_for(niche, suggested_layout or "")
        rng = random.Random(seed + len(variations))
        scored = []
        for v in variations:
            score = 1.0
            if v.get("theme") == preferred_theme:
                score += 2.0
            if v.get("layout") == preferred_layout:
                score += 1.5
            if diversity_mode == "aggressive" and v.get("layout") != preferred_layout:
                score += 1.5
            scored.append((v, score))

        total = sum(s for _, s in scored)
        pick = rng.uniform(0, total)
        upto = 0.0
        selected = scored[-1][0]
        for v, s in scored:
            upto += s
            if upto >= pick:
                selected = v
                break

        print(
            f"[VARIATOR] AI Selection: '{selected['name']}' is the optimal fit for '{niche}' (mode={diversity_mode})."
        )
        return selected


if __name__ == "__main__":
    engine = VariatorEngine()
    v = engine.generate_variations("Cafe", suggested_layout="split_showcase")
    print(engine.select_best_variation(v, "Cafe", suggested_layout="split_showcase"))
