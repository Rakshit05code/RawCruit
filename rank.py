#!/usr/bin/env python3
"""
RAWCRUIT — Intelligent Candidate Ranker
Team: Lazy4 | Redrob Hackathon 2026

5-component hybrid scoring system:
  1. Title & Career Match (semantic + anti-keyword-stuffer trap)
  2. Skills Match (endorsement-weighted, duration-trust multiplied)
  3. Experience Quality (years + career trajectory)
  4. Education Tier
  5. Behavioral Signal Modifier (availability, activity, responsiveness)

Runs in ~10s on 100K candidates, CPU-only, zero API calls.
"""

import json
import csv
import sys
import math
import re
import argparse
from datetime import date
from pathlib import Path

# ─── JD CONSTANTS ──────────────────────────────────────────────────────────────
ROLE_TITLES = {
    "ai engineer", "ml engineer", "machine learning engineer",
    "senior ai engineer", "senior ml engineer",
    "applied scientist", "applied ml engineer",
    "nlp engineer", "search engineer", "ranking engineer",
    "research engineer", "founding engineer",
    "recommendation systems engineer", "recommendations engineer",
    "ai research engineer", "search infrastructure engineer",
    "senior software engineer (ml)", "software engineer (ml)",
    "deep learning engineer", "data scientist"
}

MUST_HAVE_SKILLS = {
    "embeddings", "sentence-transformers", "vector search", "faiss",
    "pinecone", "weaviate", "qdrant", "milvus", "opensearch",
    "elasticsearch", "retrieval", "ranking", "python",
    "ndcg", "mrr", "a/b testing", "hybrid search",
    "bge", "e5", "openai embeddings", "dense retrieval",
    "information retrieval", "semantic search", "reranking",
    "bi-encoder", "cross-encoder", "learning to rank",
    "nlp", "search", "recommendation", "llm", "fine-tuning",
    "rag", "lora", "qlora", "peft", "transformers", "bert",
    "pytorch", "tensorflow", "numpy", "pandas", "sklearn",
    "scikit-learn", "xgboost", "lightgbm",
    "vector database", "vector db", "production ml",
    "deep learning", "neural network", "machine learning",
    "artificial intelligence", "bm25", "tfidf", "map",
    "recall@k", "evaluation", "benchmark", "fine-tun",
    "sentence transformer", "word2vec", "glove", "fasttext",
    "hugging face", "huggingface", "spacy", "gensim"
}

BONUS_SKILLS = {
    "distributed systems", "large-scale inference", "spark", "kafka",
    "hr-tech", "recruiting", "marketplace",
    "open-source", "kaggle", "docker", "kubernetes",
    "aws", "gcp", "azure", "mlops", "airflow", "dbt"
}

DISQUALIFIER_TITLES = {
    "marketing manager", "content writer", "graphic designer",
    "accountant", "civil engineer", "mechanical engineer",
    "sales executive", "customer support", "project manager",
    "operations manager", "hr manager", "business analyst",
    "recruiter", "teacher", "nurse", "doctor", "designer",
    "devops engineer", "qa engineer", "tester"
}

CONSULTING_FIRMS = {
    "tcs", "tata consultancy", "infosys", "wipro", "accenture",
    "cognizant", "capgemini", "tech mahindra", "hcl", "mphasis",
    "hexaware", "l&t infotech", "ltimindtree", "mindtree",
    "persistent systems", "mastech", "niit technologies",
    "dunder mifflin"  # fictional company in dataset
}

PRODUCT_COMPANIES = {
    "google", "meta", "amazon", "microsoft", "apple", "netflix",
    "uber", "airbnb", "flipkart", "meesho", "swiggy", "zomato",
    "razorpay", "cred", "phonepe", "paytm", "myntra", "nykaa",
    "freshworks", "zoho", "chargebee", "postman", "atlan",
    "openai", "anthropic", "hugging face", "databricks", "snowflake",
    "scale ai", "cohere", "mistral", "deepmind", "nvidia",
    "moengage", "clevertap", "lenskart", "groww", "zerodha",
    "browserstack", "slice", "spinny", "cars24", "redrob",
    "startup", "seed stage", "series a", "series b", "series c",
    "ola", "rapido", "dunzo", "blinkit", "bigbasket"
}

PREFERRED_LOCATIONS = {
    "pune", "noida", "hyderabad", "mumbai", "delhi",
    "gurugram", "gurgaon", "bangalore", "bengaluru",
    "ncr", "delhi ncr", "new delhi"
}


