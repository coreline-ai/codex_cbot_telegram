"""
codex_cbot_telegram Skill - Image Generation

Provider priority:
1) Codex CLI image path (if available): preferred photoreal route.
2) Local SD WebUI API (if available): photorealistic output.
3) Stock-photo fallback (LoremFlickr): photorealistic output.
4) Local Canvas renderer fallback: deterministic no-API output.

Environment variables:
- IMAGE_GEN_PROVIDER: auto | codex_cli | sd_webui | stock | canvas  (default: auto)
- CODEX_EXE: optional absolute path to codex executable (recommended on Windows)
- CODEX_IMAGE_MODEL: optional codex model override for image sub-task
- CODEX_IMAGE_MODEL_CANDIDATES: optional comma-separated fallback models
- CODEX_IMAGE_BYPASS_SANDBOX: 1 to add --dangerously-bypass-approvals-and-sandbox
- CODEX_IMAGE_SANDBOX: read-only | workspace-write | danger-full-access (default: workspace-write)
- CODEX_IMAGE_ALLOW_SHELL_TOOLS: 1 to allow shell/tool usage when native image path is unavailable
- CODEX_IMAGE_TIMEOUT: timeout seconds for codex image sub-task (default: 300)
- SD_WEBUI_URL: base URL for local WebUI (default: http://127.0.0.1:7860)
- SD_WEBUI_TIMEOUT: request timeout seconds (default: 180)
- SD_WEBUI_WIDTH / SD_WEBUI_HEIGHT (default: 1200 / 1200)
- SD_WEBUI_STEPS (default: 28)
- SD_WEBUI_CFG (default: 7.0)
- SD_WEBUI_SAMPLER (default: DPM++ 2M Karras)
- SD_WEBUI_NEGATIVE_PROMPT
- STOCK_IMAGE_URL_TEMPLATE (optional custom template; supports {width} {height} {query} {seed} {nonce})
- STOCK_IMAGE_TIMEOUT (default: 25)
- STOCK_IMAGE_WIDTH / STOCK_IMAGE_HEIGHT (default: 1600 / 1200)
- STOCK_IMAGE_RETRIES (default: 3)
"""

import asyncio
import ast
import base64
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

try:
    import requests
except Exception:
    requests = None

_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(_DIR))
GEN_DIR = os.path.join(_DIR, "generated")
RENDER_SCRIPT = os.path.join(_DIR, "canvas_render.py")
CODEX_MD = os.path.join(BASE_DIR, "codex.md")

os.makedirs(GEN_DIR, exist_ok=True)


def _slugify(text: str, max_len: int = 48) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return slug[:max_len] or "image"


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


def _resolve_codex_executables():
    candidates = []
    seen = set()

    def _add(path):
        if not path:
            return
        norm = os.path.normcase(os.path.abspath(path))
        if norm in seen:
            return
        seen.add(norm)
        lower = norm.lower()
        if lower.endswith(".ps1"):
            prefix = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", path]
        elif lower.endswith(".cmd") or lower.endswith(".bat"):
            prefix = ["cmd", "/c", path]
        else:
            prefix = [path]
        candidates.append((prefix, path))

    # Prefer explicit override first.
    manual = (os.getenv("CODEX_EXE") or "").strip()
    if manual and os.path.exists(manual):
        _add(manual)
        return candidates

    # Then try common command paths.
    _add(shutil.which("codex.exe"))
    _add(shutil.which("codex.cmd"))
    _add(shutil.which("codex"))
    _add(shutil.which("codex.ps1"))

    return candidates


def _parse_payload_line(text: str):
    lines = (text or "").splitlines()
    for line in reversed(lines):
        raw = line.strip()
        if not raw:
            continue
        if raw.startswith("{") and raw.endswith("}"):
            # Try JSON first, then Python dict literal.
            try:
                return json.loads(raw)
            except Exception:
                pass
            try:
                return ast.literal_eval(raw)
            except Exception:
                pass
    return None


