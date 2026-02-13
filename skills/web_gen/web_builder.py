import os
import sys
import json
import argparse
import base64
import re
import shutil
import ast


def _strict_realistic_enabled():
    """
    If enabled, *_realistic assets must come from an actual photoreal provider
    (currently sd_webui). Canvas fallback is treated as failure.
    """
    raw = os.getenv("STRICT_REALISTIC_ASSETS", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")

# Premium Base CSS with Glassmorphism and modern typography
PREMIUM_BASE_CSS = """
:root {
  --primary-color: #1C2833;
  --accent-color: #BF9A4A;
  --bg-color: #F4F6F6;
  --text-color: #2C3E50;
  --glass-bg: rgba(255, 255, 255, 0.7);
  --glass-border: rgba(255, 255, 255, 0.3);
}

* { margin: 0; padding: 0; box-sizing: border-box; }
body { 
  font-family: 'Inter', sans-serif; 
  background-color: var(--bg-color); 
  color: var(--text-color); 
  line-height: 1.6;
}

.glass-card {
  background: var(--glass-bg);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid var(--glass-border);
  border-radius: 20px;
  box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.15);
}

.hero {
  min-height: 80vh;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 80px 20px;
  background: radial-gradient(circle at top right, #EBF5FB, #F4F6F6);
}

h1 { font-size: 4rem; font-weight: 800; margin-bottom: 20px; }
p { font-size: 1.2rem; max-width: 600px; margin: 0 auto; }

.btn-primary {
  background-color: var(--accent-color);
  color: white;
  padding: 15px 35px;
  border-radius: 50px;
  text-decoration: none;
  font-weight: 600;
  transition: transform 0.3s ease;
  display: inline-block;
  margin-top: 30px;
}
.btn-primary:hover { transform: scale(1.05); }
"""

def validate_asset(image_path, is_reference=False):
    """
    Smart Validation: Checks if an image is likely a full-page screenshot.
    Rejects images with extreme aspect ratios or exact viewport dimensions if they are meant to be components.
    Allows screenshots if is_reference=True.
    """
    if is_reference:
        return True

    # Simple heuristic: If file size is > 200KB and ratio is > 2:1 (height:width), it's likely a scroll capture.
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            width, height = img.size
            ratio = height / width
            
            # 1. Check for scroll capture (tall images)
            if ratio > 2.0: 
                print(f"[WARN] Asset '{os.path.basename(image_path)}' rejected: Aspect ratio {ratio:.2f} suggests a full-page screenshot.")
                return False
                
            # 2. Check for exact viewport captures (1920x1080) usually used as backgrounds but not components
            if (width == 1920 and height == 1080) or (width == 1366 and height == 768):
                # Allow if explicitly named 'hero' or 'bg', otherwise warn
                if "hero" not in image_path.lower() and "bg" not in image_path.lower():
                     print(f"[WARN] Asset '{os.path.basename(image_path)}' rejected: Viewport match ({width}x{height}) suggests a raw screen capture.")
                     return False
                     
            return True
    except ImportError:
        # Fallback if PIL not installed
        size_kb = os.path.getsize(image_path) / 1024
        if size_kb > 500: # Heuristic: Component assets shouldn't be massive
             print(f"[WARN] Asset '{os.path.basename(image_path)}' suspicious: Large file size ({size_kb:.1f}KB). Verify it's not a raw capture.")
        return True
    except Exception as e:
        print(f"[WARN] Validation failed for {image_path}: {e}")
        return True

# Templates for common web assets (Blueprint suggestions)
ASSET_TEMPLATES = {
    "hero_realistic": {
        "description": "Photorealistic cinematic hero shot of a modern minimalist cafe interior",
        "prompt": "Professional architectural photography of a minimalist Nordic cafe, cinematic morning sunlight, dusty air particles, high-end furniture, 8k resolution, photorealistic."
    },
    "product_realistic": {
        "description": "Macro photorealistic shot of specialty coffee",
        "prompt": "Extreme macro close-up of complex latte art in a ceramic cup, professional food photography, shallow depth of field, warm morning light, photorealistic."
    },
    "roastery_realistic": {
        "description": "Professional shot of specialty coffee roasting",
        "prompt": "Macro shot of glossy dark roasted coffee beans in a professional roasting machine, industrial aesthetic, cinematic lighting, photorealistic."
    }
}

# Templates for Canvas Rendering (HTML Blueprints)
CANVAS_TEMPLATES = {
    "product_detail": """
    <div class="flex items-center justify-center h-screen bg-gray-50">
        <div class="text-center p-12 border border-gray-200 bg-white shadow-xl rounded-sm max-w-md">
            <div class="w-16 h-1 bg-black mx-auto mb-6"></div>
            <h2 class="text-3xl font-serif font-bold text-gray-900 mb-2">{title}</h2>
            <p class="text-sm text-gray-500 tracking-[0.2em] uppercase">{subtitle}</p>
        </div>
    </div>
    """,
    "hero_realistic": """
    <div class="flex items-center justify-center h-screen bg-neutral-900 text-white">
        <div class="text-center">
            <h1 class="text-6xl font-serif italic mb-6">{title}</h1>
            <p class="text-xl tracking-widest border-t border-b border-white/20 py-4 inline-block">{subtitle}</p>
        </div>
    </div>
    """,
    "product_realistic": """
    <div class="flex items-center justify-center h-screen bg-gradient-to-br from-amber-100 via-orange-100 to-stone-200">
        <div class="text-center p-10 rounded-xl bg-white/80 shadow-2xl max-w-lg">
            <p class="text-sm tracking-[0.25em] uppercase text-amber-800 mb-4">Product Visual</p>
            <h2 class="text-5xl font-serif font-bold text-stone-800 mb-3">{title}</h2>
            <p class="text-lg text-stone-600">{subtitle}</p>
        </div>
    </div>
    """,
    "roastery_realistic": """
    <div class="flex items-center justify-center h-screen bg-gradient-to-br from-zinc-900 via-stone-800 to-amber-900 text-white">
        <div class="text-center max-w-xl px-8">
            <p class="text-xs uppercase tracking-[0.35em] text-amber-200 mb-4">Roastery</p>
            <h2 class="text-5xl font-serif font-bold mb-4">{title}</h2>
            <p class="text-lg text-amber-100/90">{subtitle}</p>
        </div>
    </div>
    """
}

def _resolve_canvas_type(asset_type):
    """Maps any requested asset type to an available canvas template key."""
    if asset_type in CANVAS_TEMPLATES:
        return asset_type
    if "hero" in asset_type:
        return "hero_realistic"
    if "roastery" in asset_type:
        return "roastery_realistic"
    if "product" in asset_type:
        return "product_realistic"
    return "product_detail"

def run_image_gen_subprocess(prompt, output_path, image_gen_script, timeout_sec=180, expected_provider=None):
    """
    Calls image_gen.py as a subprocess and copies the generated PNG to output_path.
    Returns True on success, False otherwise.
    """
    import subprocess

    if not os.path.exists(image_gen_script):
        print(f"[WARN] image_gen script not found: {image_gen_script}")
        return False

    cmd = [sys.executable, image_gen_script, prompt]
    print(f"[EXEC] {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
    except Exception as e:
        print(f"[ERROR] image_gen subprocess execution failed: {e}")
        return False

    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()

    if result.returncode != 0:
        print(f"[ERROR] image_gen subprocess failed (exit={result.returncode}).")
        if stderr:
            print(f"[STDERR] {stderr}")
        if stdout:
            print(f"[STDOUT] {stdout}")
        return False

    payload = None
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                payload = json.loads(line)
                break
            except Exception:
                pass
            try:
                payload = ast.literal_eval(line)
                break
            except Exception:
                continue

    if not isinstance(payload, dict) or not payload.get("ok"):
        print("[ERROR] image_gen subprocess returned invalid payload.")
        if stdout:
            print(f"[STDOUT] {stdout}")
        return False

    provider = (payload.get("provider") or "").strip()
    if expected_provider:
        expected_set = {
            p.strip() for p in str(expected_provider).replace(",", "|").split("|") if p.strip()
        }
        if expected_set and provider not in expected_set:
            print(
                f"[ERROR] image_gen provider mismatch. expected one of {sorted(expected_set)} got='{provider or 'unknown'}'."
            )
            if stdout:
                print(f"[STDOUT] {stdout}")
            return False

    generated_path = payload.get("image_path")
    if not generated_path or not os.path.exists(generated_path):
        print(f"[ERROR] image_gen output missing: {generated_path}")
        return False

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if os.path.abspath(generated_path) != os.path.abspath(output_path):
        shutil.copy2(generated_path, output_path)
    return True

def generate_photorealistic_assets(assets, project_dir):
    """
    Attempts to generate photorealistic assets using sophisticated prompts.
    If direct photorealistic generation is unavailable, this falls back to canvas
    placeholders so downstream packaging does not silently miss required files.
    """
    print("\n[VIRTUAL_AGENCY] Initiating High-Fidelity Photorealistic Asset Production...")

    assets_dir = os.path.join(project_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    skills_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    image_gen_script = os.path.join(skills_dir, "image_gen", "image_gen.py")

    all_ok = True
    fallback_assets = []
    strict_realistic = _strict_realistic_enabled()
    for asset in assets:
        name = asset.get("name")
        if not name:
            print("[WARN] Skipping asset with missing 'name'.")
            all_ok = False
            continue

        a_type = asset.get("type", "product_realistic")
        custom_prompt = asset.get("prompt")

        output_file = f"{name}.png"
        full_output_path = os.path.join(assets_dir, output_file)
        template = ASSET_TEMPLATES.get(a_type, ASSET_TEMPLATES["product_realistic"])
        final_prompt = custom_prompt if custom_prompt else template["prompt"]

        print(f"  - [PROCESS] Generating: {output_file}...")
        print(f"    [PROMPT] \"{final_prompt}\"")
        if os.path.exists(full_output_path) and not strict_realistic:
            print(f"  - [SKIP] Existing asset found: {output_file}")
            continue

        # Explicit subprocess path: use image_gen first when photorealistic assets are requested.
        generated = run_image_gen_subprocess(
            final_prompt,
            full_output_path,
            image_gen_script,
            expected_provider="sd_webui|codex_cli" if strict_realistic else None,
        )
        if generated:
            print(f"  - [OK] Generated via image_gen subprocess: {output_file}")
            continue

        if strict_realistic:
            all_ok = False
            print("  - [ERROR] Strict realistic mode is ON. Canvas fallback is disabled.")
            continue

        print("  - [INFO] image_gen subprocess unavailable/failed. Using canvas fallback.")
        fallback_assets.append({
            "name": name,
            "type": _resolve_canvas_type(a_type),
            "title": asset.get("title", "Premium Visual"),
            "subtitle": asset.get("subtitle", "Auto-generated fallback asset")
        })

    if fallback_assets:
        all_ok = all_ok and generate_missing_assets(fallback_assets, project_dir)

    return all_ok

def generate_missing_assets(assets, project_dir):
    """
    Checks if assets in the 'assets' folder exist. If not, generates them
    using canvas_render.py based on predefined templates.
    """
    assets_dir = os.path.join(project_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    
    # Path to canvas_render.py
    skills_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    render_script = os.path.join(skills_dir, "image_gen", "canvas_render.py")

    all_ok = True
    for asset in assets:
        name = asset.get("name")
        if not name:
            print("[WARN] Skipping asset with missing 'name'.")
            all_ok = False
            continue

        a_type = asset.get("type", "product_detail")
        title = asset.get("title", "Premium Quality")
        subtitle = asset.get("subtitle", "Elite Experience")
        
        output_file = f"{name}.png"
        full_output_path = os.path.join(assets_dir, output_file)

        if not os.path.exists(full_output_path):
            print(f"[GENERATE] Producing missing asset: {output_file} ({a_type})")
            
            # 1. Get Template
            template = CANVAS_TEMPLATES.get(_resolve_canvas_type(a_type), CANVAS_TEMPLATES["product_detail"])

            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;700;900&family=Playfair+Display:ital@0;1&display=swap" rel="stylesheet">
    <style>body {{ font-family: 'Inter', sans-serif; }} .font-serif {{ font-family: 'Playfair Display', serif; }}</style>
</head>
<body style="margin: 0;">
    <div id="canvas-container" style="width: 1200px; height: 1200px; overflow: hidden;">
    {template.format(title=title, subtitle=subtitle)}
    </div>
</body>
</html>"""
            
            # 2. Write temp blueprint
            temp_blueprint = os.path.join(project_dir, f"temp_{name}_gen.html")
            with open(temp_blueprint, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            # 3. Call canvas_render
            import subprocess
            try:
                # Use sys.executable to ensure we use the same python environment
                cmd = [sys.executable, render_script, temp_blueprint, full_output_path, "#canvas-container", "0.5"]
                print(f"[EXEC] {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0 and os.path.exists(full_output_path):
                    print(f"[OK] Generated {output_file}")
                else:
                    all_ok = False
                    stderr = (result.stderr or "").strip()
                    stdout = (result.stdout or "").strip()
                    print(f"[ERROR] Failed to generate {output_file} (exit={result.returncode}).")
                    if stderr:
                        print(f"[STDERR] {stderr}")
                    if stdout:
                        print(f"[STDOUT] {stdout}")
            except Exception as e:
                all_ok = False
                print(f"[ERROR] Exception while calling renderer: {e}")
            
            # 4. Cleanup temp blueprint
            if os.path.exists(temp_blueprint):
                os.remove(temp_blueprint)
    return all_ok

def get_base64_image(image_path):
    """Converts an image to a Base64 data URI."""
    try:
        ext = os.path.splitext(image_path)[1].replace(".", "").lower()
        if ext == "jpg": ext = "jpeg"
        mime_type = f"image/{ext}"
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            return f"data:{mime_type};base64,{encoded_string}"
    except Exception as e:
        print(f"[WARN] Could not encode {image_path}: {e}")
        return None

def auto_embed_assets(html_content, project_dir):
    """Scans HTML for assets/ references and embeds them if they exist."""
    asset_pattern = r"(src|href)=['\"](assets/[^'\"]+)['\"]"
    assets_dir = os.path.join(project_dir, "assets")
    
    def replace_with_b64(match):
        attr = match.group(1)
        rel_path = match.group(2)
        full_path = os.path.join(project_dir, rel_path)
        
        if os.path.exists(full_path):
            b64_uri = get_base64_image(full_path)
            if b64_uri:
                print(f"[EMBED] Auto-embedded: {rel_path}")
                return f"{attr}='{b64_uri}'"
        return match.group(0)

    return re.sub(asset_pattern, replace_with_b64, html_content)

def smart_sync_assets(html_content, project_dir, source_dir="assets"):
    """
    Finds assets referenced in HTML and ensures they are copied to the project's assets folder.
    This enables a 'Link Mode' where assets are kept as separate files for better code quality.
    """
    asset_pattern = r"(src|href)=['\"](assets/[^'\"]+)['\"]"
    target_assets_dir = os.path.join(project_dir, "assets")
    os.makedirs(target_assets_dir, exist_ok=True)
    
    # We look for assets that might exist in the CWD or a specified source_dir
    matches = re.findall(asset_pattern, html_content)
    for attr, rel_path in matches:
        filename = os.path.basename(rel_path)
        # Try finding the file in several likely locations (CWD/assets, elite_nordic_cafe/assets, etc)
        potential_sources = [
            os.path.join(os.getcwd(), rel_path),
            os.path.join(os.getcwd(), "assets", filename),
            os.path.join(os.path.dirname(project_dir), rel_path)
        ]
        
        for src in potential_sources:
            if os.path.exists(src):
                # Anti-Screenshot Logic
                # Context Awareness: Check if it's explicitly stored as a reference
                is_ref = "reference" in src.lower() or "/ref/" in src.lower() or "\\ref\\" in src.lower()
                
                if not validate_asset(src, is_reference=is_ref):
                    print(f"[SKIP] Asset '{filename}' blocked by Smart Validation (suspected screenshot).")
                    continue

                dest = os.path.join(target_assets_dir, filename)
                if not os.path.exists(dest) or os.path.getmtime(src) > os.path.getmtime(dest):
                    print(f"[SYNC] Copying asset: {filename}")
                    shutil.copy2(src, dest)
                break

def create_web_package(project_name, html_content, css_content, assets=None, mode="link"):
    """
    Creates a web project directory structure and writes the files.
    Modes: 'link' (separate asset files), 'seal' (embedded Base64)
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    project_dir = os.path.join(base_dir, "web_projects", project_name)
    os.makedirs(project_dir, exist_ok=True)
    
    assets_dir = os.path.join(project_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    # Combine with base premium CSS if not already present
    final_css = PREMIUM_BASE_CSS + "\n" + css_content if "--no-base" not in sys.argv else css_content

    # If in link mode, try sync first so HTML can reference them
    if mode == "link":
        smart_sync_assets(html_content, project_dir)

    # NEW: Automated Asset Generation (High-Fidelity Priority)
    generation_ok = True
    if assets:
        print("\n[VIRTUAL_AGENCY] Analyzing asset requirements...")
        # Prioritize photorealistic generation for Elite/Premium context
        realistic_requested = any(a.get("type", "").endswith("_realistic") for a in assets) or "--elite" in sys.argv
        if realistic_requested:
            generation_ok = generate_photorealistic_assets(assets, project_dir)
        else:
            generation_ok = generate_missing_assets(assets, project_dir)
        
        # Re-sync if in link mode
        if mode == "link":
            smart_sync_assets(html_content, project_dir)

        # In strict mode, fail fast instead of silently shipping low-quality fallback output.
        if realistic_requested and _strict_realistic_enabled() and not generation_ok:
            raise RuntimeError(
                "Photorealistic asset generation failed in strict mode. "
                "Ensure image_gen provider is codex_cli or sd_webui and the backend is reachable."
            )

    # Initial write of HTML
    with open(os.path.join(project_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html_content)

    with open(os.path.join(project_dir, "styles.css"), "w", encoding="utf-8") as f:
        f.write(final_css)

    print(f"[SUCCESS] Advanced Web Package '{project_name}' created in '{mode}' mode!")
    print(f"[PATH] Location: {project_dir}")
    
    if assets:
        print("\n[ASSETS] Generation summary:")
        for asset in assets:
            name = asset.get("name", "unnamed")
            a_type = asset.get("type", "unknown")
            out_file = os.path.join(assets_dir, f"{name}.png")
            status = "[OK]" if os.path.exists(out_file) else "[MISSING]"
            print(f"  - {status} {name} (Type: {a_type}) -> assets/{name}.png")
        
        if mode == "seal":
            print("\n[TIP] Run this script again with --seal AFTER generating assets to embed them.")
        if not generation_ok:
            print("[WARN] One or more assets failed to generate.")

    # Post-process for embedding if requested (Seal Mode)
    if mode == "seal":
        print("\n[PROCESS] Running auto-sealing sequence (Base64)...")
        with open(os.path.join(project_dir, "index.html"), "r", encoding="utf-8") as f:
            current_html = f.read()
        
        sealed_html = auto_embed_assets(current_html, project_dir)
        
        with open(os.path.join(project_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(sealed_html)
        print("[SUCCESS] Package sealed with Base64 assets.")

def main():
    parser = argparse.ArgumentParser(description="Advanced Web Landing Page Builder")
    parser.add_argument("--project", help="Name of the project")
    parser.add_argument("--no-base", action="store_true", help="Don't include premium base CSS")
    parser.add_argument("--embed", action="store_true", help="Alias for --seal (deprecating)")
    parser.add_argument("--seal", action="store_true", help="Auto-embed local assets as Base64 (Seal Mode)")
    parser.add_argument("--link", action="store_true", help="Link to local assets and sync them (Link Mode, default)")
    
    args = parser.parse_args()

    # Determine mode: default is link
    mode = "link"
    if args.seal or args.embed:
        mode = "seal"

    if not sys.stdin.isatty():
        try:
            data = json.load(sys.stdin)
            create_web_package(
                data.get("project", args.project or "new_project"),
                data.get("html", "<h1>New Project</h1>"),
                data.get("css", ""),
                data.get("assets", []),
                mode=data.get("mode", mode)
            )
        except Exception as e:
            print(f"[ERROR] Error parsing advanced blueprint: {e}")
            sys.exit(1)
    else:
        print("TIP: Use: echo '{\"project\":\"test\", \"mode\":\"link\", \"html\":\"...\"}' | python web_builder.py")

if __name__ == "__main__":
    main()
