"""
analytics/insights.py

Turns pandas/NumPy aggregations into short, natural-language
insights -- no external AI API required (see product spec section
28). Every insight is derived from real stored data; nothing here
is hardcoded or fake.

Each insight is returned as a dict: {"title", "body", "icon"} so the
UI layer can render them as cards uniformly.
"""

import pandas as pd

from analytics import coding_analytics as ca
from analytics import study_analytics as sa


def _pct_text(value: float) -> str:
    direction = "more" if value >= 0 else "less"
    return f"{abs(value):.0f}% {direction}"


def generate_study_insights(study_df: pd.DataFrame) -> list[dict]:
    insights = []

    if study_df.empty:
        return insights

    growth = sa.week_over_week_growth(study_df)
    if growth is not None:
        insights.append(
            {
                "icon": "📈",
                "title": "Weekly study trend",
                "body": f"You studied {_pct_text(growth)} this week than last week.",
            }
        )

    best, worst = sa.best_and_worst_weekday(study_df)
    if best and worst and best != worst:
        insights.append(
            {
                "icon": "🗓️",
                "title": "Productivity pattern",
                "body": (
                    f"Your study activity is highest on {best} and lowest on {worst}. "
                    f"Try shifting a bit of {best}'s momentum onto {worst}."
                ),
            }
        )

    subjects = sa.subject_breakdown(study_df)
    if len(subjects) >= 2:
        top = subjects.iloc[0]
        bottom = subjects.iloc[-1]
        if top["subject"] != bottom["subject"] and top["duration_minutes"] > 0:
            ratio = top["duration_minutes"] / max(bottom["duration_minutes"], 1)
            if ratio >= 2:
                insights.append(
                    {
                        "icon": "⚖️",
                        "title": "Subject balance",
                        "body": (
                            f"You've spent a lot more time on {top['subject']} than "
                            f"{bottom['subject']}. Consider giving {bottom['subject']} "
                            f"more attention if it's still a priority."
                        ),
                    }
                )

    current_streak, longest_streak = sa.get_streaks(study_df)
    if current_streak >= 3:
        insights.append(
            {
                "icon": "🔥",
                "title": "Streak update",
                "body": f"You're on a {current_streak}-day study streak. Keep it going!",
            }
        )
    elif longest_streak >= 3 and current_streak == 0:
        insights.append(
            {
                "icon": "💡",
                "title": "Streak update",
                "body": (
                    f"Your longest study streak so far is {longest_streak} days. "
                    f"Start a new session today to begin building it back up."
                ),
            }
        )

    return insights


def generate_coding_insights(coding_df: pd.DataFrame) -> list[dict]:
    insights = []

    if coding_df.empty:
        return insights

    growth = ca.week_over_week_growth(coding_df)
    if growth is not None:
        insights.append(
            {
                "icon": "🧩",
                "title": "Coding activity trend",
                "body": f"You solved {_pct_text(growth)} problems this week than last week.",
            }
        )

    languages = ca.language_distribution(coding_df)
    if len(languages) >= 2:
        top, second = languages.iloc[0], languages.iloc[1]
        if top["count"] >= second["count"] * 1.5:
            insights.append(
                {
                    "icon": "💻",
                    "title": "Language focus",
                    "body": (
                        f"You solved significantly more {top['language']} problems "
                        f"than {second['language']} problems recently."
                    ),
                }
            )

    topics = ca.topic_distribution(coding_df)
    if len(topics) >= 2:
        strong = topics.iloc[0]
        weak = topics.iloc[-1]
        if strong["topic"] != weak["topic"]:
            insights.append(
                {
                    "icon": "🧠",
                    "title": "Topic strengths",
                    "body": (
                        f"You've solved many {strong['topic']} problems but comparatively "
                        f"few {weak['topic']} problems. Mixing in more {weak['topic']} "
                        f"practice could round out your skills."
                    ),
                }
            )

    difficulty = ca.difficulty_distribution(coding_df)
    total = difficulty["count"].sum()
    if total > 0:
        easy_share = difficulty.loc[difficulty["difficulty"] == "Easy", "count"].sum() / total
        if easy_share >= 0.7 and total >= 5:
            insights.append(
                {
                    "icon": "⬆️",
                    "title": "Difficulty check",
                    "body": (
                        "Most of your solved problems are Easy. Try adding a few "
                        "Medium problems to keep growing."
                    ),
                }
            )

    return insights


def generate_all_insights(study_df: pd.DataFrame, coding_df: pd.DataFrame) -> list[dict]:
    """Combined list of insight cards for the AI Insights page."""
    return generate_study_insights(study_df) + generate_coding_insights(coding_df)