def norm(text: str) -> str:
    return re.sub(r'\s+', ' ', str(text).lower().strip())


def skill_in_set(skill: str, skill_set: set) -> bool:
    s = norm(skill)
    if s in skill_set:
        return True
    for k in skill_set:
        if len(k) > 3 and (k in s or s in k):
            return True
    return False


def days_since(date_str: str) -> int:
    try:
        d = date.fromisoformat(str(date_str))
        return (date.today() - d).days
    except Exception:
        return 9999


def compute_skill_score(skills: list, assessments: dict) -> tuple[float, int]:
    if not skills:
        return 0.0, 0

    total_w = 0.0
    matched_w = 0.0
    n_core = 0

    for sk in skills:
        name = sk.get("name", "")
        prof = sk.get("proficiency", "beginner")
        endorse = min(sk.get("endorsements", 0), 50)
        duration = sk.get("duration_months", 0)

        prof_w = {"beginner": 0.25, "intermediate": 0.55, "advanced": 0.82, "expert": 1.0}.get(prof, 0.25)

        # Duration trust — penalize keyword stuffing (<3 months = likely stuffed)
        if duration < 3:
            dur_trust = 0.08
        elif duration < 6:
            dur_trust = 0.3
        elif duration < 12:
            dur_trust = 0.6
        else:
            dur_trust = min(duration / 24.0, 1.0)

        endorse_boost = math.log1p(endorse) / math.log1p(50)

        # Assessment score (if available on platform)
        assess_bonus = 0.0
        for ak, av in assessments.items():
            if norm(ak) in norm(name) or norm(name) in norm(ak):
                assess_bonus = (av / 100.0) * 0.2
                break

        w = (prof_w * 0.45 + dur_trust * 0.30 + endorse_boost * 0.25) + assess_bonus
        total_w += w

        if skill_in_set(name, MUST_HAVE_SKILLS):
            matched_w += w * 1.6
            n_core += 1
        elif skill_in_set(name, BONUS_SKILLS):
            matched_w += w * 0.35

    if total_w == 0:
        return 0.0, 0

    raw = matched_w / (total_w + 1e-6)
    # Scale: 0 core skills → 0, 5+ → ~0.8, 10+ → ~1.0
    n_bonus = math.log1p(n_core) / math.log1p(12)
    return min(raw * n_bonus * 2.2, 1.0), n_core


def compute_title_career_score(profile: dict, career: list) -> tuple[float, list]:
    flags = []
    score = 0.0

    current_title = norm(profile.get("current_title", ""))
    headline = norm(profile.get("headline", ""))
    summary = norm(profile.get("summary", ""))

    # Hard disqualify
    for bad in DISQUALIFIER_TITLES:
        if bad in current_title:
            flags.append(f"DISQ:{bad.split()[0]}")
            return 0.01, flags

    # Positive title match
    for good in ROLE_TITLES:
        if good in current_title or good in headline:
            score += 0.38
            flags.append("TITLE_MATCH")
            break

    # Career analysis
    ai_roles = 0
    product_months = 0
    consulting_count = 0
    ai_months = 0

    for job in career:
        co = norm(job.get("company", ""))
        title_j = norm(job.get("title", ""))
        desc = norm(job.get("description", ""))
        dur = job.get("duration_months", 0)

        is_consulting = any(f in co for f in CONSULTING_FIRMS)
        is_product = any(p in co for p in PRODUCT_COMPANIES)

        if is_consulting:
            consulting_count += 1
        if is_product:
            product_months += dur
            score += min(dur / 240.0, 0.04)

        # AI work depth in this role
        ai_kws = [
            "embedding", "retrieval", "ranking", "recommendation", "search",
            "machine learning", "deep learning", "neural", "nlp", "transformer",
            "fine-tun", "vector", "bert", "gpt", "llm", "model deploy",
            "inference", "feature pipeline", "a/b test", "ndcg", "rerank",
            "dense retrieval", "sparse", "hybrid search", "faiss", "pinecone",
            "rag", "information retrieval", "language model", "sentence"
        ]
        ai_kw_count = sum(1 for kw in ai_kws if kw in desc or kw in title_j)
        if ai_kw_count >= 4:
            ai_roles += 1
            ai_months += dur
            score += 0.07
        elif ai_kw_count >= 2:
            ai_months += dur * 0.4
            score += 0.025

    # Career-level bonuses
    if ai_roles >= 2:
        score += 0.18
        flags.append("MULTI_AI_ROLE")
    elif ai_roles == 1:
        score += 0.07

    if ai_months >= 48:
        score += 0.15
        flags.append("AI_EXP_4YR")
    elif ai_months >= 24:
        score += 0.08

    if len(career) > 0 and consulting_count == len(career):
        score *= 0.28
        flags.append("CONSULTING_ONLY")
    elif product_months >= 24:
        score += 0.08
        flags.append("PRODUCT_CO_EXP")

    # Summary depth signals (production deployment evidence)
    depth_kws = ["production", "deployed to", "real users", "at scale",
                 "ndcg", "mrr", "a/b test", "evaluation", "benchmark",
                 "billion", "million", "hybrid retrieval", "vector index"]
    depth = sum(1 for kw in depth_kws if kw in summary)
    score += min(depth * 0.025, 0.10)

    return min(score, 1.0), flags


