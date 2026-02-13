---
name: image_gen
description: "Generates high-resolution images locally using HTML5 Canvas and Playwright. This skill allows the bot to 'code' its own artwork (abstract art, charts, logos, robots) without any external API costs by rendering a local HTML file and capturing a screenshot."
---

# Image Generation (Canvas Rendering)

## Overview
This skill implements the "non-API" image generation approach. Instead of calling expensive external services, it utilizes the bot's coding capabilities to create images.

## Core Capabilities
1. **Dynamic HTML/Canvas Generation**: The agent writes full HTML5/Canvas/JS code based on the user's prompt.
2. **Local Headless Rendering**: Uses `canvas_render.py` (Playwright) to open the HTML and capture a 1200x1200px screenshot.
3. **Zero Cost**: Entirely free and unlimited as it runs on local hardware/browser sessions.

## Usage Protocol
1. **Install Browser Runtime (one-time)**: Run `python -m playwright install chromium`.
2. **Create HTML**: Code the visual logic in an HTML file. Wrap the target drawing area in a `<div id="canvas-container">`.
3. **Render**: Run `python skills/image_gen/canvas_render.py <input.html> <output.png>`.
4. **Send**: Use `core.send_photo` to deliver the final image to the user.

## Best Practices
- **Explicit Width/Height**: Always define fixed dimensions for the canvas element.
- **Wait for Rendering**: If the JS code involves complex recursive drawing or animations, increase the `wait_time` parameter in the renderer.
- **Aesthetics**: Use modern color palettes (vibrant gradients, glassmorphism) to ensure the generated art looks premium.
