"""
utils/streak_badge.py

The Dashboard's top-right "daily study goal" badge.

How it works
- Every day you reach your daily study goal (Settings) earns 1 star;
  studying double the goal earns 2 stars (max 3 a day).
- A badge level needs a number of stars that grows with the level (3, then 4,
  then 5, then 6 - see STARS_NEEDED). When they are all filled the badge UPGRADES
  to the next, fancier level (see LEVELS): plain round badge -> shield -> laurel ->
  wings -> crown -> sparkles -> aura. There are 15 levels.
- Missing a day (that isn't marked leave) resets everything back to level 0.
- The badge is faded until today's goal is reached, then it lights up.
- Every badge says "10+ HRS / DAILY STUDY" (the number comes from your goal),
  so you can tell at a glance what it is for.

The badge is drawn as an SVG and shown through an <img> tag (works the same way
as the profile picture elsewhere in the app). Render it with
st.markdown(badge_html(info), unsafe_allow_html=True).
"""

import base64
import math

from utils.helper import format_duration

# Stars needed to finish each level (the last level, Mythic, is the top and needs none).
STARS_NEEDED = [3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6]
MAX_STARS_SHOWN = 6  # stars drawn on the top level (all filled)

# Colours: face (top, bottom), rim (light, dark), ink (text on the face), ribbon (light, dark), wing (light, dark).
# Features switch on as the level grows.
LEVELS = [
    dict(name="Rookie",      face=("#DDE3EC", "#9AA6B8"), rim=("#F8FAFC", "#64748B"), ink="#334155", ribbon=("#64748B", "#475569"), wing=("#FFFFFF", "#94A3B8"), shape="circle", pearls=0,  laurel=0, wings=0, crown=0, gems=0, sparkles=0, aura=0, rays=0, rainbow=0),
    dict(name="Bronze",      face=("#F5C795", "#B97433"), rim=("#FBDDB8", "#7A4A1D"), ink="#5A3410", ribbon=("#9A3412", "#7C2D12"), wing=("#FFFFFF", "#B97433"), shape="circle", pearls=0,  laurel=0, wings=0, crown=0, gems=0, sparkles=0, aura=0, rays=0, rainbow=0),
    dict(name="Silver",      face=("#FAFBFD", "#B3BCC9"), rim=("#FFFFFF", "#7C8797"), ink="#374151", ribbon=("#475569", "#334155"), wing=("#FFFFFF", "#9CA3AF"), shape="circle", pearls=12, laurel=0, wings=0, crown=0, gems=0, sparkles=0, aura=0, rays=0, rainbow=0),
    dict(name="Gold",        face=("#FEEBA0", "#E2A610"), rim=("#FFF6C2", "#A16207"), ink="#6B4600", ribbon=("#B91C1C", "#7F1D1D"), wing=("#FFF7CC", "#D4A017"), shape="shield", pearls=0,  laurel=1, wings=0, crown=0, gems=0, sparkles=0, aura=0, rays=0, rainbow=0),
    dict(name="Platinum",    face=("#F4F6FF", "#A5B4FC"), rim=("#FFFFFF", "#8B9BBF"), ink="#33407A", ribbon=("#4338CA", "#312E81"), wing=("#FFFFFF", "#A5B4FC"), shape="shield", pearls=0,  laurel=1, wings=0, crown=0, gems=1, sparkles=0, aura=0, rays=0, rainbow=0),
    dict(name="Ruby",        face=("#FDA4AF", "#BE123C"), rim=("#FECDD3", "#881337"), ink="#FFFFFF", ribbon=("#1E3A8A", "#172554"), wing=("#FFFFFF", "#FB7185"), shape="shield", pearls=0,  laurel=1, wings=3, crown=0, gems=1, sparkles=0, aura=0, rays=0, rainbow=0),
    dict(name="Emerald",     face=("#6EE7B7", "#047857"), rim=("#A7F3D0", "#064E3B"), ink="#FFFFFF", ribbon=("#CA8A04", "#854D0E"), wing=("#FFFFFF", "#34D399"), shape="shield", pearls=0,  laurel=1, wings=4, crown=0, gems=1, sparkles=0, aura=0, rays=0, rainbow=0),
    dict(name="Sapphire",    face=("#93C5FD", "#1D4ED8"), rim=("#DBEAFE", "#1E3A8A"), ink="#FFFFFF", ribbon=("#B91C1C", "#7F1D1D"), wing=("#FFFFFF", "#60A5FA"), shape="ornate", pearls=0, laurel=1, wings=4, crown=1, gems=1, sparkles=0, aura=0, rays=0, rainbow=0),
    dict(name="Amethyst",    face=("#D8B4FE", "#7E22CE"), rim=("#F3E8FF", "#581C87"), ink="#FFFFFF", ribbon=("#0F766E", "#134E4A"), wing=("#FFFFFF", "#C084FC"), shape="ornate", pearls=0, laurel=1, wings=4, crown=1, gems=3, sparkles=2, aura=0, rays=0, rainbow=0),
    dict(name="Diamond",     face=("#CFFAFE", "#0891B2"), rim=("#FFFFFF", "#155E75"), ink="#083344", ribbon=("#1D4ED8", "#1E3A8A"), wing=("#FFFFFF", "#22D3EE"), shape="ornate", pearls=0, laurel=1, wings=5, crown=1, gems=3, sparkles=4, aura=0, rays=0, rainbow=0),
    dict(name="Champion",    face=("#A78BFA", "#4C1D95"), rim=("#FEF08A", "#B45309"), ink="#FFFFFF", ribbon=("#B91C1C", "#7F1D1D"), wing=("#FEF9C3", "#EAB308"), shape="ornate", pearls=0, laurel=1, wings=5, crown=2, gems=3, sparkles=4, aura=1, rays=0, rainbow=0),
    dict(name="Master",      face=("#FB7185", "#7F1D1D"), rim=("#FEF08A", "#B45309"), ink="#FFFFFF", ribbon=("#1E3A8A", "#172554"), wing=("#FEF9C3", "#EAB308"), shape="ornate", pearls=0, laurel=1, wings=6, crown=2, gems=5, sparkles=6, aura=1, rays=0, rainbow=0),
    dict(name="Grandmaster", face=("#3B82F6", "#0B1B4D"), rim=("#FEF08A", "#B45309"), ink="#FDE68A", ribbon=("#B91C1C", "#7F1D1D"), wing=("#FEF9C3", "#EAB308"), shape="ornate", pearls=0, laurel=1, wings=6, crown=2, gems=5, sparkles=7, aura=1, rays=0, rainbow=0),
    dict(name="Legend",      face=("#7C3AED", "#1E1B4B"), rim=("#FFFFFF", "#7C3AED"), ink="#FDE68A", ribbon=("#CA8A04", "#854D0E"), wing=("#FEF9C3", "#EAB308"), shape="ornate", pearls=0, laurel=1, wings=7, crown=2, gems=5, sparkles=8, aura=1, rays=0, rainbow=1),
    dict(name="Mythic",      face=("#374151", "#030712"), rim=("#FFFBEB", "#B45309"), ink="#FDE047", ribbon=("#CA8A04", "#713F12"), wing=("#FFFBEB", "#F59E0B"), shape="ornate", pearls=0, laurel=1, wings=7, crown=2, gems=5, sparkles=9, aura=2, rays=1, rainbow=1),
]
MAX_LEVEL = len(LEVELS) - 1

