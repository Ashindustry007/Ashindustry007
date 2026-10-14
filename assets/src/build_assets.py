#!/usr/bin/env python3
"""Builds the README banner/card SVGs in the portfolio's design language.

Text is converted to outlines (fontTools) so the typography is identical everywhere,
including GitHub, where SVG images cannot load web fonts.

Setup / run:
  npm i @fontsource/space-grotesk @fontsource/inter @fontsource/jetbrains-mono
  pip install fonttools pillow
  FONT_DIR=node_modules/@fontsource IMG_DIR=<Portfolio>/public/images OUT_DIR=assets python3 build_assets.py
Env: FONT_DIR (node_modules/@fontsource), IMG_DIR (portfolio public/images), OUT_DIR.
Palette/fonts mirror the portfolio: bg #1b1a19, accent #FF8000, Space Grotesk / Inter / mono.
"""
import base64, io, math, os
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from PIL import Image

FONT_DIR = os.environ["FONT_DIR"]
IMG_DIR = os.environ["IMG_DIR"]
OUT = os.environ["OUT_DIR"]
os.makedirs(OUT, exist_ok=True)

# Portfolio tokens (globals.css / tailwind.config.ts)
BG = "#1b1a19"      # hsl(30 6% 10%)
CARD = "#211f1e"    # hsl(30 6% 12%)
DEEP = "#161412"    # section bg
OR = "#FF8000"      # primary / accent
MUTED = "#a3a3a3"   # muted-foreground
WHITE = "#fafafa"


class Font:
    def __init__(s, path):
        s.t = TTFont(path)
        s.gs = s.t.getGlyphSet()
        s.cmap = s.t.getBestCmap()
        s.upm = s.t["head"].unitsPerEm
        s.hm = s.t["hmtx"]

    def g(s, ch):
        n = s.cmap.get(ord(ch))
        if n is None:
            raise KeyError(f"missing glyph {ch!r} U+{ord(ch):04X}")
        return n

    def adv(s, ch):
        return s.hm[s.g(ch)][0]

    def width(s, text, size, tr=0.0):
        """visual width (no trailing tracking)"""
        k = size / s.upm
        return sum(s.adv(c) for c in text) * k + tr * size * max(len(text) - 1, 0)

    def path(s, text, x, y, size, tr=0.0, anchor="start"):
        w = s.width(text, size, tr)
        if anchor == "middle":
            x -= w / 2
        elif anchor == "end":
            x -= w
        k = size / s.upm
        cx = x
        d = []
        for c in text:
            if c != " ":
                pen = SVGPathPen(s.gs, ntos=lambda v: f"{v:.1f}")
                s.gs[s.g(c)].draw(TransformPen(pen, (k, 0, 0, -k, cx, y)))
                d.append(pen.getCommands())
            cx += s.adv(c) * k + tr * size
        return "".join(d)


def F(pkg, fname):
    return Font(f"{FONT_DIR}/{pkg}/files/{fname}")


SG7 = F("space-grotesk", "space-grotesk-latin-700-normal.woff")
SG5 = F("space-grotesk", "space-grotesk-latin-500-normal.woff")
IN4 = F("inter", "inter-latin-400-normal.woff")
IN6 = F("inter", "inter-latin-600-normal.woff")
MO5 = F("jetbrains-mono", "jetbrains-mono-latin-500-normal.woff")
MO4 = F("jetbrains-mono", "jetbrains-mono-latin-400-normal.woff")


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def svg(w, h, defs, body, title, desc, css=""):
    style = f"<style>{css}</style>" if css else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-labelledby="t d">'
        f'<title id="t">{esc(title)}</title><desc id="d">{esc(desc)}</desc>'
        f"<defs>{defs}</defs>{style}{body}</svg>"
    )


def T(font, text, x, y, size, fill, tr=0.0, anchor="start", op=None):
    d = font.path(text, x, y, size, tr, anchor)
    o = f' fill-opacity="{op}"' if op is not None else ""
    return f'<path d="{d}" fill="{fill}"{o}/>'


