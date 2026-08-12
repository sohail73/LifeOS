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
- **Auth:** bcrypt password hashing via passlib

No PostgreSQL/MySQL/MongoDB/Docker required -- it runs locally with
nothing to install beyond the Python packages below.

## Running it (PyCharm or terminal)

1. Open the `LifeOS/` folder as a PyCharm project (or `cd` into it in a
   terminal).
2. Create a virtual environment and install dependencies:

   ```bash
   python -m venv venv
   # Windows: venv\Scripts\activate
   # macOS/Linux: source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Run the app:

   ```bash
   streamlit run app.py
   ```

4. Your browser opens to `http://localhost:8501`. Create an account,
   and you're in -- the database and all tables are created
   automatically on first run.

**In PyCharm specifically:** set the venv you created as the project
interpreter (Settings → Project → Python Interpreter), then either use
the terminal inside PyCharm to run the `streamlit run app.py` command
above, or add it as a Run Configuration (shell script /
`streamlit` as the "module").

## Project Structure

```
LifeOS/
├── app.py                   # Entry point: DB init + login/signup
├── requirements.txt
├── README.md
│
├── config/
│   ├── database.py          # SQLite connection helper
│   └── constants.py         # Shared dropdown options, default goals
│
├── auth/
│   ├── auth_utils.py        # Password hashing, user creation/auth
│   └── session.py           # Login/logout/session-state helpers
│
├── database/
│   ├── create_tables.py     # Schema (users, subjects, study_sessions,
│   │                           coding_logs, goals, snapshots)
│   ├── queries.py           # All parameterized SQL, one place
│   └── lifeos.db            # Created automatically on first run
│
├── analytics/
│   ├── study_analytics.py   # Study time aggregations, streaks, trends
│   ├── coding_analytics.py  # Coding tracker aggregations, trends
│   ├── insights.py          # Rule-based "AI" insight generation
│   ├── snapshot.py          # Builds + saves weekly/monthly snapshots
│   └── wrapped.py           # Monthly/Yearly Wrapped calculations
│
├── widgets/
│   └── charts.py            # Reusable Plotly chart builders
│
├── utils/
│   └── helper.py            # Duration formatting, streak calculation
│
└── pages/                   # Each file = one sidebar page (Streamlit
    ├── 1_Dashboard.py          multipage convention)
    ├── 2_Study.py
    ├── 3_Coding_Tracker.py
    ├── 4_Analytics.py
    ├── 5_AI_Insights.py
    ├── 6_Snapshots.py
    ├── 7_Wrapped.py
    └── 8_Settings.py
```

## What's implemented (v0.1)

- **Auth:** signup, secure (bcrypt) login, logout, session state --
  nothing resets between logins.
- **Study module:** subjects, a start/pause/resume/stop focus timer
  that auto-saves sessions, and manual entry as a fallback.
- **Coding tracker:** manual logging (platform, language, difficulty,
  topic, time taken) -- ready for automatic sync later if a reliable
  API becomes available; manual entry stays as the permanent fallback.
- **Analytics:** daily/weekly/monthly trends, subject & language &
  topic & difficulty distributions, weekday patterns, and a
  GitHub-style study heatmap -- all computed from real data with
  Pandas/NumPy/Plotly.
- **AI Insights:** natural-language observations (growth, streaks,
  strengths/weaknesses, productivity patterns) generated from
  statistics, no external AI API required.
- **Snapshots:** on-demand weekly/monthly snapshots, viewable
  historically, and a side-by-side comparison view.
- **Wrapped:** Monthly and Yearly Wrapped summaries in the
  Spotify-Wrapped style.

## What's intentionally not built yet

- Other modules (Finance, Health, Job Prep, Habits, Mood, Reading,
  Custom modules) and the fully dynamic module/widget system --
  the current architecture (separate `analytics/`, `database/queries.py`,
  constants-driven config) is built so these can be added without
  restructuring what exists.
- GitHub integration, automatic LeetCode sync, and ML-based
  forecasting/recommendations.
- Widget reordering/hide-show dashboard customization.