W, H = 280, 252
CX, CY = 140, 112
FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"

_SHIELD = f"M{CX} 40 L{CX+66} 58 L{CX+66} 118 C{CX+66} 156 {CX+36} 178 {CX} 192 C{CX-36} 178 {CX-66} 156 {CX-66} 118 L{CX-66} 58 Z"
_ORNATE = (
    f"M{CX} 34 C{CX+14} 44 {CX+36} 48 {CX+68} 44 L{CX+68} 118 C{CX+68} 158 {CX+36} 180 {CX} 194 "
    f"C{CX-36} 180 {CX-68} 158 {CX-68} 118 L{CX-68} 44 C{CX-36} 48 {CX-14} 44 {CX} 34 Z"
)


# --------------------------------------------------------------------------- level maths
def _cumulative():
    totals = [0]
    for needed in STARS_NEEDED:
        totals.append(totals[-1] + needed)
    return totals  # totals[level] = stars you need in total to reach that level


CUMULATIVE = _cumulative()
STARS_FOR_MAX = CUMULATIVE[-1]


def stars_needed(level: int) -> int:
    return STARS_NEEDED[level] if level < len(STARS_NEEDED) else MAX_STARS_SHOWN


def level_progress(total_stars: int, stars_today: int = 0) -> dict:
    """Where the badge stands for a given number of stars (and whether today's stars levelled it up)."""

    def split(stars: int):
        if stars >= STARS_FOR_MAX:
            return MAX_LEVEL, MAX_STARS_SHOWN
        level = max(i for i in range(len(STARS_NEEDED)) if CUMULATIVE[i] <= stars)
        return level, stars - CUMULATIVE[level]

    total_stars = max(int(total_stars), 0)
    stars_today = max(min(int(stars_today), total_stars), 0)
    level, in_level = split(total_stars)
    level_before, _ = split(total_stars - stars_today)
    is_max = total_stars >= STARS_FOR_MAX
    needed = stars_needed(level)
    return {
        "level": level,
        "stars_in_level": in_level,
        "stars_needed": needed,
        "stars_to_next": 0 if is_max else needed - in_level,
        "is_max": is_max,
        "leveled_up_today": stars_today > 0 and level > level_before,
        "new_stars_today": min(in_level, stars_today),
    }


