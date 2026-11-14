"""
analytics/goal_maintenance.py

Two ways a long-term goal's schedule can move, plus a "did this goal
just start?" check:

1. auto_shift_overdue_tasks -- if a task's date passed without being
   marked done, the day changing means it was missed. The WHOLE
   remaining schedule for that goal (every still-incomplete task)
   slides forward by the same number of days, and the goal's end date
   moves out to match -- falling behind doesn't break the plan, it
   extends it. Already-completed tasks never move. Runs at most once
   per day per session (see auth.session.require_login).

2. pull_task_forward -- the opposite case: there's time today, so a
   future task gets pulled in to be done today instead. Every other
   incomplete task scheduled on/after that task's original date
   shifts BACK by one day to close the gap it left, and the goal's
   end date moves in by one day -- finishing sooner.

3. get_goals_starting_today -- goals whose start_date is today, used
   to show a "this starts today!" notice once per day.
"""

from datetime import date, timedelta

from database.queries import (
    extend_goal_end_date,
    get_long_term_goals,
    get_tasks_for_goal,
    reschedule_task,
)


def auto_shift_overdue_tasks(user_id: int) -> list[dict]:
    """
    Returns a list of {"goal_title", "shift_days", "new_end_date"}
    for every goal whose schedule was pushed forward because a task
    was left undone past its date. Mutates the database directly.
    """
    today = date.today()
    shifted = []

    for goal in get_long_term_goals(user_id):
        tasks = get_tasks_for_goal(user_id, goal["id"])
        incomplete = [t for t in tasks if not t["is_done"]]
        if not incomplete:
            continue

        incomplete.sort(key=lambda t: t["task_date"])
        earliest_date = date.fromisoformat(incomplete[0]["task_date"])
        if earliest_date >= today:
            continue  # nothing overdue for this goal yet

        shift_days = (today - earliest_date).days
        for task in incomplete:
            new_date = date.fromisoformat(task["task_date"]) + timedelta(days=shift_days)
            reschedule_task(user_id, task["id"], new_date.isoformat())

        new_end = date.fromisoformat(goal["end_date"]) + timedelta(days=shift_days)
        extend_goal_end_date(user_id, goal["id"], new_end.isoformat())

        shifted.append(
            {"goal_title": goal["title"], "shift_days": shift_days, "new_end_date": new_end.isoformat()}
        )

    return shifted


def pull_task_forward(user_id: int, goal_id: int, task_id: int) -> dict:
    """
    Moves one future (not-yet-due, not-done) task to today, and
    shifts every OTHER incomplete task scheduled on/after that task's
    original date back by one day to close the gap it left --
    shortening the goal's remaining schedule by a day. Returns
    {"shifted": bool, "new_end_date": str | None}.
    """
    today = date.today()
    tasks = get_tasks_for_goal(user_id, goal_id)
    target = next((t for t in tasks if t["id"] == task_id), None)
    if target is None:
        return {"shifted": False, "new_end_date": None}

    original_date = date.fromisoformat(target["task_date"])
    if original_date <= today or target["is_done"]:
        return {"shifted": False, "new_end_date": None}

    reschedule_task(user_id, task_id, today.isoformat())

    for t in tasks:
        if t["id"] == task_id or t["is_done"]:
            continue
        t_date = date.fromisoformat(t["task_date"])
        if t_date >= original_date:
            reschedule_task(user_id, t["id"], (t_date - timedelta(days=1)).isoformat())

    goal = next((g for g in get_long_term_goals(user_id) if g["id"] == goal_id), None)
    new_end_str = None
    if goal is not None:
        new_end = date.fromisoformat(goal["end_date"]) - timedelta(days=1)
        # Never shorten past today -- a goal can't end before it currently is.
        if new_end >= today:
            extend_goal_end_date(user_id, goal_id, new_end.isoformat())
            new_end_str = new_end.isoformat()

    return {"shifted": True, "new_end_date": new_end_str}


def get_goals_starting_today(user_id: int) -> list[dict]:
    """Goals whose start_date is today -- for a one-time 'this starts today!' notice."""
    today_str = date.today().isoformat()
    return [g for g in get_long_term_goals(user_id) if g["start_date"] == today_str]


WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def generate_topic_tasks(goal_start: date, duration_days: int, topics: list[dict]) -> list[tuple[str, str]]:
    """
    Lays out (date_iso, topic_name) task entries for a goal from a
    structured topic list, so a topic doesn't have to be daily just
    because it's in the plan. Each topic dict has "name" and
    "schedule", one of:
      - "block": consumes `block_days` CONSECUTIVE days from a shared
        cursor (e.g. "Arrays" for 5 straight days), claimed before
        anything else.
      - "daily": cycles evenly through whatever days are left after
        block topics have claimed their run, across the goal's full
        duration.
      - "weekday": gets a task on every occurrence of `weekdays`
        (a list of Mon=0..Sun=6) within the goal's date range --
        e.g. "only on Sundays". Computed independently of the cursor,
        so it can land on the same day as a block/cycling task.
      - "interval": gets a task every `interval_n` days starting from
        goal_start (e.g. alternate days = interval_n=2) -- also
        computed independently over the full range.
      - "dates": gets a task on exactly the given `dates` (a list of
        ISO date strings) -- for "only on these specific days".
    """
    goal_end = goal_start + timedelta(days=duration_days - 1)
    tasks: list[tuple[str, str]] = []

    block_topics = [t for t in topics if t["schedule"] == "block"]
    cycle_topics = [t for t in topics if t["schedule"] == "daily"]
    pattern_topics = [t for t in topics if t["schedule"] in ("weekday", "interval")]
    dated_topics = [t for t in topics if t["schedule"] == "dates"]

    cursor = goal_start
    for t in block_topics:
        for _ in range(t["block_days"]):
            if cursor > goal_end:
                break
            tasks.append((cursor.isoformat(), t["name"]))
            cursor += timedelta(days=1)

    if cycle_topics:
        day, offset = cursor, 0
        while day <= goal_end:
            topic = cycle_topics[offset % len(cycle_topics)]
            tasks.append((day.isoformat(), topic["name"]))
            offset += 1
            day += timedelta(days=1)

    for t in pattern_topics:
        day = goal_start
        if t["schedule"] == "weekday":
            while day <= goal_end:
                if day.weekday() in t["weekdays"]:
                    tasks.append((day.isoformat(), t["name"]))
                day += timedelta(days=1)
        else:  # interval
            n = max(t.get("interval_n", 1), 1)
            offset = 0
            while day <= goal_end:
                if offset % n == 0:
                    tasks.append((day.isoformat(), t["name"]))
                day += timedelta(days=1)
                offset += 1

    for t in dated_topics:
        for d_iso in t["dates"]:
            tasks.append((d_iso, t["name"]))

    return tasks


_WEEKDAY_LOOKUP = {name.lower(): i for i, name in enumerate(WEEKDAY_NAMES)}
_WEEKDAY_ABBREV_LOOKUP = {name.lower()[:3]: i for i, name in enumerate(WEEKDAY_NAMES)}


def parse_topic_line(line: str) -> dict | None:
    """
    Parses ONE line of the goal-creation topics textarea. A topic can
    be just a name (cycles daily across the goal's Duration), or a
    name with an optional ": <rule>" suffix:
      "Arrays: 5"                          -> 5 consecutive days
      "Light Revision: alternate"          -> every other day
      "Light Revision: every 3"            -> every 3rd day
      "System Design: Sunday"              -> that weekday only
      "Mock Interview: dates 2026-08-20, 2026-08-27" -> exact dates
    Anything after the colon that doesn't match a known rule is
    treated as part of a plain (daily-cycling) topic name instead of
    silently dropped, so a typo never loses the topic entirely.
    """
    line = line.strip()
    if not line:
        return None
    if ":" not in line:
        return {"name": line, "schedule": "daily"}

    name_part, rule_part = line.split(":", 1)
    name = name_part.strip()
    rule = rule_part.strip()
    rule_lower = rule.lower()

    if rule.isdigit() and int(rule) > 0:
        return {"name": name, "schedule": "block", "block_days": int(rule)}

    if rule_lower in ("alternate", "alternate day", "alternate days", "every other day"):
        return {"name": name, "schedule": "interval", "interval_n": 2}

    if rule_lower.startswith("every "):
        n_part = rule_lower.replace("every", "", 1).strip()
        if n_part.isdigit() and int(n_part) > 0:
            return {"name": name, "schedule": "interval", "interval_n": int(n_part)}

    if rule_lower in _WEEKDAY_LOOKUP:
        return {"name": name, "schedule": "weekday", "weekdays": [_WEEKDAY_LOOKUP[rule_lower]]}
    if rule_lower in _WEEKDAY_ABBREV_LOOKUP:
        return {"name": name, "schedule": "weekday", "weekdays": [_WEEKDAY_ABBREV_LOOKUP[rule_lower]]}

    if rule_lower.startswith("dates"):
        date_text = rule[len("dates"):].strip(" :")
        parsed_dates = []
        for part in date_text.split(","):
            part = part.strip()
            try:
                parsed_dates.append(date.fromisoformat(part).isoformat())
            except ValueError:
                continue
        if parsed_dates:
            return {"name": name, "schedule": "dates", "dates": parsed_dates}

    # Unrecognized rule text -- don't lose the topic, just treat the
    # whole original line as a plain daily-cycling topic name.
    return {"name": line, "schedule": "daily"}