def _candidate_codex_models() -> List[Optional[str]]:
    # Priority:
    # 1) explicit image-model env
    # 2) explicit general model env
    # 3) optional fallback list env
    # 4) built-in safe fallback list
    raw_image = (os.getenv("CODEX_IMAGE_MODEL") or "").strip()
    raw_general = (os.getenv("CODEX_MODEL") or "").strip()
    raw_candidates = (os.getenv("CODEX_IMAGE_MODEL_CANDIDATES") or "").strip()

    candidates: List[Optional[str]] = []
    if raw_image:
        candidates.append(raw_image)
    if raw_general and raw_general not in candidates:
        candidates.append(raw_general)

    if raw_candidates:
        for part in raw_candidates.split(","):
            model = part.strip()
            if model and model not in candidates:
                candidates.append(model)
    else:
        for model in ["gpt-5.3-codex", "gpt-5-codex", "gpt-5"]:
            if model not in candidates:
                candidates.append(model)

    # Final fallback: let codex-cli choose default model.
    candidates.append(None)
    return candidates


def _env_bool(name: str, default: bool = False) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def _build_codex_cli_command(codex_prefix, prompt: str, image_path: str, model: Optional[str]):
    # Fixed command contract: avoid template drift and keep behavior deterministic.
    allow_shell_tools = _env_bool("CODEX_IMAGE_ALLOW_SHELL_TOOLS", False)
    task_prompt = (
        "You are an image generation worker. "
        f"Create one photorealistic PNG image that matches this prompt: '{prompt}'. "
        f"Save it exactly to this path: '{image_path}'. "
        "Prioritize native image-generation capabilities. "
        "Start generation immediately. "
        "After finishing, print exactly one JSON line only: "
        "{\"ok\": true, \"provider\": \"codex_cli\", \"image_path\": \"<path>\"}. "
        "If failed, print one JSON line with ok=false and error."
    )
    if allow_shell_tools:
        task_prompt += " If native path is unavailable, you may use local shell/tools to create and save the image."
    else:
        task_prompt += " Do not run shell commands, do not probe environment, and do not inspect filesystem."
    cmd = list(codex_prefix) + [
        "exec",
        "--skip-git-repo-check",
    ]
    if _env_bool("CODEX_IMAGE_BYPASS_SANDBOX", False):
        cmd.append("--dangerously-bypass-approvals-and-sandbox")
    else:
        cmd.extend(["--sandbox", os.getenv("CODEX_IMAGE_SANDBOX", "workspace-write").strip() or "workspace-write"])
        # Keep existing low-friction behavior unless explicitly disabled.
        if not _env_bool("CODEX_IMAGE_DISABLE_FULL_AUTO", False):
            cmd.append("--full-auto")
    if model:
        cmd.extend(["-m", model])
    if os.path.exists(CODEX_MD):
        cmd.extend(["--config", f"developer_instructions_file={CODEX_MD}"])
    # Use stdin prompt mode to avoid Windows cmd argument-length issues.
    cmd.append("-")
    return cmd, task_prompt


def _is_launcher_error(stderr: str, returncode: int) -> bool:
    if returncode == 0:
        return False
    s = (stderr or "").lower()
    return (
        "the system cannot find the file specified" in s
        or "지정된 파일을 찾을 수 없습니다" in s
        or "not recognized as an internal or external command" in s
    )


def _is_model_access_error(stderr: str) -> bool:
    s = (stderr or "").lower()
    return (
        "does not exist or you do not have access to it" in s
        or "model_not_found" in s
        or "unknown model" in s
    )


def _is_readonly_capability_error(error_text: str, stderr: str) -> bool:
    s = f"{error_text}\n{stderr}".lower()
    return (
        "read-only" in s
        or "read only" in s
        or "filesystem access is read-only" in s
        or "file writing are unavailable" in s
    )


def _is_image_generation_unavailable(error_text: str) -> bool:
    s = (error_text or "").lower()
    return "image generation not available in this environment" in s


