"""
utils/ui.py

Small shared UI pieces used across pages: global styling (cards, KPI
tiles, badges), a branded sidebar header, avatar rendering, and a
client-side ticking timer display (so the Study Timer visibly counts
up without needing a full Streamlit rerun every second).
"""

import streamlit as st
import streamlit.components.v1 as components

# Design tokens -- taken from the CampusX One site: a violet/indigo primary,
# near-black ink, soft lavender surfaces, plus small mint / blue / orange / amber
# accents. (Legacy names _TEAL/_CORAL are kept because other helpers use them:
# _TEAL is now the blue accent, _CORAL the orange one.)
_ACCENT = "#6558E0"
_ACCENT_DARK = "#4A3FCF"
_ACCENT_SOFT = "#ECE9FD"
_SURFACE = "#F6F4FE"
_BG = "#FAF9FE"
_INK = "#14141F"
_SLATE = "#3B4052"
_MUTED = "#6B7084"
_CARD_BG = "#FFFFFF"
_CARD_BORDER = "#E7E5F0"
_TEAL = "#2F7BE5"
_CORAL = "#F2784B"
_AMBER = "#F5A623"
_GREEN = "#2FA36B"
_MINT = "#E4F5EC"

_FONT_IMPORT = (
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800"
    "&family=Space+Grotesk:wght@500;600;700&family=Space+Mono:wght@400;700&display=swap"
)