# --------------------------------------------------------------------------- SVG pieces
def _star(cx, cy, r, fill, stroke, extra=""):
    points = []
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        radius = r if i % 2 == 0 else r * 0.46
        points.append(f"{cx + radius * math.cos(angle):.1f},{cy + radius * math.sin(angle):.1f}")
    return (
        f'<polygon points="{" ".join(points)}" fill="{fill}" stroke="{stroke}" '
        f'stroke-width="1.6" stroke-linejoin="round" {extra}/>'
    )


def _sparkle(x, y, size, delay):
    s = size
    return (
        f'<path class="sp" style="animation-delay:{delay}s" fill="#FFFFFF" stroke="#FDE68A" stroke-width=".6" '
        f'd="M{x} {y-s} Q{x} {y} {x+s} {y} Q{x} {y} {x} {y+s} Q{x} {y} {x-s} {y} Q{x} {y} {x} {y-s} Z"/>'
    )


def _wings(count):
    parts = []
    for side in (-1, 1):
        for k in range(count):
            angle = -6 - k * 13
            length = 74 - k * 5
            parts.append(
                f'<g transform="translate({CX + side * 56} {CY - 8}) scale({side} 1) rotate({angle})">'
                f'<ellipse cx="{length / 2:.1f}" cy="0" rx="{length / 2:.1f}" ry="10.5" fill="url(#wing)" '
                f'stroke="url(#rim)" stroke-width="1.3"/></g>'
            )
    return "".join(parts)


def _laurel(c2):
    leaves = []
    count = 8
    for side in (-1, 1):
        for i in range(count):
            theta = math.radians(108 + i * (96 / (count - 1)))
            radius = 78 if i % 2 == 0 else 73
            x = CX + side * radius * math.cos(theta)
            y = CY + radius * math.sin(theta)
            tangent = math.degrees(theta) + 90
            rotation = tangent if side == 1 else 180 - tangent
            leaves.append(
                f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="11" ry="4.6" fill="url(#laurel)" stroke="{c2}" '
                f'stroke-width=".8" transform="rotate({rotation + (22 if i % 2 else -22):.1f} {x:.1f} {y:.1f})"/>'
            )
    return "".join(leaves)


def _crown(size_level):
    scale = 0.95 if size_level == 1 else 1.3
    base_y = 50 if size_level == 1 else 52
    return (
        f'<g transform="translate({CX} {base_y}) scale({scale})">'
        '<path d="M-24 0 L-28 -28 L-13 -15 L0 -34 L13 -15 L28 -28 L24 0 Z" fill="url(#gold)" stroke="#92400E" stroke-width="1.4" stroke-linejoin="round"/>'
        '<rect x="-25" y="-3" width="50" height="9" rx="3" fill="url(#gold)" stroke="#92400E" stroke-width="1.2"/>'
        '<circle cx="-28" cy="-28" r="3.4" fill="#FB7185" stroke="#9F1239" stroke-width=".8"/>'
        '<circle cx="0" cy="-34" r="3.8" fill="#60A5FA" stroke="#1E3A8A" stroke-width=".8"/>'
        '<circle cx="28" cy="-28" r="3.4" fill="#FB7185" stroke="#9F1239" stroke-width=".8"/>'
        '<circle cx="0" cy="1.5" r="2.6" fill="#FFFFFF" stroke="#92400E" stroke-width=".7"/>'
        "</g>"
    )