def compute_experience_score(profile: dict, career: list) -> float:
    yoe = profile.get("years_of_experience", 0)

    # Target: 5-9 years per JD
    if 5 <= yoe <= 9:
        base = 1.0
    elif 4 <= yoe < 5 or 9 < yoe <= 11:
        base = 0.78
    elif 3 <= yoe < 4 or 11 < yoe <= 13:
        base = 0.55
    elif yoe > 13:
        base = 0.42  # likely overqualified
    else:
        base = 0.25

    # Title-hopping penalty (JD specifically calls this out)
    hop_penalty = 0.0
    for job in career:
        dur = job.get("duration_months", 0)
        is_current = job.get("is_current", False)
        if not is_current and 0 < dur < 18:
            hop_penalty += 0.045

    # Production evidence
    has_prod = any(
        kw in norm(j.get("description", ""))
        for j in career
        for kw in ["production", "deployed", "real user", "at scale", "serving"]
    )
    if not has_prod:
        base *= 0.68

    return max(0.0, min(base - hop_penalty, 1.0))


def compute_education_score(education: list) -> float:
    if not education:
        return 0.32

    best = 0.0
    for edu in education:
        tier = edu.get("tier", "unknown")
        field = norm(edu.get("field_of_study", ""))
        degree = norm(edu.get("degree", ""))

        t = {"tier_1": 1.0, "tier_2": 0.72, "tier_3": 0.48, "tier_4": 0.32, "unknown": 0.38}.get(tier, 0.38)

        if any(f in field for f in ["computer", "ai", "machine learning", "data science",
                                     "statistics", "math", "electrical", "electronics", "informatics"]):
            t = min(t + 0.15, 1.0)

        if any(d in degree for d in ["m.tech", "mtech", "m.e.", "m.s.", "ms", "phd", "ph.d",
                                      "m.sc", "master", "doctor", "post grad"]):
            t = min(t + 0.15, 1.0)

        best = max(best, t)
    return best


def compute_behavioral_score(signals: dict) -> float:
    score = 0.5

    # Recency — most important per JD guidance
    days_inactive = days_since(signals.get("last_active_date", "2000-01-01"))
    if days_inactive <= 3:
        score += 0.30
    elif days_inactive <= 7:
        score += 0.25
    elif days_inactive <= 14:
        score += 0.18
    elif days_inactive <= 30:
        score += 0.12
    elif days_inactive <= 60:
        score += 0.04
    elif days_inactive <= 90:
        score -= 0.02
    elif days_inactive <= 180:
        score -= 0.08
    else:
        score -= 0.22  # "not actually available" per JD

    # Open to work
    if signals.get("open_to_work_flag", False):
        score += 0.12

    # Recruiter response rate — critical for actual hire-ability
    rr = signals.get("recruiter_response_rate", 0)
    score += rr * 0.22

    # Avg response time
    rt = signals.get("avg_response_time_hours", 999)
    if rt <= 2:
        score += 0.07
    elif rt <= 8:
        score += 0.04
    elif rt <= 24:
        score += 0.02
    elif rt > 72:
        score -= 0.04

    # Notice period
    notice = signals.get("notice_period_days", 90)
    if notice <= 15:
        score += 0.12
    elif notice <= 30:
        score += 0.08
    elif notice <= 60:
        score += 0.03
    else:
        score -= 0.04

    # Profile completeness
    pc = signals.get("profile_completeness_score", 0)
    score += (pc / 100.0) * 0.10

    # Market demand signals
    saved = min(signals.get("saved_by_recruiters_30d", 0), 25)
    score += saved * 0.007

    apps = min(signals.get("applications_submitted_30d", 0), 10)
    score += apps * 0.012

    # Interview & offer signals
    icr = signals.get("interview_completion_rate", 0)
    score += icr * 0.06

    oar = signals.get("offer_acceptance_rate", -1)
    if oar >= 0:
        score += oar * 0.04

    # Verification (reduces ghosting)
    if signals.get("verified_email", False):
        score += 0.04
    if signals.get("verified_phone", False):
        score += 0.04
    if signals.get("linkedin_connected", False):
        score += 0.03

    # GitHub activity (external validation per JD)
    gh = signals.get("github_activity_score", -1)
    if gh > 0:
        score += min(gh / 100.0 * 0.10, 0.10)

    return max(0.05, min(score, 1.55))