def _generate_with_codex_cli(prompt: str, image_path: str) -> Dict:
    candidates = _resolve_codex_executables()
    if not candidates:
        return {"ok": False, "error": "codex CLI not found in PATH."}

    timeout = _env_int("CODEX_IMAGE_TIMEOUT", 300)
    env = os.environ.copy()

    # Isolate nested session metadata to reduce parent-session side effects.
    env.pop("CODEX_THREAD_ID", None)
    env.pop("CODEX_INTERNAL_ORIGINATOR_OVERRIDE", None)

    last_failure = None
    for codex_prefix, codex_resolved in candidates:
        for model in _candidate_codex_models():
            cmd, task_prompt = _build_codex_cli_command(codex_prefix, prompt, image_path, model=model)

            try:
                result = subprocess.run(
                    cmd,
                    input=task_prompt,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=timeout,
                    env=env,
                    cwd=BASE_DIR,
                )
            except subprocess.TimeoutExpired as exc:
                stdout = ""
                stderr = ""
                if isinstance(getattr(exc, "stdout", None), bytes):
                    stdout = exc.stdout.decode("utf-8", errors="replace")
                elif isinstance(getattr(exc, "stdout", None), str):
                    stdout = exc.stdout
                if isinstance(getattr(exc, "stderr", None), bytes):
                    stderr = exc.stderr.decode("utf-8", errors="replace")
                elif isinstance(getattr(exc, "stderr", None), str):
                    stderr = exc.stderr
                last_failure = {
                    "ok": False,
                    "error": f"codex_cli timeout after {timeout}s",
                    "codex_exe": codex_resolved,
                    "model": model,
                    "cmd": cmd,
                    "stdout": (stdout or "").strip(),
                    "stderr": (stderr or "").strip(),
                }
                continue
            except Exception as exc:
                last_failure = {
                    "ok": False,
                    "error": f"codex_cli execution failed: {exc}",
                    "codex_exe": codex_resolved,
                    "model": model,
                    "cmd": cmd,
                }
                continue

            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()

            if os.path.exists(image_path) and os.path.getsize(image_path) > 0:
                return {
                    "ok": True,
                    "provider": "codex_cli",
                    "image_path": image_path,
                    "stdout": stdout,
                    "stderr": stderr,
                    "returncode": result.returncode,
                    "cmd": cmd,
                    "codex_exe": codex_resolved,
                    "model": model,
                }

            payload = _parse_payload_line(stdout)
            if isinstance(payload, dict):
                payload_path = payload.get("image_path")
                if payload.get("ok") and payload_path and os.path.exists(payload_path):
                    return {
                        "ok": True,
                        "provider": "codex_cli",
                        "image_path": payload_path,
                        "stdout": stdout,
                        "stderr": stderr,
                        "returncode": result.returncode,
                        "cmd": cmd,
                        "codex_exe": codex_resolved,
                        "model": model,
                    }
                if payload.get("ok") is False:
                    # Command executed correctly and returned business-level failure.
                    payload_error = payload.get("error", "codex_cli returned failure payload")
                    failure = {
                        "ok": False,
                        "error": payload_error,
                        "stdout": stdout,
                        "stderr": stderr,
                        "returncode": result.returncode,
                        "cmd": cmd,
                        "codex_exe": codex_resolved,
                        "model": model,
                    }
                    if _is_readonly_capability_error(failure["error"], stderr):
                        failure["hint"] = (
                            "Nested codex exec appears read-only. "
                            "Try CODEX_IMAGE_BYPASS_SANDBOX=1, or use IMAGE_GEN_PROVIDER=sd_webui."
                        )
                    if _is_image_generation_unavailable(payload_error):
                        failure["hint"] = (
                            "This Codex runtime currently does not expose native image output. "
                            "Use IMAGE_GEN_PROVIDER=stock or run a local SD WebUI and set IMAGE_GEN_PROVIDER=sd_webui."
                        )
                    return failure

            last_failure = {
                "ok": False,
                "error": "codex_cli did not produce an output image.",
                "stdout": stdout,
                "stderr": stderr,
                "returncode": result.returncode,
                "cmd": cmd,
                "codex_exe": codex_resolved,
                "model": model,
            }
            if _is_readonly_capability_error(last_failure["error"], stderr):
                last_failure["hint"] = (
                    "Nested codex exec appears read-only. "
                    "Try CODEX_IMAGE_BYPASS_SANDBOX=1, or use IMAGE_GEN_PROVIDER=sd_webui."
                )
            if _is_image_generation_unavailable(stdout):
                last_failure["hint"] = (
                    "This Codex runtime currently does not expose native image output. "
                    "Use IMAGE_GEN_PROVIDER=stock or run a local SD WebUI and set IMAGE_GEN_PROVIDER=sd_webui."
                )

            # Retry model candidates on model-access errors.
            if _is_model_access_error(stderr):
                continue

            # Retry another executable only for launcher-level failures.
            if not _is_launcher_error(stderr, result.returncode):
                return last_failure

    return last_failure or {"ok": False, "error": "codex_cli failed with unknown launcher error."}