def auto_promote_ready_projects(user_id: int) -> list[str]:
    """
    Any "In Progress" project that has one or more linked goals, all
    of which are now 100% complete, gets automatically promoted to
    "Ready" -- you finished what you set out to do for it. Returns
    the titles of any project promoted this call.
    """
    from analytics.tasks_analytics import goal_progress
    from database.queries import get_linked_goals_for_project, get_projects, get_tasks_df, update_project

    promoted = []
    for project in get_projects(user_id):
        if project["status"] != "In Progress":
            continue

        linked_goals = get_linked_goals_for_project(user_id, project["id"])
        if not linked_goals:
            continue

        all_complete = True
        for goal in linked_goals:
            tasks_df = get_tasks_df(user_id, goal_id=goal["id"])
            progress = goal_progress(goal, tasks_df)
            if progress["total_tasks"] == 0 or progress["completion_pct"] < 100:
                all_complete = False
                break

        if all_complete:
            update_project(
                user_id,
                project["id"],
                title=project["title"],
                description=project["description"] or "",
                status="Ready",
                tech_stack=project["tech_stack"] or "",
                target_date=project["target_date"],
                notes=project["notes"] or "",
                linked_goal_id=project.get("linked_goal_id"),
            )
            promoted.append(project["title"])

    return promoted


def auto_promote_ready_jobs(user_id: int) -> list[str]:
    """
    Same idea as auto_promote_ready_projects, but for job targets:
    any "In Progress" job target whose linked goal(s) are all now
    100% complete gets automatically promoted to "Ready". Returns the
    titles of any job target promoted this call.
    """
    from analytics.tasks_analytics import goal_progress
    from database.queries import get_job_targets, get_linked_goals_for_job_target, get_tasks_df, update_job_target

    promoted = []
    for job in get_job_targets(user_id):
        if job["status"] != "In Progress":
            continue

        linked_goals = get_linked_goals_for_job_target(user_id, job["id"])
        if not linked_goals:
            continue

        all_complete = True
        for goal in linked_goals:
            tasks_df = get_tasks_df(user_id, goal_id=goal["id"])
            progress = goal_progress(goal, tasks_df)
            if progress["total_tasks"] == 0 or progress["completion_pct"] < 100:
                all_complete = False
                break

        if all_complete:
            update_job_target(
                user_id,
                job["id"],
                title=job["title"],
                company=job["company"] or "",
                status="Ready",
                notes=job["notes"] or "",
                deadline=job.get("deadline"),
                target_package=job.get("target_package") or "",
            )
            promoted.append(job["title"])

    return promoted


def auto_promote_ready_roadmap_steps(user_id: int) -> list[str]:
    """
    Same idea again, for roadmap (learning-path) steps: any "In
    Progress" step whose linked goal(s) are all now 100% complete
    gets automatically promoted to "Ready". Returns the titles of any
    step promoted this call.
    """
    from analytics.tasks_analytics import goal_progress
    from database.queries import (
        get_linked_goals_for_roadmap_step,
        get_roadmap_steps,
        get_tasks_df,
        update_roadmap_step,
    )

    promoted = []
    for step in get_roadmap_steps(user_id):
        if step["status"] != "In Progress":
            continue

        linked_goals = get_linked_goals_for_roadmap_step(user_id, step["id"])
        if not linked_goals:
            continue

        all_complete = True
        for goal in linked_goals:
            tasks_df = get_tasks_df(user_id, goal_id=goal["id"])
            progress = goal_progress(goal, tasks_df)
            if progress["total_tasks"] == 0 or progress["completion_pct"] < 100:
                all_complete = False
                break

        if all_complete:
            update_roadmap_step(user_id, step["id"], title=step["title"], status="Ready", notes=step["notes"] or "")
            promoted.append(step["title"])

    return promoted


