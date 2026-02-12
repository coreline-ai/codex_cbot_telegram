---
name: web_variator
description: Creates and compares multiple design variations for a project.
---

# Web Design Variator Skill (`web_variator`)

This skill generates 3 distinct design directions (e.g., Minimal, Bold, Classic) and provides a single comparison image for the user to choose from.

## Protocol
1. **Theming**: Selects 3 distinct CSS variable sets.
2. **Batching**: Triggers 3 parallel `web_builder` runs.
3. **Grid Preview**: Uses `canvas_render` to create a side-by-side comparison screenshot.