_GLOBAL_CSS = """
@import url('__FONT_IMPORT__');

/* ---------- base ---------- */
html, body, .stApp { font-family: 'Inter', 'Source Sans', system-ui, sans-serif; color: __INK__; }
.stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button,
.stApp [data-testid="stMarkdownContainer"], .stApp [data-testid="stCaptionContainer"],
.stApp [data-baseweb="select"] { font-family: 'Inter', 'Source Sans', system-ui, sans-serif; }
.stApp, [data-testid="stAppViewContainer"] { background: __BG__; }
header[data-testid="stHeader"] { background: transparent; }
hr { border-color: __BORDER__ !important; }
[data-testid="stCaptionContainer"] { color: __MUTED__; }

/* ---------- headings (Space Grotesk, like the reference) ---------- */
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {
    font-family: 'Space Grotesk', 'Inter', system-ui, sans-serif !important;
    color: __INK__ !important;
    letter-spacing: -0.02em;
}
.stApp h1 { font-weight: 700 !important; font-size: 2.6rem !important; line-height: 1.1 !important; }
.stApp h2 { font-weight: 700 !important; font-size: 1.7rem !important; }
.stApp h3 { font-weight: 600 !important; font-size: 1.25rem !important; }

/* eyebrow label + page header */
.lifeos-eyebrow {
    font-family: 'Space Mono', ui-monospace, monospace;
    font-size: 0.74rem; font-weight: 700; letter-spacing: 0.2em;
    text-transform: uppercase; color: __ACCENT__; margin-bottom: 6px;
}
.lifeos-page-header { margin: 0.2rem 0 0.4rem 0; }
.lifeos-page-header h1 { margin: 0 !important; padding: 0 !important; }
.lifeos-page-sub { color: __SLATE__; font-size: 1.02rem; margin-top: 6px; }
.lifeos-accent { color: __ACCENT__; }
.lifeos-hl {
    display: inline-block; background: __ACCENT__; color: #fff; border-radius: 0.2em;
    padding: 0 0.22em; line-height: 1.12; margin-left: 0.05em;
}

/* ---------- cards ---------- */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 16px !important;
    border: 1px solid __BORDER__ !important;
    background: __CARD_BG__;
    box-shadow: 0 1px 2px rgba(20,20,31,0.04), 0 8px 22px rgba(101,88,224,0.06);
    transition: box-shadow 0.18s ease, border-color 0.18s ease;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: #D9D4F6 !important;
    box-shadow: 0 1px 2px rgba(20,20,31,0.05), 0 12px 28px rgba(101,88,224,0.10);
}
div[data-testid="stMetric"] {
    background: __CARD_BG__; border: 1px solid __BORDER__; border-top: 3px solid __ACCENT__;
    border-radius: 16px; padding: 1rem 1.1rem 0.8rem 1.1rem;
    box-shadow: 0 8px 22px rgba(101,88,224,0.06);
}
div[data-testid="stMetricLabel"] {
    font-family: 'Space Mono', monospace; font-size: 0.7rem !important; font-weight: 700 !important;
    text-transform: uppercase; letter-spacing: 0.08em; color: __MUTED__ !important;
}
div[data-testid="stMetricValue"] {
    font-family: 'Space Grotesk', sans-serif; font-size: 1.9rem !important;
    font-weight: 700 !important; color: __INK__ !important;
}
[data-testid="stForm"] { border: 1px solid __BORDER__ !important; border-radius: 16px !important; background: #FCFBFF; }
[data-testid="stExpander"] { border: 1px solid __BORDER__ !important; border-radius: 14px !important; background: __CARD_BG__; }
[data-testid="stAlert"] { border-radius: 14px !important; }
div[data-testid="stDataFrame"] { border-radius: 14px !important; overflow: hidden; border: 1px solid __BORDER__ !important; }

/* ---------- inputs ---------- */
div[data-baseweb="input"], div[data-baseweb="textarea"], div[data-baseweb="select"] > div {
    border-radius: 12px !important; border-color: __BORDER__ !important; background: #fff !important;
}
div[data-baseweb="input"]:focus-within, div[data-baseweb="textarea"]:focus-within,
div[data-baseweb="select"] > div:focus-within {
    border-color: __ACCENT__ !important; box-shadow: 0 0 0 3px rgba(101,88,224,0.16) !important;
}
[data-testid="stTextInputRootElement"], [data-testid="stTextAreaRootElement"], [data-testid="stNumberInputContainer"],
[data-testid="stSelectbox"] [role="group"], [data-testid="stMultiSelect"] [role="group"] {
    border-radius: 12px !important; border: 1px solid __BORDER__ !important; background: #FFFFFF !important;
}
[data-testid="stTextInputRootElement"]:focus-within, [data-testid="stTextAreaRootElement"]:focus-within,
[data-testid="stNumberInputContainer"]:focus-within, [data-testid="stSelectbox"] [role="group"]:focus-within {
    border-color: __ACCENT__ !important; box-shadow: 0 0 0 3px rgba(101,88,224,0.16) !important;
}
[data-testid="stWidgetLabel"] p { font-weight: 600; color: __SLATE__; }

/* ---------- buttons: outline pill by default, filled pill for primary/submit ---------- */
button[data-testid="stBaseButton-secondary"] {
    border-radius: 999px !important; border: 1.5px solid __ACCENT__ !important; background: #fff !important;
    padding: 0.3rem 1.05rem !important; transition: all 0.15s ease;
}
button[data-testid="stBaseButton-secondary"], button[data-testid="stBaseButton-secondary"] p {
    color: __ACCENT__ !important; font-weight: 600 !important;
}
button[data-testid="stBaseButton-secondary"]:hover:not(:disabled) {
    background: __SURFACE__ !important; border-color: __ACCENT_DARK__ !important;
}
button[data-testid="stBaseButton-primary"],
button[data-testid="stBaseButton-primaryFormSubmit"],
button[data-testid="stBaseButton-secondaryFormSubmit"] {
    border-radius: 999px !important; border: none !important;
    background: linear-gradient(135deg, #5B4DDB 0%, #7468EA 100%) !important;
    box-shadow: 0 6px 16px rgba(101,88,224,0.28); padding: 0.45rem 1.4rem !important;
    transition: all 0.15s ease;
}
button[data-testid="stBaseButton-primary"], button[data-testid="stBaseButton-primary"] p,
button[data-testid="stBaseButton-primaryFormSubmit"], button[data-testid="stBaseButton-primaryFormSubmit"] p,
button[data-testid="stBaseButton-secondaryFormSubmit"], button[data-testid="stBaseButton-secondaryFormSubmit"] p {
    color: #fff !important; font-weight: 600 !important;
}
button[data-testid="stBaseButton-primary"]:hover:not(:disabled),
button[data-testid="stBaseButton-primaryFormSubmit"]:hover:not(:disabled),
button[data-testid="stBaseButton-secondaryFormSubmit"]:hover:not(:disabled) {
    filter: brightness(0.94); transform: translateY(-1px); box-shadow: 0 10px 22px rgba(101,88,224,0.34);
}
button[data-testid^="stBaseButton"]:disabled { opacity: 0.45; box-shadow: none; }

/* ---------- tabs: pill tabs ---------- */
[data-testid="stTabs"] [role="tablist"] { gap: 6px; border-bottom: 1px solid __BORDER__; padding-bottom: 8px; }
[data-testid="stTab"], button[data-baseweb="tab"] {
    border-radius: 999px !important; padding: 6px 16px !important; color: __SLATE__ !important;
    font-weight: 600 !important; transition: background 0.15s ease;
}
[data-testid="stTab"] p, button[data-baseweb="tab"] p { font-weight: 600 !important; color: inherit !important; }
[data-testid="stTab"]:hover, button[data-baseweb="tab"]:hover { background: __SURFACE__; }
[data-testid="stTab"][aria-selected="true"], button[data-baseweb="tab"][aria-selected="true"] {
    background: __ACCENT_SOFT__ !important; color: __ACCENT_DARK__ !important;
}
[data-testid="stTab"] > div:not([data-testid]):empty, div[data-baseweb="tab-highlight"], div[data-baseweb="tab-border"] { display: none !important; }

/* ---------- progress ---------- */
div[role="progressbar"] > div { transition: width 0.5s ease; }

/* ---------- sidebar ---------- */
section[data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid __BORDER__; }
[data-testid="stSidebarHeader"] { display: flex; align-items: center; gap: 2px; padding-top: 1.2rem; }
[data-testid="stSidebarHeader"]::before {
    content: "Life"; order: -2; font-family: 'Space Grotesk', sans-serif; font-weight: 700;
    font-size: 1.45rem; letter-spacing: -0.02em; color: __INK__; margin-left: 6px;
}
[data-testid="stSidebarHeader"]::after {
    content: "OS"; order: -1; font-family: 'Space Grotesk', sans-serif; font-weight: 700;
    font-size: 1.15rem; color: #fff; background: __ACCENT__; border-radius: 7px; padding: 0 7px; margin-left: 2px;
}
[data-testid="stSidebarCollapseButton"] { margin-left: auto; order: 5; }
[data-testid="stSidebarNavLink"] {
    border-radius: 10px; margin: 2px 6px; color: __SLATE__; font-weight: 500; transition: background 0.15s ease;
}
[data-testid="stSidebarNavLink"]:hover { background: __SURFACE__; }
[data-testid="stSidebarNavLink"][aria-current="page"] {
    background: __ACCENT_SOFT__; color: __ACCENT_DARK__; font-weight: 700;
}
.lifeos-side-user { font-weight: 700; color: __INK__; line-height: 1.2; }
.lifeos-side-tag { font-family: 'Space Mono', monospace; font-size: 0.66rem; letter-spacing: 0.12em;
                   text-transform: uppercase; color: __MUTED__; margin-top: 4px; }

/* ---------- KPI card grid (custom HTML) ---------- */
.lifeos-kpi-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 14px; margin: 0.5rem 0 1rem 0;
}
.lifeos-kpi-card {
    background: __CARD_BG__; border: 1px solid __BORDER__; border-top: 3px solid __ACCENT__;
    border-radius: 16px; padding: 16px 18px;
    box-shadow: 0 1px 2px rgba(20,20,31,0.04), 0 8px 22px rgba(101,88,224,0.06);
    transition: box-shadow 0.18s ease, transform 0.18s ease;
}
.lifeos-kpi-card:hover { transform: translateY(-2px); box-shadow: 0 12px 28px rgba(101,88,224,0.12); }
.lifeos-kpi-card:nth-of-type(4n+2) { border-top-color: __TEAL__; }
.lifeos-kpi-card:nth-of-type(4n+3) { border-top-color: __CORAL__; }
.lifeos-kpi-card:nth-of-type(4n+4) { border-top-color: __AMBER__; }
.lifeos-kpi-icon { font-size: 1.3rem; margin-bottom: 4px; }
.lifeos-kpi-label {
    font-family: 'Space Mono', monospace; font-size: 0.66rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.08em; color: __MUTED__; margin-bottom: 4px;
}
.lifeos-kpi-value {
    font-family: 'Space Grotesk', sans-serif; font-size: 1.9rem; font-weight: 700;
    color: __INK__; line-height: 1.15;
}
.lifeos-kpi-sub { font-size: 0.76rem; color: __MUTED__; margin-top: 3px; }

/* ---------- badges (mono pills) ---------- */
.lifeos-badge {
    display: inline-block; padding: 2px 10px; border-radius: 999px; font-family: 'Space Mono', monospace;
    font-size: 0.66rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
}
.lifeos-badge-purple { background: __ACCENT_SOFT__; color: __ACCENT_DARK__; }
.lifeos-badge-green { background: __MINT__; color: #1F8A5B; }
.lifeos-badge-amber { background: #FEF1D6; color: #A86A00; }
.lifeos-badge-red { background: #FDE9E4; color: #C23B2E; }
.lifeos-badge-grey { background: #F1F0F7; color: __MUTED__; }

/* ---------- pinned countdown banner (like the reference's CTA section) ---------- */
.lifeos-countdown-banner {
    display: flex; align-items: center; gap: 28px;
    background: linear-gradient(120deg, #4A3FCF 0%, #6B5DE6 100%);
    border-radius: 20px; padding: 22px 30px; margin-bottom: 1.3rem; color: #FFFFFF;
    box-shadow: 0 14px 32px rgba(74,63,207,0.28);
}
.lifeos-countdown-banner.lifeos-countdown-overdue { background: linear-gradient(120deg, #F2784B 0%, #DD4F3A 100%); box-shadow: 0 14px 32px rgba(221,79,58,0.26); }
.lifeos-countdown-banner.lifeos-countdown-achieved { background: linear-gradient(120deg, #1F8A5B 0%, #2FA36B 100%); box-shadow: 0 14px 32px rgba(31,138,91,0.26); }
.lifeos-countdown-number { font-family: 'Space Grotesk', sans-serif; font-size: 3.3rem; font-weight: 700; line-height: 1; white-space: nowrap; }
.lifeos-countdown-number-label {
    font-family: 'Space Mono', monospace; font-size: 0.7rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.14em; opacity: 0.85; margin-top: 4px;
}
.lifeos-countdown-info { display: flex; flex-direction: column; border-left: 1px solid rgba(255,255,255,0.3); padding-left: 28px; }
.lifeos-countdown-title { font-family: 'Space Grotesk', sans-serif; font-size: 1.35rem; font-weight: 700; }
.lifeos-countdown-sub { font-size: 0.9rem; opacity: 0.88; margin-top: 4px; }

/* ---------- landing / login hero ---------- */
.lifeos-pill {
    display: inline-flex; align-items: center; gap: 8px; background: __SURFACE__;
    border: 1px solid #E3DFF7; border-radius: 999px; padding: 8px 18px;
    font-family: 'Space Mono', monospace; font-size: 0.74rem; font-weight: 700;
    letter-spacing: 0.18em; text-transform: uppercase; color: __ACCENT_DARK__;
}
.lifeos-pill .dot { width: 8px; height: 8px; border-radius: 50%; background: __GREEN__; display: inline-block; }
.lifeos-hero-title {
    font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 4.4rem; line-height: 1.02;
    letter-spacing: -0.03em; color: __INK__; margin: 18px 0 6px 0;
}
.lifeos-hero-title .lifeos-hl { border-radius: 0.16em; padding: 0 0.16em; }
.lifeos-hero-sub { font-family: 'Space Grotesk', sans-serif; font-weight: 500; font-size: 2.1rem; line-height: 1.15; color: __SLATE__; margin-bottom: 26px; }
.lifeos-checks { display: grid; grid-template-columns: 1fr 1fr; gap: 16px 28px; margin-top: 8px; }
.lifeos-check { display: flex; align-items: center; gap: 12px; font-family: 'Space Mono', monospace; font-size: 0.9rem; color: __SLATE__; }
.lifeos-check .tick {
    flex: 0 0 auto; width: 32px; height: 32px; border-radius: 50%; background: __MINT__; color: __GREEN__;
    display: inline-flex; align-items: center; justify-content: center; font-weight: 700;
}
@media (max-width: 900px) {
    .lifeos-hero-title { font-size: 3rem; } .lifeos-hero-sub { font-size: 1.5rem; }
    .lifeos-checks { grid-template-columns: 1fr; }
    .lifeos-countdown-banner { flex-direction: column; align-items: flex-start; gap: 12px; }
    .lifeos-countdown-info { border-left: none; padding-left: 0; }
}
"""