def compute_location_score(profile: dict, signals: dict) -> float:
    loc = norm(profile.get("location", ""))
    country = norm(profile.get("country", ""))
    willing = signals.get("willing_to_relocate", False)
    notice = signals.get("notice_period_days", 90)

    if any(p in loc for p in PREFERRED_LOCATIONS):
        return 1.0
    if country == "india" and willing:
        return 0.72
    if country == "india":
        return 0.52
    if willing and notice <= 60:
        return 0.38
    return 0.22


def score_candidate(cand: dict) -> tuple[float, str]:
    profile = cand.get("profile", {})
    career = cand.get("career_history", [])
    education = cand.get("education", [])
    skills = cand.get("skills", [])
    signals = cand.get("redrob_signals", {})
    assessments = signals.get("skill_assessment_scores", {})

    skill_score, n_core = compute_skill_score(skills, assessments)
    title_career_score, flags = compute_title_career_score(profile, career)
    exp_score = compute_experience_score(profile, career)
    edu_score = compute_education_score(education)
    loc_score = compute_location_score(profile, signals)
    behavioral = compute_behavioral_score(signals)

    base = (
        title_career_score * 0.35 +
        skill_score        * 0.28 +
        exp_score          * 0.16 +
        loc_score          * 0.12 +
        edu_score          * 0.09
    )

    final = base * behavioral

    yoe = profile.get("years_of_experience", 0)
    rr = signals.get("recruiter_response_rate", 0)
    title = profile.get("current_title", "Unknown")
    flag_str = "; ".join(flags[:2]) if flags else "Good fit"

    reasoning = (
        f"{title} with {yoe:.1f} yrs exp; "
        f"{n_core} AI/ML core skills; "
        f"recruiter response rate {rr:.2f}; "
        f"{flag_str}"
    )

    return min(max(final, 0.0001), 0.9999), reasoning


def rank_candidates(candidates_path: str, output_path: str):
    print(f"[RAWCRUIT Lazy4] Loading candidates from {candidates_path}...")
    candidates = []
    with open(candidates_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                candidates.append(json.loads(line))

    print(f"[RAWCRUIT Lazy4] Scoring {len(candidates)} candidates...")
    scored = []
    for i, cand in enumerate(candidates):
        if i > 0 and i % 10000 == 0:
            print(f"  ... {i}/{len(candidates)}")
        cid = cand.get("candidate_id", f"CAND_{i:07d}")
        score, reason = score_candidate(cand)
        scored.append((cid, score, reason))

    # Sort: descending score, tie-break candidate_id ascending (per spec)
    scored.sort(key=lambda x: (-x[1], x[0]))

    # Apply small epsilon spread to make scores distinct (still monotone non-increasing)
    EPSILON = 0.000001
    for i in range(1, min(100, len(scored))):
        prev_score = scored[i-1][1]
        cur_score = scored[i][1]
        if cur_score >= prev_score:
            cur_score = prev_score - EPSILON
        scored[i] = (scored[i][0], max(cur_score, 0.0001), scored[i][2])

    print(f"[RAWCRUIT Lazy4] Writing top 100 to {output_path}...")
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        for rank, (cid, score, reason) in enumerate(scored[:100], 1):
            writer.writerow([cid, rank, f"{score:.4f}", reason])

    print(f"\n✓ Done. Top 5:")
    for r, (cid, sc, rsn) in enumerate(scored[:5], 1):
        print(f"  #{r}: {cid} | {sc:.4f} | {rsn}")
    return scored


def main():
    parser = argparse.ArgumentParser(description="RAWCRUIT Candidate Ranker — Team Lazy4")
    parser.add_argument("--candidates", default="candidates.jsonl")
    parser.add_argument("--out", default="submission.csv")
    args = parser.parse_args()
    rank_candidates(args.candidates, args.out)


if __name__ == "__main__":
    main()