def _detect_theme(prompt: str) -> Tuple[str, bool]:
    lower = (prompt or "").lower()
    is_product = any(k in lower for k in ["product", "detail", "close-up", "closeup", "shot", "feature", "thumbnail"])

    if any(k in lower for k in ["cafe", "coffee", "latte", "espresso", "roastery", "menu", "카페", "커피", "라떼"]):
        return "cafe", is_product
    if any(k in lower for k in ["tech", "saas", "ai", "startup", "software", "dashboard"]):
        return "tech", is_product
    if any(k in lower for k in ["fashion", "lookbook", "apparel", "style"]):
        return "fashion", is_product
    if any(k in lower for k in ["travel", "hotel", "resort", "beach", "trip", "tour"]):
        return "travel", is_product
    if any(k in lower for k in ["medical", "clinic", "hospital", "health"]):
        return "medical", is_product
    return "default", is_product


def _build_sd_prompt(prompt: str) -> str:
    theme, _ = _detect_theme(prompt)
    suffix = (
        "ultra detailed, photorealistic, cinematic lighting, high dynamic range, "
        "professional composition, 8k quality"
    )

    if theme == "cafe":
        themed = "specialty cafe interior, warm wood tones, coffee steam, natural morning light"
    elif theme == "tech":
        themed = "futuristic technology environment, clean surfaces, neon accents"
    elif theme == "fashion":
        themed = "editorial fashion scene, premium styling, magazine-grade framing"
    elif theme == "travel":
        themed = "luxury travel destination, atmospheric sky, cinematic landscape"
    elif theme == "medical":
        themed = "modern clinical environment, clean white-blue palette, professional atmosphere"
    else:
        themed = "premium visual scene"

    return f"{prompt}, {themed}, {suffix}"


def _sd_negative_prompt() -> str:
    return os.getenv(
        "SD_WEBUI_NEGATIVE_PROMPT",
        "low quality, blurry, noisy, distorted anatomy, watermark, text overlay, logo, jpeg artifacts",
    )


def _sd_webui_available(base_url: str, timeout: int) -> bool:
    if requests is None:
        return False
    try:
        resp = requests.get(f"{base_url.rstrip('/')}/sdapi/v1/options", timeout=timeout)
        return resp.status_code < 500
    except Exception:
        return False