def _style_tokens(css: str) -> str:
    tokens = {
        "__FONT_IMPORT__": _FONT_IMPORT, "__ACCENT_DARK__": _ACCENT_DARK, "__ACCENT_SOFT__": _ACCENT_SOFT,
        "__ACCENT__": _ACCENT, "__SURFACE__": _SURFACE, "__BG__": _BG, "__INK__": _INK, "__SLATE__": _SLATE,
        "__MUTED__": _MUTED, "__CARD_BG__": _CARD_BG, "__BORDER__": _CARD_BORDER, "__TEAL__": _TEAL,
        "__CORAL__": _CORAL, "__AMBER__": _AMBER, "__GREEN__": _GREEN, "__MINT__": _MINT,
    }
    for key, value in tokens.items():
        css = css.replace(key, value)
    return css


def inject_global_css() -> None:
    """
    One shared stylesheet applied on every page (called automatically
    from render_sidebar_branding, so no page needs to remember to call
    it separately). Restyles Streamlit's default chrome -- buttons, tabs,
    cards, inputs, sidebar -- into the CampusX-One-inspired look:
    indigo accents, pill buttons, rounded white cards on a lavender page.
    """
    st.markdown(f"<style>{_style_tokens(_GLOBAL_CSS)}</style>", unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "", eyebrow: str = "") -> None:
    """Page heading in the reference's style: mono eyebrow label, bold title, slate subtitle."""
    import html as html_lib

    eyebrow_html = f'<div class="lifeos-eyebrow">{html_lib.escape(eyebrow)}</div>' if eyebrow else ""
    subtitle_html = f'<div class="lifeos-page-sub">{html_lib.escape(subtitle)}</div>' if subtitle else ""
    st.markdown(
        f'<div class="lifeos-page-header">{eyebrow_html}<h1>{html_lib.escape(title)}</h1>{subtitle_html}</div>',
        unsafe_allow_html=True,
    )


