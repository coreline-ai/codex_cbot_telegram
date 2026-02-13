import random


class CopyEngine:
    def __init__(self):
        self.templates = {
            "Luxury": {
                "headline": ["Timeless Elegance.", "Beyond Luxury.", "The Art of Living."],
                "subtext": [
                    "Crafted for the uncompromising.",
                    "Experience the pinnacle of sophistication.",
                    "Where heritage meets modern mastery.",
                ],
                "cta": ["Discover the Collection", "Inquire Now", "Private Viewing"],
            },
            "Tech": {
                "headline": ["The Future, Defined.", "Innovate Faster.", "Powering Tomorrow."],
                "subtext": [
                    "Engineered for performance.",
                    "Seamless integration for modern workflows.",
                    "Break the boundaries of possible.",
                ],
                "cta": ["Get Started", "View Specs", "Request Demo"],
            },
            "Cafe": {
                "headline": ["Taste the Moment.", "Brewed Perfection.", "Morning Rituals."],
                "subtext": [
                    "Artisanal beans, roasted daily.",
                    "Experience the warmth of true connection.",
                    "A sanctuary for your senses.",
                ],
                "cta": ["View Menu", "Find Us", "Order Online"],
            },
            "Fashion": {
                "headline": ["Wear Your Story.", "Modern Silhouette.", "Effortless Style."],
                "subtext": [
                    "Sustainable fabrics, ethical design.",
                    "For those who walk their own path.",
                    "Curated looks for the season.",
                ],
                "cta": ["Shop Now", "New Arrivals", "Lookbook"],
            },
            "Travel": {
                "headline": ["Journey Beautifully.", "Stay Beyond Ordinary.", "Escape in Style."],
                "subtext": [
                    "Handpicked experiences for refined travelers.",
                    "Every destination, thoughtfully curated.",
                    "Where comfort meets discovery.",
                ],
                "cta": ["Plan Your Trip", "View Destinations", "Book Now"],
            },
            "Medical": {
                "headline": ["Care You Can Trust.", "Precision for Better Health.", "Your Wellbeing First."],
                "subtext": [
                    "Evidence-based care with a human touch.",
                    "Advanced diagnostics and clear guidance.",
                    "Reliable treatment pathways for every stage.",
                ],
                "cta": ["Book Appointment", "Find a Specialist", "Contact Clinic"],
            },
            "General": {
                "headline": ["Built for Your Next Move.", "Clarity, Crafted.", "Design That Converts."],
                "subtext": [
                    "A high-impact experience tailored to your audience.",
                    "Fast, reliable, and built for measurable outcomes.",
                    "Modern storytelling with clear calls to action.",
                ],
                "cta": ["Get Started", "Learn More", "Contact Us"],
            },
        }

    def generate_copy(self, niche):
        """
        Generate marketing copy by niche.
        Unknown niche falls back to General.
        """
        requested = (niche or "General").strip()
        selected_key = "General"
        for key in self.templates:
            if key.lower() in requested.lower() or requested.lower() in key.lower():
                selected_key = key
                break

        data = self.templates[selected_key]
        year = 2026
        return {
            "headline": random.choice(data["headline"]),
            "subtext": random.choice(data["subtext"]),
            "cta": random.choice(data["cta"]),
            "copyright": f"Copyright {year} {requested}. All rights reserved.",
        }


if __name__ == "__main__":
    engine = CopyEngine()
    print(engine.generate_copy("Cafe"))
