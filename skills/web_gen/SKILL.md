---
name: web_gen
description: Automated HTML5/CSS3 landing page generation with local asset integration.
---

# Web Landing Page Generation Skill (`web_gen`)

This skill enables the autonomous creation of professional, responsive web landing pages. It leverages the `image_gen` skill to create custom visual assets (logos, heroes, icons) locally, ensuring a complete, ready-to-use web package without external API costs.

## Skill Capabilities

- **Intelligent Layout Design**: Generates modern HTML5/CSS3 structures based on user briefs.
- **Local Asset Integration**: Automatically triggers the `image_gen` skill to create required images.
- **Responsive Styling**: Uses vanilla CSS with modern techniques (Flexbox, Grid) for mobile-friendly designs.
- **Self-Contained Packages**: Organizes HTML, CSS, and images into a single project folder.

## Usage Guide

### 1. Simple Generation
Ask Codex to create a landing page for a specific topic.
> "Create a landing page for a coffee shop called 'Lunar Brew' with a minimalist dark theme."

### 2. Asset-Rich Generation
Codex will identify image needs and use its sub-tools to create them.
> "Build a landing page for 'CyberDrone' delivery. Generate a hero image of a drone in a neon city and a logo."

## Design Systems & Principles

Before generating any code, you must select a design system that matches the brand's identity and energy.

### Premium Color Palettes (Reference)
- **Classic Blue**: Deep navy (#1C2833), slate gray (#2E4053), silver (#AAB7B8), off-white (#F4F6F6)
- **Teal & Coral**: Teal (#5EA8A7), deep teal (#277884), coral (#FE4447), white (#FFFFFF)
- **Burgundy Luxury**: Burgundy (#5D1D2E), crimson (#951233), rust (#C15937), gold (#997929)
- **Deep Purple & Emerald**: Purple (#B165FB), dark blue (#181B24), emerald (#40695B)
- **Black & Gold**: Gold (#BF9A4A), black (#000000), cream (#F4F6F6)
- **Sage & Terracotta**: Sage (#87A96B), terracotta (#E07A5F), charcoal (#2C2C2C)

### Typography Rules
- **Modern Minimalist**: Inter, Roboto, or Outfit for body; Bold headers.
- **Visual Hierarchy**: Use extreme size contrast (e.g., 64px for Hero Title vs 16px for body).
- **Whitespace**: Ensure generous padding (80px-120px) between major sections.

## Recursive Asset Generation & Sealing Protocol

1. **Blueprint**: Identify specific image requirements (Logo, Hero, Icons).
2. **Local Generation**: For each asset, create a dedicated Canvas script and use `image_gen` to render it.
3. **Injection**: Save assets to `./assets/` and reference them dynamically in the HTML/CSS (e.g., `src='assets/hero.png'`).
1.  **Blueprint**: Identify specific image requirements (Logo, Hero, Icons).
2.  **Local Generation**: For each asset, create a dedicated Canvas script and use `image_gen` to render it.
3.  **Injection**: Save assets to `./assets/` and reference them dynamically in the HTML/CSS (e.g., `src='assets/hero.png'`).
4.  **Sealing (Optional)**: Once assets are ready, run `web_builder.py --seal` to sweep the project and convert all local images to Base64 data URIs. This is useful for zero-dependency portability.

## Operational Modes

### Asset Operational Modes

1.  **Link Mode (Default)**: Use relative paths for assets. Ideal for professional development.
2.  **Seal Mode**: Embed assets as Base64 for a portable, single-file delivery.

### High-Fidelity Visual Protocol (Elite Standard)

- **Photorealistic Priority**: For "Elite" or "Premium" projects, **never** use abstract blueprints or minimal vector-like images if photorealistic assets are feasible.
- **Smart Generation**: Always use the `generate_image` tool with descriptive, professional photography prompts (e.g., "Cinematic lighting", "Macro food photography", "Minimalist architectural interior").
- **Asset Placement**: All generated assets must be saved to `[project]/assets/` and linked via relative paths in `index.html`.
- **Placeholder Fallback**: If generation is unavailable, use high-fidelity Unsplash or professional placeholders that match the brand's aesthetic, never basic solid-color divs.

### Anti-Screenshot Protocol (Context-Aware)

- **Asset Mode (Strict)**: 
    - Full-page screenshots or viewport captures are **REJECTED** as component assets.
    - Assets must be isolated visual elements (e.g., product shot, icon, texture).
- **Design Mode (Open)**:
    - Full-page screenshots are **ALLOWED** if explicitly tagged as "references" or stored in a `references/` folder.
    - Use this mode for analyzing layouts, inspiration, or optimal design research.
- **Validation**: `web_builder.py` enforces this distinction via the `is_reference` flag or `type="reference"`.

## Script: `web_builder.py`
Usage: `python skills/web_gen/web_builder.py --project "<name>" [--link | --seal]`

**Enhanced Features**:
- **Automatic Smart Sync**: In Link Mode, the script automatically copies referenced assets from the environment to the project's local `/assets/` directory.
- **Folder Management**: Creates project and assets structural hierarchy.
- **Glassmorphism & Micro-animations**: Integrated into the default CSS components.

## Design Principles

- **Rich Imagery**: Always generate high-fidelity assets for every card and section.
- **Zero Dependencies**: Aim for self-contained packages via Base64 embedding.
- **Premium Aesthetics**: Use modern typography (Inter), 8pt grids, and clean whitespace.
- **SEO Optimized**: Include proper meta tags and semantic HTML.