def render_sidebar_branding(user_name: str = "", avatar_base64: str | None = None) -> None:
    """
    Applies the global stylesheet, then shows a small branded header in
    the sidebar of every logged-in page, underneath Streamlit's
    automatic page navigation. Keeping this consistent across pages is
    what makes the app feel like one product instead of ten separate
    scripts.
    """
    inject_global_css()

    import html as html_lib

    with st.sidebar:
        st.markdown("---")
        user_html = f'<div class="lifeos-side-user">{html_lib.escape(user_name or "LifeOS")}</div>'
        tag_html = '<div class="lifeos-side-tag">Track. Analyze. Improve.</div>'
        if avatar_base64 and user_name:
            col1, col2 = st.columns([1, 3])
            with col1:
                st.markdown(avatar_img_tag(avatar_base64, size=38), unsafe_allow_html=True)
            with col2:
                st.markdown(user_html + tag_html, unsafe_allow_html=True)
        else:
            st.markdown(user_html + tag_html, unsafe_allow_html=True)


def avatar_img_tag(avatar_base64: str, size: int = 40) -> str:
    """A circular <img> tag from a stored base64 image, for inline use in st.markdown."""
    return (
        f'<img src="data:image/png;base64,{avatar_base64}" '
        f'style="width:{size}px;height:{size}px;border-radius:50%;object-fit:cover;" />'
    )