def _gem(x, y, r):
    return (
        f'<path d="M{x} {y-r} L{x+r} {y} L{x} {y+r*1.25} L{x-r} {y} Z" fill="url(#gem)" stroke="#FFFFFF" '
        f'stroke-width="1" stroke-linejoin="round"/>'
    )


def _book(ink):
    return (
        f'<g transform="translate({CX} 82)">'
        f'<path d="M-15 -9 C-8 -12 -3 -11 0 -6 C3 -11 8 -12 15 -9 L15 8 C8 5 3 6 0 11 C-3 6 -8 5 -15 8 Z" '
        f'fill="{ink}" opacity=".92"/><path d="M0 -6 V11" stroke="#FFFFFF" stroke-opacity=".55" stroke-width="1.4"/></g>'
    )


def build_svg(level: int, stars_in_level: int, star_count: int, new_stars: int, label: str, unit: str, animate: bool, title: str) -> str:
    cfg = LEVELS[level]
    face1, face2 = cfg["face"]
    rim1, rim2 = cfg["rim"]
    rib1, rib2 = cfg["ribbon"]
    wing1, wing2 = cfg["wing"]
    ink = cfg["ink"]
    shape_path = {"shield": _SHIELD, "ornate": _ORNATE}.get(cfg["shape"])
    scale_face = f'transform="translate({CX} {CY + 4}) scale(.9) translate({-CX} {-(CY + 4)})"'

    css = ""
    if animate:
        css = (
            "<style>"
            "@keyframes tw{0%,100%{opacity:.1;transform:scale(.5)}50%{opacity:1;transform:scale(1)}}"
            "@keyframes pu{0%,100%{opacity:.45}50%{opacity:1}}"
            "@keyframes sp360{to{transform:rotate(360deg)}}"
            "@keyframes pop{0%{transform:scale(.1);opacity:0}60%{transform:scale(1.45);opacity:1}100%{transform:scale(1)}}"
            ".sp{transform-box:fill-box;transform-origin:center;animation:tw 2.6s ease-in-out infinite}"
            ".aura{animation:pu 3.2s ease-in-out infinite}"
            ".rays{transform-box:fill-box;transform-origin:center;animation:sp360 40s linear infinite}"
            ".pop{transform-box:fill-box;transform-origin:center;animation:pop .9s ease-out 1}"
            "</style>"
        )

    if cfg["rainbow"]:
        spin = (
            '<animateTransform attributeName="gradientTransform" type="rotate" from="0 .5 .5" to="360 .5 .5" dur="9s" repeatCount="indefinite"/>'
            if animate
            else ""
        )
        rim_stops = (
            '<stop offset="0" stop-color="#EF4444"/><stop offset=".2" stop-color="#F59E0B"/><stop offset=".4" stop-color="#22C55E"/>'
            '<stop offset=".6" stop-color="#06B6D4"/><stop offset=".8" stop-color="#6366F1"/><stop offset="1" stop-color="#EC4899"/>'
            + spin
        )
    else:
        rim_stops = f'<stop offset="0" stop-color="{rim1}"/><stop offset="1" stop-color="{rim2}"/>'

    if shape_path:
        clip = f'<clipPath id="fc"><path d="{shape_path}" {scale_face}/></clipPath>'
    else:
        clip = f'<clipPath id="fc"><circle cx="{CX}" cy="{CY}" r="62"/></clipPath>'

    defs = (
        "<defs>"
        f'<linearGradient id="rim" x1="0" y1="0" x2="1" y2="1">{rim_stops}</linearGradient>'
        f'<linearGradient id="face" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{face1}"/><stop offset="1" stop-color="{face2}"/></linearGradient>'
        f'<linearGradient id="ribbon" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{rib1}"/><stop offset="1" stop-color="{rib2}"/></linearGradient>'
        f'<linearGradient id="wing" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{wing2}"/><stop offset="1" stop-color="{wing1}"/></linearGradient>'
        '<linearGradient id="gold" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FEF08A"/><stop offset=".55" stop-color="#FACC15"/><stop offset="1" stop-color="#CA8A04"/></linearGradient>'
        '<linearGradient id="laurel" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#BBF7D0"/><stop offset="1" stop-color="#16A34A"/></linearGradient>'
        '<linearGradient id="gem" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FFFFFF"/><stop offset=".5" stop-color="#7DD3FC"/><stop offset="1" stop-color="#2563EB"/></linearGradient>'
        '<radialGradient id="aura"><stop offset="0" stop-color="#FDE68A" stop-opacity=".85"/><stop offset=".6" stop-color="#FBBF24" stop-opacity=".25"/><stop offset="1" stop-color="#FBBF24" stop-opacity="0"/></radialGradient>'
        '<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        + clip
        + "</defs>"
    )

    parts = [css, defs]

    # behind the badge: aura, rays, wings
    if cfg["aura"]:
        radius = 124 if cfg["aura"] == 2 else 110
        parts.append(f'<circle class="aura" cx="{CX}" cy="{CY}" r="{radius}" fill="url(#aura)"/>')
    if cfg["rays"]:
        rays = "".join(
            f'<polygon points="{CX},{CY} {CX + 126 * math.cos(math.radians(a - 4)):.1f},{CY + 126 * math.sin(math.radians(a - 4)):.1f} '
            f'{CX + 126 * math.cos(math.radians(a + 4)):.1f},{CY + 126 * math.sin(math.radians(a + 4)):.1f}" fill="#FDE68A" opacity=".28"/>'
            for a in range(0, 360, 30)
        )
        parts.append(f'<g class="rays">{rays}</g>')
    if cfg["wings"]:
        parts.append(_wings(cfg["wings"]))

    # ribbon tails (behind the badge)
    parts.append(
        f'<path d="M{CX-100} 164 H{CX-60} V192 H{CX-100} L{CX-91} 178 Z" fill="{rib2}" stroke="#000" stroke-opacity=".25" stroke-width="1"/>'
        f'<path d="M{CX+100} 164 H{CX+60} V192 H{CX+100} L{CX+91} 178 Z" fill="{rib2}" stroke="#000" stroke-opacity=".25" stroke-width="1"/>'
    )

    if cfg["laurel"]:
        parts.append(_laurel("#15803D"))

    # badge body: rim, face, inner line, shine
    inner_line = f'transform="translate({CX} {CY + 4}) scale(.84) translate({-CX} {-(CY + 4)})"'
    if shape_path:
        parts.append(f'<path d="{shape_path}" fill="url(#rim)" stroke="{rim2}" stroke-width="1.6" stroke-linejoin="round"/>')
        parts.append(f'<path d="{shape_path}" fill="url(#face)" {scale_face}/>')
        parts.append(f'<path d="{shape_path}" fill="none" stroke="#FFFFFF" stroke-opacity=".4" stroke-width="1.4" {inner_line}/>')
    else:
        parts.append(f'<circle cx="{CX}" cy="{CY}" r="70" fill="url(#rim)" stroke="{rim2}" stroke-width="1.6"/>')
        parts.append(f'<circle cx="{CX}" cy="{CY}" r="62" fill="url(#face)"/>')
        parts.append(f'<circle cx="{CX}" cy="{CY}" r="56" fill="none" stroke="#FFFFFF" stroke-opacity=".4" stroke-width="1.4"/>')
    parts.append(f'<g clip-path="url(#fc)"><ellipse cx="{CX}" cy="{CY - 36}" rx="58" ry="30" fill="#FFFFFF" opacity=".24"/></g>')
    for i in range(cfg["pearls"]):
        a = math.radians(i * 360 / cfg["pearls"])
        parts.append(
            f'<circle cx="{CX + 66 * math.cos(a):.1f}" cy="{CY + 66 * math.sin(a):.1f}" r="2.3" fill="#FFFFFF" stroke="{rim2}" stroke-width=".6"/>'
        )

    # emblem: book + big number + unit (this is what says "10+ hr study")
    parts.append(_book(ink))
    size = 38 if len(label) <= 3 else 29
    parts.append(
        f'<text x="{CX}" y="{CY + 24}" text-anchor="middle" font-family="{FONT}" font-weight="800" font-size="{size}" '
        f'fill="{ink}" stroke="#000" stroke-opacity=".12" stroke-width=".8">{label}</text>'
        f'<text x="{CX}" y="{CY + 39}" text-anchor="middle" font-family="{FONT}" font-weight="800" font-size="11" '
        f'letter-spacing="3" fill="{ink}" opacity=".9">{unit}</text>'
    )

    # ribbon front
    parts.append(
        f'<path d="M{CX-62} 156 H{CX+62} V184 H{CX-62} Z" fill="url(#ribbon)" stroke="#000" stroke-opacity=".3" stroke-width="1"/>'
        f'<path d="M{CX-62} 184 L{CX-50} 184 L{CX-62} 192 Z" fill="#000" opacity=".28"/>'
        f'<path d="M{CX+62} 184 L{CX+50} 184 L{CX+62} 192 Z" fill="#000" opacity=".28"/>'
        f'<text x="{CX}" y="175" text-anchor="middle" font-family="{FONT}" font-weight="800" font-size="12" letter-spacing="1.6" fill="#FFFFFF">DAILY STUDY</text>'
    )

    # gems
    if cfg["gems"] and shape_path:
        parts.append(_gem(CX, 188, 5.5))
        if cfg["gems"] >= 3:
            parts.append(_gem(CX - 52, 70, 5))
            parts.append(_gem(CX + 52, 70, 5))
        if cfg["gems"] >= 5:
            parts.append(_gem(CX - 60, 104, 4))
            parts.append(_gem(CX + 60, 104, 4))

    if cfg["crown"]:
        parts.append(_crown(cfg["crown"]))

    spots = [(52, 62, 8), (228, 58, 8), (36, 132, 6), (244, 140, 6), (84, 24, 7), (196, 22, 7), (140, 8, 6), (22, 96, 5), (258, 98, 5)]
    for i in range(cfg["sparkles"]):
        x, y, s = spots[i]
        parts.append(_sparkle(x, y, s, round(i * 0.45, 2)))

    # the star row (3 to 6 stars, depending on the level)
    spacing = {3: 46, 4: 42, 5: 38, 6: 36}.get(star_count, 36)
    base_r = {3: 15, 4: 15, 5: 14, 6: 13}.get(star_count, 13)
    mid = (star_count - 1) / 2
    first_new = stars_in_level - new_stars
    for i in range(star_count):
        offset = (i - mid) / mid if mid else 0
        x = CX + (i - mid) * spacing
        y = 220 + 6 * offset * offset
        r = base_r + (4 if (star_count % 2 == 1 and i == int(mid)) else 0)
        if i < stars_in_level:
            extra = 'filter="url(#glow)"' if animate else ""
            klass = ' class="pop"' if (animate and i >= first_new) else ""
            parts.append(f"<g{klass}>" + _star(x, y, r, "url(#gold)", "#B45309", extra) + "</g>")
        else:
            parts.append(_star(x, y, r, "#94A3B8", "#64748B", 'fill-opacity=".28" stroke-opacity=".7" stroke-dasharray="3 2"'))

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img">'
        f"<title>{title}</title>" + "".join(parts) + "</svg>"
    )


