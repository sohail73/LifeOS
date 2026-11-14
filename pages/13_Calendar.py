"""
pages/13_Calendar.py

A month-view calendar for things you want to keep track of on a date:
internships, interviews, applications, exams, hackathons, deadlines...
Add an event for one day or a whole date range (e.g. a 2-month
internship), see it on the month grid in its category's colour, and
edit or delete it later from the All Events tab. Days you marked as
leave (Dashboard > App Streak) show up in blue.
"""

import calendar
import html as html_lib
from datetime import date

import streamlit as st

from auth.session import current_user_id, current_user_name, require_login
from database.queries import (
    add_calendar_event,
    delete_calendar_event,
    get_avatar_base64,
    get_calendar_events,
    get_leave_dates,
    update_calendar_event,
)
from utils.ui import kpi_card_row, page_header, render_sidebar_branding

st.set_page_config(page_title="Calendar - LifeOS", page_icon="⚡", layout="wide")
require_login()

user_id = current_user_id()
render_sidebar_branding(current_user_name(), get_avatar_base64(user_id))
page_header("Calendar", eyebrow="Plan")
st.caption("Your internships, interviews, exams and deadlines -- all on one calendar.")

CATEGORY_COLORS = {
    "Internship": "#6558E0",
    "Interview": "#F2784B",
    "Application": "#14A3B8",
    "Exam": "#E5484D",
    "Hackathon": "#2FA36B",
    "Deadline": "#C98A0B",
    "Other": "#6B7084",
}
CATEGORIES = list(CATEGORY_COLORS.keys())
LEAVE_COLOR = "#2F7BE5"

today = date.today()
events = get_calendar_events(user_id)
leave_dates = get_leave_dates(user_id)


def _d(iso: str) -> date:
    return date.fromisoformat(iso)


def _fmt_range(ev: dict) -> str:
    start, end = _d(ev["start_date"]), _d(ev["end_date"])
    if start == end:
        return start.strftime("%d %b %Y")
    return f"{start.strftime('%d %b %Y')} → {end.strftime('%d %b %Y')}"


def _events_on(day: date) -> list:
    return [e for e in events if _d(e["start_date"]) <= day <= _d(e["end_date"])]


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
ongoing = [e for e in events if _d(e["start_date"]) <= today <= _d(e["end_date"])]
upcoming = [e for e in events if _d(e["start_date"]) > today]
next_event = upcoming[0] if upcoming else None

kpi_card_row([
    {"icon": " ", "label": "Happening Now", "value": len(ongoing)},
    {"icon": " ", "label": "Upcoming", "value": len(upcoming)},
    {
        "icon": " ",
        "label": "Next Up",
        "value": f"{(_d(next_event['start_date']) - today).days}d" if next_event else "--",
        "sub": html_lib.escape(next_event["title"]) if next_event else "nothing scheduled",
    },
    {"icon": " ", "label": "Total Events", "value": len(events)},
])

month_tab, add_tab, all_tab = st.tabs(["Month View", "Add Event", "All Events"])

