#!/usr/bin/env python3
"""
RAWCRUIT Analysis Script — Team Lazy4
Generates detailed statistics about the ranking and candidate pool.
Run after rank.py to get insights.
"""

import json
import csv
from datetime import date
from pathlib import Path
import sys

def analyze(candidates_path: str, submission_path: str):
    print("=" * 60)
    print("  RAWCRUIT Analysis — Team Lazy4")
    print("=" * 60)

    # Load submission
    top100 = {}
    with open(submission_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            top100[row["candidate_id"]] = {
                "rank": int(row["rank"]),
                "score": float(row["score"]),
                "reasoning": row["reasoning"]
            }

    # Load candidates
    top100_cands = {}
    all_titles = {}
    total = 0
    with open(candidates_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            cand = json.loads(line)
            cid = cand["candidate_id"]
            title = cand.get("profile", {}).get("current_title", "Unknown")
            all_titles[title] = all_titles.get(title, 0) + 1
            total += 1
            if cid in top100:
                top100_cands[cid] = cand

    print(f"\n📊 Pool: {total:,} candidates")
    print(f"📋 Top 100 analyzed\n")

    print("─── TOP 10 RANKED CANDIDATES ───")
    for cid, meta in sorted(top100.items(), key=lambda x: x[1]["rank"])[:10]:
        cand = top100_cands.get(cid, {})
        p = cand.get("profile", {})
        print(f"  #{meta['rank']:2d} {cid} | {p.get('current_title','?'):35s} | {p.get('years_of_experience',0):.1f}y | score={meta['score']:.4f}")

    print("\n─── TITLE DISTRIBUTION IN TOP 100 ───")
    title_dist = {}
    for cid, cand in top100_cands.items():
        t = cand.get("profile", {}).get("current_title", "Unknown")
        title_dist[t] = title_dist.get(t, 0) + 1
    for t, n in sorted(title_dist.items(), key=lambda x: -x[1])[:10]:
        print(f"  {n:3d}x  {t}")

    print("\n─── BEHAVIORAL SIGNAL STATS (TOP 100) ───")
    active_week = active_month = open_work = 0
    rr_sum = 0
    for cid, cand in top100_cands.items():
        sig = cand.get("redrob_signals", {})
        last = sig.get("last_active_date", "2000-01-01")
        try:
            days = (date.today() - date.fromisoformat(last)).days
        except:
            days = 9999
        if days <= 7: active_week += 1
        if days <= 30: active_month += 1
        if sig.get("open_to_work_flag"): open_work += 1
        rr_sum += sig.get("recruiter_response_rate", 0)

    print(f"  Active last 7 days:  {active_week}")
    print(f"  Active last 30 days: {active_month}")
    print(f"  Open to work:        {open_work}")
    print(f"  Avg response rate:   {rr_sum/max(len(top100_cands),1):.2f}")

    print("\n─── EXPERIENCE DISTRIBUTION (TOP 100) ───")
    exp_buckets = {"0-3": 0, "3-5": 0, "5-9 (target)": 0, "9-12": 0, "12+": 0}
    for cid, cand in top100_cands.items():
        y = cand.get("profile", {}).get("years_of_experience", 0)
        if y < 3: exp_buckets["0-3"] += 1
        elif y < 5: exp_buckets["3-5"] += 1
        elif y <= 9: exp_buckets["5-9 (target)"] += 1
        elif y <= 12: exp_buckets["9-12"] += 1
        else: exp_buckets["12+"] += 1
    for bucket, n in exp_buckets.items():
        bar = "█" * n
        print(f"  {bucket:15s}: {n:3d} {bar}")

    print("\n✓ Analysis complete.")


if __name__ == "__main__":
    cands = sys.argv[1] if len(sys.argv) > 1 else "candidates.jsonl"
    sub = sys.argv[2] if len(sys.argv) > 2 else "submission.csv"
    analyze(cands, sub)
