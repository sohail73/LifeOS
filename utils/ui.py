"""
utils/ui.py

Small shared UI pieces used across pages: global styling (cards, KPI
tiles, badges), a branded sidebar header, avatar rendering, and a
client-side ticking timer display (so the Study Timer visibly counts
up without needing a full Streamlit rerun every second).
"""

import streamlit as st
import streamlit.components.v1 as components

_ACCENT = "#274245"
_ACCENT_DARK = "#16292B"
_INK = "#1B2426"
_MUTED = "#5C6B69"
_CARD_BG = "#FFFFFF"
_CARD_BORDER = "#E8E1C9"
_TEAL = "#3D6B66"
_CORAL = "#C97B4A"
_AMBER = "#DFD6AE"


def inject_global_css() -> None:
    """
    One shared stylesheet applied on every page (called automatically
    from render_sidebar_branding, so no page needs to remember to call
    it separately). Restyles Streamlit's default metric/button/tab/
    dataframe/container chrome into a consistent, colorful card-based
    look instead of a flat white default.
    """
    st.markdown(
        f"""
        <style>
            /* App background -- a soft tinted gradient instead of flat white */
            [data-testid="stAppViewContainer"] > .main {{
                background: linear-gradient(160deg, #FAF7EE 0%, #F3EFDD 45%, #FBF9F0 100%);
            }}

            /* Headings */
            h1, h2, h3 {{
                font-weight: 700 !important;
                letter-spacing: -0.01em;
                color: {_INK} !important;
            }}
            h1 {{
                background: linear-gradient(90deg, {_ACCENT} 0%, {_TEAL} 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                display: inline-block;
                padding-bottom: 0.3rem;
            }}

            /* Metric tiles -> colorful KPI cards, cycling accent colors */
            div[data-testid="stMetric"] {{
                background: {_CARD_BG};
                border: 1px solid {_CARD_BORDER};
                border-left: 4px solid {_ACCENT};
                border-radius: 14px;
                padding: 1rem 1.1rem 0.8rem 1.1rem;
                box-shadow: 0 3px 12px rgba(39, 66, 69, 0.10);
            }}
            div[data-testid="stMetricLabel"] {{
                font-size: 0.78rem !important;
                font-weight: 600 !important;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                color: {_MUTED} !important;
            }}
            div[data-testid="stMetricValue"] {{
                font-size: 1.9rem !important;
                font-weight: 800 !important;
                color: {_INK} !important;
            }}

            /* Hover lift -- cards rise slightly and deepen their shadow.
               (No entrance/fade-in animation here -- Streamlit reruns the
               whole script on every click, so anything that "plays in"
               on render would replay on every single interaction and
               feel like the page reloading instead of a nice touch.) */
            div[data-testid="stMetric"],
            div[data-testid="stVerticalBlockBorderWrapper"],
            .lifeos-kpi-card {{
                transition: transform 0.18s ease, box-shadow 0.18s ease;
            }}
            div[data-testid="stMetric"]:hover,
            div[data-testid="stVerticalBlockBorderWrapper"]:hover,
            .lifeos-kpi-card:hover {{
                transform: translateY(-3px);
                box-shadow: 0 8px 20px rgba(39, 66, 69, 0.18);
            }}

            /* Bordered containers -> soft elevated cards */
            div[data-testid="stVerticalBlockBorderWrapper"] {{
                border-radius: 14px !important;
                border: 1px solid {_CARD_BORDER} !important;
                background: {_CARD_BG};
                box-shadow: 0 3px 12px rgba(39, 66, 69, 0.08);
            }}

            /* Buttons */
            .stButton > button, .stFormSubmitButton > button {{
                border-radius: 10px !important;
                font-weight: 600 !important;
                border: 1px solid {_CARD_BORDER} !important;
                transition: all 0.15s ease;
            }}
            .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{
                background: {_ACCENT} !important;
                border: none !important;
            }}
            .stButton > button:hover, .stFormSubmitButton > button:hover {{
                border-color: {_ACCENT} !important;
                color: {_ACCENT} !important;
                transform: translateY(-1px) scale(1.01);
            }}

            /* Tabs */
            button[data-baseweb="tab"] {{
                font-weight: 600 !important;
                border-radius: 8px 8px 0 0 !important;
            }}
            button[aria-selected="true"] {{
                color: {_ACCENT} !important;
            }}
            div[data-baseweb="tab-highlight"] {{
                background-color: {_ACCENT} !important;
            }}

            /* Progress bar */
            /* Progress bar uses the theme's primaryColor automatically
               (set in .streamlit/config.toml) -- no custom color
               override here, since a mismatched selector could hide
               it instead of just failing to color it. A transition is
               safe either way -- worst case it simply doesn't match. */
            div[role="progressbar"] > div {{
                transition: width 0.5s ease;
            }}

            /* Dataframes */
            div[data-testid="stDataFrame"] {{
                border-radius: 12px !important;
                overflow: hidden;
                border: 1px solid {_CARD_BORDER} !important;
            }}

            /* Sidebar */
            section[data-testid="stSidebar"] {{
                border-right: 1px solid {_CARD_BORDER};
                background: linear-gradient(180deg, #F3EFDD 0%, #FAF8F0 100%);
            }}

            /* LifeOS KPI card grid (custom HTML component) -- each card
               cycles through an accent color via its top border for a
               livelier, less monotone look than a single flat color. */
            .lifeos-kpi-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 12px;
                margin: 0.5rem 0 1rem 0;
            }}
            .lifeos-kpi-card {{
                background: linear-gradient(160deg, {_CARD_BG} 0%, #FBF9F0 100%);
                border: 1px solid {_CARD_BORDER};
                border-top: 3px solid {_ACCENT};
                border-radius: 14px;
                padding: 16px 18px;
                box-shadow: 0 3px 12px rgba(39, 66, 69, 0.10);
            }}
            .lifeos-kpi-card:nth-of-type(4n+2) {{ border-top-color: {_TEAL}; }}
            .lifeos-kpi-card:nth-of-type(4n+3) {{ border-top-color: {_CORAL}; }}
            .lifeos-kpi-card:nth-of-type(4n+4) {{ border-top-color: {_AMBER}; }}
            .lifeos-kpi-icon {{ font-size: 1.3rem; margin-bottom: 4px; }}
            .lifeos-kpi-label {{
                font-size: 0.72rem;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                color: {_MUTED};
                margin-bottom: 2px;
            }}
            .lifeos-kpi-value {{
                font-size: 1.7rem;
                font-weight: 800;
                color: {_INK};
                line-height: 1.2;
            }}
            .lifeos-kpi-sub {{
                font-size: 0.75rem;
                color: {_MUTED};
                margin-top: 2px;
            }}

            /* Badges (status/difficulty pills) */
            .lifeos-badge {{
                display: inline-block;
                padding: 2px 10px;
                border-radius: 999px;
                font-size: 0.72rem;
                font-weight: 700;
                letter-spacing: 0.02em;
            }}
            .lifeos-badge-purple {{ background: #DCE6E5; color: {_ACCENT_DARK}; }}
            .lifeos-badge-green {{ background: #D7F7EF; color: #0D8A73; }}
            .lifeos-badge-amber {{ background: #FEF0D9; color: #B4720A; }}
            .lifeos-badge-red {{ background: #FFE4E1; color: #C23B2E; }}
            .lifeos-badge-grey {{ background: #F1EFFA; color: {_MUTED}; }}
        </style>
        """,
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

    with st.sidebar:
        st.markdown("---")
        if avatar_base64 and user_name:
            col1, col2 = st.columns([1, 3])
            with col1:
                st.markdown(avatar_img_tag(avatar_base64, size=36), unsafe_allow_html=True)
            with col2:
                st.markdown(f"**LifeOS**  \n{user_name}")
        else:
            st.markdown("**LifeOS**")
            if user_name:
                st.caption(user_name)
        st.caption("Track. Analyze. Improve.")


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
    "sub": optional smaller caption below the value}.

    Built as ONE continuous line with no leading whitespace on any
    line -- st.markdown runs content through a markdown parser even
    with unsafe_allow_html=True, and any line indented 4+ spaces
    after a blank line gets treated as a literal code block instead
    of being rendered as HTML. Keeping this single-line avoids that.
    """
    cards = []
    for item in items:
        sub_html = f'<div class="lifeos-kpi-sub">{item["sub"]}</div>' if item.get("sub") else ""
        cards.append(
            '<div class="lifeos-kpi-card">'
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
    <div id="lifeos-timer-{key}" style="
        font-size: 2.6rem;
        font-weight: 800;
        font-family: 'Source Code Pro', monospace;
        color: {_ACCENT};
        padding: 10px 0;
        text-align: center;
        background: linear-gradient(160deg, #FFFFFF 0%, #FAF7EE 100%);
        border: 1px solid {_CARD_BORDER};
        border-radius: 14px;
        box-shadow: 0 2px 10px rgba(39, 66, 69, 0.12);
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
