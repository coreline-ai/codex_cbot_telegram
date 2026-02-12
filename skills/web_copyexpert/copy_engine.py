import random

class CopyEngine:
    def __init__(self):
        self.templates = {
            "Luxury": {
                "headline": ["Timeless Elegance.", "Beyond Luxury.", "The Art of Living."],
                "subtext": ["Crafted for the uncompromising.", "Experience the pinnacle of sophistication.", "Where heritage meets modern mastery."],
                "cta": ["Discover the Collection", "Inquire Now", "Private Viewing"]
            },
            "Tech": {
                "headline": ["The Future, Defined.", "Innovate Faster.", "Powering Tomorrow."],
                "subtext": ["Engineered for performance.", "Seamless integration for modern workflows.", "Break the boundaries of possible."],
                "cta": ["Get Started", "View Specs", "Request Demo"]
            },
            "Cafe": {
                "headline": ["Taste the Moment.", "Brewed perfection.", "Morning Rituals."],
                "subtext": ["Artisanal beans, roasted daily.", "Experience the warmth of true connection.", "A sanctuary for your senses."],
                "cta": ["View Menu", "Find Us", "Order Online"]
            },
            "Fashion": {
                "headline": ["Wear Your Story.", "Modern Silhouette.", "Effortless Style."],
                "subtext": ["Sustainable fabrics, ethical design.", "For those who walk their own path.", "Curated looks for the season."],
                "cta": ["Shop Now", "New Arrivals", "Lookbook"]
            }
        }

    def generate_copy(self, niche):
        """
        Generates marketing copy elements based on the provided niche.
        If niche doesn't match a template, falls back to a generic 'Premium' style.
        """
        # Simple keyword matching to find best template
        key = "Luxury" # Default
        for k in self.templates.keys():
            if k.lower() in niche.lower():
                key = k
                break
        
        data = self.templates[key]
        
        return {
            "headline": random.choice(data["headline"]),
            "subtext": random.choice(data["subtext"]),
            "cta": random.choice(data["cta"]),
            "copyright": f"© 2026 {niche}. All Rights Reserved."
        }

# Standalone execution for testing
if __name__ == "__main__":
    engine = CopyEngine()
    print(engine.generate_copy("High-End Cafe"))