def progress_bar_html(percent: float, label: str = "") -> None:
    """
    A goal-completion progress bar. Uses Streamlit's own st.progress
    (reliable, and already picks up the purple accent color from
    inject_global_css). Defensively clamps the value and always shows
    the percentage as plain text too, so the number is visible even
    in the unlikely case the bar itself fails to render.
    """
    try:
        percent = float(percent)
    except (TypeError, ValueError):
        percent = 0.0
    if percent != percent:  # NaN check (NaN != NaN is True)
        percent = 0.0
    percent = max(0.0, min(100.0, percent))

    text = f"{label} — {percent:.0f}%" if label else f"{percent:.0f}%"
    try:
        st.progress(percent / 100, text=text)
    except Exception:
        # Guaranteed fallback -- the number is always visible even if
        # the progress widget itself can't render for some reason.
        st.caption(text)


def countdown_banner_html(title: str, sub: str, number: str, number_label: str, variant: str = "default") -> None:
    """
    A big, prominent countdown card for the Dashboard -- "how many
    days until I need to crack this job". variant: "default"
    (in-progress countdown), "overdue" (past the deadline, still not
    achieved), or "achieved" (got it).

    Built as ONE continuous line with no leading whitespace on any
    line, same reasoning as kpi_card_row -- st.markdown's markdown
    parser would otherwise treat an indented line after a blank one
    as a literal code block instead of rendering it as HTML.
    """
    variant_class = f" lifeos-countdown-{variant}" if variant in ("overdue", "achieved") else ""
    st.markdown(
        f'<div class="lifeos-countdown-banner{variant_class}">'
        f'<div><div class="lifeos-countdown-number">{number}</div>'
        f'<div class="lifeos-countdown-number-label">{number_label}</div></div>'
        '<div class="lifeos-countdown-info">'
        f'<div class="lifeos-countdown-title">{title}</div>'
        f'<div class="lifeos-countdown-sub">{sub}</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )


_FLOW_CSS = """
* { box-sizing: border-box; }
body { margin: 0; font-family: "Inter", "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: __INK__; }
.lane-label { position: absolute; left: 6px; font-family: "Space Mono", monospace; font-size: 11px; font-weight: 700;
              letter-spacing: .16em; text-transform: uppercase; color: __ACCENT__; }
.node { position: absolute; width: __NODE_W__px; height: __NODE_H__px; padding: 9px 12px; border-radius: 14px;
        border: 2px solid __BORDER__; background: #FFFFFF; overflow: hidden; }
.node.ready { border-color: __GREEN__; background: __MINT__; }
.node.progress { border-color: __ACCENT__; background: __SOFT__; box-shadow: 0 0 0 4px rgba(101,88,224,.16); }
.node.future { opacity: .82; }
.ord { font-family: "Space Mono", monospace; font-size: 10px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: __MUTED__; }
.ttl { font-family: "Space Grotesk", "Inter", sans-serif; font-size: 15px; font-weight: 700; line-height: 1.2; margin-top: 2px; max-height: 36px; overflow: hidden; }
.sts { font-family: "Space Mono", monospace; font-size: 10.5px; font-weight: 700; letter-spacing: .05em; text-transform: uppercase; margin-top: 3px; }
.ready .sts { color: #1F8A5B; } .progress .sts { color: __ACCENT_DARK__; } .future .sts { color: __MUTED__; }
.pwrap { position: absolute; left: 12px; right: 12px; bottom: 9px; display: flex; align-items: center; gap: 7px; }
.pbar { flex: 1; height: 7px; border-radius: 4px; background: rgba(20,20,31,.10); overflow: hidden; }
.pbar span { display: block; height: 100%; border-radius: 4px; background: __MUTED__; }
.ready .pbar span { background: __GREEN__; } .progress .pbar span { background: __ACCENT__; }
.pct { font-size: 11px; font-weight: 700; min-width: 30px; text-align: right; }
.nogoal { font-size: 10.5px; color: __MUTED__; }
svg { position: absolute; left: 0; overflow: visible; }
"""


def roadmap_flowchart_html(steps: list[dict]) -> None:
    """
    Renders the learning roadmap as a real flowchart.

    * Each track ("lane") is its own row, labelled "Track N" when there is
      more than one.
    * Inside a track, steps that share a step number are ONE stage and are
      stacked vertically (they run in parallel). Arrows fan out from every
      step of the previous stage to every step of the next stage, and fan
      back in -- like a normal flowchart's split/join.
    * Each box shows its status colour and a completion % bar (from the
      linked goals' tasks; "No goal linked" if there's nothing to measure).

    Each item: {"order_index": 4, "title": "FastAPI", "status": "In Progress",
    "lane": 1, "progress_pct": 45.0 or None, "goal_titles": [..optional..]}.

    Drawn inside an iframe (components.html) so the SVG connector lines are
    guaranteed to render -- st.markdown can strip SVG. Box sizes are fixed,
    which is what lets the connector coordinates be computed exactly.
    """
    import html as html_lib

    NODE_W, NODE_H, GAP_Y, CONN_W, PAD = 178, 112, 14, 72, 6
    LABEL_H, LANE_GAP = 22, 18
    status_class = {"Ready": "ready", "In Progress": "progress", "Future": "future"}

    lanes: dict[int, dict[int, list[dict]]] = {}
    for step in steps:
        lanes.setdefault(step.get("lane", 1), {}).setdefault(step["order_index"], []).append(step)
    show_labels = len(lanes) > 1

    body, svg_defs_done = [], False
    y_cursor, max_width = PAD, 0
    for lane_number in sorted(lanes):
        stages = [lanes[lane_number][n] for n in sorted(lanes[lane_number])]
        stage_heights = [len(st_) * NODE_H + (len(st_) - 1) * GAP_Y for st_ in stages]
        lane_h = max(stage_heights)
        lane_w = len(stages) * NODE_W + (len(stages) - 1) * CONN_W
        max_width = max(max_width, lane_w)

        if show_labels:
            body.append(f'<div class="lane-label" style="top:{y_cursor}px">Track {lane_number}</div>')
            y_cursor += LABEL_H
        lane_top = y_cursor

        # y of the vertical centre of each box, per stage (stages are vertically centred in the lane)
        centres, boxes = [], []
        for i, stage in enumerate(stages):
            x = PAD + i * (NODE_W + CONN_W)
            offset = (lane_h - stage_heights[i]) / 2
            stage_centres = []
            for j, step in enumerate(stage):
                y = lane_top + offset + j * (NODE_H + GAP_Y)
                stage_centres.append(y - lane_top + NODE_H / 2)
                cls = status_class.get(step["status"], "future")
                pct = step.get("progress_pct")
                if pct is None:
                    progress_html = '<div class="pwrap"><span class="nogoal">No goal linked</span></div>'
                else:
                    shown = max(0.0, min(float(pct), 100.0))
                    progress_html = (
                        f'<div class="pwrap"><div class="pbar"><span style="width:{shown}%"></span></div>'
                        f'<span class="pct">{shown:.0f}%</span></div>'
                    )
                tip = html_lib.escape(", ".join(step.get("goal_titles") or []))
                boxes.append(
                    f'<div class="node {cls}" title="{tip}" style="left:{x}px;top:{y}px">'
                    f'<div class="ord">Step {step["order_index"]}</div>'
                    f'<div class="ttl">{html_lib.escape(step["title"])}</div>'
                    f'<div class="sts">{html_lib.escape(step["status"])}</div>'
                    f'{progress_html}</div>'
                )
            centres.append(stage_centres)

        # connectors: every box of a stage -> every box of the next stage (split / join)
        paths = []
        for i in range(len(stages) - 1):
            x1 = PAD + i * (NODE_W + CONN_W) + NODE_W
            x2 = PAD + (i + 1) * (NODE_W + CONN_W)
            mid = (x1 + x2) / 2
            for y1 in centres[i]:
                for y2 in centres[i + 1]:
                    paths.append(
                        f'<path d="M{x1} {y1} C{mid} {y1}, {mid} {y2}, {x2 - 2} {y2}" fill="none" '
                        f'stroke="#9A94C9" stroke-opacity=".9" stroke-width="2" marker-end="url(#arr)"/>'
                    )
        if paths:
            body.append(
                f'<svg style="top:{lane_top}px" width="{lane_w + PAD * 2}" height="{lane_h}">'
                + "".join(paths) + "</svg>"
            )
        body.extend(boxes)
        y_cursor = lane_top + lane_h + LANE_GAP

    total_h = y_cursor + 16  # extra room for a horizontal scrollbar when the chart is wide
    css = (
        _FLOW_CSS.replace("__INK__", _INK).replace("__MUTED__", _MUTED).replace("__BORDER__", _CARD_BORDER)
        .replace("__ACCENT_DARK__", _ACCENT_DARK).replace("__ACCENT__", _ACCENT).replace("__GREEN__", _GREEN)
        .replace("__MINT__", _MINT).replace("__SOFT__", _ACCENT_SOFT)
        .replace("__NODE_W__", str(NODE_W)).replace("__NODE_H__", str(NODE_H))
    )
    marker = (
        '<svg width="0" height="0" style="position:absolute"><defs>'
        f'<marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
        f'<path d="M0 0 L10 5 L0 10 z" fill="#9A94C9"/></marker></defs></svg>'
    )
    doc = (
        f"<style>@import url('{_FONT_IMPORT}');{css}</style>{marker}"
        f'<div style="position:relative;width:{max_width + PAD * 2}px;height:{y_cursor}px">'
        + "".join(body) + "</div>"
    )
    components.html(doc, height=total_h, scrolling=True)


def duration_input(label: str, key: str, default_minutes: int = 30, max_hours: int = 23) -> int:
    """
    A paired hours+minutes input that returns the total as minutes.
    Used everywhere the app collects a duration, so the person can
    enter '1h 30m' instead of doing the minutes math themselves.
    """
    default_hours, default_mins = divmod(max(int(default_minutes), 0), 60)
    st.caption(label)
    col1, col2 = st.columns(2)
    with col1:
        hours = st.number_input(
            "Hours", min_value=0, max_value=max_hours, value=default_hours, key=f"{key}_hours"
        )
    with col2:
        minutes = st.number_input(
            "Minutes", min_value=0, max_value=59, value=default_mins, key=f"{key}_minutes"
        )
    return int(hours) * 60 + int(minutes)


def kpi_card_row(items: list[dict]) -> None:
    """
    A row of polished KPI cards -- nicer than plain st.metric for
    headline numbers (Dashboard top row, Wrapped highlights). Each
    item: {"icon": "🔥", "label": "Current Streak", "value": "12 days",
    "sub": optional smaller caption below the value, "color": optional
    top-border color override -- one of "accent"/"green" (dark green),
    "teal"/"sage", "coral"/"tan-brown", "amber"/"tan", or any raw CSS
    color -- otherwise cards cycle through those four automatically.

    Built as ONE continuous line with no leading whitespace on any
    line -- st.markdown runs content through a markdown parser even
    with unsafe_allow_html=True, and any line indented 4+ spaces
    after a blank line gets treated as a literal code block instead
    of being rendered as HTML. Keeping this single-line avoids that.
    """
    named_colors = {
        "accent": _ACCENT, "green": _GREEN, "indigo": _ACCENT,
        "teal": _TEAL, "sage": _TEAL,
        "coral": _CORAL, "tan-brown": _CORAL,
        "amber": _AMBER, "tan": _AMBER,
    }
    cards = []
    for item in items:
        sub_html = f'<div class="lifeos-kpi-sub">{item["sub"]}</div>' if item.get("sub") else ""
        color_style = ""
        if item.get("color"):
            resolved_color = named_colors.get(item["color"], item["color"])
            color_style = f' style="border-top-color: {resolved_color};"'
        cards.append(
            f'<div class="lifeos-kpi-card"{color_style}>'
            f'<div class="lifeos-kpi-icon">{item.get("icon", "")}</div>'
            f'<div class="lifeos-kpi-label">{item["label"]}</div>'
            f'<div class="lifeos-kpi-value">{item["value"]}</div>'
            f'{sub_html}'
            '</div>'
        )
    st.markdown(f'<div class="lifeos-kpi-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def badge(text: str, color: str = "purple") -> str:
    """
    Returns an inline HTML pill/badge span, e.g. badge("Easy", "green").
    Colors: purple, green, amber, red, grey. Use inside st.markdown(...,
    unsafe_allow_html=True) or embed in a larger HTML string.
    """
    return f'<span class="lifeos-badge lifeos-badge-{color}">{text}</span>'


def difficulty_badge(difficulty: str) -> str:
    """Difficulty -> pre-colored badge (Easy=green, Medium=amber, Hard=red)."""
    color = {"Easy": "green", "Medium": "amber", "Hard": "red"}.get(difficulty, "grey")
    return badge(difficulty, color)


def priority_badge(priority: int) -> str:
    """Task priority (1=High, 2=Medium, 3=Low) -> pre-colored badge."""
    label = {1: "High", 2: "Medium", 3: "Low"}.get(priority, "Medium")
    color = {1: "red", 2: "amber", 3: "grey"}.get(priority, "amber")
    return badge(label, color)


def status_badge(status: str) -> str:
    """Project/job-target/milestone status -> pre-colored badge."""
    color = {
        "Ready": "green", "In Progress": "purple", "Planned": "grey", "On Hold": "amber", "Done": "green",
        "Future": "grey", "Upcoming": "grey", "Achieved": "green",
    }.get(status, "grey")
    return badge(status, color)


def live_timer_display(start_epoch_ms: float, base_elapsed_ms: float, key: str) -> None:
    """
    Renders a stopwatch-style HH:MM:SS display that keeps ticking up
    client-side (via a small embedded script) without needing
    Streamlit to rerun the whole app every second. `start_epoch_ms` is
    when the current running segment began; `base_elapsed_ms` is
    whatever elapsed time had already accumulated before this segment
    (e.g. from a previous pause/resume).
    """
    html = f"""
    <style>@import url('{_FONT_IMPORT}'); body {{ margin: 0; }}</style>
    <div id="lifeos-timer-{key}" style="
        font-size: 2.8rem;
        font-weight: 700;
        font-family: 'Space Mono', ui-monospace, monospace;
        letter-spacing: 0.04em;
        color: {_ACCENT_DARK};
        padding: 12px 0;
        text-align: center;
        background: {_SURFACE};
        border: 1px solid #E3DFF7;
        border-radius: 18px;
        box-shadow: 0 8px 22px rgba(101, 88, 224, 0.10);
    ">00:00:00</div>
    <script>
        (function() {{
            const startEpoch = {start_epoch_ms};
            const baseElapsed = {base_elapsed_ms};
            const el = document.getElementById("lifeos-timer-{key}");

            function formatTime(totalMs) {{
                const totalSeconds = Math.floor(totalMs / 1000);
                const h = Math.floor(totalSeconds / 3600);
                const m = Math.floor((totalSeconds % 3600) / 60);
                const s = totalSeconds % 60;
                const pad = (n) => String(n).padStart(2, "0");
                return pad(h) + ":" + pad(m) + ":" + pad(s);
            }}

            function tick() {{
                const now = Date.now();
                const elapsed = baseElapsed + (now - startEpoch);
                if (el) {{
                    el.textContent = formatTime(elapsed);
                }}
            }}

            tick();
            setInterval(tick, 1000);
        }})();
    </script>
    """
    components.html(html, height=90)
