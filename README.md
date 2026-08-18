# LifeOS

**Track. Analyze. Improve.**

LifeOS is a personal analytics app: log your study sessions and coding
practice, and it turns that data into dashboards, trends, AI-style
insights, historical snapshots, and Spotify-Wrapped-style summaries.

This is **v0.1** -- the Study module (study timer, manual entry, coding
tracker, analytics, insights, snapshots, wrapped) is fully implemented.
Other life areas (Finance, Health, Habits, ...) are intentionally not
built yet; the architecture is designed to add them later without a
rewrite.

## Tech Stack

- **UI:** Streamlit
- **Database:** SQLite (`database/lifeos.db`, created automatically)
- **Analysis:** Pandas, NumPy
- **Charts:** Plotly
- **Auth:** bcrypt password hashing (direct, not via passlib)
- **LeetCode sync:** `requests` (unofficial public GraphQL endpoint)

No PostgreSQL/MySQL/MongoDB/Docker required -- it runs locally with
nothing to install beyond the Python packages below.



## What's implemented (v0.1)

- **Auth:** signup, secure (bcrypt) login, logout, session state --
  nothing resets between logins. Settings includes a password change
  and a password-protected full data reset (wipes activity, keeps the
  account, re-seeds defaults).
- **Study module:** subjects (add/remove, with a warning if sessions are
  attached), a start/pause/resume/stop focus timer with a live-ticking
  on-screen clock, manual entry as a fallback, and a **Future Topics**
  wishlist for things to study eventually (not tied to any date/goal yet).
- **Coding tracker:** manual logging with a user-managed language list
  (add any language, e.g. Pandas), plus an optional **LeetCode Sync**
  tab that pulls recent accepted submissions from a public LeetCode
  profile (unofficial API -- see integrations/leetcode_sync.py for
  caveats), stages them for review, and lets you confirm before saving.
  Manual entry always remains the fallback.
- **Goals & Tasks:** a daily to-do list, optionally linked to a
  long-term goal ("crack the job in 60 days"). Creating a goal lists
  subjects/topics in a plain textarea, one per line -- "Arrays: 5" for
  5 consecutive days, or just "Arrays" to cycle across the Duration
  field. Optional patterns if you need them, same simple syntax:
  ": alternate", ": every 3", ": Sunday", or ": dates 2026-08-20,
  2026-08-27" -- see analytics/goal_maintenance.py's parse_topic_line.
  Every goal is a manageable card (full controls on Goals & Tasks; a
  read-only progress view on the Dashboard) -- expand it to check off
  any topic (asks how long you studied and logs a real study session,
  or just mark it done with no subject if it doesn't need one),
  reschedule a task, add more topics, extend the deadline, or edit
  the description. If a task's date passes without being marked done,
  the whole remaining schedule for that goal auto-shifts forward (and
  the deadline moves out) the next time you open the app. A future
  task can also be pulled forward to "do today", closing the gap by
  shifting everything after it back a day and finishing the goal
  sooner. A toast notifies you when a goal starts today. Deleting a
  goal removes its tasks too (already-logged study time stays intact
  either way). Plus a streak + GitHub-style completion heatmap.
- **Projects:** track what you're **Ready** for, working **In
  Progress** on (optionally linked to one or more long-term goals
  tracking it -- once every linked goal hits 100%, the project
  auto-promotes to Ready), or **Planned** for the future (optionally
  linked to Future Topics wishlist items) -- description, tech stack,
  target date, notes, all optional. Plus a simple **Skills I Know**
  tab -- a flat list of what you can already do.
- **Analytics:** daily/weekly/monthly trends (in hours), subject &
  language & topic & difficulty distributions, weekday patterns, and
  GitHub-style heatmaps -- all computed from real data with
  Pandas/NumPy/Plotly.
- **AI Insights:** natural-language observations (growth, streaks,
  strengths/weaknesses, productivity patterns) generated from
  statistics, no external AI API required.
- **Snapshots:** weekly/monthly/yearly snapshots that refresh
  automatically once a day you have the app open (there's no
  background scheduler in Streamlit -- see analytics/snapshot.py),
  viewable historically, with a side-by-side comparison view.
- **Wrapped:** Monthly and Yearly Wrapped summaries in the
  Spotify-Wrapped style, plus a **Your Journey** timeline -- every
  active month, click to open and see what you studied, how much,
  your streak, strongest/weakest topic, and that month's goal
  completion.
- **Dashboard:** today's tasks front and center (with the same
  checkbox-to-complete flow), an all-time Overall Performance
  overview, an automatic weekly recap (built from snapshots),
  today/week/month numbers, recent activity, an overall **App
  Streak** (study OR coding activity, whichever happened, with a
  combined heatmap showing hours studied + problems solved + the
  date on hover), upcoming goal deadlines, every active goal as a
  read-only progress card (full management stays on the Goals & Tasks
  page), and a date picker to look up any day's activity.
- **Profile:** optional avatar (shown in the sidebar and Settings). A
  new real, correctly-attributed motivational quote appears next to
  Today's Tasks on the Dashboard each day (config/constants.py's
  DAILY_MOTIVATION, picked deterministically by date) -- or set your
  own fixed one in Settings.
- **Design:** a consistent light, purple-accent theme with KPI cards,
  status/difficulty badges, and matching chart styling throughout.

## What's intentionally not built yet

- Other modules (Finance, Health, Job Prep, Habits, Mood, Reading,
  Custom modules) and the fully dynamic module/widget system --
  the current architecture (separate `analytics/`, `database/queries.py`,
  constants-driven config) is built so these can be added without
  restructuring what exists.
- GitHub integration and ML-based forecasting/recommendations.
- Widget reordering/hide-show dashboard customization.
- Real-time push sync for LeetCode (no webhook exists -- Sync Now is
  a manual pull, not automatic).
