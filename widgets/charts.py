"""
widgets/charts.py

Small, reusable Plotly chart builders. Every function returns a
plotly.graph_objects Figure -- pages call st.plotly_chart(fig, ...)
on the result. Keeping chart construction here (instead of inline in
every page) means one consistent, professional look across
Dashboard, Analytics, AI Insights, and Wrapped -- matching the
indigo accent theme (CampusX One inspired) in .streamlit/config.toml and utils/ui.py.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.helper import load_leave_dates

PRIMARY_COLOR = "#6558E0"
PRIMARY_COLOR_SOFT = "rgba(101, 88, 224, 0.16)"
INK = "#14141F"
MUTED = "#6B7084"
GRID_COLOR = "#ECEAF5"
# indigo first, then the reference site's blue / orange / green / amber accents
LEAVE_COLOR = "#2F7BE5"  # blue: a day you were away (see Dashboard > App Streak > Mark leave)
COLOR_SEQUENCE = ["#6558E0", "#2F7BE5", "#F2784B", "#2FA36B", "#F5A623", "#A99BF5", "#6B7084"]

_FONT = dict(family="Inter, sans-serif", color=INK, size=13)


def _apply_base_layout(fig: go.Figure, title: str = "") -> go.Figure:
    """Shared layout polish applied to every chart: transparent card
    background, clean gridlines, consistent typography, and a bold
    left-aligned title matching the rest of the app's visual language."""
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=INK, family="Space Grotesk, Inter, sans-serif"), x=0, xanchor="left"),
        font=_FONT,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(font=dict(size=12, color=MUTED)),
        hoverlabel=dict(bgcolor="white", font=dict(color=INK, size=12), bordercolor=GRID_COLOR),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor=GRID_COLOR, tickfont=dict(color=MUTED))
    fig.update_yaxes(showgrid=True, gridcolor=GRID_COLOR, zeroline=False, tickfont=dict(color=MUTED))
    return fig


def line_chart(df: pd.DataFrame, x: str, y: str, title: str, y_label: str = "") -> go.Figure:
    fig = px.line(df, x=x, y=y, markers=True)
    fig.update_traces(line_color=PRIMARY_COLOR, line_width=2.5, fill="tozeroy", fillcolor=PRIMARY_COLOR_SOFT)
    fig = _apply_base_layout(fig, title)
    fig.update_layout(yaxis_title=y_label, xaxis_title="", hovermode="x unified")
    return fig


def multi_line_chart(df: pd.DataFrame, x: str, y: str, color: str, title: str) -> go.Figure:
    """Used for the language trend chart -- one line per language."""
    fig = px.line(df, x=x, y=y, color=color, markers=True, color_discrete_sequence=COLOR_SEQUENCE)
    fig.update_traces(line_width=2.5)
    fig = _apply_base_layout(fig, title)
    fig.update_layout(
        yaxis_title="Problems solved", xaxis_title="", hovermode="x unified", legend_title="Language",
    )
    return fig


def bar_chart(df: pd.DataFrame, x: str, y: str, title: str, orientation: str = "v") -> go.Figure:
    if orientation == "h":
        fig = px.bar(df, x=y, y=x, orientation="h", color_discrete_sequence=[PRIMARY_COLOR])
    else:
        fig = px.bar(df, x=x, y=y, color_discrete_sequence=[PRIMARY_COLOR])
    fig.update_traces(marker_line_width=0)
    fig = _apply_base_layout(fig, title)
    fig.update_layout(xaxis_title="", yaxis_title="")
    return fig


def donut_chart(df: pd.DataFrame, names: str, values: str, title: str) -> go.Figure:
    fig = px.pie(df, names=names, values=values, hole=0.6, color_discrete_sequence=COLOR_SEQUENCE)
    fig.update_traces(
        textinfo="label+percent",
        textfont=dict(size=12, color=INK),
        marker=dict(line=dict(color="#FFFFFF", width=2)),
    )
    fig = _apply_base_layout(fig, title)
    fig.update_layout(showlegend=False)
    return fig


def _week_key(d) -> str:
    return pd.Timestamp(d).strftime("%G-W%V")


def _leave_weeks(data: pd.DataFrame, date_col: str, leave_dates) -> list:
    """Week keys of leave days that fall inside the chart's date range --
    added to the x axis so a leave day is visible even when its whole
    week has no activity rows (e.g. the task-completion heatmap)."""
    if not leave_dates or data.empty:
        return []
    lo, hi = data[date_col].min().date(), data[date_col].max().date()
    return [_week_key(d) for d in leave_dates if lo <= d <= hi]


def _leave_overlay(week_order: list, leave_dates, activity_pivot: pd.DataFrame):
    """
    A blue heatmap layer drawn over the activity heatmap: one blue cell per
    leave day that had no real activity (a day you studied anyway keeps its
    green). Transparent everywhere else. Returns None if there's nothing
    to draw.
    """
    if not leave_dates:
        return None

    z = np.full((7, len(week_order)), np.nan)
    text = np.full((7, len(week_order)), "", dtype=object)
    col_index = {w: i for i, w in enumerate(week_order)}
    drawn = False
    for d in leave_dates:
        col = col_index.get(_week_key(d))
        if col is None:
            continue
        row = pd.Timestamp(d).weekday()
        if activity_pivot.iloc[row, col] == 0:
            z[row, col] = 1
            text[row, col] = pd.Timestamp(d).strftime("%d %b %Y")
            drawn = True
    if not drawn:
        return None

    return go.Heatmap(
        z=z,
        x=week_order,
        y=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        text=text,
        zmin=0,
        zmax=1,
        colorscale=[[0, LEAVE_COLOR], [1, LEAVE_COLOR]],
        showscale=False,
        xgap=3,
        ygap=3,
        hoverongaps=False,
        hovertemplate="%{text}<br>On leave (streak safe)<extra></extra>",
    )


