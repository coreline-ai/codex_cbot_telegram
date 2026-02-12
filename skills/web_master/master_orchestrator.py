import os
import sys
import json
import argparse
import subprocess

# Add skills path to sys.path to ensure imports work
skills_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(skills_dir)

# Import Engines
try:
    from web_recon.recon_engine import ReconEngine
    from web_copyexpert.copy_engine import CopyEngine
    from web_variator.variator_engine import VariatorEngine
    from web_motion.motion_engine import MotionEngine
    from web_auditor.audit_engine import AuditEngine
    # Note: web_builder is usually called via subprocess or imported if needed
except ImportError as e:
    print(f"[FAIL] [ORCHESTRATOR] Import Error: {e}")
    sys.exit(1)

class WebMasterOrchestrator:
    def __init__(self, project_name):
        self.project_name = project_name
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.project_path = os.path.join(self.base_dir, "web_projects", project_name)

        # Initialize Engines
        self.recon = ReconEngine()
        self.copy_expert = CopyEngine()
        self.variator = VariatorEngine()
        self.motion = MotionEngine()
        self.auditor = AuditEngine()

    def log(self, step, message):
        print(f"[{step.upper()}] {message}")

    def run_pipeline(self, brief):
        print(f"[ORCHESTRATOR] Starting Master Pipeline for '{self.project_name}'...")
        
        # 1. Intelligence (Recon)
        self.log("recon", f"Analyzing brief: {brief}")
        recon_data = self.recon.analyze(brief)
        niche = recon_data.get("niche", "Premium")
        self.log("recon", f"Identified Niche: {niche}")

        # 2. Strategy (Copywriting)
        self.log("copy", "Generating strategic marketing copy...")
        copy_data = self.copy_expert.generate_copy(niche)
        self.log("copy", f"Headline: {copy_data['headline']}")

        # 3. Design Variations (Variator)
        self.log("variator", "Generating design concepts...")
        variations = self.variator.generate_variations(niche)
        best_design = self.variator.select_best_variation(variations, niche)
        self.log("variator", f"Selected Optimal Design: {best_design['name']}")

        # 4. Construction (Real Web Builder)
        self.log("builder", "Constructing commercial-grade Web Package...")
        
        # Prepare inputs for the Real Builder
        html_content = f"""
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
                                primary: '{best_design['config']['text'].split('-')[1]}', 
                                accent: '{best_design['config']['accent'].split('-')[1]}' 
                            }},
                            fontFamily: {{
                                sans: ['{best_design['config']['font']}', 'sans-serif']
                            }}
                        }}
                    }}
                }}
            </script>
            <link href="https://fonts.googleapis.com/css2?family={best_design['config']['font'].replace(' ', '+')}:wght@300;400;700;900&display=swap" rel="stylesheet">
            <style>
                body {{ font-family: '{best_design['config']['font']}', sans-serif; }}
                .hero-section {{
                    background: radial-gradient(circle at center, rgba(255,255,255,0.1) 0%, rgba(0,0,0,0.8) 100%);
                }}
            </style>
        </head>
        <body class="{best_design['config']['bg']} {best_design['config']['text']} antialiased">
            <!-- Navigation -->
            <nav class="flex justify-between items-center p-6 glass-card mx-4 mt-4 relative z-10">
                <div class="text-2xl font-bold tracking-tighter">{self.project_name.upper()}</div>
                <button class="{best_design['config']['accent']} text-white px-6 py-2 rounded-full text-sm font-bold shadow-lg hover:scale-105 transition-transform">
                    Shop Now
                </button>
            </nav>

            <!-- Hero Section -->
            <section class="hero hero-section min-h-screen flex flex-col items-center justify-center text-center relative overflow-hidden -mt-24">
                <div class="relative z-10 p-10 max-w-4xl">
                    <span class="text-sm uppercase tracking-[0.3em] opacity-80 mb-4 block animate-fade-in">New Collection</span>
                    <h1 class="text-7xl font-bold mb-6 leading-tight animate-fade-in-up">{copy_data['headline']}</h1>
                    <p class="text-xl opacity-80 mb-10 max-w-2xl mx-auto font-light leading-relaxed animate-fade-in-up delay-100">{copy_data['subtext']}</p>
                    
                    <div class="flex gap-4 justify-center animate-fade-in-up delay-200">
                        <button class="{best_design['config']['accent']} text-white px-10 py-4 rounded-full text-lg font-bold shadow-2xl hover:shadow-accent/50 transition-all hover:-translate-y-1">
                            {copy_data['cta']}
                        </button>
                        <button class="border border-current px-10 py-4 rounded-full text-lg font-bold hover:bg-white/10 transition-all">
                            View Lookbook
                        </button>
                    </div>
                </div>
                
                <!-- Background Decoration -->
                <div class="absolute inset-0 z-0 opacity-30">
                    <!-- Placeholder for potentially generated background texture -->
                </div>
            </section>

            <!-- Features -->
            <section class="py-20 px-6">
                <div class="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-8">
                    <div class="glass-card p-10 text-center hover:-translate-y-2 transition-transform duration-500">
                        <div class="text-4xl mb-4">💎</div>
                        <h3 class="text-xl font-bold mb-2">Premium Quality</h3>
                        <p class="opacity-70 text-sm">Crafted with the finest materials.</p>
                    </div>
                    <div class="glass-card p-10 text-center hover:-translate-y-2 transition-transform duration-500 delay-100">
                        <div class="text-4xl mb-4">🚀</div>
                        <h3 class="text-xl font-bold mb-2">Global Shipping</h3>
                        <p class="opacity-70 text-sm">We deliver luxury to your doorstep.</p>
                    </div>
                    <div class="glass-card p-10 text-center hover:-translate-y-2 transition-transform duration-500 delay-200">
                        <div class="text-4xl mb-4">🛡️</div>
                        <h3 class="text-xl font-bold mb-2">Lifetime Warranty</h3>
                        <p class="opacity-70 text-sm">Quality that stands the test of time.</p>
                    </div>
                </div>
            </section>
        </body>
        </html>
        """
        
        # Define needed assets based on niche (Strategy)
        required_assets = [
            {"name": "hero_bg", "type": "hero_realistic", "prompt": f"Cinematic background for {niche} brand, dark moody lighting, 8k"},
            {"name": "product_feature", "type": "product_realistic", "prompt": f"High detailed product shot for {niche}, studio lighting"}
        ]

        # Call the REAL Web Builder
        try:
            from web_gen.web_builder import create_web_package
            create_web_package(
                project_name=self.project_name,
                html_content=html_content,
                css_content=f".glass-card {{ background: rgba(255,255,255,0.05); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1); }}",
                assets=required_assets,
                mode="link"
            )
        except Exception as e:
            self.log("builder", f"Wait, falling back to manual write due to: {e}")
            # Fallback manual write if import fails
            os.makedirs(self.project_path, exist_ok=True)
            with open(os.path.join(self.project_path, "index.html"), "w", encoding="utf-8") as f:
                f.write(html_content)
        
        # 5. Motion Injection
        self.log("motion", "Injecting life (animations)...")
        index_path = os.path.join(self.project_path, "index.html")
        self.motion.inject_motion(index_path)

        # 6. Quality Audit
        self.log("audit", "Performing final quality assurance...")
        report = self.auditor.audit_project(self.project_path)
        
        print(f"\n✅ [DONE] Master Pipeline Complete.")
        print(f"   Quality Score: {report['score']}/100")
        print(f"   Output: {self.project_path}")

def main():
    parser = argparse.ArgumentParser(description="Web Master Orchestrator")
    parser.add_argument("--project", required=True, help="Project name")
    parser.add_argument("--brief", required=True, help="User design brief")
    
    args = parser.parse_args()
    
    orchestrator = WebMasterOrchestrator(args.project)
    orchestrator.run_pipeline(args.brief)

if __name__ == "__main__":
    main()
