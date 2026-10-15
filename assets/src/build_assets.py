#!/usr/bin/env python3
"""Builds the profile-README SVGs (hero, about, focus, experience, achievements, repo catalogue,
CTA, buttons) in the portfolio's design language.

Text is converted to outlines (fontTools) so the typography is identical everywhere,
including GitHub, where SVG images cannot load web fonts.

Setup / run:
  npm i @fontsource/space-grotesk @fontsource/inter @fontsource/jetbrains-mono
  pip install fonttools pillow
  FONT_DIR=node_modules/@fontsource IMG_DIR=<Portfolio>/public/images OUT_DIR=assets python3 build_assets.py
Env: FONT_DIR (node_modules/@fontsource), IMG_DIR (portfolio public/images), OUT_DIR,
     ALT_JSON (optional: dump of each SVG's description, used for README alt text).
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
        s.key = os.path.basename(path)
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

    def glyph_d(s, ch):
        """outline in font units (y up); placed with scale(k,-k)"""
        pen = SVGPathPen(s.gs, ntos=lambda v: f"{v:.0f}")
        s.gs[s.g(ch)].draw(pen)
        return pen.getCommands()

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


ALTS, _last_desc = {}, [""]


def svg(w, h, defs, body, title, desc, css=""):
    _last_desc[0] = desc
    style = f"<style>{css}</style>" if css else ""
    defs += "".join(f'<path id="{i}" d="{d}"/>' for i, d in GLY.values())
    GLY.clear()
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-labelledby="t d">'
        f'<title id="t">{esc(title)}</title><desc id="d">{esc(desc)}</desc>'
        f"<defs>{defs}</defs>{style}{body}</svg>"
    )


GLY = {}  # (font key, char) -> (id, d); emitted once per SVG by svg(), then cleared


def T(font, text, x, y, size, fill, tr=0.0, anchor="start", op=None):
    w = font.width(text, size, tr)
    if anchor == "middle":
        x -= w / 2
    elif anchor == "end":
        x -= w
    k = size / font.upm
    cx, uses = x, []
    for c in text:
        if c != " ":
            key = (font.key, c)
            if key not in GLY:
                GLY[key] = (f"g{len(GLY)}", font.glyph_d(c))
            uses.append(f'<use xlink:href="#{GLY[key][0]}" transform="translate({cx:.1f} {y:.1f}) '
                        f'scale({k:.6f} {-k:.6f})"/>')
        cx += font.adv(c) * k + tr * size
    o = f' fill-opacity="{op}"' if op is not None else ""
    return f'<g fill="{fill}"{o}>' + "".join(uses) + "</g>"


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
    ALTS[name] = _last_desc[0]
    with open(f"{OUT}/{name}", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"{name:26s} {len(content)/1024:7.1f} KB")


# ───────────────────────────── RICH TEXT (**bold** markup) ─────────────────────────────
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


# ───────────────────────────── SHARED PIECES ─────────────────────────────
def fit(font, text, size, maxw, tr=0.0):
    """largest size <= `size` at which `text` fits in `maxw`"""
    while font.width(text, size, tr) > maxw and size > 8:
        size -= 0.5
    return size


def hair(x, y, w, op=".08"):
    return f'<rect x="{x}" y="{y}" width="{w}" height="1" fill="#fff" fill-opacity="{op}"/>'


def trophy(x, y, color=BG, s=1.0):
    """14x14 trophy cup, top-left at (x, y)"""
    return (f'<g transform="translate({x},{y}) scale({s})" fill="none" stroke="{color}" stroke-width="1.7" '
            f'stroke-linecap="round" stroke-linejoin="round"><path d="M3.5 1.5h7v4.2a3.5 3.5 0 0 1-7 0z"/>'
            f'<path d="M3.5 3H1.2c0 2.6 1 3.8 2.6 4M10.5 3h2.3c0 2.6-1 3.8-2.6 4"/>'
            f'<path d="M7 9.4V12M4.5 12.6h5"/></g>')


def icon_network(cx, cy, r=34):
    """agent graph glyph: a hub wired to four satellites"""
    pts = [(-r, -r * .62), (r, -r * .62), (-r * .8, r * .72), (r * .8, r * .72)]
    e = "".join(f"M{cx} {cy}L{cx+px:.1f} {cy+py:.1f}" for px, py in pts)
    e += f"M{cx-r:.1f} {cy-r*.62:.1f}L{cx+r:.1f} {cy-r*.62:.1f}"
    s = (f'<path d="{e}" fill="none" stroke="{OR}" stroke-opacity=".55" stroke-width="1.6" stroke-linecap="round"/>')
    for px, py in pts:
        s += f'<circle cx="{cx+px:.1f}" cy="{cy+py:.1f}" r="5" fill="{BG}" stroke="{OR}" stroke-width="2"/>'
    s += f'<circle cx="{cx}" cy="{cy}" r="9" fill="{OR}"/><circle cx="{cx}" cy="{cy}" r="3.2" fill="{BG}"/>'
    return s


def icon_code(x, y):
    return (f'<path d="M{x+12} {y+6}L{x+2} {y+16}L{x+12} {y+26}M{x+28} {y+6}L{x+38} {y+16}L{x+28} {y+26}'
            f'M{x+23} {y+4}L{x+17} {y+28}" fill="none" stroke="{OR}" stroke-width="2.2" stroke-linecap="round" '
            f'stroke-linejoin="round"/>')


def icon_camera(x, y):
    return (f'<g fill="none" stroke="{OR}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            f'<rect x="{x}" y="{y+7}" width="40" height="23" rx="4"/><circle cx="{x+20}" cy="{y+18.5}" r="6.2"/>'
            f'<path d="M{x+13} {y+7}L{x+16} {y+2}H{x+24}L{x+27} {y+7}"/></g>')


def icon_compass(x, y):
    return (f'<g fill="none" stroke="{OR}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            f'<circle cx="{x+20}" cy="{y+16}" r="14"/>'
            f'<path d="M{x+20} {y+7}L{x+25} {y+16}L{x+20} {y+25}L{x+15} {y+16}Z" stroke-opacity=".9"/></g>'
            f'<circle cx="{x+20}" cy="{y+16}" r="1.8" fill="{OR}"/>')


def cta_row(pad, W, H, label, rule=True):
    fy = H - 40
    b = hair(pad, fy - 24, W - 2 * pad) if rule else ""
    b += f'<rect x="{pad}" y="{fy-1}" width="32" height="1.5" fill="{OR}" fill-opacity=".5"/>'
    cw = MO5.width(label, 10.5, 0.18)
    b += T(MO5, label, pad + 44, fy + 3.5, 10.5, OR, 0.18, op=.85)
    b += arrow_ne(pad + 44 + cw + 9, fy - 6, 10, OR, 1.7, .85)
    return b


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
    b += T(MO5, "CAT — CODER | ARTIST | TRAVELER", 936, 66, 12, WHITE, 0.2, "end", .6)
    b += T(MO5, "HEY, MY NAME IS", 64, 122, 13, OR, 0.3, op=.9)
    b += T(SG7, "ASHISH", 64, 212, 80, WHITE, -0.04)
    b += T(SG7, "KUMAR", 64, 284, 80, WHITE, -0.04)
    b += TO(SG7, "PANDA", 64, 356, 80, WHITE, 1.6, -0.04, op=.85)
    b += f'<rect x="66" y="386" width="56" height="2" rx="1" fill="{OR}"/>'
    b += block(SG7, ["ENGINEERING", "INTELLIGENCE."], 936, 214, 19, 27, OR, 0.12, "end")
    intro_txt = ("MSCS student at UC San Diego. AI Engineer building intelligent systems through computer vision "
                 "and agentic architectures.")
    b += block(IN4, wrap(intro_txt, IN4, 15, 300), 936, 282, 15, 24, MUTED, anchor="end", op=.95)
    b += f'<rect x="64" y="488" width="872" height="1" fill="#fff" fill-opacity=".14"/>'
    skills = [("#01", "AI AGENTS ENGINEERING"), ("#02", "AI AGENTS + CV"), ("#03", "SYSTEMS FOR AI AGENTS")]
    col = 872 / 3
    for i, (sid, lab) in enumerate(skills):
        x = 64 + i * col
        b += T(MO4, sid, x, 518, 11, OR, 0.15, op=.55)
        b += T(SG5, lab, x, 541, 13.5, WHITE, 0.1, op=.78)
    b += (f'<g fill="none" stroke="{OR}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
          f'<path class="b1" d="M492 452l8 8 8-8"/><path class="b2" d="M492 462l8 8 8-8"/></g>')
    b += "</g>"
    b += f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="23.5" fill="none" stroke="#fff" stroke-opacity=".1"/>'
    write("hero.svg", svg(W, H, defs, b,
          "Ashish Kumar Panda — Engineering Intelligence",
          "MSCS student at UC San Diego and AI Engineer building intelligent systems through computer vision and "
          "agentic architectures. Focus: AI agents engineering, AI agents plus computer vision, and systems for AI agents.",
          css))


# ───────────────────────────── ABOUT ─────────────────────────────
ABOUT_PARAS = [
    "I am an **AI Engineer** pursuing my **MSCS at UC San Diego**, bridging **theoretical research and scalable, "
    "real-world systems**. My focus sits where **computer vision meets agentic AI**.",
    "With a foundation from **OUTR (B.Tech)**, I have built intelligent pipelines for hard problems, from "
    "**cancer-risk assessment via spatial transcriptomics** to **agentic automation of pre-silicon chip design**.",
    "Right now I am building **agents that act on real systems** and can show their work: a **cited legal-case "
    "digest**, **vision-grounded reasoning over scene graphs**, and **human-approved browser automation**.",
]


def about():
    W, PAD, colw = 1000, 56, 500
    h1, h2 = "SHAPING THE FUTURE OF", "AI-POWERED CREATION"
    hs = min(fit(SG7, h1, 40, colw, -0.03), fit(SG7, h2, 40, colw, -0.03))
    body, y = "", 262
    for p in ABOUT_PARAS:
        s, last = rich(p, PAD, y, 16, 26, colw)
        body += s
        y = last + 26 + 12
    H_left = int(y - 12 - 26 + PAD + 30)
    ROW = 76
    ph = 152 + 3 * ROW + 24 + 42 + 28
    H = max(H_left, ph + 88)
    px, pw = 616, 328
    py = (H - ph) / 2
    cx = px + pw / 2
    defs = clip(W, H) + glow("g", OR, ".34")
    b = f'<g clip-path="url(#c)">{frame(W, H)}'
    b += f'<circle cx="{cx}" cy="{H/2}" r="300" fill="url(#g)"/>'
    b += T(MO5, "ABOUT ME", PAD, 92, 13, OR, 0.3)
    b += T(SG7, h1, PAD, 156, hs, WHITE, -0.03)
    b += T(SG7, h2, PAD, 156 + hs * 1.2, hs, OR, -0.03)
    b += body
    b += (f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="20" fill="{CARD}" fill-opacity=".92" '
          f'stroke="#fff" stroke-opacity=".08"/>')
    b += icon_network(cx, py + 66, 34)
    b += T(MO5, "AT A GLANCE", cx, py + 136, 11, MUTED, 0.3, "middle")
    rows = [("#01", "CODER", icon_code), ("#02", "ARTIST", icon_camera), ("#03", "TRAVELER", icon_compass)]
    ry = py + 160
    for i, (rid, lab, ic) in enumerate(rows):
        y0 = ry + i * ROW
        b += hair(px + 28, y0, pw - 56)
        b += ic(px + 32, y0 + ROW / 2 - 16)
        b += T(MO4, rid, px + 92, y0 + ROW / 2 - 6, 10, OR, 0.15, op=.55)
        b += T(SG5, lab, px + 92, y0 + ROW / 2 + 16, 17, WHITE, 0.06)
    y1 = ry + 3 * ROW
    b += hair(px + 28, y1, pw - 56)
    pyy = y1 + 24
    b += (f'<rect x="{px+28}" y="{pyy}" width="{pw-56}" height="42" rx="21" fill="{OR}" fill-opacity=".08" '
          f'stroke="{OR}" stroke-opacity=".45"/>')
    b += T(MO5, "MSCS @ UC SAN DIEGO", cx, pyy + 25.5, 10.5, OR, 0.14, "middle")
    b += "</g>"
    plain = "About me. " + h1.title() + " " + h2.title() + ". " + " ".join(ABOUT_PARAS).replace("**", "") + \
        " Coder, artist, traveler. MSCS at UC San Diego."
    write("about.svg", svg(W, H, defs, b, "About me", plain))


# ───────────────────────────── SECTION HEADER ─────────────────────────────
def header(file, eyebrow, w1, w2, right):
    W, H = 1000, 124
    defs = clip(W, H) + glow("g", OR, ".26")
    b = f'<g clip-path="url(#c)">{frame(W, H, fill=DEEP)}<circle cx="930" cy="10" r="220" fill="url(#g)"/>'
    b += T(MO5, eyebrow, 56, 52, 13, OR, 0.3)
    b += T(SG7, w1, 56, 100, 44, WHITE, -0.03)
    wd = SG7.width(w1 + " ", 44, -0.03)
    b += T(SG7, w2, 56 + wd, 100, 44, OR, -0.03)
    assert 56 + wd + SG7.width(w2, 44, -0.03) < 690, (w1, w2)
    b += hair(700, 66, 244, ".12")
    b += T(MO4, right, 944, 54, 11, MUTED, 0.25, "end", .8)
    b += "</g>"
    write(file, svg(W, H, defs, b, f"{w1.title()} {w2.title()}", f"{w1.title()} {w2.title()}"))


# ───────────────────────────── FOCUS ─────────────────────────────
FOCUS = [
    dict(file="focus-agents.svg", n="01", t=("AI AGENTS", "ENGINEERING"),
         body="Agents that plan, call tools and cite their sources, kept in check by verified outputs and "
              "human-in-the-loop guardrails.",
         chips=["TOOL CALLING", "LANGGRAPH", "RAG", "CLAUDE"], proof="CASE PULSE · QUALCOMM"),
    dict(file="focus-cv.svg", n="02", t=("AI AGENTS", "+ CV"),
         body="Giving agents eyes: vision-language models reasoning over verified scene graphs, grounded in "
              "hands-on segmentation research with self-supervised vision transformers.",
         chips=["VLMS", "SCENE GRAPHS", "DINOV3", "SEGMENTATION"], proof="LRTSG · BOOLEAN LAB"),
    dict(file="focus-systems.svg", n="03", t=("SYSTEMS FOR", "AI AGENTS"),
         body="The plumbing around the model: WebSocket bridges, secure backends, streaming and retrieval that "
              "let agents run on real, sensitive systems.",
         chips=["FASTAPI", "WEBSOCKETS", "SSE", "DOCKER"], proof="QUALCOMM · CASE PULSE"),
]


def focus_cards():
    W, pad = 320, 28
    inner = W - 2 * pad
    lay = []
    for c in FOCUS:
        bl = wrap(c["body"], IN4, 14.5, inner)
        y_body = 104 + 30 + 34
        y_chip = y_body + (len(bl) - 1) * 22.5 + 28
        _, cb = chip_flow(pad, y_chip, c["chips"], inner)
        lay.append((bl, y_body, y_chip, cb))
    H = int(max(l[3] for l in lay) + 84)
    for c, (bl, yb, yc, _), ox in zip(FOCUS, lay, (0, 20 / 3, 40 / 3)):
        defs = clip(W, H, 20) + glow("g", OR, ".22")
        b = f'<g transform="translate({ox:.2f},0)"><g clip-path="url(#c)">{frame(W, H, 20, fill=CARD)}'
        b += f'<circle cx="300" cy="10" r="170" fill="url(#g)"/>'
        b += TO(SG7, c["n"], W - 24, 80, 64, WHITE, 1, -0.04, "end", .12)
        b += T(MO5, c["n"], pad, 52, 15, OR, 0.05)
        b += T(SG7, c["t"][0], pad, 104, 26, WHITE, -0.02)
        b += T(SG7, c["t"][1], pad, 134, 26, OR, -0.02)
        b += block(IN4, bl, pad, yb, 14.5, 22.5, MUTED)
        ch, _ = chip_flow(pad, yc, c["chips"], inner)
        b += ch
        fy = H - 40
        b += hair(pad, fy - 24, W - 2 * pad)
        b += T(MO4, "PROOF", pad, fy + 3.5, 10.5, MUTED, 0.2)
        b += T(MO5, c["proof"], pad + 56, fy + 3.5, 10.5, OR, 0.14, op=.9)
        b += "</g></g>"
        alt = f"{c['t'][0].title()} {c['t'][1].title()}. {c['body']} Seen in: {c['proof'].title()}."
        write(c["file"], svg(W + 40 / 3, H, defs, b, f"{c['t'][0].title()} {c['t'][1].title()}", alt))


# ───────────────────────────── EXPERIENCE ─────────────────────────────
EXP = [
    dict(co="QUALCOMM", role="AI ENGINEER INTERN", big="53", lab="BROWSER-AUTOMATION PLAYBOOKS AUTHORED",
         desc="AI-assisted browser automation for pre-silicon chip-design tools: engineers drive internal web portals "
              "in natural language. Built and compared an LLM bridge and a stateful agentic Chrome extension, with "
              "per-page guardrails and mandatory user approval."),
    dict(co="BOOLEAN LAB · UCSD HEALTH", role="AI RESEARCH INTERN", big="81%", lab="mIoU IN CRYPT-LEVEL SEGMENTATION",
         desc="Self-supervised computer vision for colon-tissue analysis: DINOv3-7B Vision Transformers fine-tuned "
              "with LoRA (75% less memory) plus a Mask2Former head, cutting manual annotation time by 90%."),
    dict(co="OPEN FINANCIAL TECHNOLOGIES", role="SOFTWARE ENGINEER", big="92%", lab="OF INVOICES AUTO-CONVERTED",
         desc="Two years on a neobanking platform after an internship: multi-modal invoice AI, payroll and "
              "payment-gateway work, and RBI-compliant risk controls protecting 50K+ users."),
    dict(co="PUCHO DIGITAL HEALTHCARE", role="DEEP LEARNING RESEARCH INTERN", big="96.55%",
         lab="SENSITIVITY IN DISEASE-CELL DETECTION",
         desc="Deep learning for healthcare: in-silico mRNA vaccine design and explainable computer vision for "
              "disease-cell detection in MRI scans, using XAI to justify predictions."),
    dict(co="ANALYTICS LABS", role="DATA SCIENCE INTERN", big="98.5%", lab="RECALL ON CREDIT-CARD FRAUD",
         desc="Predictive and anomaly-detection models across epidemiology, finance and predictive maintenance, "
              "including 89%-accurate COVID-19 spread forecasts from a hybrid statistical and deep-learning model."),
]


def experience():
    W, NX, X0, TW, RX = 1000, 70, 106, 548, 944
    rows, y = [], 48
    for e in EXP:
        dl = wrap(e["desc"], IN4, 14.5, TW)
        h = max(80 + (len(dl) - 1) * 22 + 40, 124)
        rows.append((y, dl, h))
        y += h
    H = int(y + 2)
    defs = clip(W, H) + glow("g", OR, ".24")
    b = f'<g clip-path="url(#c)">{frame(W, H)}<circle cx="940" cy="0" r="300" fill="url(#g)"/>'
    y_first, y_last = rows[0][0] + 18, rows[-1][0] + 18
    b += f'<rect x="{NX-.75}" y="{y_first}" width="1.5" height="{y_last-y_first}" fill="{OR}" fill-opacity=".35"/>'
    for i, (e, (y0, dl, h)) in enumerate(zip(EXP, rows)):
        if i:
            b += hair(X0, y0 - 20, RX - X0)
        b += f'<circle cx="{NX}" cy="{y0+18}" r="7" fill="{BG}" stroke="{OR}" stroke-width="2"/>'
        b += f'<circle cx="{NX}" cy="{y0+18}" r="2.6" fill="{OR}"/>'
        cs = fit(SG7, e["co"], 24, TW, -0.02)
        b += T(SG7, e["co"], X0, y0 + 26, cs, WHITE, -0.02)
        b += T(MO5, e["role"], X0, y0 + 50, 11.5, OR, 0.18, op=.95)
        b += block(IN4, dl, X0, y0 + 80, 14.5, 22, MUTED)
        b += T(SG7, e["big"], RX, y0 + 36, 44, OR, -0.03, "end")
        ll = wrap(e["lab"], MO4, 10.5, 230, 0.16)
        b += block(MO4, ll, RX, y0 + 62, 10.5, 16, MUTED, 0.16, "end")
    b += "</g>"
    alt = "Past experience. " + " ".join(
        f"{e['role'].title()}, {e['co'].title()}: {e['desc']} Highlight: {e['big']} {e['lab'].lower()}." for e in EXP)
    write("experience.svg", svg(W, H, defs, b, "Past experience", alt))


# ───────────────────────────── ACHIEVEMENTS ─────────────────────────────
def winner():
    W, H = 1000, 312
    defs = clip(W, H) + glow("g", OR, ".30")
    b = f'<g clip-path="url(#c)">{frame(W, H, fill=CARD)}<circle cx="860" cy="40" r="340" fill="url(#g)"/>'
    # WINNER pill
    pw_ = 14 + 8 + MO5.width("WINNER", 11.5, 0.2) + 36
    b += f'<rect x="56" y="44" width="{pw_:.1f}" height="30" rx="15" fill="{OR}"/>'
    b += trophy(56 + 18, 52, BG, 1.0)
    b += T(MO5, "WINNER", 56 + 18 + 14 + 8, 63.5, 11.5, BG, 0.2)
    b += T(SG7, "GDG CHALLENGE", 56, 132, 46, WHITE, -0.03)
    b += T(SG7, "DATAHACKS 2026", 56, 184, 46, OR, -0.03)
    body = ("Won against 100+ teams, judged by 80+ judges and mentors, with Allerion: AI-powered, "
            "species-specific pollen forecasting.")
    b += block(IN4, wrap(body, IN4, 15, 540), 56, 222, 15, 23, MUTED)
    b += cta_row(56, 600 + 56, H, "SEE THE PROJECT", rule=False)
    # stats
    b += f'<rect x="664" y="40" width="1" height="{H-80}" fill="#fff" fill-opacity=".1"/>'
    stats = [("100", "TEAMS"), ("450", "PARTICIPANTS"), ("80", "JUDGES & MENTORS")]
    for i, (num, lab) in enumerate(stats):
        ry = 40 + i * 78
        if i:
            b += hair(700, ry - 2, 244)
        b += T(SG7, num, 700, ry + 44, 40, WHITE, -0.03)
        b += T(SG7, "+", 700 + SG7.width(num, 40, -0.03), ry + 44, 40, OR, -0.03)
        b += T(MO4, lab, 700, ry + 64, 10.5, MUTED, 0.2)
    b += "</g>"
    alt = ("Winner: GDG Challenge at DataHacks 2026, with Allerion, an AI-powered, species-specific pollen "
           "forecasting system. Competed against 100+ teams (450+ participants), judged by 80+ judges and mentors.")
    write("achievement-winner.svg", svg(W, H, defs, b, "GDG Challenge Winner, DataHacks 2026", alt))


MINIS = [
    dict(file="ach-codevita.svg", eyebrow="WORLD RANK", big="96TH", title="TCS CODEVITA SEASON 10",
         sub="COMPETITIVE PROGRAMMING", link=False,
         alt="Achieved world rank 96th in TCS CodeVita Season 10."),
    dict(file="ach-aws.svg", eyebrow="RANKED AMONG", big="TOP 5", title="AWS GENERATIVE AI HACKATHON",
         sub="AT OPEN FINANCIAL TECHNOLOGIES", link=False,
         alt="Ranked among the top 5 in the AWS Generative AI Hackathon, conducted by AWS at Open Financial Technologies."),
    dict(file="ach-kaggle.svg", eyebrow="KAGGLE", big="EXPERT", title="NOTEBOOKS CATEGORY",
         sub="VIEW PROFILE", link=True,
         alt="Kaggle Expert in the Notebooks category. View profile."),
    dict(file="ach-paper.svg", eyebrow="PUBLISHED", big="IEEE", title="ODIA HANDWRITTEN NUMERAL RECOGNITION",
         sub="ICECA 2021 · READ PAPER", link=True,
         alt="Published paper: Odia Handwritten Numeral Recognition, a hybrid modelling approach, at ICECA 2021 (IEEE). Read the paper."),
]


def minis():
    W, pad = 235, 24
    inner = W - 2 * pad
    lay = []
    for m in MINIS:
        tl = wrap(m["title"], SG7, 14, inner, 0.02)
        sl = wrap(m["sub"], MO4, 10, inner - (16 if m["link"] else 0), 0.14)
        y_t = 128
        y_s = y_t + (len(tl) - 1) * 19 + 28
        lay.append((tl, sl, y_t, y_s, y_s + (len(sl) - 1) * 15))
    H = int(max(l[4] for l in lay) + 40)
    for m, (tl, sl, yt, ys, ye), ox in zip(MINIS, lay, (0, 5, 10, 15)):
        defs = clip(W, H, 20) + glow("g", OR, ".22")
        b = f'<g transform="translate({ox},0)"><g clip-path="url(#c)">{frame(W, H, 20, fill=CARD)}'
        b += f'<circle cx="225" cy="10" r="140" fill="url(#g)"/>'
        b += T(MO5, m["eyebrow"], pad, 44, 10, MUTED, 0.22)
        bs = fit(SG7, m["big"], 40, inner, -0.03)
        b += T(SG7, m["big"], pad, 98, bs, OR, -0.03)
        b += block(SG7, tl, pad, yt, 14, 19, WHITE, 0.02)
        b += block(MO4, sl, pad, ys, 10, 15, MUTED, 0.14)
        if m["link"]:
            lw = MO4.width(sl[-1], 10, 0.14)
            b += arrow_ne(pad + lw + 8, ye - 9, 9, OR, 1.6, .9)
        b += "</g></g>"
        write(m["file"], svg(W + 15, H, defs, b, f"{m['big']} {m['title'].title()}", m["alt"]))


# ───────────────────────────── CATALOGUE ─────────────────────────────
REPOS = [
    dict(file="repo-casepulse.svg", n="01", title="CASE PULSE", sub="SWANS 2026 · LAW-DI-GRAS HACKATHON",
         img="casepulse.jpg", award=False,
         body="Cited case digestion for personal-injury firms. Reads Clio read-only and ties every fact to its "
              "exact source span, with 147/147 citations verified at $1.10 per full case.",
         chips=["CLAUDE HAIKU + OPUS", "FASTAPI", "SQLITE-VEC", "HYBRID RETRIEVAL"]),
    dict(file="repo-allerion.svg", n="02", title="ALLERION", sub="DATAHACKS 2026 · GDG CHALLENGE WINNER",
         img="allerion.jpg", award=True,
         body="Species-specific pollen forecasting that fuses iNaturalist citizen-science data, the Google Pollen "
              "API and a phenology engine into 14-day, neighborhood-level forecasts, with Gemini 2.5 Flash agents "
              "for advisories and photo-based plant ID.",
         chips=["GEMINI 2.5 FLASH", "PHENOLOGY ENGINE", "INATURALIST", "H3 HEATMAP"]),
    dict(file="repo-lrtsg.svg", n="03", title="LRTSG", sub="LANGUAGE REASONING WITH SCENE GRAPHS",
         img="lrtsg.jpg", award=False,
         body="Zero-shot agentic pipeline for visual reasoning: six agents plan, narrate, build, localize, audit "
              "and answer over a verified Scene Graph, using ReAct/CodeAct tool use with Qwen3-VL or Gemini.",
         chips=["SIX AGENTS", "SCENE GRAPH", "REACT / CODEACT", "QWEN3-VL"]),
    dict(file="repo-safe.svg", n="04", title="SAFE", sub="SMART ANALYTICS FOR FIRE EMERGENCIES",
         img="safe.jpg", award=False,
         body="Wildfire intelligence platform from the Reboot the Earth hackathon: Rothermel fire-spread simulation "
              "on 3D terrain, plus an LLM assistant that fails over across Groq, Gemini, OpenAI/Mistral and a "
              "local fallback.",
         chips=["ROTHERMEL MODEL", "REACT THREE FIBER", "LANGCHAIN", "MULTI-PROVIDER FAILOVER"]),
]

EARLIER = [
    dict(file="repo-musicnet.svg", title="MUSICNET", sub="GENERATIVE AI FOR MUSIC",
         body="Beethoven-style music generation with an LSTM and embedding model trained on 157 MIDI pieces "
              "across 130 note classes, rendered back to audio with music21.",
         chips=["LSTM", "EMBEDDINGS", "MIDI", "MUSIC21"]),
    dict(file="repo-retina.svg", title="RETINAL VESSEL SEGMENTATION", sub="DIABETIC RETINOPATHY · DRIVE",
         body="Pixel-level segmentation of retinal images on the DRIVE dataset, classifying vessel versus "
              "non-vessel pixels with a U-Net as groundwork for early diabetic retinopathy detection.",
         chips=["U-NET", "DRIVE DATASET", "PREPROCESSING"]),
]


def feature_cards():
    W, pad, CH = 490, 32, 214
    inner = W - 2 * pad
    lay = []
    for r in REPOS:
        bl = wrap(r["body"], IN4, 14.5, inner)
        y_t = CH + 52
        y_s = y_t + 26
        y_b = y_s + 34
        y_c = y_b + (len(bl) - 1) * 22.5 + 26
        _, cb = chip_flow(pad, y_c, r["chips"], inner)
        lay.append((bl, y_t, y_s, y_b, y_c, cb))
    H = int(max(l[5] for l in lay) + 84)
    for r, (bl, yt, ys, yb, yc, _), ox in zip(REPOS, lay, (0, 10, 0, 10)):
        uri = jpeg_uri(f"{IMG_DIR}/projects/{r['img']}", 840, 72)
        defs = (clip(W, H, 20)
                + f'<linearGradient id="gf" x1="0" y1="0" x2="0" y2="1"><stop offset=".55" stop-color="{CARD}" '
                  f'stop-opacity="0"/><stop offset="1" stop-color="{CARD}" stop-opacity="1"/></linearGradient>'
                + glow("g", OR, ".16"))
        b = f'<g transform="translate({ox},0)"><g clip-path="url(#c)">{frame(W, H, 20, fill=CARD)}'
        b += f'<image xlink:href="{uri}" width="{W}" height="{CH}" preserveAspectRatio="xMidYMid slice"/>'
        b += f'<rect width="{W}" height="{CH}" fill="url(#gf)"/>'
        b += f'<circle cx="470" cy="{CH}" r="200" fill="url(#g)"/>'
        # index pill (top-left)
        lab = f"{r['n']} / 04"
        lw = MO5.width(lab, 10.5, 0.2)
        b += (f'<rect x="20" y="20" width="{lw+26:.1f}" height="26" rx="13" fill="{BG}" fill-opacity=".72" '
              f'stroke="#fff" stroke-opacity=".14"/>')
        b += T(MO5, lab, 33, 37.2, 10.5, WHITE, 0.2, op=.85)
        if r["award"]:
            ww = 14 + 8 + MO5.width("WINNER", 10.5, 0.2) + 30
            b += f'<rect x="{W-20-ww:.1f}" y="20" width="{ww:.1f}" height="26" rx="13" fill="{OR}"/>'
            b += trophy(W - 20 - ww + 14, 26, BG, .9)
            b += T(MO5, "WINNER", W - 20 - ww + 14 + 8 + 14, 37.2, 10.5, BG, 0.2)
        b += T(SG7, r["title"], pad, yt, 25, WHITE, -0.02)
        sf = fit(MO5, r["sub"], 10.5, inner, 0.16)
        b += T(MO5, r["sub"], pad, ys, sf, OR, 0.16, op=.9)
        b += block(IN4, bl, pad, yb, 14.5, 22.5, MUTED)
        ch, _ = chip_flow(pad, yc, r["chips"], inner)
        b += ch
        b += cta_row(pad, W, H, "VIEW ON GITHUB")
        b += "</g></g>"
        alt = f"{r['title'].title()}, {r['sub'].title()}. {r['body']}"
        write(r["file"], svg(W + 10, H, defs, b, r["title"].title(), alt))


def compact_cards():
    W, pad = 490, 32
    inner = W - 2 * pad
    lay = []
    for r in EARLIER:
        bl = wrap(r["body"], IN4, 14.5, inner)
        y_t, y_s = 92, 118
        y_b = y_s + 34
        y_c = y_b + (len(bl) - 1) * 22.5 + 26
        _, cb = chip_flow(pad, y_c, r["chips"], inner)
        lay.append((bl, y_b, y_c, cb))
    H = int(max(l[3] for l in lay) + 84)
    for r, (bl, yb, yc, _), ox in zip(EARLIER, lay, (0, 10)):
        defs = clip(W, H, 20) + glow("g", OR, ".18")
        b = f'<g transform="translate({ox},0)"><g clip-path="url(#c)">{frame(W, H, 20, fill=CARD)}'
        b += f'<circle cx="470" cy="10" r="200" fill="url(#g)"/>'
        b += T(MO5, "EARLIER RESEARCH", pad, 52, 11, OR, 0.3)
        ts = fit(SG7, r["title"], 25, inner, -0.02)
        b += T(SG7, r["title"], pad, 92, ts, WHITE, -0.02)
        b += T(MO4, r["sub"], pad, 118, 11, MUTED, 0.18)
        b += block(IN4, bl, pad, yb, 14.5, 22.5, MUTED)
        ch, _ = chip_flow(pad, yc, r["chips"], inner)
        b += ch
        b += cta_row(pad, W, H, "VIEW ON GITHUB")
        b += "</g></g>"
        alt = f"{r['title'].title()}, {r['sub'].title()}. {r['body']}"
        write(r["file"], svg(W + 10, H, defs, b, r["title"].title(), alt))


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
    write(file, svg(w, H, "", b, label.title(), label.title()))


if __name__ == "__main__":
    hero()
    about()
    header("h-focus.svg", "NOW", "CURRENT", "FOCUS", "03 AREAS")
    focus_cards()
    header("h-experience.svg", "WORK", "PAST", "EXPERIENCE", "05 ROLES")
    experience()
    header("h-achievements.svg", "RECOGNITION", "SELECTED", "ACHIEVEMENTS", "05 HIGHLIGHTS")
    winner()
    minis()
    header("h-catalogue.svg", "GITHUB", "REPO", "CATALOGUE", "06 FEATURED")
    feature_cards()
    compact_cards()
    cta()
    button("btn-portfolio.svg", "PORTFOLIO", True, 200)
    button("btn-linkedin.svg", "LINKEDIN", False, 188)
    button("btn-email.svg", "EMAIL", False, 150)
    button("btn-kaggle.svg", "KAGGLE", False, 168)
    if os.environ.get("ALT_JSON"):
        import json
        json.dump(ALTS, open(os.environ["ALT_JSON"], "w"), indent=1, ensure_ascii=False)
