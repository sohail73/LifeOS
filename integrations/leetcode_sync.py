"""
integrations/leetcode_sync.py

Optional "pull" sync against LeetCode's PUBLIC, UNOFFICIAL GraphQL
endpoint (the same one leetcode.com's own frontend uses to render a
public profile page). Important limits to be upfront about:

- There is no official LeetCode API and no push/webhook mechanism,
  so this can't be truly real-time. It's triggered manually (the
  "Sync Now" button on the Coding Tracker page) and pulls whatever
  is in your recent accepted-submissions history at that moment.
- Only works if the LeetCode profile is set to PUBLIC.
- The endpoint is undocumented and could change or start blocking
  requests without warning. If it breaks, manual entry (already
  built, and always available) is the fallback -- see product spec
  section 15/23 on hybrid manual+automatic data collection.
- This module was written without internet access in its dev
  environment, so it could NOT be tested against the real
  leetcode.com. Test it against your own username after installing
  `requests` and report back if the response shape needs adjusting.

Nothing here writes to the database directly -- preview_new_submissions
returns a list for the UI to show the user, who confirms/edits language
before database.queries.add_coding_log actually saves anything.
"""

from datetime import date, datetime

import requests

_GRAPHQL_URL = "https://leetcode.com/graphql"
_HEADERS = {
    "Content-Type": "application/json",
    "Referer": "https://leetcode.com",
    "User-Agent": "Mozilla/5.0 (LifeOS personal study tracker)",
}
_TIMEOUT_SECONDS = 10

_RECENT_SUBMISSIONS_QUERY = """
query recentAcSubmissions($username: String!, $limit: Int!) {
  recentAcSubmissionList(username: $username, limit: $limit) {
    title
    titleSlug
    timestamp
  }
}
"""

_QUESTION_META_QUERY = """
query questionMeta($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    difficulty
    topicTags {
      name
    }
  }
}
"""


class LeetCodeSyncError(Exception):
    """Raised when the sync couldn't complete (network issue, bad username, private profile, etc.)."""


def _graphql(query: str, variables: dict) -> dict:
    try:
        response = requests.post(
            _GRAPHQL_URL,
            json={"query": query, "variables": variables},
            headers=_HEADERS,
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise LeetCodeSyncError(f"Couldn't reach LeetCode: {exc}") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise LeetCodeSyncError("LeetCode returned an unexpected response.") from exc

    if payload.get("errors"):
        raise LeetCodeSyncError(
            "LeetCode rejected the request -- double check the username is correct "
            "and the profile's submission history is public."
        )
    return payload.get("data") or {}


def fetch_recent_accepted(username: str, limit: int = 20) -> list[dict]:
    """
    Recent accepted submissions for a public LeetCode profile.
    Returns a list of {title, titleSlug, date_solved} dicts, most
    recent first. Raises LeetCodeSyncError on failure.
    """
    if not username.strip():
        raise LeetCodeSyncError("No LeetCode username set.")

    data = _graphql(_RECENT_SUBMISSIONS_QUERY, {"username": username.strip(), "limit": limit})
    submissions = data.get("recentAcSubmissionList") or []

    results = []
    for sub in submissions:
        try:
            solved_date = datetime.fromtimestamp(int(sub["timestamp"])).date().isoformat()
        except (KeyError, ValueError, TypeError):
            solved_date = date.today().isoformat()
        results.append(
            {
                "title": sub.get("title", "Untitled"),
                "titleSlug": sub.get("titleSlug", ""),
                "date_solved": solved_date,
            }
        )
    return results


def fetch_question_meta(title_slug: str) -> dict:
    """Difficulty + topic tags for one problem. Returns {'difficulty': str, 'topics': [str, ...]}."""
    data = _graphql(_QUESTION_META_QUERY, {"titleSlug": title_slug})
    question = data.get("question") or {}
    topics = [t["name"] for t in (question.get("topicTags") or [])]
    return {
        "difficulty": (question.get("difficulty") or "Medium").title(),
        "topics": topics or ["Other"],
    }


def preview_new_submissions(username: str, already_synced_ids: set, limit: int = 20) -> list[dict]:
    """
    Fetch recent accepted submissions and filter out ones already
    logged (matched by titleSlug, i.e. coding_logs.external_id). For
    each genuinely new one, also fetch its difficulty/topic. Returns
    a list ready for the UI to show the user for confirmation --
    nothing is written to the database by this function.
    """
    recent = fetch_recent_accepted(username, limit=limit)

    # A problem can appear more than once in the recent-submissions
    # list (re-submitted, or LeetCode logging multiple accepted runs).
    # Keep only the first (most recent) occurrence of each titleSlug so
    # the UI never has to render two rows for the same problem.
    seen_slugs = set()
    deduped = []
    for s in recent:
        if s["titleSlug"] and s["titleSlug"] not in seen_slugs:
            seen_slugs.add(s["titleSlug"])
            deduped.append(s)

    new_submissions = [s for s in deduped if s["titleSlug"] not in already_synced_ids]

    enriched = []
    for sub in new_submissions:
        try:
            meta = fetch_question_meta(sub["titleSlug"])
        except LeetCodeSyncError:
            # Difficulty/topic lookup failing shouldn't block the whole
            # sync -- fall back to sensible defaults the user can edit.
            meta = {"difficulty": "Medium", "topics": ["Other"]}
        enriched.append(
            {
                **sub,
                "difficulty": meta["difficulty"],
                "topic": meta["topics"][0] if meta["topics"] else "Other",
            }
        )
    return enriched
