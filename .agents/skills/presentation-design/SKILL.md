---
name: presentation-design
description: Guidelines and design tokens for building clean, modern, rounded, publication-grade academic and conference presentation slides (.pptx). Use whenever designing, generating, or refactoring slide decks.
---

# Presentation Design Skill

Guidelines for building clean, modern, readable, and beautifully proportioned PowerPoint (`.pptx`) slides for academic monitoring, thesis defenses, conference talks, and executive presentations.

## Core Design Principles

### 1. Breathable Layouts (No Rigid Header Chrome)
- **Avoid artificial UI chrome:** Do not place heavy multi-tab navigation bars, dense section tracking rows, or time pills at the top of content slides. These make slides feel rigid, cluttered, and strange.
- **Top hierarchy:**
  1. Small rounded category pill tag (e.g., `SECTION 1  •  BACKGROUND`) at the top left.
  2. Clear, prominent slide title (22–26pt bold, dark slate `#1E293B`).
  3. One-line subtitle or takeaway (12–13pt muted slate `#64748B`).
- **Vertical breathing room:** Start the content area around `top = 1.60"` to `1.70"`, giving at least 5.0 inches of vertical space for cards, figures, or tables.

### 2. Modern Rounded Geometry
- **Rounded cards:** Use `MSO_SHAPE.ROUNDED_RECTANGLE` with a subtle corner radius (`adjustments[0] = 0.04` to `0.06`).
- **Capsule pills & badges:** Use `adjustments[0] = 0.5` for pill tags and metadata badges.
- **No harsh top stripes:** Do not glue sharp rectangular color bars to the top of rounded cards. Instead, use soft card background fills (`#FFFFFF` or `#F8FAFC`), gentle borders (`#E2E8F0` or `#CBD5E1`), and pill badges.
- **Soft tinted callouts:** For highlight cards, use a gentle background tint (e.g. `#FDF2F2` for crimson accents) with a matching soft border (`#F5C2C4`).

### 3. Collision-Proof Text Flow
- **Single text frame for cards:** Place the card title, spacing, and bullet points within the same text frame using paragraph sequencing (`space_after = Pt(8)` to `Pt(10)`).
- **Why this matters:** When card titles wrap to 2 or 3 lines, a single text frame automatically pushes the following bullet paragraphs downward. Never place a hardcoded divider line or separate bullet text box at a fixed Y coordinate below a title, as multi-line wrapping will cause severe visual overlap.

### 4. Typography & Visual Hierarchy
- **Font:** Clean, universally compatible sans-serif (`Calibri`, `Carlito`, `Arial`).
- **Slide Title:** 22–24pt Bold (`#1E293B` Dark Slate).
- **Card Titles:** 13–15pt Bold (`#1E293B` Dark Slate).
- **Body & Bullets:** 11–12.5pt Regular (`#334155` Slate Body). Bold key phrases for rapid scannability.
- **Captions & Metadata:** 9.5–10.5pt (`#64748B` Slate Muted).

### 5. Color Palette (Academic & Telkom University)
- **Primary Accent:** Telkom University Crimson `#B6252A` (`RGBColor(182, 37, 42)`).
- **Dark Neutral:** Dark Slate `#1E293B` (`RGBColor(30, 41, 59)`).
- **Body Text:** Slate `#334155` (`RGBColor(51, 65, 85)`).
- **Muted Text:** Slate Muted `#64748B` (`RGBColor(100, 116, 139)`).
- **Card Background:** Crisp White `#FFFFFF` or Light Slate `#F8FAFC`.
- **Card Border:** Subtle Slate `#E2E8F0` (`RGBColor(226, 232, 240)`).
- **Soft Accent Tint:** Crimson Soft `#FDF2F2`, Crimson Border `#F5C2C4`.

### 6. Speaker Notes & Script
- Embed full spoken scripts in each slide's speaker notes with time targets, formatted to plain formal academic English (no `, and`, no em dashes, no marker vocabulary, steady rhythm).