def _generate_with_sd_webui(prompt: str, image_path: str) -> Dict:
    if requests is None:
        return {"ok": False, "error": "requests module is not installed."}

    base_url = os.getenv("SD_WEBUI_URL", "http://127.0.0.1:7860").rstrip("/")
    timeout = _env_int("SD_WEBUI_TIMEOUT", 180)

    if not _sd_webui_available(base_url, timeout=min(timeout, 10)):
        return {"ok": False, "error": f"SD WebUI not available at {base_url}"}

    width = _env_int("SD_WEBUI_WIDTH", 1200)
    height = _env_int("SD_WEBUI_HEIGHT", 1200)
    steps = _env_int("SD_WEBUI_STEPS", 28)
    cfg_scale = _env_float("SD_WEBUI_CFG", 7.0)
    sampler = os.getenv("SD_WEBUI_SAMPLER", "DPM++ 2M Karras")

    payload = {
        "prompt": _build_sd_prompt(prompt),
        "negative_prompt": _sd_negative_prompt(),
        "width": width,
        "height": height,
        "steps": steps,
        "cfg_scale": cfg_scale,
        "sampler_name": sampler,
        "seed": -1,
        "n_iter": 1,
        "batch_size": 1,
    }

    try:
        response = requests.post(f"{base_url}/sdapi/v1/txt2img", json=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        images = data.get("images") or []
        if not images:
            return {"ok": False, "error": "SD WebUI returned no images."}

        encoded = images[0]
        if "," in encoded:
            encoded = encoded.split(",", 1)[1]

        binary = base64.b64decode(encoded)
        os.makedirs(os.path.dirname(os.path.abspath(image_path)), exist_ok=True)
        with open(image_path, "wb") as f:
            f.write(binary)

        return {
            "ok": True,
            "provider": "sd_webui",
            "image_path": image_path,
            "meta": {
                "width": width,
                "height": height,
                "steps": steps,
                "cfg_scale": cfg_scale,
                "sampler": sampler,
                "base_url": base_url,
            },
        }
    except Exception as exc:
        return {"ok": False, "error": f"SD WebUI generation failed: {exc}"}


def _stock_query_from_prompt(prompt: str) -> str:
    tokens = re.findall(r"[a-zA-Z0-9]+", (prompt or "").lower())
    if not tokens:
        return "product,studio,photo"
    compact = []
    for token in tokens:
        if token in ("the", "and", "with", "from", "that", "this", "for", "shot", "image"):
            continue
        compact.append(token)
        if len(compact) >= 6:
            break
    if not compact:
        compact = ["product", "studio", "photo"]
    return ",".join(compact)


def _write_png(binary: bytes, image_path: str) -> bool:
    try:
        from PIL import Image

        with Image.open(io.BytesIO(binary)) as img:
            converted = img.convert("RGB")
            converted.save(image_path, format="PNG", optimize=True)
        return True
    except Exception:
        return False


def _generate_with_stock_photo(prompt: str, image_path: str) -> Dict:
    timeout = _env_int("STOCK_IMAGE_TIMEOUT", 25)
    width = _env_int("STOCK_IMAGE_WIDTH", 1600)
    height = _env_int("STOCK_IMAGE_HEIGHT", 1200)
    retries = max(1, _env_int("STOCK_IMAGE_RETRIES", 3))
    query = _stock_query_from_prompt(prompt)
    os.makedirs(os.path.dirname(os.path.abspath(image_path)), exist_ok=True)

    last_error = "unknown"
    final_url = ""
    for attempt in range(1, retries + 1):
        encoded_query = quote_plus(query.replace(",", " "))
        nonce = int(time.time() * 1000)
        seed = quote_plus(f"{query}-{nonce}-{attempt}")
        candidate_urls = [
            f"https://picsum.photos/seed/{seed}/{width}/{height}",
            f"https://loremflickr.com/{width}/{height}/{encoded_query}/all?r={nonce}",
        ]
        custom_template = (os.getenv("STOCK_IMAGE_URL_TEMPLATE") or "").strip()
        if custom_template:
            candidate_urls.insert(
                0,
                custom_template.format(
                    width=width,
                    height=height,
                    query=encoded_query,
                    seed=seed,
                    nonce=nonce,
                ),
            )

        for url in candidate_urls:
            final_url = url
            try:
                req = Request(
                    url,
                    headers={
                        "User-Agent": "codex-cbot-image-gen/1.0",
                        "Accept": "image/*",
                    },
                )
                with urlopen(req, timeout=timeout) as resp:
                    binary = resp.read()

                if not binary or len(binary) < 15 * 1024:
                    last_error = f"received too-small payload ({len(binary) if binary else 0} bytes)"
                    continue

                if not _write_png(binary, image_path):
                    with open(image_path, "wb") as f:
                        f.write(binary)

                if not os.path.exists(image_path) or os.path.getsize(image_path) < 15 * 1024:
                    last_error = "saved file is missing or too small"
                    continue

                return {
                    "ok": True,
                    "provider": "stock",
                    "prompt": prompt,
                    "image_path": image_path,
                    "meta": {
                        "url": url,
                        "query": query,
                        "width": width,
                        "height": height,
                        "attempt": attempt,
                    },
                }
            except Exception as exc:
                last_error = str(exc)
                continue

    return {
        "ok": False,
        "error": f"stock provider failed after {retries} attempts: {last_error}",
        "meta": {"url": final_url, "query": query, "retries": retries},
    }


def _build_canvas_html(prompt: str) -> str:
    escaped_prompt = prompt.replace("\\", "\\\\").replace("'", "\\'")
    theme, is_product = _detect_theme(prompt)

    return f"""<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <title>Generated Image</title>
  <style>
    html, body {{ margin: 0; width: 100%; height: 100%; background: #0b1020; overflow: hidden; }}
    #canvas-container {{ width: 1200px; height: 1200px; }}
    #art {{ width: 1200px; height: 1200px; display: block; }}
  </style>
</head>
<body>
  <div id=\"canvas-container\"><canvas id=\"art\" width=\"1200\" height=\"1200\"></canvas></div>
  <script>
    const prompt = '{escaped_prompt}';
    const lowerPrompt = prompt.toLowerCase();
    const theme = '{theme}';
    const isProduct = {str(is_product).lower()};
    const hasCounterFocus = lowerPrompt.includes('counter') || lowerPrompt.includes('bar') || lowerPrompt.includes('espresso');
    const isEvening = lowerPrompt.includes('night') || lowerPrompt.includes('evening') || lowerPrompt.includes('blue hour');
    const canvas = document.getElementById('art');
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    function hashText(text) {{
      let h = 2166136261;
      for (let i = 0; i < text.length; i += 1) {{
        h ^= text.charCodeAt(i);
        h += (h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24);
      }}
      return h >>> 0;
    }}
    function rng(seed) {{
      let x = seed || 1;
      return () => {{
        x ^= x << 13; x ^= x >>> 17; x ^= x << 5;
        return (x >>> 0) / 4294967296;
      }};
    }}

    const rand = rng(hashText(prompt));
    const palettes = {{
      cafe: ['#28170f', '#4a2f20', '#7d523a'],
      tech: ['#0b1329', '#143464', '#1b5b8f'],
      fashion: ['#251922', '#553548', '#8f5f74'],
      travel: ['#18445d', '#2a6f89', '#58adc2'],
      medical: ['#14384c', '#1d5872', '#3a98b8'],
      default: ['#111827', '#1f2937', '#334155']
    }};

    function fillBg(colors) {{
      const g = ctx.createLinearGradient(0, 0, width, height);
      g.addColorStop(0, colors[0]);
      g.addColorStop(0.6, colors[1]);
      g.addColorStop(1, colors[2]);
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, width, height);
    }}

    function drawCafe() {{
      if (isProduct) {{
        // Product close-up (latte + beans)
        ctx.fillStyle = 'rgba(58,38,26,0.92)';
        ctx.fillRect(0, 760, width, 440);

        const cupX = 610;
        const cupY = 520;
        const cupW = 340;
        const cupH = 260;

        ctx.fillStyle = 'rgba(246,243,238,0.98)';
        ctx.fillRect(cupX - cupW/2, cupY - cupH/2, cupW, cupH);
        ctx.fillStyle = 'rgba(92,54,31,0.96)';
        ctx.beginPath();
        ctx.ellipse(cupX, cupY - cupH*0.18, cupW*0.44, 38, 0, 0, Math.PI*2);
        ctx.fill();

        for (let i = 0; i < 84; i += 1) {{
          const bx = rand() * width;
          const by = 780 + rand() * 390;
          ctx.fillStyle = `rgba(52,29,17,${{0.68 + rand()*0.28}})`;
          ctx.beginPath();
          ctx.ellipse(bx, by, 8 + rand()*10, 5 + rand()*7, rand()*Math.PI, 0, Math.PI*2);
          ctx.fill();
        }}
        return;
      }}

      // Interior wide / counter-focused shots inspired by warm Korean cafe style
      const wallTone = isEvening ? 'rgba(52,34,24,0.95)' : 'rgba(72,49,36,0.92)';
      const floorGrad = ctx.createLinearGradient(0, 620, 0, height);
      floorGrad.addColorStop(0, isEvening ? '#3f2e24' : '#5c4332');
      floorGrad.addColorStop(1, '#2a1d14');

      // Ceiling + beams
      ctx.fillStyle = '#1b130f';
      ctx.fillRect(0, 0, width, 175);
      for (let i = 0; i < 7; i += 1) {{
        ctx.fillStyle = 'rgba(12,8,6,0.55)';
        ctx.fillRect(80 + i * 170, 0, 42, 175);
      }}

      // Pendant lights
      for (let i = 0; i < 7; i += 1) {{
        const lx = 120 + i * 165 + (rand() * 24 - 12);
        const ly = 38 + (rand() * 6 - 3);
        ctx.strokeStyle = 'rgba(230,220,190,0.55)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(lx, 0);
        ctx.lineTo(lx, ly);
        ctx.stroke();

        ctx.fillStyle = 'rgba(248,241,220,0.95)';
        ctx.fillRect(lx - 14, ly, 28, 34);
        ctx.fillStyle = 'rgba(255,232,178,0.18)';
        ctx.fillRect(lx - 42, ly + 22, 84, 84);
      }}

      // Main walls + floor
      ctx.fillStyle = wallTone;
      ctx.fillRect(0, 175, width, 445);
      ctx.fillStyle = floorGrad;
      ctx.fillRect(0, 620, width, 580);

      // Left wooden panel wall
      ctx.fillStyle = 'rgba(169,132,89,0.9)';
      ctx.fillRect(0, 175, 255, 500);
      for (let i = 0; i < 10; i += 1) {{
        ctx.fillStyle = 'rgba(126,92,62,0.55)';
        ctx.fillRect(18 + i * 22, 185, 4, 470);
      }}

      // Right glass windows
      ctx.fillStyle = isEvening ? 'rgba(40,62,95,0.56)' : 'rgba(78,118,158,0.46)';
      ctx.fillRect(850, 175, 350, 630);
      for (let i = 0; i < 6; i += 1) {{
        ctx.fillStyle = 'rgba(18,16,16,0.75)';
        ctx.fillRect(850 + i * 58, 175, 10, 630);
      }}

      // Back counter + menu boards
      ctx.fillStyle = 'rgba(238,231,218,0.95)';
      ctx.fillRect(265, 300, 540, 150);
      ctx.fillStyle = 'rgba(24,21,21,0.92)';
      ctx.fillRect(265, 450, 540, 90);
      for (let i = 0; i < 6; i += 1) {{
        ctx.fillStyle = 'rgba(245,243,238,0.96)';
        ctx.fillRect(292 + i * 84, 245, 68, 45);
      }}

      // Counter machinery accents
      ctx.fillStyle = 'rgba(180,186,194,0.85)';
      ctx.fillRect(520, 395, 120, 54);
      ctx.fillStyle = 'rgba(70,120,224,0.55)';
      ctx.fillRect(655, 408, 44, 26);

      if (hasCounterFocus) {{
        // Counter-focused framing
        ctx.fillStyle = 'rgba(64,42,28,0.96)';
        ctx.fillRect(0, 620, width, 580);
        ctx.fillStyle = 'rgba(195,156,116,0.82)';
        ctx.fillRect(80, 640, 1040, 115);
        for (let i = 0; i < 10; i += 1) {{
          const cx = 120 + i * 98;
          ctx.fillStyle = 'rgba(248,246,238,0.95)';
          ctx.fillRect(cx, 560 + rand() * 30, 26, 48);
        }}
        return;
      }}

      // Seating layout (tables + chairs)
      for (let r = 0; r < 3; r += 1) {{
        for (let c = 0; c < 4; c += 1) {{
          const tx = 295 + c * 160 + (rand() * 8 - 4);
          const ty = 610 + r * 150 + (rand() * 8 - 4);

          ctx.fillStyle = 'rgba(118,78,51,0.95)';
          ctx.fillRect(tx, ty, 120, 68);

          // chairs
          ctx.fillStyle = 'rgba(76,50,34,0.95)';
          ctx.fillRect(tx - 24, ty + 8, 18, 48);
          ctx.fillRect(tx + 126, ty + 8, 18, 48);
          ctx.fillRect(tx + 18, ty + 72, 20, 44);
          ctx.fillRect(tx + 82, ty + 72, 20, 44);
        }}
      }}
    }}

    function drawGeneral() {{
      for (let i = 0; i < 55; i += 1) {{
        const x = rand() * width;
        const y = rand() * height;
        const r = 30 + rand() * 190;
        ctx.fillStyle = `rgba(255,255,255,${{0.04 + rand()*0.12}})`;
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();
      }}
    }}

    fillBg(palettes[theme] || palettes.default);
    if (theme === 'cafe') drawCafe();
    else drawGeneral();

    ctx.fillStyle = 'rgba(0,0,0,0.35)';
    ctx.fillRect(38, 1030, 1124, 126);
    ctx.fillStyle = 'rgba(255,255,255,0.92)';
    ctx.font = 'bold 30px Arial';
    ctx.fillText(`Theme: ${{theme.toUpperCase()}}`, 72, 1084);
    ctx.font = '24px Arial';
    ctx.fillStyle = 'rgba(255,255,255,0.8)';
    const shortPrompt = prompt.length > 82 ? prompt.slice(0, 82) + '...' : prompt;
    ctx.fillText(shortPrompt, 72, 1134);
  </script>
</body>
</html>
"""


async def _generate_with_canvas(prompt: str, html_path: str, image_path: str) -> Dict:
    if not os.path.exists(RENDER_SCRIPT):
        return {"ok": False, "error": f"Renderer not found: {RENDER_SCRIPT}"}

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(_build_canvas_html(prompt))

    cmd = [sys.executable, RENDER_SCRIPT, html_path, image_path, "#canvas-container", "0.6"]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    stdout_text = (stdout or b"").decode("utf-8", errors="replace").strip()
    stderr_text = (stderr or b"").decode("utf-8", errors="replace").strip()

    if proc.returncode != 0 or not os.path.exists(image_path):
        return {
            "ok": False,
            "error": "Canvas renderer process failed.",
            "returncode": proc.returncode,
            "stdout": stdout_text,
            "stderr": stderr_text,
            "html_path": html_path,
            "image_path": image_path,
        }

    return {
        "ok": True,
        "provider": "canvas",
        "prompt": prompt,
        "html_path": html_path,
        "image_path": image_path,
        "stdout": stdout_text,
    }


async def generate_image(prompt: str):
    """Generate a local image from prompt using configured provider chain."""
    normalized = (prompt or "").strip()
    if not normalized:
        return {"ok": False, "error": "Prompt is empty."}

    timestamp = int(time.time())
    slug = _slugify(normalized)
    html_path = os.path.join(GEN_DIR, f"{timestamp}_{slug}.html")
    image_path = os.path.join(GEN_DIR, f"{timestamp}_{slug}.png")

    provider = os.getenv("IMAGE_GEN_PROVIDER", "auto").strip().lower()
    attempts = []

    try:
        if provider in ("auto", "codex_cli"):
            codex_result = _generate_with_codex_cli(normalized, image_path)
            attempts.append({"provider": "codex_cli", "ok": codex_result.get("ok"), "error": codex_result.get("error")})
            if codex_result.get("ok"):
                codex_result.update({"prompt": normalized, "html_path": None, "attempts": attempts})
                return codex_result
            if provider == "codex_cli":
                codex_result["attempts"] = attempts
                codex_result["image_path"] = image_path
                codex_result["html_path"] = None
                return codex_result

        if provider in ("auto", "sd_webui"):
            sd_result = _generate_with_sd_webui(normalized, image_path)
            attempts.append({"provider": "sd_webui", "ok": sd_result.get("ok"), "error": sd_result.get("error")})
            if sd_result.get("ok"):
                sd_result.update({"prompt": normalized, "html_path": None})
                return sd_result
            if provider == "sd_webui":
                sd_result["attempts"] = attempts
                sd_result["image_path"] = image_path
                sd_result["html_path"] = None
                return sd_result

        if provider in ("auto", "stock"):
            stock_result = _generate_with_stock_photo(normalized, image_path)
            attempts.append({"provider": "stock", "ok": stock_result.get("ok"), "error": stock_result.get("error")})
            if stock_result.get("ok"):
                stock_result.update({"prompt": normalized, "html_path": None, "attempts": attempts})
                return stock_result
            if provider == "stock":
                stock_result["attempts"] = attempts
                stock_result["image_path"] = image_path
                stock_result["html_path"] = None
                return stock_result

        canvas_result = await _generate_with_canvas(normalized, html_path, image_path)
        attempts.append({"provider": "canvas", "ok": canvas_result.get("ok"), "error": canvas_result.get("error")})
        if canvas_result.get("ok"):
            canvas_result["attempts"] = attempts
            return canvas_result

        return {
            "ok": False,
            "error": "All providers failed.",
            "attempts": attempts,
            "html_path": html_path,
            "image_path": image_path,
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "attempts": attempts,
            "html_path": html_path,
            "image_path": image_path,
        }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python image_gen.py <prompt>")
        sys.exit(1)

    result = asyncio.run(generate_image(" ".join(sys.argv[1:])))
    # Windows cp949 consoles can fail on raw unicode from subprocess logs.
    # Emit one ASCII-safe JSON line for stable parent parsing.
    print(json.dumps(result, ensure_ascii=True))
    sys.exit(0 if result.get("ok") else 1)