def TO(font, text, x, y, size, stroke, sw=1.5, tr=0.0, anchor="start", op=1):
    d = font.path(text, x, y, size, tr, anchor)
    return (f'<path d="{d}" fill="none" stroke="{stroke}" stroke-opacity="{op}" '
            f'stroke-width="{sw}" stroke-linejoin="round"/>')


def block(font, ls, x, y, size, lh, fill, tr=0.0, anchor="start", op=None):
    return "".join(T(font, l, x, y + i * lh, size, fill, tr, anchor, op) for i, l in enumerate(ls))


def wrap(text, font, size, maxw, tr=0.0):
    lines, cur = [], ""
    for w in text.split():
        t = f"{cur} {w}" if cur else w
        if font.width(t, size, tr) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def frame(w, h, rx=24, fill=BG):
    return (f'<rect width="{w}" height="{h}" rx="{rx}" fill="{fill}"/>'
            f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="{rx-.5}" fill="none" '
            f'stroke="#fff" stroke-opacity=".08"/>')


def clip(w, h, rx=24, cid="c"):
    return f'<clipPath id="{cid}"><rect width="{w}" height="{h}" rx="{rx}"/></clipPath>'


def glow(cid, color=OR, op=".30"):
    return (f'<radialGradient id="{cid}"><stop offset="0" stop-color="{color}" stop-opacity="{op}"/>'
            f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>')


def jpeg_uri(path, w, q=74):
    im = Image.open(path).convert("RGB")
    h = round(im.height * w / im.width)
    im = im.resize((w, h), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, "JPEG", quality=q, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


def arrow_right(x, y, ln, color=OR, sw=1.8, op=1):
    return (f'<path d="M{x} {y}H{x+ln}M{x+ln-6} {y-5}L{x+ln} {y}L{x+ln-6} {y+5}" fill="none" '
            f'stroke="{color}" stroke-opacity="{op}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>')


def arrow_ne(x, y, s, color=OR, sw=1.8, op=1):
    return (f'<path d="M{x} {y+s}L{x+s} {y}M{x+s*.2:.1f} {y}H{x+s}V{y+s*.8:.1f}" fill="none" '
            f'stroke="{color}" stroke-opacity="{op}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>')


def infinity(cx, cy, a, color=OR, sw=3):
    pts = []
    for i in range(0, 121):
        t = i / 120 * 2 * math.pi
        den = 1 + math.sin(t) ** 2
        pts.append((cx + a * math.cos(t) / den, cy + a * math.sin(t) * math.cos(t) / den))
    d = "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "Z"
    return (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linejoin="round"/>')


def chip(x, y, text, size=11):
    w = MO5.width(text, size, 0.12) + 22
    s = (f'<rect x="{x}" y="{y}" width="{w:.1f}" height="26" rx="13" fill="{OR}" fill-opacity=".07" '
         f'stroke="{OR}" stroke-opacity=".38"/>')
    s += T(MO5, text, x + 11, y + 17.2, size, OR, 0.12, op=.92)
    return s, w


def chip_flow(x0, y0, texts, maxw, gap=8, rowh=34):
    out, x, y = "", x0, y0
    for t in texts:
        w = MO5.width(t, 11, 0.12) + 22
        if x > x0 and x + w > x0 + maxw:
            x = x0
            y += rowh
        s, w = chip(x, y, t)
        out += s
        x += w + gap
    return out, y + 26


def write(name, content):
    with open(f"{OUT}/{name}", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"{name:26s} {len(content)/1024:7.1f} KB")


# ───────────────────────────── HERO ─────────────────────────────
def hero():
    W, H = 1000, 571
    uri = jpeg_uri(f"{IMG_DIR}/Whisk_10337cfa6353d339fb244045bb2d450ddr-ezgif.com-png-to-webp-converter.webp", 1500)
    defs = (
        clip(W, H)
        + f'<linearGradient id="gv" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG}" stop-opacity=".5"/>'
          f'<stop offset=".2" stop-color="{BG}" stop-opacity="0"/><stop offset=".6" stop-color="{BG}" stop-opacity="0"/>'
          f'<stop offset="1" stop-color="{BG}" stop-opacity=".96"/></linearGradient>'
        + f'<linearGradient id="gh" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{BG}" stop-opacity=".65"/>'
          f'<stop offset=".34" stop-color="{BG}" stop-opacity="0"/><stop offset=".68" stop-color="{BG}" stop-opacity="0"/>'
          f'<stop offset="1" stop-color="{BG}" stop-opacity=".6"/></linearGradient>'
    )
    css = ("@keyframes bob{0%,100%{transform:translateY(0);opacity:.3}50%{transform:translateY(7px);opacity:1}}"
           ".b1{animation:bob 1.8s ease-in-out infinite}.b2{animation:bob 1.8s ease-in-out .25s infinite}"
           "@media (prefers-reduced-motion:reduce){.b1,.b2{animation:none}}")
    b = f'<g clip-path="url(#c)"><rect width="{W}" height="{H}" fill="#0a0a0a"/>'
    b += f'<image xlink:href="{uri}" width="{W}" height="{H}" preserveAspectRatio="xMidYMid slice"/>'
    b += f'<rect width="{W}" height="{H}" fill="url(#gh)"/><rect width="{W}" height="{H}" fill="url(#gv)"/>'
    # top-right tagline
    b += T(MO5, "CAT — CODER | ARTIST | TRAVELER", 936, 66, 12, WHITE, 0.2, "end", .6)
    # left: greeting + name (portfolio hero)
    b += T(MO5, "HEY, MY NAME IS", 64, 122, 13, OR, 0.3, op=.9)
    b += T(SG7, "ASHISH", 64, 212, 80, WHITE, -0.04)
    b += T(SG7, "KUMAR", 64, 284, 80, WHITE, -0.04)
    b += TO(SG7, "PANDA", 64, 356, 80, WHITE, 1.6, -0.04, op=.85)
    b += f'<rect x="66" y="386" width="56" height="2" rx="1" fill="{OR}"/>'
    # right: subheadline + intro (right aligned, like the portfolio)
    b += block(SG7, ["ENGINEERING", "INTELLIGENCE."], 936, 214, 19, 27, OR, 0.12, "end")
    intro = wrap("Researcher and engineer applying AI to healthcare, bioinformatics, and scientific discovery.",
                 IN4, 15, 296)
    b += block(IN4, intro, 936, 282, 15, 24, MUTED, anchor="end", op=.95)
    # bottom: skills bar
    b += f'<rect x="64" y="488" width="872" height="1" fill="#fff" fill-opacity=".14"/>'
    skills = [("#01", "AI FOR HEALTHCARE"), ("#02", "BIOINFORMATICS"), ("#03", "MEDICAL IMAGING"), ("#04", "GENERATIVE MODELS")]
    for i, (sid, lab) in enumerate(skills):
        x = 64 + i * 224
        b += T(MO4, sid, x, 518, 11, OR, 0.15, op=.55)
        b += T(SG5, lab, x, 541, 13.5, WHITE, 0.1, op=.78)
    # animated scroll chevrons (portfolio's bouncing pointer)
    b += (f'<g fill="none" stroke="{OR}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
          f'<path class="b1" d="M492 452l8 8 8-8"/><path class="b2" d="M492 462l8 8 8-8"/></g>')
    b += "</g>"
    b += f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="23.5" fill="none" stroke="#fff" stroke-opacity=".1"/>'
    write("hero.svg", svg(W, H, defs, b,
          "Ashish Kumar Panda — Engineering Intelligence",
          "Researcher and engineer applying AI to healthcare, bioinformatics, and scientific discovery.", css))


# ───────────────────────────── ABOUT ─────────────────────────────
def tokens(markup):
    out, prev_end_space = [], True
    for i, seg in enumerate(markup.split("**")):
        style = "b" if i % 2 else "r"
        if seg == "":
            continue
        starts_space = seg[0] == " "
        for j, w in enumerate(seg.split()):
            out.append([w, style, j == 0 and not starts_space and not prev_end_space and len(out) > 0])
        prev_end_space = seg[-1] == " "
    return out


def rich_lines(markup, size, maxw):
    fonts = {"r": IN4, "b": IN6}
    space = IN4.adv(" ") * size / IN4.upm
    lines, cur, x = [], [], 0.0
    for w, st, attach in tokens(markup):
        ww = fonts[st].width(w, size)
        if cur and not attach and x + space + ww > maxw:
            lines.append(cur)
            cur, x = [], 0.0
        if cur and not attach:
            x += space
        cur.append((w, st, x))
        x += ww
    if cur:
        lines.append(cur)
    return lines


def rich(markup, x, y, size, lh, maxw, rfill=MUTED, bfill=WHITE):
    fonts = {"r": (IN4, rfill), "b": (IN6, bfill)}
    out, ls = "", rich_lines(markup, size, maxw)
    for i, line in enumerate(ls):
        for w, st, dx in line:
            f, fill = fonts[st]
            out += T(f, w, x + dx, y + i * lh, size, fill)
    return out, y + (len(ls) - 1) * lh


def icon_dna(x, y):
    a, b = [], []
    for i in range(0, 41):
        px = x + i
        py1 = y + 15 + 10 * math.sin(i / 40 * 2 * math.pi * 1.5)
        py2 = y + 15 - 10 * math.sin(i / 40 * 2 * math.pi * 1.5)
        a.append(f"{px:.1f} {py1:.1f}")
        b.append(f"{px:.1f} {py2:.1f}")
    rungs = ""
    for i in (3, 8, 13, 18, 23, 28, 33, 38):
        yy1 = y + 15 + 10 * math.sin(i / 40 * 2 * math.pi * 1.5)
        yy2 = y + 15 - 10 * math.sin(i / 40 * 2 * math.pi * 1.5)
        if abs(yy1 - yy2) > 6:
            rungs += f"M{x+i} {yy1:.1f}V{yy2:.1f}"
    return (f'<g fill="none" stroke="{OR}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            f'<path d="M{"L".join(a)}"/><path d="M{"L".join(b)}"/><path d="{rungs}" stroke-opacity=".5" stroke-width="1.4"/></g>')


def icon_image(x, y):
    return (f'<g fill="none" stroke="{OR}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            f'<rect x="{x}" y="{y+2}" width="40" height="28" rx="4"/><circle cx="{x+12}" cy="{y+11}" r="3.2"/>'
            f'<path d="M{x+3} {y+26}L{x+15} {y+16}L{x+23} {y+22}L{x+29} {y+17}L{x+37} {y+26}"/></g>')


def icon_text(x, y):
    rows = [(7, 40), (14, 30), (21, 40), (28, 20)]
    d = "".join(f"M{x} {y+r}H{x+l}" for r, l in rows)
    return f'<path d="{d}" fill="none" stroke="{OR}" stroke-width="2.6" stroke-linecap="round"/>'


def about():
    W = 1000
    PAD = 56
    colw = 500
    md = ("I am a researcher and engineer passionate about applying **AI to healthcare, bioinformatics, and scientific "
          "discovery**. I see patterns everywhere—whether in biological data, images, or natural language—and I love "
          "turning them into insights using machine learning. My curiosity drives me to explore both the "
          "**theoretical depth of algorithms** and their **real-world applications** in health and science.")
    plain = md.replace("**", "")
    para, last_y = rich(md, PAD, 262, 16.5, 27.5, colw)
    H_left = int(last_y + 27.5 + PAD - 6)
    ROW = 64
    panel_need = 200 + 3 * ROW + 24 + 42 + 28 - 44   # panel height needed (panel starts at y=44)
    H = max(H_left, panel_need + 88, 470)
    px, pw = 616, 328
    ph = H - 2 * 44
    defs = clip(W, H) + glow("g", OR, ".34")
    b = f'<g clip-path="url(#c)">{frame(W, H)}'
    b += f'<circle cx="{px+pw/2}" cy="{H/2}" r="300" fill="url(#g)"/>'
    b += T(MO5, "ABOUT ME", PAD, 92, 13, OR, 0.3)
    b += T(SG7, "I SEE PATTERNS", PAD, 158, 46, WHITE, -0.03)
    b += T(SG7, "EVERYWHERE.", PAD, 210, 46, OR, -0.03)
    b += para
    # right panel
    b += (f'<rect x="{px}" y="44" width="{pw}" height="{ph}" rx="20" fill="{CARD}" fill-opacity=".92" '
          f'stroke="#fff" stroke-opacity=".08"/>')
    cx = px + pw / 2
    b += infinity(cx, 112, 40, OR, 3.2)
    b += T(MO5, "PATTERNS IN", cx, 176, 11, MUTED, 0.3, "middle")
    rows = [("#01", "BIOLOGICAL DATA", icon_dna), ("#02", "IMAGES", icon_image), ("#03", "NATURAL LANGUAGE", icon_text)]
    ry = 200
    for i, (rid, lab, ic) in enumerate(rows):
        y = ry + i * ROW
        b += f'<rect x="{px+28}" y="{y}" width="{pw-56}" height="1" fill="#fff" fill-opacity=".08"/>'
        b += ic(px + 32, y + 20)
        b += T(MO4, rid, px + 92, y + 30, 10, OR, 0.15, op=.55)
        b += T(SG5, lab, px + 92, y + 51, 16, WHITE, 0.06)
    y = ry + 3 * ROW
    b += f'<rect x="{px+28}" y="{y}" width="{pw-56}" height="1" fill="#fff" fill-opacity=".08"/>'
    # insight pill
    pyy = y + 24
    b += (f'<rect x="{px+28}" y="{pyy}" width="{pw-56}" height="42" rx="21" fill="{OR}" fill-opacity=".08" '
          f'stroke="{OR}" stroke-opacity=".45"/>')
    lw = MO5.width("MACHINE LEARNING", 10.5, 0.14)
    iw = MO5.width("INSIGHTS", 10.5, 0.14)
    total = lw + 12 + 26 + 12 + iw
    sx = cx - total / 2
    b += T(MO5, "MACHINE LEARNING", sx, pyy + 25.5, 10.5, OR, 0.14)
    b += arrow_right(sx + lw + 12, pyy + 21, 26, OR, 1.8)
    b += T(MO5, "INSIGHTS", sx + lw + 12 + 26 + 12, pyy + 25.5, 10.5, WHITE, 0.14)
    b += "</g>"
    write("about.svg", svg(W, H, defs, b, "About me", plain))


# ───────────────────────────── SECTION HEADER ─────────────────────────────
def research_header():
    W, H = 1000, 150
    defs = clip(W, H) + glow("g", OR, ".26")
    b = f'<g clip-path="url(#c)">{frame(W, H, fill=DEEP)}<circle cx="930" cy="20" r="220" fill="url(#g)"/>'
    b += T(MO5, "WORK", 56, 62, 13, OR, 0.3)
    b += T(SG7, "RESEARCH", 56, 118, 46, WHITE, -0.03)
    wd = SG7.width("RESEARCH ", 46, -0.03)
    b += T(SG7, "EXPERIENCE", 56 + wd, 118, 46, OR, -0.03)
    b += f'<rect x="700" y="74" width="244" height="1" fill="#fff" fill-opacity=".12"/>'
    b += T(MO4, "03 PROJECTS", 944, 62, 11, MUTED, 0.25, "end", .8)
    b += "</g>"
    write("research-header.svg", svg(W, H, defs, b, "Research Experience", "Research Experience"))


# ───────────────────────────── RESEARCH CARDS ─────────────────────────────
CARDS = [
    dict(file="card-retinal.svg", n="01", title="Retinal Vessel Segmentation", sub="DIABETIC RETINOPATHY",
         body="For diabetic retinopathy, using deep learning: U-Net with preprocessing pipelines.",
         chips=["U-NET", "PREPROCESSING"], cta="VIEW ON GITHUB",
         alt="Retinal Vessel Segmentation for diabetic retinopathy using deep learning (U-Net, preprocessing pipelines)."),
    dict(file="card-odia.svg", n="02", title="Odia Handwritten Numeral Recognition", sub="ICECA 2021 · OCR",
         body="CNN-based recognition, contributing to OCR for low-resource languages.",
         chips=["CNN", "OCR"], cta="READ THE PAPER",
         alt="Odia Handwritten Numeral Recognition with CNNs, contributing to OCR for low-resource languages."),
    dict(file="card-music.svg", n="03", title="Generative AI for Music", sub="SEQUENCE MODELING",
         body="Sequence modeling of notes and chords to generate Beethoven-style compositions.",
         chips=["GENERATIVE AI", "NOTES & CHORDS"], cta="VIEW ON GITHUB",
         alt="Generative AI for Music: sequence modeling of notes and chords to generate Beethoven-style compositions."),
]


def card_layout(c, W=320, pad=28):
    inner = W - 2 * pad
    tl = wrap(c["title"].upper(), SG7, 21, inner, -0.02)
    bl = wrap(c["body"], IN4, 14.5, inner)
    y_title = 100
    y_sub = y_title + (len(tl) - 1) * 26 + 30
    y_body = y_sub + 34
    y_chip = y_body + (len(bl) - 1) * 22.5 + 28
    return tl, bl, y_title, y_sub, y_body, y_chip


def cards():
    W, pad = 320, 28
    lay = [card_layout(c) for c in CARDS]
    H = int(max(l[5] for l in lay) + 26 + 22 + 62)
    for c, (tl, bl, yt, ys, yb, yc), ox in zip(CARDS, lay, (0, 20 / 3, 40 / 3)):
        defs = clip(W, H, 20) + glow("g", OR, ".22")
        b = f'<g transform="translate({ox:.2f},0)"><g clip-path="url(#c)">{frame(W, H, 20)}<circle cx="300" cy="10" r="170" fill="url(#g)"/>'
        b += T(MO5, c["n"], pad, 56, 15, OR, 0.05)
        b += block(SG7, tl, pad, yt, 21, 26, WHITE, -0.02)
        b += T(MO4, c["sub"], pad, ys, 11, MUTED, 0.18)
        b += block(IN4, bl, pad, yb, 14.5, 22.5, MUTED)
        ch, _ = chip_flow(pad, yc, c["chips"], W - 2 * pad)
        b += ch
        fy = H - 40
        b += f'<rect x="{pad}" y="{fy-24}" width="{W-2*pad}" height="1" fill="#fff" fill-opacity=".08"/>'
        b += f'<rect x="{pad}" y="{fy-1}" width="32" height="1.5" fill="{OR}" fill-opacity=".5"/>'
        cw = MO5.width(c["cta"], 10.5, 0.18)
        b += T(MO5, c["cta"], pad + 44, fy + 3.5, 10.5, OR, 0.18, op=.85)
        b += arrow_ne(pad + 44 + cw + 9, fy - 6, 10, OR, 1.7, .85)
        b += "</g></g>"
        write(c["file"], svg(W + 40 / 3, H, defs, b, c["title"], c["alt"]))


# ───────────────────────────── EXPLORE / COLLAB PANELS ─────────────────────────────
def panel(file, num, label, l1, l2, body_md, bullets, chips, H=None):
    W, pad = 490, 36
    inner = W - 2 * pad
    y = 176
    body_svg, last = "", y
    if body_md:
        body_svg, last = rich(body_md, pad, y, 15.5, 25, inner)
    extra = ""
    bottom = last
    if bullets:
        yy = y
        for bm in bullets:
            s, ly = rich(bm, pad + 22, yy, 15.5, 25, inner - 22)
            extra += f'<rect x="{pad}" y="{yy-9}" width="7" height="7" rx="2" fill="{OR}"/>' + s
            yy = ly + 25 + 12
        bottom = yy - 12
    if chips:
        cs, cb = chip_flow(pad, (bottom if bullets else last) + 26, chips, inner)
        extra += cs
        bottom = cb - 25
    need = int(bottom + 25 + 40)
    return need, dict(file=file, num=num, label=label, l1=l1, l2=l2, body_svg=body_svg, extra=extra)


def panels():
    W = 490
    exploring = panel(
        "panel-exploring.svg", "NOW", "NOW", "CURRENTLY", "EXPLORING",
        "The use of **AI and machine learning for healthcare and biological data** for discovery and analysis, including:",
        None, ["COMPUTATIONAL BIOLOGY", "BIO-MOLECULAR MODELING", "MEDICAL IMAGING", "GENERATIVE MODELS"])
    collab = panel(
        "panel-collab.svg", "OPEN", "OPEN TO", "LOOKING TO", "COLLABORATE ON", None,
        ["Research projects combining **machine learning with biomedical or biomolecular data**.",
         "Applications of **AI in healthcare, genomics, and scientific discovery**."],
        ["BIOMEDICAL DATA", "BIOMOLECULAR DATA", "GENOMICS"])
    H = max(exploring[0], collab[0], 330)
    alts = {
        "panel-exploring.svg": "Currently exploring: the use of AI and machine learning for healthcare and biological data, "
                               "including computational biology, bio-molecular modeling, medical imaging, and generative "
                               "models for discovery and analysis.",
        "panel-collab.svg": "Looking to collaborate on: research projects combining machine learning with biomedical or "
                            "biomolecular data, and applications of AI in healthcare, genomics, and scientific discovery.",
    }
    for (_, p), ox in zip((exploring, collab), (0, 10)):
        p['ox'] = ox
        defs = clip(W, H) + glow("g", OR, ".28")
        b = f'<g transform="translate({p["ox"]},0)"><g clip-path="url(#c)">{frame(W, H)}<circle cx="470" cy="20" r="230" fill="url(#g)"/>'
        b += TO(SG7, p["num"], W - 30, 104, 70, WHITE, 1.1, -0.04, "end", .12)
        b += T(MO5, p["label"], 36, 62, 13, OR, 0.3)
        b += T(SG7, p["l1"], 36, 108, 30, WHITE, -0.02)
        b += T(SG7, p["l2"], 36, 144, 30, OR, -0.02)
        b += p["body_svg"] + p["extra"] + "</g></g>"
        title = p["l1"].title() + " " + p["l2"].title()
        write(p["file"], svg(W + 10, H, defs, b, title, alts[p["file"]]))


# ───────────────────────────── INDUSTRY ─────────────────────────────
def info_card(x, y, w, label, title_lines, sub, body, accent_title=False):
    inner = w - 56
    bl = wrap(body, IN4, 15, inner)
    return dict(x=x, y=y, w=w, label=label, tl=title_lines, sub=sub, bl=bl)


def industry():
    W = 1000
    L = info_card(40, 96, 400, "WORKED AS", ["BACKEND ENGINEER"], "OPEN FINANCIAL TECHNOLOGIES",
                  "Designed scalable systems and reliable data pipelines.")
    R = info_card(560, 96, 400, "NOW BRINGING THOSE SKILLS TO", ["LARGE-SCALE", "SCIENTIFIC DATASETS"], None,
                  "Managing and processing them for AI-driven research.")

    def height(c):
        yy = 34 + 40 + (len(c["tl"]) - 1) * 32 + (34 if c["sub"] else 0) + 22
        return yy + (len(c["bl"]) - 1) * 23 + 30
    ch = int(max(height(L), height(R)))
    H = 96 + ch + 40
    defs = clip(W, H) + glow("g", OR, ".22")
    b = f'<g clip-path="url(#c)">{frame(W, H, fill=DEEP)}<circle cx="500" cy="{96+ch/2}" r="300" fill="url(#g)"/>'
    b += T(MO5, "INDUSTRY BACKGROUND", 40, 62, 13, OR, 0.3)
    for c, accent in ((L, False), (R, True)):
        x, y, w = c["x"], c["y"], c["w"]
        b += f'<rect x="{x}" y="{y}" width="{w}" height="{ch}" rx="18" fill="{CARD}" stroke="#fff" stroke-opacity=".08"/>'
        yy = y + 34
        b += T(MO4, c["label"], x + 28, yy, 10.5, MUTED, 0.22)
        yy += 40
        for i, t in enumerate(c["tl"]):
            b += T(SG7, t, x + 28, yy + i * 32, 27, OR if accent else WHITE, -0.02)
        yy += (len(c["tl"]) - 1) * 32
        if c["sub"]:
            yy += 30
            b += T(MO5, c["sub"], x + 28, yy, 12, OR, 0.16, op=.9)
        yy += 30
        b += block(IN4, c["bl"], x + 28, yy, 15, 23, MUTED)
    # connector
    cy = 96 + ch / 2
    b += f'<circle cx="500" cy="{cy}" r="27" fill="{BG}" stroke="{OR}" stroke-opacity=".6" stroke-width="1.5"/>'
    b += arrow_right(488, cy, 24, OR, 2)
    b += "</g>"
    desc = ("Worked as a Backend Engineer at Open Financial Technologies, designing scalable systems and reliable data "
            "pipelines. Now bringing those skills into managing and processing large-scale scientific datasets for "
            "AI-driven research.")
    write("industry.svg", svg(W, H, defs, b, "Industry background", desc))


# ───────────────────────────── CTA ─────────────────────────────
def cta():
    W, H = 1000, 340
    uri = jpeg_uri(f"{IMG_DIR}/15d1e769-a062-4f93-9554-bf19ab63428e-ezgif.com-png-to-webp-converter.webp", 1500)
    defs = (
        clip(W, H)
        + f'<linearGradient id="gh" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{BG}" stop-opacity="1"/>'
          f'<stop offset=".08" stop-color="{BG}" stop-opacity="1"/><stop offset=".5" stop-color="{BG}" stop-opacity=".25"/>'
          f'<stop offset=".78" stop-color="{BG}" stop-opacity="0"/></linearGradient>'
        + f'<linearGradient id="gv" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG}" stop-opacity=".35"/>'
          f'<stop offset=".25" stop-color="{BG}" stop-opacity="0"/><stop offset=".75" stop-color="{BG}" stop-opacity="0"/>'
          f'<stop offset="1" stop-color="{BG}" stop-opacity=".4"/></linearGradient>'
    )
    b = f'<g clip-path="url(#c)"><rect width="{W}" height="{H}" fill="{BG}"/>'
    # image drawn 1000 wide, shifted right so the left is free for text; seam hidden by the opaque gradient edge
    b += f'<image xlink:href="{uri}" x="90" y="-34" width="1000" height="571"/>'
    b += f'<rect width="{W}" height="{H}" fill="url(#gh)"/><rect width="{W}" height="{H}" fill="url(#gv)"/>'
    b += T(MO5, "FINAL CALL", 56, 76, 13, OR, 0.4)
    b += T(SG7, "LET’S BUILD", 56, 148, 40, WHITE, -0.03)
    b += T(SG7, "INTELLIGENT SYSTEMS", 56, 196, 40, OR, -0.03)
    b += T(SG7, "TOGETHER", 56, 244, 40, WHITE, -0.03)
    b += f'<rect x="58" y="274" width="56" height="2" rx="1" fill="{OR}"/>'
    b += "</g>"
    b += f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="23.5" fill="none" stroke="#fff" stroke-opacity=".1"/>'
    write("cta.svg", svg(W, H, defs, b, "Let’s build intelligent systems together",
                         "Final call: let’s build intelligent systems together."))


# ───────────────────────────── BUTTONS ─────────────────────────────
def button(file, label, filled, w):
    H = 52
    defs = ""
    if filled:
        b = f'<rect width="{w}" height="{H}" rx="26" fill="{OR}"/>'
        txt, ar = BG, BG
    else:
        b = (f'<rect x=".5" y=".5" width="{w-1}" height="{H-1}" rx="25.5" fill="{BG}" stroke="#fff" stroke-opacity=".22"/>')
        txt, ar = WHITE, OR
    tw = SG7.width(label, 13.5, 0.14)
    total = tw + 10 + 11
    sx = (w - total) / 2
    b += T(SG7, label, sx, 31, 13.5, txt, 0.14)
    b += arrow_ne(sx + tw + 10, 20, 11, ar, 2)
    write(file, svg(w, H, defs, b, label.title(), label.title()))


if __name__ == "__main__":
    hero()
    about()
    research_header()
    cards()
    panels()
    industry()
    cta()
    button("btn-portfolio.svg", "PORTFOLIO", True, 200)
    button("btn-linkedin.svg", "LINKEDIN", False, 188)
    button("btn-gmail.svg", "GMAIL", False, 160)
    button("btn-kaggle.svg", "KAGGLE", False, 168)