def study_heatmap(df: pd.DataFrame, title: str = "Study Activity") -> go.Figure:
    """
    GitHub-style calendar heatmap: weeks along x, weekday along y,
    colored by study minutes that day. Expects df with columns
    'date' (datetime64) and 'duration_minutes'.
    """
    return calendar_heatmap(
        df, date_col="date", value_col="duration_minutes", title=title,
        colorscale="Greens", hover_suffix=" min",
    )


def calendar_heatmap(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    title: str,
    colorscale: str = "Greens",
    hover_suffix: str = "",
    leave_dates=None,
) -> go.Figure:
    """
    Generic GitHub-style calendar heatmap: weeks along x, weekday
    along y, colored by value_col that day. Used for the Study
    heatmap, the Dashboard coding-streak heatmap, and the task-
    completion streak heatmap. Leave days (leave_dates, default: the
    logged-in user's) are drawn in blue.
    """
    if df.empty:
        return go.Figure()

    if leave_dates is None:
        leave_dates = load_leave_dates()

    data = df.copy()
    data["weekday"] = data[date_col].dt.weekday  # 0=Monday
    # Distinguish weeks across year boundaries by combining year + week.
    data["week_key"] = data[date_col].dt.strftime("%G-W%V")

    week_order = sorted(set(data["week_key"].unique()) | set(_leave_weeks(data, date_col, leave_dates)))
    weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    pivot = data.pivot_table(
        index="weekday", columns="week_key", values=value_col, aggfunc="sum", fill_value=0
    ).reindex(index=range(7), columns=week_order, fill_value=0)

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=weekday_labels,
            colorscale=colorscale,
            hovertemplate=f"Week %{{x}}<br>%{{y}}: %{{z:.0f}}{hover_suffix}<extra></extra>",
            showscale=True,
            xgap=3,
            ygap=3,
            colorbar=dict(thickness=12, outlinewidth=0, tickfont=dict(color=MUTED, size=11)),
        )
    )
    overlay = _leave_overlay(week_order, [d for d in leave_dates if d <= data[date_col].max().date()], pivot)
    if overlay is not None:
        fig.add_trace(overlay)
    fig = _apply_base_layout(fig, title)
    fig.update_layout(xaxis=dict(showticklabels=False, showgrid=False), yaxis=dict(showgrid=False))
    return fig


def gym_heatmap(df: pd.DataFrame, title: str = "Gym Activity") -> go.Figure:
    """GitHub-style calendar heatmap of workout minutes per day."""
    return calendar_heatmap(
        df, date_col="date", value_col="duration_minutes", title=title,
        colorscale="Greens", hover_suffix=" min",
    )


def activity_heatmap(df: pd.DataFrame, title: str = "App Activity", leave_dates=None) -> go.Figure:
    """
    The Dashboard's overall app-activity heatmap: colored by a
    combined study+coding intensity score, with a rich hover showing
    the exact date, hours studied, and problems solved that day --
    not just coding, so it reflects the whole app's streak. Expects
    df from analytics.study_analytics.combined_daily_activity
    (columns: date, hours, problems, score).
    """
    if df.empty:
        return go.Figure()

    if leave_dates is None:
        leave_dates = load_leave_dates()

    data = df.copy()
    data["weekday"] = data["date"].dt.weekday
    data["week_key"] = data["date"].dt.strftime("%G-W%V")
    data["date_label"] = data["date"].dt.strftime("%d %b %Y")

    week_order = sorted(set(data["week_key"].unique()) | set(_leave_weeks(data, "date", leave_dates)))
    weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    def _pivot(value_col, fill=0):
        return data.pivot_table(
            index="weekday", columns="week_key", values=value_col, aggfunc="first", fill_value=fill
        ).reindex(index=range(7), columns=week_order, fill_value=fill)

    pivot_score = data.pivot_table(
        index="weekday", columns="week_key", values="score", aggfunc="sum", fill_value=0
    ).reindex(index=range(7), columns=week_order, fill_value=0)
    pivot_hours = _pivot("hours")
    pivot_problems = _pivot("problems")
    pivot_dates = _pivot("date_label", fill="")

    customdata = np.dstack([pivot_dates.values, pivot_hours.values, pivot_problems.values])

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot_score.values,
            x=pivot_score.columns,
            y=weekday_labels,
            colorscale="Greens",
            customdata=customdata,
            hovertemplate=(
                "%{customdata[0]}<br>📚 %{customdata[1]:.1f}h studied"
                "<br>🧩 %{customdata[2]:.0f} problem(s)<extra></extra>"
            ),
            showscale=True,
            xgap=3,
            ygap=3,
            colorbar=dict(thickness=12, outlinewidth=0, tickfont=dict(color=MUTED, size=11)),
        )
    )
    overlay = _leave_overlay(week_order, [d for d in leave_dates if d <= data["date"].max().date()], pivot_score)
    if overlay is not None:
        fig.add_trace(overlay)
    fig = _apply_base_layout(fig, title)
    fig.update_layout(xaxis=dict(showticklabels=False, showgrid=False), yaxis=dict(showgrid=False))
    return fig
