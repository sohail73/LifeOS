"""
widgets/charts.py

Small, reusable Plotly chart builders. Every function returns a
plotly.graph_objects Figure -- pages call st.plotly_chart(fig, ...)
on the result. Keeping chart construction here (instead of inline
in every page) means one consistent look across Analytics, AI
Insights, and Wrapped.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

PRIMARY_COLOR = "#6C5CE7"
COLOR_SEQUENCE = px.colors.qualitative.Set2


def line_chart(df: pd.DataFrame, x: str, y: str, title: str, y_label: str = "") -> go.Figure:
    fig = px.line(df, x=x, y=y, title=title, markers=True)
    fig.update_traces(line_color=PRIMARY_COLOR, fill="tozeroy", fillcolor="rgba(108,92,231,0.15)")
    fig.update_layout(
        margin=dict(l=10, r=10, t=50, b=10),
        yaxis_title=y_label,
        xaxis_title="",
        hovermode="x unified",
    )
    return fig


def multi_line_chart(df: pd.DataFrame, x: str, y: str, color: str, title: str) -> go.Figure:
    """Used for the language trend chart -- one line per language."""
    fig = px.line(df, x=x, y=y, color=color, title=title, markers=True, color_discrete_sequence=COLOR_SEQUENCE)
    fig.update_layout(
        margin=dict(l=10, r=10, t=50, b=10),
        yaxis_title="Problems solved",
        xaxis_title="",
        hovermode="x unified",
        legend_title="Language",
    )
    return fig


def bar_chart(df: pd.DataFrame, x: str, y: str, title: str, orientation: str = "v") -> go.Figure:
    if orientation == "h":
        fig = px.bar(df, x=y, y=x, orientation="h", title=title, color_discrete_sequence=[PRIMARY_COLOR])
    else:
        fig = px.bar(df, x=x, y=y, title=title, color_discrete_sequence=[PRIMARY_COLOR])
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), xaxis_title="", yaxis_title="")
    return fig


def donut_chart(df: pd.DataFrame, names: str, values: str, title: str) -> go.Figure:
    fig = px.pie(df, names=names, values=values, title=title, hole=0.55, color_discrete_sequence=COLOR_SEQUENCE)
    fig.update_traces(textinfo="label+percent")
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    return fig


def study_heatmap(df: pd.DataFrame, title: str = "Study Activity") -> go.Figure:
    """
    GitHub-style calendar heatmap: weeks along x, weekday along y,
    colored by study minutes that day. Expects df with columns
    'date' (datetime64) and 'duration_minutes'.
    """
    return calendar_heatmap(
        df, date_col="date", value_col="duration_minutes", title=title,
        colorscale="Purples", hover_suffix=" min",
    )


def calendar_heatmap(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    title: str,
    colorscale: str = "Purples",
    hover_suffix: str = "",
) -> go.Figure:
    """
    Generic GitHub-style calendar heatmap: weeks along x, weekday
    along y, colored by value_col that day. Used for both the Study
    heatmap and the task-completion streak heatmap.
    """
    if df.empty:
        return go.Figure()

    data = df.copy()
    data["weekday"] = data[date_col].dt.weekday  # 0=Monday
    # Distinguish weeks across year boundaries by combining year + week.
    data["week_key"] = data[date_col].dt.strftime("%G-W%V")

    week_order = sorted(data["week_key"].unique())
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
        )
    )
    fig.update_layout(
        title=title,
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis_title="",
        yaxis_title="",
        xaxis=dict(showticklabels=False),
    )
    return fig