# ---------------------------------------------------------------------------
# Month view
# ---------------------------------------------------------------------------
with month_tab:
    if "cal_year" not in st.session_state:
        st.session_state["cal_year"] = today.year
        st.session_state["cal_month"] = today.month

    def _shift_month(delta: int) -> None:
        month = st.session_state["cal_month"] + delta
        year = st.session_state["cal_year"]
        if month < 1:
            month, year = 12, year - 1
        elif month > 12:
            month, year = 1, year + 1
        st.session_state["cal_month"], st.session_state["cal_year"] = month, year

    def _go_today() -> None:
        st.session_state["cal_year"], st.session_state["cal_month"] = today.year, today.month

    nav_prev, nav_title, nav_today, nav_next = st.columns([1, 4, 1, 1])
    nav_prev.button("◀ Prev", on_click=_shift_month, args=(-1,), use_container_width=True)
    nav_next.button("Next ▶", on_click=_shift_month, args=(1,), use_container_width=True)
    nav_today.button("Today", on_click=_go_today, use_container_width=True)

    year, month = st.session_state["cal_year"], st.session_state["cal_month"]
    nav_title.markdown(f"### {calendar.month_name[month]} {year}")

    weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)
    MAX_CHIPS = 3

    css = (
        "<style>"
        ".lo-cal{width:100%;border-collapse:separate;border-spacing:4px;table-layout:fixed;}"
        ".lo-cal th{font-size:12px;color:#6B7084;font-weight:600;padding:4px 0;text-align:center;}"
        ".lo-cal td{vertical-align:top;height:104px;padding:6px;border-radius:10px;"
        "background:#FFFFFF;border:1px solid #ECEAF5;overflow:hidden;}"
        ".lo-cal td.out{background:transparent;border-color:transparent;opacity:.45;}"
        ".lo-cal td.today{border:2px solid #6558E0;}"
        f".lo-cal td.leave{{background:rgba(47,123,229,.16);border-color:{LEAVE_COLOR};}}"
        ".lo-daynum{font-size:12px;font-weight:600;color:#14141F;margin-bottom:3px;}"
        ".lo-chip{display:block;font-size:11px;line-height:1.25;color:#fff;border-radius:6px;"
        "padding:2px 6px;margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}"
        ".lo-more{font-size:11px;color:#6B7084;}"
        ".lo-leave{font-size:10px;color:#2F7BE5;font-weight:600;}"
        "</style>"
    )

    rows_html = []
    for week in weeks:
        cells = []
        for day in week:
            classes = []
            if day.month != month:
                classes.append("out")
            if day == today:
                classes.append("today")
            if day in leave_dates:
                classes.append("leave")

            inner = f'<div class="lo-daynum">{day.day}</div>'
            if day in leave_dates:
                inner += '<div class="lo-leave">On leave</div>'
            day_events = _events_on(day)
            for ev in day_events[:MAX_CHIPS]:
                color = CATEGORY_COLORS.get(ev["category"], CATEGORY_COLORS["Other"])
                label = html_lib.escape(ev["title"])
                tip = html_lib.escape(f"{ev['category']}: {ev['title']}")
                inner += f'<span class="lo-chip" style="background:{color}" title="{tip}">{label}</span>'
            if len(day_events) > MAX_CHIPS:
                inner += f'<div class="lo-more">+{len(day_events) - MAX_CHIPS} more</div>'

            cells.append(f'<td class="{" ".join(classes)}">{inner}</td>')
        rows_html.append(f'<tr>{"".join(cells)}</tr>')

    header = "".join(f"<th>{d}</th>" for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    st.markdown(
        css + f'<table class="lo-cal"><thead><tr>{header}</tr></thead><tbody>{"".join(rows_html)}</tbody></table>',
        unsafe_allow_html=True,
    )

    legend = "".join(
        f'<span class="lo-chip" style="display:inline-block;margin-right:6px;background:{c}">{html_lib.escape(n)}</span>'
        for n, c in CATEGORY_COLORS.items()
    )
    legend += f'<span class="lo-chip" style="display:inline-block;background:{LEAVE_COLOR}">Leave</span>'
    st.markdown(legend, unsafe_allow_html=True)

    # Events overlapping the month being viewed
    month_start, month_end = weeks[0][0], weeks[-1][-1]
    first_of_month = date(year, month, 1)
    last_of_month = date(year, month, calendar.monthrange(year, month)[1])
    month_events = [
        e for e in events if _d(e["start_date"]) <= last_of_month and _d(e["end_date"]) >= first_of_month
    ]

    st.markdown(f"#### Events in {calendar.month_name[month]} {year}")
    if not month_events:
        st.caption("Nothing scheduled this month. Add something in the **Add Event** tab.")
    else:
        for ev in month_events:
            color = CATEGORY_COLORS.get(ev["category"], CATEGORY_COLORS["Other"])
            line = (
                f'<span class="lo-chip" style="display:inline-block;background:{color}">'
                f'{html_lib.escape(ev["category"])}</span> '
                f'**{ev["title"]}**'
            )
            if ev["company"]:
                line += f" · {ev['company']}"
            line += f" · {_fmt_range(ev)}"
            st.markdown(line, unsafe_allow_html=True)
            if ev["notes"]:
                st.caption(ev["notes"])

# ---------------------------------------------------------------------------
# Add event
# ---------------------------------------------------------------------------
with add_tab:
    st.subheader("Add an Event")
    with st.form("calendar_add_form", clear_on_submit=True):
        title = st.text_input("Title", placeholder="e.g. Data Science Intern, Technocrats Hackathon, DBMS Exam")
        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox("Category", CATEGORIES)
        with col2:
            company = st.text_input("Company / Place (optional)", placeholder="e.g. Google, Bhopal")
        date_range = st.date_input(
            "Date or date range",
            value=(today, today),
            help="One day: pick it twice (or just once). Several days (e.g. a 2-month internship): pick the start and the end date.",
        )
        notes = st.text_area("Notes (optional)", placeholder="Stipend, link, interviewer, what to prepare...")
        submitted = st.form_submit_button("Add to Calendar", use_container_width=True)

    if submitted:
        picked = list(date_range) if isinstance(date_range, (tuple, list)) else [date_range]
        if not title.strip():
            st.warning("Give the event a title.")
        elif not picked:
            st.warning("Pick a date first.")
        else:
            add_calendar_event(
                user_id=user_id,
                title=title,
                category=category,
                start_date=picked[0].isoformat(),
                end_date=picked[-1].isoformat(),
                company=company,
                notes=notes,
            )
            st.success(f"Added '{title.strip()}' to your calendar.")
            st.rerun()

# ---------------------------------------------------------------------------
# All events -- edit / delete
# ---------------------------------------------------------------------------
with all_tab:
    st.subheader("All Events")
    if not events:
        st.info("No events yet. Add your first one in the **Add Event** tab.")
    else:
        filter_choice = st.selectbox("Category", ["All"] + CATEGORIES, key="cal_filter")
        show_past = st.checkbox("Show past events", value=False)

        visible = [
            e for e in events
            if (filter_choice == "All" or e["category"] == filter_choice)
            and (show_past or _d(e["end_date"]) >= today)
        ]
        if not visible:
            st.caption("No events match this filter.")

        for ev in visible:
            start, end = _d(ev["start_date"]), _d(ev["end_date"])
            if start <= today <= end:
                when = "happening now"
            elif start > today:
                when = f"in {(start - today).days} day(s)"
            else:
                when = "past"
            heading = f"{ev['title']}" + (f" -- {ev['company']}" if ev["company"] else "")
            with st.expander(f"{heading}  ·  {ev['category']}  ·  {_fmt_range(ev)}  ·  {when}"):
                with st.form(f"cal_edit_{ev['id']}"):
                    new_title = st.text_input("Title", value=ev["title"], key=f"cal_t_{ev['id']}")
                    ecol1, ecol2 = st.columns(2)
                    with ecol1:
                        cat_index = CATEGORIES.index(ev["category"]) if ev["category"] in CATEGORIES else len(CATEGORIES) - 1
                        new_category = st.selectbox("Category", CATEGORIES, index=cat_index, key=f"cal_c_{ev['id']}")
                    with ecol2:
                        new_company = st.text_input("Company / Place", value=ev["company"] or "", key=f"cal_co_{ev['id']}")
                    new_range = st.date_input("Date or date range", value=(start, end), key=f"cal_d_{ev['id']}")
                    new_notes = st.text_area("Notes", value=ev["notes"] or "", key=f"cal_n_{ev['id']}")
                    save = st.form_submit_button("Save changes", use_container_width=True)

                if save:
                    picked = list(new_range) if isinstance(new_range, (tuple, list)) else [new_range]
                    if not new_title.strip():
                        st.warning("Title can't be empty.")
                    elif not picked:
                        st.warning("Pick a date first.")
                    else:
                        update_calendar_event(
                            user_id, ev["id"], new_title, new_category,
                            picked[0].isoformat(), picked[-1].isoformat(), new_company, new_notes,
                        )
                        st.rerun()

                if st.button("Delete event", key=f"cal_del_{ev['id']}"):
                    delete_calendar_event(user_id, ev["id"])
                    st.rerun()