# --------------------------------------------------------------------------- HTML wrapper
_CSS = (
    "<style>"
    ".lo-bd-row{display:flex;justify-content:flex-end;}"
    ".lo-bd{display:flex;align-items:center;justify-content:flex-end;gap:6px;flex-wrap:wrap;}"
    ".lo-bd-text{text-align:right;max-width:210px;}"
    ".lo-bd-name{font-size:17px;font-weight:800;color:#1E1B4B;line-height:1.15;}"
    ".lo-bd-lv{font-size:11px;font-weight:700;color:#7C7A9E;letter-spacing:.6px;text-transform:uppercase;margin-top:2px;}"
    ".lo-bd-status{font-size:12.5px;color:#4A4775;margin-top:6px;line-height:1.35;}"
    ".lo-bd-status.up{color:#B45309;font-weight:800;}"
    ".lo-bd-meta{font-size:11px;color:#7C7A9E;margin-top:5px;line-height:1.35;}"
    ".lo-bd-streak{display:inline-flex;align-items:center;margin-top:9px;padding:4px 13px 4px 9px;border-radius:999px;"
    "background:#F1F0FB;color:#6B6890;font-size:12px;font-weight:700;}"
    ".lo-bd-streak b{font-size:19px;font-weight:800;color:#4A4775;line-height:1;margin:0 5px 0 6px;}"
    ".lo-bd-streak.on{background:linear-gradient(135deg,#FFEDD5,#FED7AA);color:#9A3412;box-shadow:0 2px 8px rgba(249,115,22,.22);}"
    ".lo-bd-streak.on b{color:#C2410C;}"
    ".lo-bd-streak svg{display:block;}"
    "</style>"
)


