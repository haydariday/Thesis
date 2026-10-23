# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "python-pptx>=1.0.2",
#     "pillow>=10.0.0",
# ]
# ///
"""Build thesis-progress-slides.pptx from the Thesis 1 Progress Report (Sections 1 to 5).

Clean, modern, rounded academic presentation style without artificial tracking headers.
Usage:
    uv run docs/thesis-1/build_slides.py
"""
from __future__ import annotations

import re
from pathlib import Path
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

HERE = Path(__file__).resolve().parent
MD_SCRIPT = HERE / "thesis-progress-slides.md"
OUT_PPTX = HERE / "thesis-progress-slides.pptx"

FIG_FRAMEWORK = HERE / "figures/fig-framework.png"
FIG_DEBATE = HERE / "figures/fig-debate.png"
FIG_DATA_FLOW = HERE / "figures/fig-data-flow.png"
FIG_HUMAN_DIFF = HERE.parent.parent / "experiments/pilot-02/figures/F1_human_difficulty.png"
FIG_CONFUSION = HERE.parent.parent / "experiments/pilot-02-va-analysis/figures/F7_quartile_confusion.png"

# Color Palette: Modern Telkom Crimson + Slate Neutrals
CRIMSON = RGBColor(0xB6, 0x25, 0x2A)        # #B6252A Primary Telkom Crimson
CRIMSON_DARK = RGBColor(0x88, 0x17, 0x1B)   # #88171B Deep Crimson
CRIMSON_SOFT = RGBColor(0xFD, 0xF4, 0xF4)   # #FDF4F4 Very soft crimson tint
CRIMSON_BORDER = RGBColor(0xF5, 0xC6, 0xC8) # #F5C6C8 Soft crimson card border

SLATE_DARK = RGBColor(0x1E, 0x29, 0x3B)     # #1E293B Headings & high-emphasis text
SLATE_BODY = RGBColor(0x33, 0x41, 0x55)     # #334155 Body / bullet text
SLATE_MUTED = RGBColor(0x64, 0x74, 0x8B)    # #64748B Subtitles, captions & metadata
SLATE_LIGHT = RGBColor(0xF8, 0xFA, 0xFC)    # #F8FAFC Card surface background
SLATE_ALT = RGBColor(0xF1, 0xF5, 0xF9)      # #F1F5F9 Table alternating row
SLATE_BORDER = RGBColor(0xE2, 0xE8, 0xF0)   # #E2E8F0 Soft modern card border
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

FONT_MAIN = "Calibri"


def load_spoken_scripts() -> dict[int, tuple[str, str]]:
    """Parse (timing_label, spoken_script) for each slide 1..16 from thesis-progress-slides.md."""
    text = MD_SCRIPT.read_text(encoding="utf-8").split("## References")[0]
    blocks = text.split("## Slide ")[1:]
    scripts: dict[int, tuple[str, str]] = {}
    for blk in blocks:
        first_line = blk.splitlines()[0].strip()
        m_num = re.match(r"^(\d+):", first_line)
        m_time = re.search(r"\(([^)]+)\)\s*$", first_line)
        if not m_num:
            continue
        slide_no = int(m_num.group(1))
        timing = m_time.group(1) if m_time else ""
        parts = blk.split("**Spoken Script:**")
        spoken = parts[1].strip().split("---")[0].strip() if len(parts) > 1 else ""
        scripts[slide_no] = (timing, spoken)
    return scripts


def add_rounded_rect(slide, left: float, top: float, width: float, height: float,
                     fill: RGBColor, border: RGBColor | None = None, border_pt: float = 1.0,
                     radius_adj: float = 0.04):
    """Add a smooth rounded rectangle shape."""
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    if shp.adjustments:
        shp.adjustments[0] = radius_adj
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if border is not None:
        shp.line.color.rgb = border
        shp.line.width = Pt(border_pt)
    else:
        shp.line.fill.background()
    return shp


def add_rich_paragraph(tf, text: str, font_size: float = 12.0, color: RGBColor = SLATE_BODY,
                       bold: bool = False, space_after: float = 5.0, space_before: float = 0.0,
                       align=PP_ALIGN.LEFT, bullet: bool = False, line_spacing: float = 1.15):
    """Append or populate a paragraph supporting **bold** and *italic* tokens."""
    if len(tf.paragraphs) == 1 and tf.paragraphs[0].text == "" and len(tf.paragraphs[0].runs) == 0:
        p = tf.paragraphs[0]
    else:
        p = tf.add_paragraph()
    p.alignment = align
    p.space_after = Pt(space_after)
    p.space_before = Pt(space_before)
    p.line_spacing = line_spacing

    prefix = "•  " if bullet else ""
    full = prefix + text
    tokens = re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", full)
    for tok in tokens:
        if not tok:
            continue
        r = p.add_run()
        r.font.name = FONT_MAIN
        r.font.size = Pt(font_size)
        if tok.startswith("**") and tok.endswith("**"):
            r.text = tok[2:-2]
            r.font.bold = True
            r.font.color.rgb = SLATE_DARK if color == SLATE_BODY else color
        elif tok.startswith("*") and tok.endswith("*"):
            r.text = tok[1:-1]
            r.font.italic = True
            r.font.color.rgb = color
        else:
            r.text = tok
            r.font.bold = bold
            r.font.color.rgb = color
    return p


