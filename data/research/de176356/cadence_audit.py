"""DE-3: measure scheduled-refresh cadence from the saved GitHub run history.

Input: pages-runs.json (gh run list --workflow pages.yml, saved verbatim).
Cron in .github/workflows/pages.yml: '17 */4 * * *' (slots 00:17, 04:17, 08:17, 12:17, 16:17, 20:17 UTC).
A slot counts as "run" when a scheduled run started within +/-2 hours of it.
Output: cadence-audit.json.
"""
import datetime as dt
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
runs = sorted(json.loads((HERE / "pages-runs.json").read_text()), key=lambda r: r["createdAt"])


def ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


sched = [r for r in runs if r["event"] == "schedule"]
first_sched = ts(sched[0]["createdAt"])
last_sched = ts(sched[-1]["createdAt"])
observed_until = ts(runs[-1]["createdAt"])
now = dt.datetime.now(dt.timezone.utc)

gaps = []
for a, b in zip(sched, sched[1:]):
    gaps.append({"from": a["createdAt"], "to": b["createdAt"],
                 "hours": round((ts(b["createdAt"]) - ts(a["createdAt"])).total_seconds() / 3600, 2)})

slots = []
t = dt.datetime(first_sched.year, first_sched.month, first_sched.day, 0, 17, tzinfo=dt.timezone.utc)
while t <= now:
    if t >= first_sched - dt.timedelta(hours=4):
        hit = [r for r in sched if abs((ts(r["createdAt"]) - t).total_seconds()) <= 2 * 3600]
        slots.append({"slot_utc": t.strftime("%Y-%m-%dT%H:%MZ"),
                      "scheduled_run_within_2h": bool(hit),
                      "run_id": hit[0]["databaseId"] if hit else None})
    t += dt.timedelta(hours=4)

out = {
    "workflow": "Refresh and deploy CS2 dashboard (.github/workflows/pages.yml)",
    "cron": "17 */4 * * *",
    "cron_reference": "https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows",
    "github_docs_quote": ("The schedule event can be delayed during periods of high loads of GitHub Actions "
                          "workflow runs. High load times include the start of every hour. If the load is "
                          "sufficiently high enough, some queued jobs may be dropped."),
    "github_docs_quote_2": ("In a public repository, scheduled workflows are automatically disabled when no "
                            "repository activity has occurred in 60 days."),
    "run_history_source": "https://github.com/buffedlizard55-lab/MaltaProj3/actions/workflows/pages.yml",
    "run_history_saved": "data/research/de176356/pages-runs.json",
    "observation_window": {"first_scheduled_run": first_sched.isoformat(), "last_scheduled_run": last_sched.isoformat(),
                           "run_history_latest_run_created": observed_until.isoformat(),
                           "audit_clock_utc": now.isoformat()},
    "total_runs_listed": len(runs),
    "scheduled_runs": [{"created": r["createdAt"], "conclusion": r["conclusion"], "run_id": r["databaseId"],
                        "url": r["url"]} for r in sched],
    "gaps_between_scheduled_runs": gaps,
    "max_gap_hours_completed": max(g["hours"] for g in gaps) if gaps else None,
    "hours_since_last_scheduled_run_at_audit": round((now - last_sched).total_seconds() / 3600, 2),
    "four_hour_slots_checked": slots,
    "slots_with_scheduled_run": sum(s["scheduled_run_within_2h"] for s in slots),
    "slots_checked": len(slots),
    "non_success_runs": [{"created": r["createdAt"], "event": r["event"], "conclusion": r["conclusion"],
                          "title": r["displayTitle"], "run_id": r["databaseId"], "url": r["url"]}
                         for r in runs if r["conclusion"] not in ("success",)],
    "user_requirement": "refresh every 4-8 hours",
}
(HERE / "cadence-audit.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps({k: out[k] for k in ["slots_with_scheduled_run", "slots_checked", "max_gap_hours_completed",
                                      "hours_since_last_scheduled_run_at_audit"]}, indent=2))
print(json.dumps(out["four_hour_slots_checked"], indent=1))