def _goal_label(goal_minutes: float):
    if goal_minutes >= 60:
        return f"{goal_minutes / 60:g}+", "HRS"
    return f"{goal_minutes:g}+", "MIN"


def badge_html(info: dict) -> str:
    """info = analytics.study_analytics.goal_streak(...). One HTML string, no blank lines."""
    progress = level_progress(info["total_stars"], info["stars_today"])
    level = progress["level"]
    cfg = LEVELS[level]
    lit = bool(info["today_met"])
    label, unit = _goal_label(info["goal_minutes"])

    title = f"Daily {label} {unit.lower()} study goal. Level {level + 1}: {cfg['name']}, {progress['stars_in_level']} of {progress['stars_needed']} stars."
    svg = build_svg(level, progress["stars_in_level"], progress["stars_needed"], progress["new_stars_today"] if lit else 0, label, unit, lit, title)
    data = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    img_style = "width:158px;height:auto;display:block;" + ("" if lit else "filter:grayscale(1);opacity:.55;")

    goal = info["goal_minutes"]
    remaining = max(goal - info["today_minutes"], 0)
    status_class = "lo-bd-status"
    if lit and progress["leveled_up_today"]:
        status, status_class = f"Level up! You are now {cfg['name']}", "lo-bd-status up"
    elif lit:
        n = info["stars_today"]
        status = f"{n} stars earned today (extra hours count!)" if n > 1 else "1 star earned today"
    elif info["on_leave"]:
        status = "On leave - your progress is safe"
    elif info["total_stars"] > 0:
        status = f"Study {format_duration(remaining)} more today to earn a star"
    elif info["today_minutes"] > 0:
        status = f"{format_duration(remaining)} more today to earn your first star"
    else:
        status = f"Study {format_duration(goal)} today to earn your first star"

    if progress["is_max"]:
        next_line = "Max level reached"
    else:
        left = progress["stars_to_next"]
        next_line = f"{left} star{'s' if left != 1 else ''} to {LEVELS[level + 1]['name']}"

    meta = f"{progress['stars_in_level']}/{progress['stars_needed']} stars &middot; {next_line} &middot; best streak {int(info['longest'])} days"
    days = int(info["current"])
    flame = (
        '<svg width="14" height="18" viewBox="0 0 16 20"><path d="M8 0C9 4 14 6 14 12.5A6 6 0 0 1 2 12.5C2 9.5 3.6 8 4.8 6.6'
        'C5.2 8.4 6.2 9 7 8.6C6.6 5.6 6.6 3 8 0Z" fill="' + ("#F97316" if lit else "#9CA3AF") + '"/>'
        '<path d="M8 20A3.4 3.4 0 0 1 4.6 16.6C4.6 14.6 6.5 13.6 8 11.4C9.5 13.6 11.4 14.6 11.4 16.6A3.4 3.4 0 0 1 8 20Z" '
        'fill="' + ("#FDE68A" if lit else "#E5E7EB") + '"/></svg>'
    )
    streak_note = "" if (lit or days == 0 or info["on_leave"]) else " &middot; keep it going today"
    streak = (
        f'<div class="lo-bd-streak{" on" if lit else ""}" title="Days in a row you reached your daily goal">'
        f"{flame}<b>{days}</b> day streak{streak_note}</div>"
    )

    return (
        _CSS
        + '<div class="lo-bd-row"><div class="lo-bd">'
        + '<div class="lo-bd-text">'
        + f'<div class="lo-bd-name">{cfg["name"]}</div>'
        + f'<div class="lo-bd-lv">Level {level + 1} of {MAX_LEVEL + 1}</div>'
        + streak
        + f'<div class="{status_class}">{status}</div>'
        + f'<div class="lo-bd-meta">{meta}</div>'
        + "</div>"
        + f'<img alt="{title}" title="{title}" style="{img_style}" src="data:image/svg+xml;base64,{data}"/>'
        + "</div></div>"
    )
