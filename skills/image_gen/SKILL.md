---
name: image_gen
description: "Generates images through multiple providers (Codex native image, SD WebUI, stock photo fallback, canvas rendering)."
---

# Image Generation (Multi-Provider)

## Overview
This skill uses a reliability-first provider chain:
1. `codex_cli` native image path (when available)
2. `sd_webui` local Stable Diffusion API
3. `stock` photoreal fallback (LoremFlickr)
4. `canvas` deterministic local render (Playwright screenshot)

## Core Capabilities
1. **Photoreal Priority**: Attempts real-image providers first (`codex_cli`, `sd_webui`, `stock`).
2. **Deterministic Fallback**: Uses local Canvas + Playwright when photoreal providers are unavailable.
3. **Portable CLI**: `skills/image_gen/image_gen.py "<prompt>"` always returns JSON payload with provider/error.

## Usage Protocol
1. **Install Browser Runtime (one-time)**: Run `python -m playwright install chromium`.
2. **Default Use**: Run `python skills/image_gen/image_gen.py "<prompt>"` (`IMAGE_GEN_PROVIDER=auto`).
3. **Forced Provider**: Override via `IMAGE_GEN_PROVIDER` (`codex_cli`, `sd_webui`, `stock`, `canvas`).
4. **Send**: Use `core.send_photo` to deliver the output image path.

## Best Practices
- **Explicit Width/Height**: Always define fixed dimensions for the canvas element.
- **Wait for Rendering**: If the JS code involves complex recursive drawing or animations, increase the `wait_time` parameter in the renderer.
- **Aesthetics**: Use modern color palettes (vibrant gradients, glassmorphism) to ensure the generated art looks premium.
