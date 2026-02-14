import argparse
import os
import sys
from urllib.parse import quote

# Add skills path to sys.path to ensure imports work
skills_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(skills_dir)

try:
    from web_recon.recon_engine import ReconEngine
    from web_copyexpert.copy_engine import CopyEngine
    from web_variator.variator_engine import VariatorEngine
    from web_motion.motion_engine import MotionEngine
    from web_auditor.audit_engine import AuditEngine
except ImportError as e:
    print(f"[FAIL] [ORCHESTRATOR] Import Error: {e}")
    sys.exit(1)


class WebMasterOrchestrator:
    def __init__(self, project_name):
        self.project_name = project_name
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.project_path = os.path.join(self.base_dir, "web_projects", project_name)

        self.recon = ReconEngine()
        self.copy_expert = CopyEngine()
        self.variator = VariatorEngine()
        self.motion = MotionEngine()
        self.auditor = AuditEngine()

    def log(self, step, message):
        print(f"[{step.upper()}] {message}")

    def _preview_url_for_path(self, abs_file_path):
        base = (os.getenv("WEB_PREVIEW_BASE_URL") or "http://127.0.0.1:8080/api/files").strip().rstrip("/")
        rel = os.path.relpath(abs_file_path, self.base_dir).replace(os.sep, "/")
        return f"{base}/{quote(rel, safe='/')}"

    def _layout_hero_centered(self, design, copy_data, images):
        return f"""
            <nav class="flex justify-between items-center p-6 asset-card mx-4 mt-4 rounded-2xl relative z-10">
                <div class="text-2xl font-bold tracking-tighter">{self.project_name.upper()}</div>
                <button class="{design['accent']} text-white px-6 py-2 rounded-full text-sm font-bold shadow-lg hover:scale-105 transition-transform">
                    Shop Now
                </button>
            </nav>

            <section class="hero hero-section min-h-screen flex flex-col items-center justify-center text-center relative overflow-hidden -mt-24">
                <div class="relative z-10 p-10 max-w-4xl">
                    <span class="text-sm uppercase tracking-[0.3em] opacity-80 mb-4 block">New Collection</span>
                    <h1 class="text-7xl font-bold mb-6 leading-tight">{copy_data['headline']}</h1>
                    <p class="text-xl opacity-80 mb-10 max-w-2xl mx-auto font-light leading-relaxed">{copy_data['subtext']}</p>
                    <div class="flex gap-4 justify-center">
                        <button class="{design['accent']} text-white px-10 py-4 rounded-full text-lg font-bold shadow-2xl transition-all hover:-translate-y-1">
                            {copy_data['cta']}
                        </button>
                        <button class="border border-current px-10 py-4 rounded-full text-lg font-bold hover:bg-white/10 transition-all">
                            View Lookbook
                        </button>
                    </div>
                </div>
                <div class="absolute bottom-6 right-6 z-10 max-w-sm asset-card p-4 rounded-2xl shadow-2xl">
                    <img src="{images['product']}" alt="Featured product visual" class="w-full h-52 object-cover rounded-xl">
                    <p class="text-sm mt-3 opacity-80">Signature product visual generated for this page.</p>
                </div>
            </section>
        """

    def _layout_split_showcase(self, design, copy_data, images):
        return f"""
            <nav class="flex justify-between items-center p-6 mx-4 mt-4">
                <div class="text-2xl font-bold tracking-tight">{self.project_name.upper()}</div>
                <button class="{design['accent']} text-white px-6 py-2 rounded-full text-sm font-bold">Book Demo</button>
            </nav>

            <section class="hero min-h-[80vh] grid grid-cols-1 lg:grid-cols-2 items-stretch gap-0">
                <div class="p-10 md:p-16 flex flex-col justify-center">
                    <span class="text-xs uppercase tracking-[0.4em] opacity-70 mb-5">Performance Collection</span>
                    <h1 class="text-6xl md:text-7xl font-bold leading-tight mb-6">{copy_data['headline']}</h1>
                    <p class="text-lg opacity-80 max-w-xl mb-8">{copy_data['subtext']}</p>
                    <div class="flex gap-3">
                        <button class="{design['accent']} text-white px-8 py-4 rounded-full text-sm font-bold">{copy_data['cta']}</button>
                        <button class="border border-current px-8 py-4 rounded-full text-sm font-bold">Live Tour</button>
                    </div>
                </div>
                <div class="relative overflow-hidden">
                    <img src="{images['hero']}" alt="Hero visual" class="absolute inset-0 w-full h-full object-cover">
                    <div class="absolute inset-0 bg-gradient-to-t from-black/45 to-transparent"></div>
                    <div class="absolute right-8 bottom-8 max-w-xs asset-card p-4 rounded-2xl">
                        <img src="{images['product']}" alt="Primary product" class="w-full h-40 rounded-xl object-cover">
                    </div>
                </div>
            </section>
        """

    def _layout_editorial_stack(self, design, copy_data, images):
        return f"""
            <nav class="flex justify-between items-center p-6 mx-4 mt-4">
                <div class="text-2xl font-bold tracking-[0.15em]">{self.project_name.upper()}</div>
                <button class="border border-current px-6 py-2 rounded-full text-sm font-semibold">Editorial Drop</button>
            </nav>

            <section class="hero min-h-[78vh] px-6 md:px-12 py-10 grid grid-cols-1 lg:grid-cols-3 gap-6">
                <article class="asset-card rounded-2xl p-8 lg:col-span-2 flex flex-col justify-between">
                    <div>
                        <span class="text-xs uppercase tracking-[0.35em] opacity-70">Story Chapter 01</span>
                        <h1 class="text-5xl md:text-7xl font-bold mt-6 mb-6 leading-tight">{copy_data['headline']}</h1>
                        <p class="text-lg opacity-80 max-w-2xl">{copy_data['subtext']}</p>
                    </div>
                    <div class="flex gap-3 mt-10">
                        <button class="{design['accent']} text-white px-8 py-4 rounded-full text-sm font-bold">{copy_data['cta']}</button>
                        <button class="border border-current px-8 py-4 rounded-full text-sm font-bold">Read Lookbook</button>
                    </div>
                </article>
                <article class="rounded-2xl overflow-hidden relative min-h-[360px]">
                    <img src="{images['hero']}" alt="Editorial hero visual" class="absolute inset-0 w-full h-full object-cover">
                    <div class="absolute inset-0 bg-black/35"></div>
                </article>
            </section>
        """

    def _layout_catalog_grid(self, design, copy_data, images):
        return f"""
            <nav class="flex justify-between items-center p-6 mx-4 mt-4">
                <div class="text-2xl font-bold">{self.project_name.upper()}</div>
                <button class="{design['accent']} text-white px-6 py-2 rounded-full text-sm font-bold">Open Catalog</button>
            </nav>

            <section class="hero min-h-[70vh] px-6 py-12">
                <div class="max-w-6xl mx-auto">
                    <div class="text-center mb-10">
                        <h1 class="text-6xl md:text-7xl font-bold mb-6">{copy_data['headline']}</h1>
                        <p class="text-lg opacity-80 max-w-3xl mx-auto">{copy_data['subtext']}</p>
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
                        <article class="asset-card rounded-2xl overflow-hidden">
                            <img src="{images['hero']}" alt="Catalog hero" class="w-full h-44 object-cover">
                            <div class="p-4 text-sm opacity-85">Featured Story</div>
                        </article>
                        <article class="asset-card rounded-2xl overflow-hidden">
                            <img src="{images['product']}" alt="Catalog product" class="w-full h-44 object-cover">
                            <div class="p-4 text-sm opacity-85">Best Seller</div>
                        </article>
                        <article class="asset-card rounded-2xl overflow-hidden">
                            <img src="{images['g1']}" alt="Catalog variation 1" class="w-full h-44 object-cover">
                            <div class="p-4 text-sm opacity-85">Limited Drop</div>
                        </article>
                        <article class="asset-card rounded-2xl overflow-hidden">
                            <img src="{images['g2']}" alt="Catalog variation 2" class="w-full h-44 object-cover">
                            <div class="p-4 text-sm opacity-85">New Arrival</div>
                        </article>
                    </div>
                    <div class="text-center mt-10">
                        <button class="{design['accent']} text-white px-10 py-4 rounded-full text-sm font-bold">{copy_data['cta']}</button>
                    </div>
                </div>
            </section>
        """

    def _render_layout(self, layout_name, design, copy_data, images):
        layout_name = (layout_name or "hero_centered").strip().lower()
        if layout_name == "split_showcase":
            return self._layout_split_showcase(design, copy_data, images)
        if layout_name == "editorial_stack":
            return self._layout_editorial_stack(design, copy_data, images)
        if layout_name == "catalog_grid":
            return self._layout_catalog_grid(design, copy_data, images)
        return self._layout_hero_centered(design, copy_data, images)

    def _build_html(self, design, copy_data, images):
        layout_name = design.get("layout", "hero_centered")
        main_block = self._render_layout(layout_name, design, copy_data, images)
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{self.project_name}</title>
            <script src="https://cdn.tailwindcss.com"></script>
            <script>
                tailwind.config = {{
                    theme: {{
                        extend: {{
                            colors: {{
                                primary: '{design['text'].split('-')[1]}',
                                accent: '{design['accent'].split('-')[1]}'
                            }},
                            fontFamily: {{
                                sans: ['{design['font']}', 'sans-serif']
                            }}
                        }}
                    }}
                }}
            </script>
            <link href="https://fonts.googleapis.com/css2?family={design['font'].replace(' ', '+')}:wght@300;400;700;900&display=swap" rel="stylesheet">
            <style>
                body {{ font-family: '{design['font']}', sans-serif; }}
                .hero-section {{
                    background-image:
                        linear-gradient(180deg, rgba(0,0,0,0.45) 0%, rgba(0,0,0,0.75) 100%),
                        url('{images['hero']}');
                    background-size: cover;
                    background-position: center;
                }}
                .asset-card {{
                    background: rgba(255, 255, 255, 0.07);
                    backdrop-filter: blur(10px);
                    border: 1px solid rgba(255,255,255,0.2);
                }}
            </style>
        </head>
        <body class="{design['bg']} {design['text']} antialiased">
            {main_block}

            <section class="py-20 px-6">
                <div class="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-8">
                    <div class="asset-card p-10 text-center rounded-2xl hover:-translate-y-2 transition-transform duration-500">
                        <div class="text-4xl mb-4">01</div>
                        <h3 class="text-xl font-bold mb-2">Precision Fit Lab</h3>
                        <p class="opacity-70 text-sm">3D fit analysis and premium tailoring for every drop.</p>
                    </div>
                    <div class="asset-card p-10 text-center rounded-2xl hover:-translate-y-2 transition-transform duration-500 delay-100">
                        <div class="text-4xl mb-4">02</div>
                        <h3 class="text-xl font-bold mb-2">Limited Release</h3>
                        <p class="opacity-70 text-sm">Small-batch production with seasonal capsules.</p>
                    </div>
                    <div class="asset-card p-10 text-center rounded-2xl hover:-translate-y-2 transition-transform duration-500 delay-200">
                        <div class="text-4xl mb-4">03</div>
                        <h3 class="text-xl font-bold mb-2">Express Delivery</h3>
                        <p class="opacity-70 text-sm">Local same-day and global priority shipping.</p>
                    </div>
                </div>
            </section>

            <section class="pb-24 px-6">
                <div class="max-w-6xl mx-auto">
                    <div class="flex items-end justify-between mb-8">
                        <h2 class="text-3xl md:text-4xl font-bold">Photoreal Product Highlights</h2>
                        <p class="text-sm opacity-70">Layout: {layout_name}</p>
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <article class="asset-card rounded-2xl overflow-hidden">
                            <img src="{images['g1']}" alt="Detail closeup" class="w-full h-72 object-cover">
                            <div class="p-4"><p class="text-sm opacity-80">01. Material detail</p></div>
                        </article>
                        <article class="asset-card rounded-2xl overflow-hidden">
                            <img src="{images['g2']}" alt="Lifestyle styling" class="w-full h-72 object-cover">
                            <div class="p-4"><p class="text-sm opacity-80">02. Lifestyle story</p></div>
                        </article>
                        <article class="asset-card rounded-2xl overflow-hidden">
                            <img src="{images['g3']}" alt="Studio profile" class="w-full h-72 object-cover">
                            <div class="p-4"><p class="text-sm opacity-80">03. Studio composition</p></div>
                        </article>
                    </div>
                </div>
            </section>
        </body>
        </html>
        """

    def run_pipeline(self, brief):
        print(f"[ORCHESTRATOR] Starting Master Pipeline for '{self.project_name}'...")
        deploy_info = None

        self.log("recon", f"Analyzing brief: {brief}")
        recon_data = self.recon.analyze(brief)
        niche = recon_data.get("niche", "Premium")
        layout_hint = recon_data.get("layout", "hero_centered")
        self.log("recon", f"Identified Niche: {niche}")
        self.log("recon", f"Suggested Layout: {layout_hint}")

        self.log("copy", "Generating strategic marketing copy...")
        copy_data = self.copy_expert.generate_copy(niche)
        self.log("copy", f"Headline: {copy_data['headline']}")

        self.log("variator", "Generating design concepts...")
        variations = self.variator.generate_variations(niche, suggested_layout=layout_hint)
        best_variation = self.variator.select_best_variation(variations, niche, suggested_layout=layout_hint)
        best_design = best_variation["config"]
        selected_layout = best_variation.get("layout", best_design.get("layout", "hero_centered"))
        self.log("variator", f"Selected Variation: {best_variation['name']}")
        self.log("variator", f"Selected Layout: {selected_layout}")

        self.log("builder", "Constructing commercial-grade Web Package...")
        images = {
            "hero": "assets/hero_bg.png",
            "product": "assets/product_feature.png",
            "g1": "assets/product_alt_1.png",
            "g2": "assets/product_alt_2.png",
            "g3": "assets/product_alt_3.png",
        }
        html_content = self._build_html(best_design, copy_data, images)

        if "cafe" in niche.lower():
            required_assets = [
                {"name": "hero_bg", "type": "hero_realistic", "prompt": "Warm specialty cafe interior with wooden textures, ambient lighting, coffee steam, latte mood, hero background"},
                {"name": "product_feature", "type": "product_realistic", "prompt": "Close-up latte art cup on wooden table with roasted coffee beans, product shot composition, high detail"},
                {"name": "product_alt_1", "type": "product_realistic", "prompt": "Photoreal specialty dessert plate and coffee set, macro detail, natural window light, premium food styling"},
                {"name": "product_alt_2", "type": "product_realistic", "prompt": "Barista hand-pour coffee scene, stainless dripper, cinematic documentary style, shallow depth of field"},
                {"name": "product_alt_3", "type": "hero_realistic", "prompt": "Wide photoreal cafe seating area with warm ambient bulbs, lifestyle mood shot, high-end interior composition"},
            ]
        else:
            required_assets = [
                {"name": "hero_bg", "type": "hero_realistic", "prompt": f"Cinematic background for {niche} brand, premium composition, hero background"},
                {"name": "product_feature", "type": "product_realistic", "prompt": f"High detail product shot for {niche}, studio composition"},
                {"name": "product_alt_1", "type": "product_realistic", "prompt": f"Photoreal close-up detail shot for {niche}, premium material texture, studio softbox lighting"},
                {"name": "product_alt_2", "type": "product_realistic", "prompt": f"Photoreal lifestyle action shot for {niche}, urban environment, dynamic framing, editorial look"},
                {"name": "product_alt_3", "type": "product_realistic", "prompt": f"Photoreal side profile hero product for {niche}, clean background, commercial advertising style"},
            ]

        try:
            from web_gen.web_builder import create_web_package

            deploy_info = create_web_package(
                project_name=self.project_name,
                html_content=html_content,
                css_content=".asset-card { background: rgba(255,255,255,0.05); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1); }",
                assets=required_assets,
                mode="link",
            )
        except Exception as e:
            if "Photorealistic asset generation failed in strict mode" in str(e):
                self.log("builder", f"Fatal quality gate: {e}")
                raise

            self.log("builder", f"Fallback to manual write due to non-critical builder error: {e}")
            os.makedirs(self.project_path, exist_ok=True)
            fallback_index = os.path.join(self.project_path, "index.html")
            with open(fallback_index, "w", encoding="utf-8") as f:
                f.write(html_content)
            deploy_info = {
                "project": self.project_name,
                "project_dir": self.project_path,
                "index_path": fallback_index,
                "preview_url": self._preview_url_for_path(fallback_index),
            }

        self.log("motion", "Injecting life (animations)...")
        index_path = os.path.join(self.project_path, "index.html")
        self.motion.inject_motion(index_path)

        self.log("audit", "Performing final quality assurance...")
        report = self.auditor.audit_project(self.project_path)

        print("\n[DONE] Master Pipeline Complete.")
        print(f"   Quality Score: {report['score']}/100")
        print(f"   Output: {self.project_path}")
        print(f"   Layout: {selected_layout}")
        if isinstance(deploy_info, dict) and deploy_info.get("preview_url"):
            print(f"   Preview URL: {deploy_info['preview_url']}")


def main():
    parser = argparse.ArgumentParser(description="Web Master Orchestrator")
    parser.add_argument("--project", required=True, help="Project name")
    parser.add_argument("--brief", required=True, help="User design brief")

    args = parser.parse_args()
    orchestrator = WebMasterOrchestrator(args.project)
    orchestrator.run_pipeline(args.brief)


if __name__ == "__main__":
    main()