def auto_advance_roadmap_lanes(user_id: int) -> list[str]:
    """
    Parallel tracks + parallel steps. Each lane (track) moves forward on
    its own; inside a lane, steps sharing a step number are one "stage"
    that runs in parallel (e.g. FastAPI and Cloud both numbered 4).

    When every step of a stage is Ready and the next stage still has
    Future steps, those Future steps all become In Progress together --
    i.e. the next stage only starts once the whole previous stage (all
    its parallel steps) is done. A lane that's still running something
    (any In Progress step) is left alone, and a lane that was never
    started (nothing Ready yet) is left alone too. Other lanes aren't
    touched. Returns the titles of steps started this call.
    """
    from database.queries import get_roadmap_steps, update_roadmap_step

    started = []
    lanes: dict[int, dict[int, list[dict]]] = {}
    for step in get_roadmap_steps(user_id):
        lanes.setdefault(step["lane"], {}).setdefault(step["order_index"], []).append(step)

    for stages_by_number in lanes.values():
        stages = [stages_by_number[n] for n in sorted(stages_by_number)]
        if any(s["status"] == "In Progress" for stage in stages for s in stage):
            continue  # this track is already running something
        for prev_stage, next_stage in zip(stages, stages[1:]):
            future_steps = [s for s in next_stage if s["status"] == "Future"]
            if all(s["status"] == "Ready" for s in prev_stage) and future_steps:
                for nxt in future_steps:
                    update_roadmap_step(
                        user_id, nxt["id"], title=nxt["title"], status="In Progress", notes=nxt["notes"] or ""
                    )
                    started.append(nxt["title"])
                break
    return started


def roadmap_step_progress_pct(user_id: int, step: dict) -> float | None:
    """
    Completion % of a roadmap step, from the tasks of the goal(s) linked
    to it (completed tasks / total tasks across all of them). A Ready step
    is always 100. Returns None when nothing is linked / no tasks exist yet,
    so the flowchart can show "no goal linked" instead of a fake 0%.
    """
    from analytics.tasks_analytics import goal_progress
    from database.queries import get_linked_goals_for_roadmap_step, get_tasks_df

    if step["status"] == "Ready":
        return 100.0
    total = done = 0
    for goal in get_linked_goals_for_roadmap_step(user_id, step["id"]):
        progress = goal_progress(goal, get_tasks_df(user_id, goal_id=goal["id"]))
        total += progress["total_tasks"]
        done += progress["completed_tasks"]
    return round(done / total * 100, 1) if total else None


def job_target_progress_pct(user_id: int, job: dict) -> float | None:
    """
    Completion % of a job target, from the tasks of the goal(s) linked to it
    (completed tasks / all tasks across them). Ready and Achieved jobs are
    always 100. Returns None when nothing measurable is linked, so the board
    can say "No goal linked" instead of showing a fake 0%.
    """
    from analytics.tasks_analytics import goal_progress
    from database.queries import get_linked_goals_for_job_target, get_tasks_df

    if job["status"] in ("Ready", "Achieved"):
        return 100.0
    total = done = 0
    for goal in get_linked_goals_for_job_target(user_id, job["id"]):
        progress = goal_progress(goal, get_tasks_df(user_id, goal_id=goal["id"]))
        total += progress["total_tasks"]
        done += progress["completed_tasks"]
    return round(done / total * 100, 1) if total else None


def job_role_readiness(user_id: int, role: dict) -> dict:
    """
    How ready you are for a job role, worked out from the roadmap steps attached to it:

    * "Ready"       -- every attached step is Ready (this happens by itself as the
                       steps' goals complete -- nothing to tick on the role).
    * "In Progress" -- at least one attached step is Ready or In Progress.
    * "Future"      -- steps are attached but none has been started.
    * "No steps"    -- nothing attached yet.

    pct is the average completion of the attached steps (a Ready step counts as 100,
    other steps use their linked goals' progress, or 0 if they have none).
    Returns {"status", "pct", "ready_count", "total", "steps": [step dicts + progress_pct]}.
    """
    from database.queries import get_job_role_steps

    steps = []
    for step in get_job_role_steps(user_id, role["id"]):
        pct = roadmap_step_progress_pct(user_id, step)
        steps.append(dict(step, progress_pct=pct))

    total = len(steps)
    ready_count = sum(1 for s in steps if s["status"] == "Ready")
    if total == 0:
        status = "No steps"
    elif ready_count == total:
        status = "Ready"
    elif any(s["status"] in ("Ready", "In Progress") for s in steps):
        status = "In Progress"
    else:
        status = "Future"
    pct = round(sum((s["progress_pct"] or 0.0) for s in steps) / total, 1) if total else 0.0
    return {"status": status, "pct": pct, "ready_count": ready_count, "total": total, "steps": steps}