def add_rounded_card(slide, left: float, top: float, width: float, height: float,
                     title: str | None, items: list[str], badge: str | None = None,
                     fill: RGBColor = WHITE, border: RGBColor = SLATE_BORDER,
                     font_size: float = 12.0, bullet: bool = True, space_after: float = 6.0,
                     radius_adj: float = 0.04, pad_y: float = 0.16):
    """Add a modern rounded card with collision-proof single text-frame layout."""
    # Outer rounded card background
    add_rounded_rect(slide, left, top, width, height, fill=fill, border=border, border_pt=1.0, radius_adj=radius_adj)

    pad_x = 0.22

    # Optional pill badge at top left of card
    title_top = top + pad_y
    if badge:
        b_w = max(0.55, len(badge) * 0.082 + 0.22)
        b_shp = add_rounded_rect(slide, left + pad_x, top + pad_y, b_w, 0.26, fill=CRIMSON_SOFT, border=CRIMSON_BORDER, border_pt=0.8, radius_adj=0.5)
        btf = b_shp.text_frame
        btf.vertical_anchor = MSO_ANCHOR.MIDDLE
        btf.margin_left = btf.margin_right = btf.margin_top = btf.margin_bottom = 0
        add_rich_paragraph(btf, badge, font_size=9.5, color=CRIMSON_DARK, bold=True, space_after=0, align=PP_ALIGN.CENTER)
        title_top = top + pad_y + 0.32

    # Single text box for title + bullets: guarantees title wrapping never overlaps bullets!
    content_w = width - (2 * pad_x)
    content_h = (top + height) - title_top - pad_y
    tb = slide.shapes.add_textbox(Inches(left + pad_x), Inches(title_top), Inches(content_w), Inches(content_h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0

    # Title paragraph inside the frame (if provided)
    if title:
        add_rich_paragraph(tf, title, font_size=13.5, color=SLATE_DARK, bold=True, space_after=6.5, space_before=0.0)

    # Bullet paragraphs
    for item in items:
        add_rich_paragraph(tf, item, font_size=font_size, color=SLATE_BODY, bullet=bullet, space_after=space_after)


def add_rounded_callout(slide, left: float, top: float, width: float, height: float,
                        text: str, font_size: float = 12.0, radius_adj: float = 0.05):
    """Add a gentle rounded callout banner."""
    add_rounded_rect(slide, left, top, width, height, fill=CRIMSON_SOFT, border=CRIMSON_BORDER, border_pt=1.0, radius_adj=radius_adj)
    tb = slide.shapes.add_textbox(Inches(left + 0.24), Inches(top + 0.08), Inches(width - 0.48), Inches(height - 0.16))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    add_rich_paragraph(tf, text, font_size=font_size, color=SLATE_DARK, space_after=0)


def add_rounded_kpi(slide, left: float, top: float, width: float, height: float,
                    value: str, label: str, sublabel: str = "", radius_adj: float = 0.06):
    """Add a clean rounded KPI metric box."""
    add_rounded_rect(slide, left, top, width, height, fill=WHITE, border=SLATE_BORDER, border_pt=1.0, radius_adj=radius_adj)
    tb = slide.shapes.add_textbox(Inches(left + 0.10), Inches(top + 0.10), Inches(width - 0.20), Inches(height - 0.20))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    add_rich_paragraph(tf, value, font_size=20.0, color=CRIMSON, bold=True, space_after=2.0, align=PP_ALIGN.CENTER)
    add_rich_paragraph(tf, label, font_size=11.0, color=SLATE_DARK, bold=True, space_after=1.0, align=PP_ALIGN.CENTER)
    if sublabel:
        add_rich_paragraph(tf, sublabel, font_size=9.5, color=SLATE_MUTED, space_after=0, align=PP_ALIGN.CENTER)


def add_rounded_image_frame(slide, img_path: Path, box_left: float, box_top: float,
                            box_width: float, box_height: float, caption: str | None = None,
                            radius_adj: float = 0.03):
    """Embed an image within a rounded card frame with an optional caption."""
    add_rounded_rect(slide, box_left, box_top, box_width, box_height, fill=WHITE, border=SLATE_BORDER, border_pt=1.0, radius_adj=radius_adj)
    cap_h = 0.36 if caption else 0.0
    pad = 0.12
    avail_w = box_width - (2 * pad)
    avail_h = box_height - (2 * pad) - cap_h

    with Image.open(img_path) as im:
        w_px, h_px = im.size
    aspect = w_px / h_px
    if avail_w / avail_h > aspect:
        draw_h = avail_h
        draw_w = draw_h * aspect
    else:
        draw_w = avail_w
        draw_h = draw_w / aspect

    img_x = box_left + pad + (avail_w - draw_w) / 2
    img_y = box_top + pad + (avail_h - draw_h) / 2
    slide.shapes.add_picture(str(img_path), Inches(img_x), Inches(img_y), width=Inches(draw_w), height=Inches(draw_h))

    if caption:
        tb = slide.shapes.add_textbox(Inches(box_left + pad), Inches(box_top + box_height - cap_h - 0.06),
                                      Inches(avail_w), Inches(cap_h))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        add_rich_paragraph(tf, caption, font_size=9.5, color=SLATE_MUTED, space_after=0, align=PP_ALIGN.CENTER)


def add_styled_table(slide, left: float, top: float, width: float, height: float,
                     headers: list[str], rows: list[list[str]], col_widths: list[float],
                     font_size: float = 11.0, align_cols: list[PP_ALIGN] | None = None,
                     highlight_rows: set[int] | None = None):
    """Add a clean, beautifully styled PowerPoint table."""
    n_rows = len(rows) + 1
    n_cols = len(headers)
    table_shape = slide.shapes.add_table(n_rows, n_cols, Inches(left), Inches(top), Inches(width), Inches(height))
    tbl = table_shape.table

    for idx, cw in enumerate(col_widths):
        tbl.columns[idx].width = Inches(cw)

    # Header row
    for c_idx, h_text in enumerate(headers):
        cell = tbl.cell(0, c_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = SLATE_DARK
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.margin_left = cell.margin_right = Inches(0.08)
        cell.margin_top = cell.margin_bottom = Inches(0.04)
        tf = cell.text_frame
        tf.word_wrap = True
        al = align_cols[c_idx] if align_cols else (PP_ALIGN.LEFT if c_idx == 0 else PP_ALIGN.CENTER)
        add_rich_paragraph(tf, h_text, font_size=font_size, color=WHITE, bold=True, space_after=0, align=al)

    # Data rows
    for r_idx, row in enumerate(rows):
        is_hi = highlight_rows and r_idx in highlight_rows
        bg = CRIMSON_SOFT if is_hi else (WHITE if r_idx % 2 == 0 else SLATE_ALT)
        for c_idx, val in enumerate(row):
            cell = tbl.cell(r_idx + 1, c_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = bg
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left = cell.margin_right = Inches(0.08)
            cell.margin_top = cell.margin_bottom = Inches(0.04)
            tf = cell.text_frame
            tf.word_wrap = True
            al = align_cols[c_idx] if align_cols else (PP_ALIGN.LEFT if c_idx == 0 else PP_ALIGN.CENTER)
            add_rich_paragraph(
                tf,
                val,
                font_size=font_size,
                color=CRIMSON_DARK if is_hi and c_idx > 0 else (SLATE_DARK if c_idx == 0 else SLATE_BODY),
                bold=(c_idx == 0 or is_hi),
                space_after=0,
                align=al,
            )
    return table_shape


def new_content_slide(prs: Presentation, slide_no: int, total_slides: int,
                      category_label: str, title: str, subtitle: str,
                      timing: str, spoken_script: str, refs_short: str = "",
                      header_width: float = 12.133):
    """Create a clean slide with no rigid tracking headers and ample breathing room."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Top category rounded pill badge
    cat_w = max(1.10, len(category_label) * 0.088 + 0.28)
    cat_shp = add_rounded_rect(slide, 0.60, 0.48, cat_w, 0.28, fill=CRIMSON_SOFT, border=CRIMSON_BORDER, border_pt=0.8, radius_adj=0.5)
    ctf = cat_shp.text_frame
    ctf.vertical_anchor = MSO_ANCHOR.MIDDLE
    ctf.margin_left = ctf.margin_right = ctf.margin_top = ctf.margin_bottom = 0
    add_rich_paragraph(ctf, category_label, font_size=9.5, color=CRIMSON_DARK, bold=True, space_after=0, align=PP_ALIGN.CENTER)

    # Slide Title
    tb_title = slide.shapes.add_textbox(Inches(0.60), Inches(0.82), Inches(header_width), Inches(0.42))
    ttf = tb_title.text_frame
    ttf.word_wrap = True
    ttf.margin_left = ttf.margin_right = ttf.margin_top = ttf.margin_bottom = 0
    add_rich_paragraph(ttf, title, font_size=22.0, color=SLATE_DARK, bold=True, space_after=0)

    # Subtitle
    tb_sub = slide.shapes.add_textbox(Inches(0.60), Inches(1.24), Inches(header_width), Inches(0.30))
    stf = tb_sub.text_frame
    stf.word_wrap = True
    stf.margin_left = stf.margin_right = stf.margin_top = stf.margin_bottom = 0
    add_rich_paragraph(stf, subtitle, font_size=12.0, color=SLATE_MUTED, space_after=0)

    # Subtle bottom divider and footer
    add_rounded_rect(slide, 0.60, 7.08, 12.133, 0.012, fill=SLATE_BORDER, border=None)

    footer_text = "Muhammad Haydar Maulana [203012510020]  |  Master of Informatics, Telkom University"
    if refs_short:
        footer_text += f"   •   Refs: {refs_short}"
    tb_fl = slide.shapes.add_textbox(Inches(0.60), Inches(7.14), Inches(10.6), Inches(0.26))
    fltf = tb_fl.text_frame
    fltf.margin_left = fltf.margin_right = fltf.margin_top = fltf.margin_bottom = 0
    add_rich_paragraph(fltf, footer_text, font_size=9.0, color=SLATE_MUTED, space_after=0)

    tb_fr = slide.shapes.add_textbox(Inches(11.3), Inches(7.12), Inches(1.433), Inches(0.26))
    frtf = tb_fr.text_frame
    frtf.margin_left = frtf.margin_right = frtf.margin_top = frtf.margin_bottom = 0
    add_rich_paragraph(frtf, f"Slide {slide_no} / {total_slides}", font_size=9.5, color=CRIMSON, bold=True, space_after=0, align=PP_ALIGN.RIGHT)

    # Speaker Notes (Spoken Script)
    notes_tf = slide.notes_slide.notes_text_frame
    notes_tf.text = f"[Slide {slide_no}/{total_slides} | {timing}] {title}\n\n{spoken_script}"
    return slide


def build_deck() -> Path:
    scripts = load_spoken_scripts()
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    total_slides = 17

    # =========================================================================
    # SLIDE 1: TITLE SLIDE (Modern Rounded Layout)
    # =========================================================================
    s1 = prs.slides.add_slide(prs.slide_layouts[6])
    t1_time, t1_script = scripts[1]

    # University & Monitoring Capsule Pill
    p_shp = add_rounded_rect(s1, 0.85, 0.70, 4.80, 0.36, fill=CRIMSON_SOFT, border=CRIMSON_BORDER, border_pt=1.0, radius_adj=0.5)
    ptf = p_shp.text_frame
    ptf.vertical_anchor = MSO_ANCHOR.MIDDLE
    ptf.margin_left = ptf.margin_right = ptf.margin_top = ptf.margin_bottom = 0
    add_rich_paragraph(
        ptf,
        "THESIS 1 PROGRESS REPORT  •  FIRST MONITORING",
        font_size=10.5,
        color=CRIMSON_DARK,
        bold=True,
        space_after=0,
        align=PP_ALIGN.CENTER,
    )

    # Main Title & Subtitle
    tb_title = s1.shapes.add_textbox(Inches(0.85), Inches(1.22), Inches(11.6), Inches(1.12))
    ttf = tb_title.text_frame
    ttf.word_wrap = True
    add_rich_paragraph(
        ttf,
        "Persona-Based Multi-Agent LLM Debate as an Automated Playtester:",
        font_size=27.0,
        color=SLATE_DARK,
        bold=True,
        space_after=5.0,
    )
    add_rich_paragraph(
        ttf,
        "Validating Game Difficulty Data Against Human Performance Baselines",
        font_size=22.5,
        color=CRIMSON,
        bold=True,
        space_after=0.0,
    )

    # Author Rounded Card (matching user's simplified Slide 1 layout)
    add_rounded_card(
        s1, 0.85, 2.74, 5.65, 2.50,
        title="Submitted By",
        badge="AUTHOR",
        items=[
            "**Muhammad Haydar Maulana** [203012510020]",
            "Concentration: **Informatics Software Engineering**",
            "Master of Informatics (MIF), Telkom University",
            "E-mail: haydariday@gmail.com",
        ],
        font_size=13.0,
        bullet=False,
        space_after=6.5,
        radius_adj=0.04,
    )
    s1.notes_slide.notes_text_frame.text = f"[Slide 1/{total_slides} | {t1_time}] Title Slide\n\n{t1_script}"

    # =========================================================================
    # SLIDE 2: 1. BACKGROUND (PART 1)
    # =========================================================================
    t_time, t_script = scripts[2]
    s2 = new_content_slide(
        prs, 2, total_slides, "SECTION 1  •  BACKGROUND",
        "1. Background: The Playtesting Cost Problem",
        "Why game difficulty balancing matters and why manual playtesting is prohibitive for indie developers.",
        t_time, t_script,
        refs_short="Xiao & Yang [1]; Weber [2]; Karavidas [3]; Prasetya [6]; Zhao [7]; Francillette [8]; Delfosse [9]",
    )

    add_rounded_card(
        s2, 0.60, 1.68, 3.85, 4.45,
        title="Why Difficulty Matters",
        badge="1A",
        items=[
            "**Key question:** \"Is the game hard enough for the intended player?\" [2].",
            "**Too hard:** Drives players away and causes early frustration [3].",
            "**Too easy:** Quickly becomes stale and loses engagement [3].",
            "**Impact:** Both extremes hurt retention, player reviews and reception [3], [4], [5].",
        ],
        font_size=12.0,
        space_after=8.0,
    )

    add_rounded_card(
        s2, 4.74, 1.68, 3.85, 4.45,
        title="Manual Playtesting Limits",
        badge="1B",
        items=[
            "**How designers test:** Repeated human playtesting sessions [2].",
            "**Resource-intensive:** Requires many human testers over multiple sessions [2], [6], [7].",
            "**Iterative burden:** Must be repeated after every significant design update [6], [7].",
            "**Indie barrier:** Prohibitive cost and time for budget-constrained indie developers.",
        ],
        font_size=12.0,
        space_after=8.0,
    )

    add_rounded_card(
        s2, 8.88, 1.68, 3.85, 4.45,
        title="Automated Alternatives",
        badge="1C",
        items=[
            "**Hand-crafted agents:** Programmed agents [6] and math models [8] need heavy per-game coding.",
            "**Deep RL:** Needs large training compute while playing unlike human players [9].",
            "**LLM agents:** Play games from text rules alone without task-specific training [10], [11], [12].",
            "**Difficulty tracking:** Xiao and Yang [1] show LLM difficulty in Wordle follows human difficulty.",
        ],
        font_size=11.8,
        space_after=7.0,
    )

    add_rounded_callout(
        s2, 0.60, 6.26, 12.133, 0.62,
        "**Key Takeaway:** LLM agents avoid per-game engineering and RL training while experiencing difficulty that tracks human players [1].",
    )

    # =========================================================================
    # SLIDE 3: 1. BACKGROUND (PART 2)
    # =========================================================================
    t_time, t_script = scripts[3]
    s3 = new_content_slide(
        prs, 3, total_slides, "SECTION 1  •  BACKGROUND",
        "1. Background: The Gap in Playstyle Diversity and Consensus",
        "Moving from single-agent LLM playtesting to a consistent, human-aligned multi-agent debate playtester.",
        t_time, t_script,
        refs_short="Xiao & Yang [1]; Sreedhar & Chilton [13]; Constant et al. [14]",
    )

    add_rounded_card(
        s3, 0.60, 1.68, 5.90, 3.55,
        title="The Research Gap in LLM Playtesting",
        badge="RESEARCH GAP",
        items=[
            "**Single playstyle limitation:** Prior LLM playtesters [1] rely on a single agent playing with one rigid prompt style.",
            "**Human strategic diversity:** Real players differ in strategy, as some take risks while others play safely.",
            "**Strategic reasoning fidelity:** Single LLMs replicate human strategic behavior less closely than multi-agent systems do [13].",
            "**Missing consensus:** Multi-agent debate could reconcile several playstyles into one consensus action, yet remains absent from difficulty measurement.",
        ],
        font_size=12.0,
        space_after=6.5,
    )

    add_rounded_card(
        s3, 6.83, 1.68, 5.90, 3.55,
        title="Two Required Conditions Before Use",
        badge="CONDITIONS",
        items=[
            "**1. Outcome consistency across runs:** Since LLM outputs vary between calls, the same puzzle can end differently. Xiao and Yang [1] play 20 runs per puzzle yet report only the mean, leaving run-to-run consistency unknown.",
            "**2. Agreement with human difficulty:** A consistent playtester that finds every puzzle equally easy is still of no practical value.",
            "**Actionable insights:** Practical utility for game designers requires direct expert validation.",
        ],
        font_size=12.0,
        space_after=6.5,
    )

    add_rounded_card(
        s3, 0.60, 5.38, 12.133, 1.50,
        title="Proposed Solution: Persona-Based Multi-Agent LLM Debate on Wordle",
        badge=None,
        fill=CRIMSON_SOFT,
        border=CRIMSON_BORDER,
        items=[
            "**Objective Difficulty:** Measured from play outcomes (guesses used) rather than subjective player perceptions [14].",
            "**Why Wordle:** Short games, deterministic feedback, studied in [1] and backed by public human guess distributions.",
            "**Practical Value:** Gives indie developers a cheaper source of difficulty data that still reflects diverse human players.",
        ],
        font_size=11.8,
        space_after=4.0,
        pad_y=0.09,
    )

    # =========================================================================
    # SLIDE 4: 2.1 - 2.3 RESEARCH QUESTIONS, OBJECTIVES & HYPOTHESES
    # =========================================================================
    t_time, t_script = scripts[4]
    s4 = new_content_slide(
        prs, 4, total_slides, "SECTION 2.1 – 2.3  •  FOUNDATIONS",
        "2. Objective and Hypotheses: RQs, Objectives and Hypotheses",
        "Direct alignment between the three research questions, the three research objectives and the three hypotheses.",
        t_time, t_script,
    )

    add_rounded_card(
        s4, 0.60, 1.68, 3.85, 5.18,
        title="2.1 Research Questions",
        badge="RQs",
        items=[
            "**RQ1 (Consistency):** How consistent are the Wordle playtest outcomes produced by the persona-based multi-agent debate playtester across repeated runs on the same puzzles?",
            "**RQ2 (Human Agreement):** To what extent do the Wordle difficulty estimates derived from the playtester's outcomes agree with human difficulty, measured by average guess scores and difficulty categories?",
            "**RQ3 (Expert Utility):** How do industry experts evaluate the utility and efficacy of multi-agent LLM debate for automated difficulty testing?",
        ],
        font_size=11.5,
        space_after=8.0,
    )

    add_rounded_card(
        s4, 4.74, 1.68, 3.85, 5.18,
        title="2.2 Objectives",
        badge="OBJECTIVES",
        items=[
            "**Objective 1:** Implement a multi-agent LLM debate framework that operationalizes difficulty measurement through diverse personas, transforming point estimates into consensus-based assessments, with Wordle as the case study.",
            "**Objective 2:** Evaluate outcome consistency across repeated runs and validate agreement with human performance baselines (answers **RQ1** and **RQ2**).",
            "**Objective 3:** Gather expert evaluations regarding utility and efficacy in game development workflows (answers **RQ3**).",
        ],
        font_size=11.5,
        space_after=8.0,
    )

    add_rounded_card(
        s4, 8.88, 1.68, 3.85, 5.18,
        title="2.3 Hypotheses",
        badge="HYPOTHESES",
        items=[
            "*Note: The pilot study is descriptive; H1 and H2 are tested in the final study, while H3 is tested via expert evaluation.*",
            "**H1 (Consistency):** Within-puzzle standard deviation stays below a margin that is fixed from the pilot results before the final run.",
            "**H2 (Human Agreement):** Ranks puzzles in the same order of difficulty as humans while difficulty categories agree beyond chance.",
            "**H3 (Expert Viability):** Industry experts evaluate the framework as viable for automated playtesting.",
        ],
        font_size=11.3,
        space_after=7.0,
    )

    # =========================================================================
    # SLIDE 5: 2.4 METHOD AND CONCEPT (Collision-Proof Cards)
    # =========================================================================
    t_time, t_script = scripts[5]
    s5 = new_content_slide(
        prs, 5, total_slides, "SECTION 2.4  •  CONCEPT",
        "2.4 Method and Concept",
        "Synthesizing persona-based playtesting and multi-agent debate for LLM game difficulty measurement.",
        t_time, t_script,
        refs_short="Xiao & Yang [1]; Sreedhar & Chilton [13]; Holmgård et al. [15]; Liang et al. [16]; Smit et al. [17]",
    )

    # Top 3 pillar cards
    add_rounded_card(
        s5, 0.60, 1.68, 3.85, 2.40,
        title="Playstyle Personas",
        badge="PILLAR 1",
        items=[
            "Adopted from **persona-based playtesting** (Holmgård et al. [15]).",
            "Represents distinct player tendencies (risk-taking, cautious, casual daily play) rather than a single monolithic player.",
        ],
        font_size=12.0,
        space_after=5.0,
    )

    add_rounded_card(
        s5, 4.74, 1.68, 3.85, 2.40,
        title="Multi-Agent Debate Consensus",
        badge="PILLAR 2",
        items=[
            "Adopted from **manager-led multi-agent debate** (Liang et al. [16]).",
            "Advisors critique proposals across rounds while a managing Game Master synthesizes the consensus action.",
        ],
        font_size=12.0,
        space_after=5.0,
    )

    add_rounded_card(
        s5, 8.88, 1.68, 3.85, 2.40,
        title="LLM Difficulty Measurement",
        badge="PILLAR 3",
        items=[
            "Applied to the **outcome-based playtesting** setup of Xiao and Yang [1].",
            "Compares completed playthrough guess counts against human performance baselines on the same puzzles.",
        ],
        font_size=12.0,
        space_after=5.0,
    )

    # Bottom 2 distinction cards (Fixed wrapping titles without collision!)
    add_rounded_card(
        s5, 0.60, 4.22, 5.90, 2.64,
        title="Difference from Single-Agent Playtesting [1]",
        badge="VS. SINGLE AGENT",
        fill=CRIMSON_SOFT,
        border=CRIMSON_BORDER,
        items=[
            "**Xiao and Yang [1]:** Uses a single LLM agent with one prompt style to play each puzzle.",
            "**Our Playtester:** Lets several agents with different playstyles (Bold, Cautious, Casual) debate and decide each guess together under a Game Master.",
        ],
        font_size=12.0,
        space_after=6.0,
    )

    add_rounded_card(
        s5, 6.83, 4.22, 5.90, 2.64,
        title="Difference from Benchmark Studies [13], [17]",
        badge="VALIDATION FOCUS",
        items=[
            "**Benchmark Studies [13], [17]:** Compare multi-agent systems against single-agent baselines on generic reasoning benchmarks.",
            "**Our Validation Focus:** Validates the playtester **as a complete system** against human difficulty data and industry experts, rather than claiming debate beats a single agent.",
        ],
        font_size=12.0,
        space_after=6.0,
    )

    # =========================================================================
    # SLIDE 6: 3.1 EXISTING METHODS
    # =========================================================================
    t_time, t_script = scripts[6]
    s6 = new_content_slide(
        prs, 6, total_slides, "SECTION 3.1  •  LITERATURE",
        "3.1 Existing Software, Systems and Methods",
        "Comparison of hand-crafted, learning-based and LLM-based playtesting and debate methods.",
        t_time, t_script,
        refs_short="Xiao [1]; Prasetya [6]; Zhao [7]; Francillette [8]; Delfosse [9]; Holmgård [15]; Liang [16]; Smit [17]; Gudmundsson [18]; Bateni [19]; Chen [20]; Du [21]; Baltaji [22]",
    )

    add_rounded_card(
        s6, 0.60, 1.68, 3.85, 5.18,
        title="Hand-Crafted Playtesters",
        badge=None,
        items=[
            "**Strengths:** Highly controlled behavior; no neural training required.",
            "**APLib Goal Agents (Prasetya et al. [6]):** Builds test agents with explicit goal structures, requiring heavy programming effort and a steep learning curve.",
            "**Platformer Math Model (Francillette et al. [8]):** Needs no complex AI, yet is restricted to platformer games with a complex setup.",
            "**Core Limitation:** Must be rebuilt from scratch for each new game or genre.",
        ],
        font_size=11.5,
        space_after=6.5,
    )

    add_rounded_card(
        s6, 4.74, 1.68, 3.85, 5.18,
        title="Learning-Based Playtesters",
        badge=None,
        items=[
            "**Human-Move DNN (Gudmundsson et al. [18]):** Trains a deep network on human moves to predict level difficulty, yet requires a large dataset of prior human play.",
            "**Deep RL (Delfosse et al. [9]):** Learns from self-play without human data, yet demands substantial training resources and lacks human behavioral patterns.",
            "**Procedural Personas (Holmgård et al. [15]):** Models playstyles via MCTS, yet still relies on heuristics evolved for the specific game.",
        ],
        font_size=11.5,
        space_after=6.5,
    )

    add_rounded_card(
        s6, 8.88, 1.68, 3.85, 5.18,
        title="LLMs & Multi-Agent Debate",
        badge=None,
        items=[
            "**Rule-Only Play:** Match-3 board-to-text [7] and Slay the Spire planning [19] without specialized training.",
            "**Single-Agent Difficulty (Xiao & Yang [1]):** Measures Wordle difficulty; needs a handicap so hard levels do not all tie at a loss.",
            "**Debate & Personas:** MIMIC [20] adds personality traits; Du et al. [21] and Liang et al. [16] use multi-round debate with a manager.",
            "**Open Risks:** Debate gains depend on setup [17] and agents may drift from assigned personas [22].",
        ],
        font_size=11.5,
        space_after=5.5,
    )

    # =========================================================================
    # SLIDE 7: 3.2 REQUIREMENT SPECIFICATION
    # =========================================================================
    t_time, t_script = scripts[7]
    s7 = new_content_slide(
        prs, 7, total_slides, "SECTION 3.2  •  SPECIFICATION",
        "3.2 Software, System and Method Requirement Specification",
        "System features (3.2.1), LLM integration requirements (3.2.2) and expert evaluation participants (3.2.3).",
        t_time, t_script,
    )

    add_rounded_card(
        s7, 0.60, 1.68, 5.90, 5.18,
        title=None,
        badge="FEATURES",
        items=[
            "**1. Multi-Agent Debate Loop:** Support multiple agents collaborating across rounds within each turn.",
            "**2. State-to-Text Extraction:** Pull structured Wordle state data and render it into readable text for the LLM.",
            "**3. Diverse Personas:** Assign distinct strategic viewpoints so agents do not agree immediately.",
            "**4. Adaptive GM Stopping:** Allow the Game Master to stop debate once enough perspectives are heard and finalize the consensus action.",
            "**5. Engine Execution:** Validate and execute the consensus action directly inside the Wordle environment.",
            "**6. Complete Audit Logging:** Record every model call, debate decision and game outcome for downstream analysis.",
        ],
        font_size=11.5,
        bullet=False,
        space_after=6.0,
    )

    add_rounded_card(
        s7, 6.83, 1.68, 5.90, 2.50,
        title="LLM Integration (DeepSeek-V4.1-Flash)",
        badge="MODEL SELECTION",
        items=[
            "**Model Selection:** Chosen over OpenAI GPT contenders because disabling thinking mode allows a **fixed temperature** at a **low cost per game**.",
            "**Three Capabilities Required:** (1) Multi-step reasoning over game states, (2) Context window fitting rules + state + full turn transcript, (3) Reliable JSON replies (with repair retries and token/time logging).",
        ],
        font_size=11.5,
        space_after=5.0,
    )

    add_rounded_card(
        s7, 6.83, 4.34, 5.90, 2.52,
        title=None,
        badge="PARTICIPANTS",
        items=[
            "**Target Pool:** **5 to 7 industry experts** recruited via professional networks and game development communities.",
            "**Inclusion Criteria:** Game designers, QA testers or producers with **≥ 3 years of industry experience** and hands-on work in **difficulty balancing or player experience** (puzzle, strategy or roguelike games preferred).",
            "**Ethics:** Informed consent obtained; names and responses kept strictly anonymous.",
        ],
        font_size=11.5,
        space_after=5.0,
    )

    # =========================================================================
    # SLIDE 8: 3.3.1 - 3.3.2 FRAMEWORK (FIG 1) & PERSONAS (TABLE 1)
    # =========================================================================
    t_time, t_script = scripts[8]
    s8 = new_content_slide(
        prs, 8, total_slides, "SECTION 3.3.1 – 3.3.2  •  DESIGN",
        "3.3.1 – 3.3.2 Playtester Framework and Debate Personas",
        "The three-part architecture around Wordle (Figure 1) and the four personas grounded in explore–exploit play (Table 1).",
        t_time, t_script,
        refs_short="Zhao & Tang [7]; Holmgård [15]; Liang [16]; Du [21]; Drachen [23]; Wilson [24]; Bertsimas [25]; J. Liang [26]",
    )

    # Left: Figure 1 in rounded frame
    add_rounded_image_frame(
        s8, FIG_FRAMEWORK,
        box_left=0.60, box_top=1.68, box_width=6.10, box_height=5.18,
        caption="Figure 1. The multi-agent debate playtester framework for Wordle (game environment in dashed box).",
    )

    # Right top: Table 1 (Personas)
    tb_cap = s8.shapes.add_textbox(Inches(6.95), Inches(1.65), Inches(5.78), Inches(0.28))
    add_rich_paragraph(tb_cap.text_frame, "**Table 1.** The personas of the debate (1 Managing Agent + 3 Playstyle Advisors).", font_size=11.0, color=SLATE_DARK, space_after=0)

    add_styled_table(
        s8, left=6.95, top=1.95, width=5.78, height=2.85,
        headers=["Persona", "Role", "Playstyle"],
        rows=[
            ["Game Master", "Managing agent", "Neutral. Proposes a guess, evaluates every advisor's argument and keeps or revises its proposal."],
            ["Bold", "Advisor", "Plays to win now. Prefers guesses that could still be the answer and accepts the risk of using more guesses later."],
            ["Cautious", "Advisor", "Plays not to lose. Prefers guesses that rule out the most remaining letters, even if they cannot be the answer."],
            ["Casual", "Advisor", "Plays like a typical daily player. Prefers common, familiar words with a habitual opener and does not compute letter statistics."],
        ],
        col_widths=[1.15, 1.15, 3.48],
        font_size=10.0,
        align_cols=[PP_ALIGN.LEFT, PP_ALIGN.LEFT, PP_ALIGN.LEFT],
    )

    # Right bottom: Grounding card (matching user's badge-free layout)
    add_rounded_card(
        s8, 6.95, 4.96, 5.78, 1.90,
        title="Theoretical Grounding & Advisor Sizing",
        badge=None,
        items=[
            "**Explore vs. Exploit [24]:** Cautious explores fresh letters like optimal Wordle play (`LIGHT` → `FERMS` [25]); Bold exploits candidates [26]; Casual mirrors typical daily heuristic play [15], [23].",
            "**3 Advisors:** Debates with 3 agents yield clear gains [21], whereas adding more debaters raises token cost and causes context forgetting [16].",
        ],
        font_size=11.0,
        space_after=3.5,
        pad_y=0.14,
    )

    # =========================================================================
    # SLIDE 9: 3.3.3 - 3.3.6 BRIDGE, DEBATE PROTOCOL (FIG 2), KNOWLEDGE & LOGS
    # =========================================================================
    t_time, t_script = scripts[9]
    s9 = new_content_slide(
        prs, 9, total_slides, "SECTION 3.3.3 – 3.3.6  •  DESIGN",
        "3.3.3 – 3.3.6 Bridge, Debate Protocol, Knowledge and Turn Statistics",
        "Public-only state extraction, reciprocal debate with adaptive stopping (Figure 2) and persona verification logs.",
        t_time, t_script,
        refs_short="Liang et al. [16]; Baltaji et al. [22]; Atkins [27]; Licato et al. [28]",
    )

    # Left column: 3 compact rounded cards (matching user's badge-free layout)
    add_rounded_card(
        s9, 0.60, 1.68, 5.40, 1.65,
        title="3.3.3 Bridge: State & Consensus Action",
        badge=None,
        items=[
            "**Public JSON State:** Guess history (G/Y/B) + keyboard summary (`_ _ _ T _`, misplaced S, absent letters). **Hides answer and limit.**",
            "**Validation:** Verifies final guess is an unplayed word in the **14,855-word allowed list** [27] before executing.",
        ],
        font_size=11.0,
        space_after=3.0,
        pad_y=0.14,
    )

    add_rounded_card(
        s9, 0.60, 3.45, 5.40, 1.68,
        title="3.3.4 Debate Protocol & Adaptive Stopping",
        badge=None,
        items=[
            "**Turn Order:** (1) GM proposes → (2) **Bold, Cautious, Casual** critique in fixed order → (3) GM reviews and decides [16].",
            "**Adaptive Break:** GM stops early when consensus is reached, capped at **3 rounds**. Invalid JSON/word triggers up to **2 retries**.",
        ],
        font_size=11.0,
        space_after=3.0,
        pad_y=0.14,
    )

    add_rounded_card(
        s9, 0.60, 5.25, 5.40, 1.61,
        title="3.3.5 Game Knowledge & 3.3.6 Turn Statistics",
        badge=None,
        items=[
            "**Game Knowledge:** Static rules, JSON reply schema (`action`, `reason`, `stop`) and per-agent persona prompt.",
            "**Turn Statistics:** Logs proposals, suggestions and candidate validity to verify Cautious suggests non-candidates more often than Bold [22], [28].",
        ],
        font_size=11.0,
        space_after=3.0,
        pad_y=0.12,
    )

    # Right: Figure 2 in rounded frame
    add_rounded_image_frame(
        s9, FIG_DEBATE,
        box_left=6.25, box_top=1.68, box_width=6.48, box_height=5.18,
        caption="Figure 2. Debate protocol in Turn 2 of a pilot game: Bold and Cautious correct GM's STORM (S ruled out at pos 1) to STORK.",
    )

    # =========================================================================
    # SLIDE 10: 3.4.1 STUDY PIPELINE (FIG 3 — FULL-HEIGHT RIGHT IMAGE)
    # =========================================================================
    t_time, t_script = scripts[10]
    s10 = new_content_slide(
        prs, 10, total_slides, "SECTION 3.4.1  •  METHOD",
        "3.4.1 Study Pipeline",
        "Strict information boundary from the puzzle archive to outside evaluation (Figure 3).",
        t_time, t_script,
        refs_short="Xiao & Yang [1]",
        header_width=5.45,
    )

    # Left Column: Two detailed cards on 3.4.1 Study Pipeline
    add_rounded_card(
        s10, 0.60, 1.68, 5.45, 2.48,
        title="Preparation & Strict Information Boundary",
        badge=None,
        items=[
            "**Wordle Puzzle Archive:** Answers and human guess distributions enter the study input step, where **human shares** go only to data cleaning and **outside evaluation** [1].",
            "**Game Under Test:** **Puzzle answers** go only to the Wordle engine (with the 14,855-word allowed list) and never enter any agent prompt.",
            "**Zero Data Leakage:** Neither the answer word nor the human score ever enters a prompt, so the playtester cannot copy the difficulty it is measured against [1].",
        ],
        font_size=10.8,
        space_after=4.0,
        pad_y=0.14,
    )

    add_rounded_card(
        s10, 0.60, 4.32, 5.45, 2.54,
        title="Playtester System & Outside Evaluation",
        badge=None,
        fill=CRIMSON_SOFT,
        border=CRIMSON_BORDER,
        items=[
            "**Manifest-Only Input:** The playtester system receives **only** the stratified puzzle list (puzzles × repetitions).",
            "**Turn-by-Turn Play & Run Records:** The experiment runner plays each puzzle and repetition as a separate game via the bridge and multi-agent debate, saving guesses used, turn debates and call logs.",
            "**Outside Evaluation:** Analysis compares run records with the human baseline for **RQ1** and **RQ2** [1], followed by the planned expert evaluation (**RQ3**).",
        ],
        font_size=10.8,
        space_after=4.0,
        pad_y=0.14,
    )

    # Right Column: Full-height Figure 3 (Study Pipeline)
    add_rounded_image_frame(
        s10, FIG_DATA_FLOW,
        box_left=6.20, box_top=0.36, box_width=6.53, box_height=6.58,
        caption="Figure 3. Study pipeline from input to output (solid box = playtester system; dashed boxes = study steps and game).",
    )

    # =========================================================================
    # SLIDE 11: 3.4.2 HUMAN DATA (FIG 4 — LARGE RIGHT CHART)
    # =========================================================================
    t_time, t_script = scripts[11]
    s11 = new_content_slide(
        prs, 11, total_slides, "SECTION 3.4.2  •  METHOD",
        "3.4.2 Human Performance Baseline Data",
        "Engaging Data 7-bin guess distribution across 1,861 cleaned puzzles and frozen D1–D4 quartiles (Figure 4).",
        t_time, t_script,
        refs_short="Constant et al. [14]; Engaging Data [29]",
    )

    # Left Column: Two cards on 3.4.2 Human Data
    add_rounded_card(
        s11, 0.60, 1.68, 4.65, 2.48,
        title="Engaging Data Archive & Data Cleaning",
        badge=None,
        items=[
            "**Human Guess Distribution [29]:** Daily share of players solving each Wordle puzzle in **1 to 6 guesses**; remaining unsolved share is scored as **7**.",
            "**7-Bin Objective Difficulty [14]:** Each puzzle has a 7-bin outcome distribution measuring objective play performance rather than subjective perception.",
            "**Data Cleaning:** Removed **4 puzzles** for data errors (missing sample size or implausible solved share), leaving **1,861 of 1,865 puzzles**.",
        ],
        font_size=10.8,
        space_after=4.0,
        pad_y=0.14,
    )

    add_rounded_card(
        s11, 0.60, 4.32, 4.65, 2.54,
        title="Frozen Difficulty Quartiles (D1 to D4)",
        badge=None,
        fill=CRIMSON_SOFT,
        border=CRIMSON_BORDER,
        items=[
            "**Equal Quartile Split:** The 1,861 cleaned puzzles are sorted by human mean and divided into four equal quartiles from **D1 (easiest)** to **D4 (hardest)**.",
            "**Frozen Cut-Points:** Cut-points at **3.98, 4.24 and 4.53 guesses** were frozen before any pilot run started.",
            "**Narrow Middle Spread:** As Figure 4(a) shows, the two middle quartiles (**D2 and D3**) span only **0.55 guesses** between 3.98 and 4.53.",
        ],
        font_size=10.8,
        space_after=4.0,
        pad_y=0.14,
    )

    # Right Column: Large Figure 4 (Human Difficulty Distribution)
    add_rounded_image_frame(
        s11, FIG_HUMAN_DIFF,
        box_left=5.42, box_top=1.68, box_width=7.31, box_height=5.18,
        caption="Figure 4. Human difficulty of the 1,861 cleaned puzzles: (a) quartile cut-points, (b) 7-bin distributions by quartile.",
    )

    # =========================================================================
    # SLIDE 12: 3.4.3 - 3.4.4 PILOT DESIGN (TABLE 2) & MEASURES
    # =========================================================================
    t_time, t_script = scripts[12]
    s12 = new_content_slide(
        prs, 12, total_slides, "SECTION 3.4.3 – 3.4.4  •  METHOD",
        "3.4.3 – 3.4.4 Pilot Design and Evaluation Measures",
        "Two complementary pilot experiments (Table 2), frozen configuration with a 12-guess handicap and dual-scale measures.",
        t_time, t_script,
        refs_short="Xiao & Yang [1]; Thompson [30]; Julious [31]",
    )

    # Left: Table 2 + Sizing Card
    tb_cap2 = s12.shapes.add_textbox(Inches(0.60), Inches(1.65), Inches(5.85), Inches(0.28))
    add_rich_paragraph(tb_cap2.text_frame, "**Table 2.** The two experiments of the pilot study.", font_size=11.0, color=SLATE_DARK, space_after=0)

    add_styled_table(
        s12, left=0.60, top=1.95, width=5.85, height=1.75,
        headers=["Design Parameter", "Exp A (deep)", "Exp B (wide)"],
        rows=[
            ["Puzzles", "12 (3 per quartile)", "48 (12 per quartile)"],
            ["Runs per puzzle", "32", "3"],
            ["Sampling", "Stratified random, seed 20261013", "Stratified random, seed 20261014, disjoint from Exp A"],
        ],
        col_widths=[1.55, 1.95, 2.35],
        font_size=10.5,
        align_cols=[PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.CENTER],
    )

    add_rounded_card(
        s12, 0.60, 3.88, 5.85, 2.98,
        title="Sample-Size Rules & Frozen Configuration",
        badge="3.4.3",
        items=[
            "**Exp A Sizing (Thompson [30]):** 32 runs per puzzle keep all 7 multinomial bin shares within **±20 percentage points** simultaneously at 95% confidence (answers **RQ1**).",
            "**Exp B Sizing (Julious [31]):** 12 puzzles per quartile follows the rule of 12 per group for a pilot study (answers **RQ2** across 48 puzzles).",
            "**Frozen Config:** `DeepSeek-V4.1-Flash` (thinking disabled, **temp 0.2**, 1,024-token limit) with a hidden **12-guess handicap** [1]. Failed games retried once.",
        ],
        font_size=11.2,
        space_after=4.5,
    )

    # Right: Dual scoring & Measures cards
    add_rounded_card(
        s12, 6.75, 1.68, 5.98, 2.35,
        title="3.4.4 Why Two Scoring Scales? (12-g vs. 6-g)",
        badge="SCALES",
        fill=CRIMSON_SOFT,
        border=CRIMSON_BORDER,
        items=[
            "**The Handicap Problem [1]:** LLM agents lose many games within 6 guesses, which would tie hard puzzles at 7. Playing up to **12 hidden guesses** keeps hard puzzles apart.",
            "**12-Guess Score:** Actual guesses used (loss = **13**). Used for rankings and categories.",
            "**6-Guess Score:** Cuts the same game at 6 guesses (loss = **7**), matching human Wordle rules since agents never see the limit. Used for **Bias**, **MAE** and **loss share**.",
        ],
        font_size=11.0,
        space_after=4.0,
    )

    add_rounded_card(
        s12, 6.75, 4.18, 5.98, 2.68,
        title="3.4.4 Statistical Measures for RQ1 and RQ2",
        badge="METRICS",
        items=[
            "**RQ1 (Consistency):** Within-puzzle **SD** (spread across runs), single-game **ICC(1,1)** and k-run mean **ICC(1,k)** (reliability of the averaged difficulty score).",
            "**RQ2 (Average Alignment):** **Pearson r** (linear) and **Spearman ρ** (rank order) with p-values [1]; **Bias** and **MAE** compared against a **constant human-mean baseline**.",
            "**RQ2 (Categories):** Playtester means split by **rank** into four equal quartiles (D1–D4) and compared with human quartiles in a **confusion matrix**.",
        ],
        font_size=11.0,
        space_after=4.0,
    )

    # =========================================================================
    # SLIDE 13: 4.1 EXPERIMENT RESULT — COMPLETION AND COST
    # =========================================================================
    t_time, t_script = scripts[13]
    s13 = new_content_slide(
        prs, 13, total_slides, "SECTION 4.1  •  RESULTS",
        "4.1 Experiment Result: Completion and Cost",
        "Run completion across 543 attempts, failure causes, token consumption and adaptive stopping behavior.",
        t_time, t_script,
    )

    # Top KPI row: 4 rounded boxes
    add_rounded_kpi(s13, 0.60, 1.68, 2.85, 1.25, "525 / 543", "Completed Games", "96.7% overall completion rate")
    add_rounded_kpi(s13, 3.69, 1.68, 2.85, 1.25, "383 / 395", "Exp A (Deep, 12×32)", "11 of 12 puzzles hit all 32 runs")
    add_rounded_kpi(s13, 6.78, 1.68, 2.85, 1.25, "142 / 148", "Exp B (Wide, 48×3)", "46 of 48 puzzles hit all 3 runs")
    add_rounded_kpi(s13, 9.88, 1.68, 2.85, 1.25, "67s – 71s", "Mean Runtime / Game", "~80k–89k total tokens per game")

    add_rounded_card(
        s13, 0.60, 3.15, 5.90, 3.71,
        title="Completion & Breakdown of the 18 Failed Attempts",
        badge="RELIABILITY",
        items=[
            "**Total Attempts:** 543 attempts across both experiments yielded **525 completed games**.",
            "**Invalid Reply (13 attempts):** Ended because an agent still returned an invalid JSON or disallowed word after two correction requests.",
            "**Runner Stopped (4 attempts):** Cut off in Exp A when a batch run was manually stopped.",
            "**Service Timeout (1 attempt):** Ended on a timeout from the model service in Exp A.",
            "**Retry Policy:** Each failed game was retried once; **11/12 Exp A** and **46/48 Exp B** puzzles reached all planned runs.",
        ],
        font_size=11.8,
        space_after=6.0,
    )

    add_rounded_card(
        s13, 6.83, 3.15, 5.90, 3.71,
        title="Token Cost, Runtime and Debate Rounds",
        badge="COST & ROUNDS",
        items=[
            "**Exp A (Deep) Per Game:** Averaged **71 seconds**, **75,800 prompt tokens** and **3,900 completion tokens**.",
            "**Exp B (Wide) Per Game:** Averaged **67 seconds**, **84,800 prompt tokens** and **4,300 completion tokens**.",
            "**Model Consistency:** Every answered API call returned the exact same model version identifier.",
            "**Adaptive Stopping:** The GM ended the debate early in **57 of 2,198 turns (2.6%)** in Exp A and **19 of 887 turns (2.1%)** in Exp B; all other turns ran to the limit of **3 rounds**.",
        ],
        font_size=11.8,
        space_after=6.0,
    )

    # =========================================================================
    # SLIDE 14: 4.2 RQ1 RESULTS — OUTCOME CONSISTENCY (TABLES 3 & 4)
    # =========================================================================
    t_time, t_script = scripts[14]
    s14 = new_content_slide(
        prs, 14, total_slides, "SECTION 4.2  •  RESULTS",
        "4.2 RQ1 Results: Outcome Consistency Across Repeated Runs",
        "Overall measures (Table 3) and within-puzzle SD by quartile (Table 4) across both scoring scales.",
        t_time, t_script,
    )

    # Left Column: Table 3 (Overall RQ1 measures) + Card
    tb_cap3 = s14.shapes.add_textbox(Inches(0.60), Inches(1.65), Inches(5.90), Inches(0.28))
    add_rich_paragraph(
        tb_cap3.text_frame,
        "**Table 3.** Overall RQ1 consistency measures on 12-g and 6-g scores.",
        font_size=10.5,
        color=SLATE_DARK,
        space_after=0,
    )

    add_styled_table(
        s14, left=0.60, top=1.95, width=5.90, height=1.90,
        headers=[
            "Measure",
            "Exp A, 12-g",
            "Exp A, 6-g",
            "Exp B, 12-g",
            "Exp B, 6-g",
        ],
        rows=[
            ["Within-puzzle SD", "1.53", "0.96", "1.52", "0.85"],
            ["ICC(1,1), one game", "0.49", "0.55", "0.48", "0.44"],
            ["ICC(1,k), mean of runs", "0.97", "0.98", "0.73", "0.70"],
        ],
        col_widths=[1.90, 1.00, 1.00, 1.00, 1.00],
        font_size=10.0,
        highlight_rows={2},
    )

    add_rounded_card(
        s14, 0.60, 4.15, 5.90, 2.70,
        title="Single-Game Spread vs. Multi-Run Reliability",
        badge="ICC(1,1) & ICC(1,k)",
        fill=CRIMSON_SOFT,
        border=CRIMSON_BORDER,
        items=[
            "**Single-Game Variance:** ICC(1,1) is **0.49** (12-g) and **0.55** (6-g) in Exp A; **0.48** and **0.44** in Exp B. Roughly half of single-run score variance stems from run-to-run noise (~1.5 guesses SD).",
            "**Multi-Run Reliability:** Averaging across repeated runs reaches **ICC(1,k) = 0.97** (12-g) and **0.98** (6-g) in Exp A (32 runs) and **0.73** in Exp B (3 runs).",
            "**Core Finding:** Multi-agent playtesting requires multiple runs per puzzle to average out debate randomness and yield a stable difficulty score.",
        ],
        font_size=11.2,
        space_after=4.5,
    )

    # Right Column: Table 4 (Within-puzzle SD by quartile) + Card
    tb_cap4 = s14.shapes.add_textbox(Inches(6.83), Inches(1.65), Inches(5.90), Inches(0.28))
    add_rich_paragraph(
        tb_cap4.text_frame,
        "**Table 4.** Mean within-puzzle SD (guesses) by human quartile.",
        font_size=10.5,
        color=SLATE_DARK,
        space_after=0,
    )

    add_styled_table(
        s14, left=6.83, top=1.95, width=5.90, height=2.05,
        headers=[
            "Human Quartile",
            "Exp A, 12-g",
            "Exp A, 6-g",
            "Exp B, 12-g",
            "Exp B, 6-g",
        ],
        rows=[
            ["D1 (Easiest)", "0.94", "0.74", "1.06", "0.89"],
            ["D2", "1.37", "1.10", "1.75", "0.78"],
            ["D3", "1.48", "0.95", "1.35", "0.79"],
            ["D4 (Hardest)", "2.30", "1.04", "1.93", "0.95"],
        ],
        col_widths=[1.90, 1.00, 1.00, 1.00, 1.00],
        font_size=10.0,
        highlight_rows={3},
    )

    add_rounded_card(
        s14, 6.83, 4.15, 5.90, 2.70,
        title="Quartile Spread Growth with Puzzle Hardness",
        badge="D1 → D4 ANALYSIS",
        items=[
            "**12-Guess SD Growth:** Mean within-puzzle SD escalates from **0.94 guesses** for **D1 (easiest)** to **2.30 guesses** for **D4 (hardest)** in Exp A, with Exp B showing a similar climb (**1.06 → 1.93**).",
            "**Tail & Loss Dynamics:** Harder puzzles force longer search paths and occasional losses (loss = 13), creating wider run-to-run dispersion.",
            "**6-Guess Truncation:** Capping games at 6 guesses suppresses this variance (**0.74 to 1.10** across quartiles), as failed games are compressed to score 7.",
        ],
        font_size=11.2,
        space_after=4.5,
    )

    # =========================================================================
    # SLIDE 15: 4.3 RQ2 RESULTS — AGREEMENT WITH HUMAN DIFFICULTY (TABLE 5 & FIG 5)
    # =========================================================================
    t_time, t_script = scripts[15]
    s15 = new_content_slide(
        prs, 15, total_slides, "SECTION 4.3  •  RESULTS",
        "4.3 RQ2 Results: Agreement with Human Difficulty",
        "Correlation and level error (Table 5) alongside rank-based D1–D4 quartile agreement on Exp B (Figure 5).",
        t_time, t_script,
        refs_short="Xiao & Yang [1]",
    )

    # Left: Table 5 + summary card
    tb_cap5 = s15.shapes.add_textbox(Inches(0.60), Inches(1.65), Inches(5.95), Inches(0.28))
    add_rich_paragraph(
        tb_cap5.text_frame,
        "**Table 5.** RQ2 results of Exp B (48×3) and Exp A (12×32) with correlation p-values [1].",
        font_size=10.5,
        color=SLATE_DARK,
        space_after=0,
    )

    add_styled_table(
        s15, left=0.60, top=1.95, width=5.95, height=2.85,
        headers=["Measure", "Exp B, 12-g", "Exp B, 6-g", "Exp A, 12-g", "Exp A, 6-g"],
        rows=[
            ["Playtester avg. guesses", "6.34", "5.54", "5.76", "5.29"],
            ["Human avg. guesses", "4.26", "4.26", "4.25", "4.25"],
            ["Pearson r", "0.30 (p=.039)", "0.38 (p=.007)", "0.70 (p=.011)", "0.60 (p=.041)"],
            ["Spearman ρ", "0.34 (p=.017)", "0.36 (p=.012)", "0.72 (p=.008)", "0.62 (p=.031)"],
            ["Bias (guesses)", "–", "+1.28", "–", "+1.04"],
            ["MAE (guesses)", "–", "1.38", "–", "1.26"],
        ],
        col_widths=[1.75, 1.05, 1.05, 1.05, 1.05],
        font_size=9.8,
        highlight_rows={3},
    )

    add_rounded_card(
        s15, 0.60, 4.96, 5.95, 1.90,
        title="Level Bias vs. Quartile Agreement",
        badge=None,
        items=[
            "**Level Bias:** Averages **5.54 vs. 4.26** guesses in Exp B (**+1.28 bias**, **1.38 MAE**); fails within 6 guesses **~27 pp** more often than humans in Exp A.",
            "**Quartile Confusion (Fig 5, Exp B):** **16/48 exact diagonal**, **31/48 within one quartile**, **0 human D4 placed in D1** (Exp A: **4/12** exact, **10/12** within one quartile).",
        ],
        font_size=10.5,
        space_after=3.5,
        pad_y=0.14,
    )

    # Right: Figure 5 in rounded frame
    add_rounded_image_frame(
        s15, FIG_CONFUSION,
        box_left=6.80, box_top=1.68, box_width=5.93, box_height=5.18,
        caption="Figure 5. Difficulty categories of the 48 wide puzzles in Exp B (split by rank): (a) puzzle means, (b) confusion matrix.",
    )

    # =========================================================================
    # SLIDE 16: 5.1 - 5.2 ANALYSIS OF RQ1 AND RQ2
    # =========================================================================
    t_time, t_script = scripts[16]
    s16 = new_content_slide(
        prs, 16, total_slides, "SECTION 5.1 – 5.2  •  ANALYSIS",
        "5.1 – 5.2 Analysis of RQ1 (Consistency) and RQ2 (Human Agreement)",
        "Why repeated runs are necessary (RQ1) and why the playtester measures relative difficulty better than absolute level (RQ2).",
        t_time, t_script,
        refs_short="Xiao & Yang [1]",
    )

    add_rounded_card(
        s16, 0.60, 1.68, 5.90, 4.45,
        title="5.1 RQ1 Analysis: Consistency Across Runs",
        badge="5.1 RQ1",
        items=[
            "**Single-Run Noise:** ICC(1,1) = **0.49** means roughly half of the score variance lies between puzzles while half comes from run-to-run noise (~1.5 guesses spread).",
            "**Multi-Run Reliability:** Averaging across runs is highly reliable (**ICC(1,k) = 0.97** at 32 runs; **0.73** at 3 runs), proving each puzzle should be played several times before using its mean.",
            "**Why Hard Puzzles Vary More:** D4 puzzles produce long games and occasional losses. This variance is essential, as a playtester that wins every game in few guesses cannot separate puzzles.",
        ],
        font_size=11.8,
        space_after=6.5,
    )

    add_rounded_card(
        s16, 6.83, 1.68, 5.90, 4.45,
        title="5.2 RQ2 Analysis: Agreement with Human Difficulty",
        badge="5.2 RQ2",
        items=[
            "**Statistically Significant Ranking:** Both experiments rank puzzles in the same direction as humans ($p < 0.05$).",
            "**Effect of Run Count on Precision:** Ranking is much stronger in Exp A (**ρ = 0.72**) than Exp B (**ρ = 0.34**) because 32 runs yield a cleaner puzzle mean, matching Xiao and Yang's best 20-run correlation (**r = 0.62**) [1].",
            "**Why Raw Scores Cannot Be Read Directly:** The playtester plays **~1.3 guesses worse** than humans. Its **1.38 MAE** is more than twice the **0.55-guess width** of the middle two quartiles (3.98 to 4.53), while an MAE close to the bias (+1.28) shows most error is a **constant shift**.",
            "**Rank-Based Quartiles Work:** Splitting by rank places **two thirds (31/48)** of Exp B puzzles within one quartile of their human category.",
        ],
        font_size=11.6,
        space_after=5.5,
    )

    add_rounded_callout(
        s16, 0.60, 6.26, 12.133, 0.62,
        "**Core Finding (Sections 5.1–5.2):** Averaging over repeated runs produces a reliable score that measures **relative difficulty (ranks and categories)** much better than **absolute difficulty**.",
    )

    # =========================================================================
    # SLIDE 17: 5.3 - 5.4 RQ3 PLANNED & IMPLICATIONS FOR THE FINAL STUDY
    # =========================================================================
    t_time, t_script = scripts[17]
    s17 = new_content_slide(
        prs, 17, total_slides, "SECTION 5.3 – 5.4  •  NEXT STEPS",
        "5.3 – 5.4 Planned Expert Evaluation (RQ3) and Final Study Implications",
        "Mixed-method expert evaluation design and the four design decisions fixed before running the final study.",
        t_time, t_script,
    )

    add_rounded_card(
        s17, 0.60, 1.68, 5.60, 5.18,
        title="5.3 RQ3: Expert Evaluation (Planned Next Stage)",
        badge="5.3 RQ3",
        items=[
            "**Schedule Position:** Follows the quantitative analysis in the research schedule.",
            "**Stimulus Material:** The 5–7 industry experts will inspect the final RQ1 consistency and RQ2 human-agreement results.",
            "**Part 1 — Likert-Scale Survey (1 to 5):** Experts rate utility and efficacy statements on a 1–5 scale, after which the overall average score is reported.",
            "**Part 2 — Semi-Structured Interviews:** Analyzed thematically to capture practical workflow insights, with each recurring theme reported as a share of the expert pool.",
        ],
        font_size=11.8,
        space_after=7.0,
    )

    add_rounded_card(
        s17, 6.55, 1.68, 6.18, 5.18,
        title="5.4 Four Implications Fixed Before the Final Study",
        badge="5.4 FINAL STUDY",
        fill=CRIMSON_SOFT,
        border=CRIMSON_BORDER,
        items=[
            "**1. Reliability-Based Run Sizing:** Set the number of runs per puzzle ($k$) so the puzzle mean reaches a target reliability, such as **ICC(1,k) ≥ 0.9**.",
            "**2. Fixed H1 Consistency Margin:** Fix the RQ1 hypothesis margin from the pilot spread before the final run (for example, within-puzzle **SD ≤ 0.5** on the 6-guess score).",
            "**3. Primary RQ2 Measures (H2):** Judge agreement with human difficulty primarily through **rank correlation** and **rank-based quartiles**.",
            "**4. Descriptive Distribution Case Study:** Show the guess distributions of the **3 easiest and 3 hardest puzzles** by human mean.",
            "**Fresh Test Set:** The final study will play **fresh puzzles** that were never used in the pilot.",
        ],
        font_size=11.6,
        bullet=False,
        space_after=6.0,
    )

    prs.save(str(OUT_PPTX))
    return OUT_PPTX


if __name__ == "__main__":
    out = build_deck()
    print(f"Built {out} ({out.stat().st_size:,} bytes)")
