---
name: web_recon
description: Autonomous web reconnaissance and design analysis using Playwright.
---

# Web Reconnaissance Skill (`web_recon`)

This skill enables the agent to research real-world websites, extract their architectural structure (Header, Sections, Footer), and capture visual references. This intelligence is fed back to the design engine to generate high-fidelity, benchmarking-based landing pages.

## Skill Capabilities

- **Site Crawling**: Navigates to target URLs and waits for full content rendering.
- **Structural Analysis**: Identifies and categorizes DOM elements into "Header", "Hero", "Features", "Footer", etc.
- **Data Extraction**: Collects typography (fonts), color schemes (computed CSS), and component lists.
- **Visual Evidence**: Captures full-page screenshots for the LLM to analyze the "mood" and "energy" of the site.

## Usage Guide

### 1. Topic-Based Reconnaissance
Ask Codex to find and analyze reference sites for a niche.
> "Reconnaissance top 3 minimal portfolio sites and report their section headers."

### 2. Deep Dive Analysis
Provide a specific URL for architectural extraction.
> "Analyze the structure of 'https://example-cafe.com' and extract its color palette and section list."

## Implementation Details

The skill uses `recon_engine.py` to perform the heavy lifting of browser automation.

### Script: `recon_engine.py`
Usage: `python skills/web_recon/recon_engine.py --url "<url>" --output_dir "<dir>"`

**Outputs**:
- `structure.json`: A JSON map of identified sections and their metadata (text, tags, colors).
- `screenshot.png`: A full-page visual capture.

## Design Workflow Integration

1. **Recon Phase**: Use `web_recon` to gather intelligence.
2. **Analysis Phase**: LLM processes `structure.json` to identify modern patterns.
3. **Execution Phase**: LLM uses `web_gen` with Tailwind CSS to build the enhanced project.
