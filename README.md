# RAWCRUIT — Intelligent Candidate Discovery & Ranking
**Team Lazy4 | Redrob Hackathon 2026**

> *"The best hire isn't the one with the most keywords. It's the one with the right story."*

---

## 🏆 What We Built

RAWCRUIT is a **5-component hybrid scoring engine** that reads job descriptions the way a great recruiter does — not by matching keywords, but by reasoning about fit, trajectory, and availability.

Built to rank 100,000 candidates for a Senior AI Engineer role in **~10 seconds on CPU, zero API calls, zero dependencies beyond Python stdlib.**

---

## 🧠 The Core Insight

The JD gave us a hint that most teams would miss:

> *"The right answer involves reasoning about the gap between what the JD says and what the JD means. A candidate who has all the AI keywords listed as skills but whose title is 'Marketing Manager' is not a fit, no matter how perfect their skill list looks."*

So we built a system that:
1. **Checks if title/career matches** before even looking at skills
2. **Penalizes keyword stuffing** (skills with <3 months duration get 92% weight penalty)
3. **Weights behavioral signals as a multiplier**, not an afterthought
4. **Explicitly disqualifies** consulting-only careers and bad-fit titles

---

## 🔬 Architecture: 5-Layer Scoring

```
RAWCRUIT Score = Base × Behavioral_Multiplier

Base = (
  title_career_score × 0.35  ← Most important: actual role fit
  + skill_score        × 0.28  ← Genuine skill depth (anti-stuffing)
  + experience_quality × 0.16  ← Years + production evidence
  + location_score     × 0.12  ← Pune/Noida/NCR/Hyderabad preferred
  + education_score    × 0.09  ← Institution tier + field match
)

Behavioral_Multiplier ∈ [0.05, 1.55]
  ← Availability, recency, response rate, notice period
```

### Layer 1: Title + Career Match (35%)
- Checks current title against 15+ valid ML/AI role patterns
- Hard-disqualifies non-AI titles (marketing manager, accountant, etc.)
- Analyzes career descriptions for real ML work (embedding, retrieval, ranking, etc.)
- **Consulting-only careers (TCS, Infosys, Wipro...) → 72% score penalty**
- Product-company tenure → bonus points
- Summary depth signals (mentions of "production", "NDCG", "A/B test") → further boost

### Layer 2: Skill Depth Score (28%)
```python
skill_weight = (
  proficiency_weight × 0.45 +   # expert=1.0, advanced=0.82, intermediate=0.55
  duration_trust     × 0.30 +   # <3 months → 0.08 (keyword stuffer penalty!)
  endorsement_boost  × 0.25     # log-scaled, capped at 50
) + assessment_bonus            # platform assessment scores add up to +0.2
```
**Anti-stuffing mechanism**: A skill listed with duration=0 and endorsements=0 carries only 8% of full weight. A recruiter can't trust it.

### Layer 3: Experience Quality (16%)
- JD target: 5-9 years → score 1.0
- Title-hopping (<18 months per role) → −4.5% per job
- No production evidence in career history → −32% multiplier
- >13 years → reduced (overqualified per JD)

### Layer 4: Location Score (12%)
- Pune / Noida / NCR / Hyderabad → 1.0
- India + willing to relocate → 0.72
- India, not relocating → 0.52
- Outside India, not relocating → 0.22

### Layer 5: Education Tier (9%)
- Tier 1 institution + CS/AI field → up to 1.0
- Additional bonus for M.Tech/PhD
- Education is the least important factor — a Tier-4 grad with great career > Tier-1 grad with poor career

### Behavioral Multiplier (×0.05 – 1.55)
The JD's most important hint: *"A perfect-on-paper candidate who hasn't logged in for 6 months and has a 5% recruiter response rate is, for hiring purposes, not actually available."*

| Signal | Impact |
|--------|--------|
| Active in last 7 days | +25% |
| Active 7–30 days | +12% |
| Inactive 90–180 days | −8% |
| Inactive >180 days | **−22%** |
| open_to_work = true | +12% |
| Recruiter response rate (×0.22) | Up to +22% |
| Notice period ≤15 days | +12% |
| Notice period >90 days | −4% |
| Verified email + phone | +8% |
| GitHub activity (per JD: external validation) | Up to +10% |

---

## 🪤 Honeypot Detection

The JD warned us: *"find candidates whose skills section contains the most AI keywords — that's a trap we've explicitly built into the dataset."*

Our system catches keyword stuffers via:
1. Duration trust — skills with <3 months usage → near-zero weight
2. Title disqualification — "Marketing Manager" with 10 AI skills = score near 0
3. Career mismatch — no AI work in job descriptions → title match alone insufficient
4. Consulting-only penalty — no product-company experience → 72% base penalty

---

## 🚀 Running the Ranker

```bash
# Single command, as specified:
python rank.py --candidates ./candidates.jsonl --out ./submission.csv

# Or with explicit paths:
python rank.py --candidates /path/to/candidates.jsonl --out ./my_submission.csv
```

**Requirements**: Python 3.9+ (zero pip dependencies)
**Runtime**: ~10 seconds for 100,000 candidates on any modern CPU

---

## 📁 Repository Structure

```
rawcruit-ranker/
├── rank.py                    ← Main ranking engine (run this)
├── submission.csv             ← Our ranked output (100 candidates)
├── submission_metadata.yaml   ← Team metadata + methodology declaration
├── requirements.txt           ← Zero deps (Python stdlib only)
├── README.md                  ← This file
└── demo/
    └── rawcruit_demo.html     ← Interactive UI demo (open in browser)
```

---

## 📊 Submission Details

- **Format**: `candidate_id, rank, score, reasoning`
- **Rows**: Exactly 100 (ranks 1–100)
- **Score range**: 0.9999 (rank 1) → non-increasing
- **Validation**: Passes `validate_submission.py` ✓

**Top 5 ranked candidates:**
| Rank | Candidate | Title | Key Signal |
|------|-----------|-------|------------|
| 1 | CAND_0000031 | Recommendation Systems Engineer (6y) | 8 AI skills; 0.91 response rate; product co |
| 2 | CAND_0001610 | Machine Learning Engineer (3y) | 10 AI skills; multi-AI roles; active |
| 3 | CAND_0002025 | Senior AI Engineer (5.9y) | 13 AI skills; 0.80 response; multi-AI roles |
| 4 | CAND_0002120 | ML Engineer (6.5y) | 6 AI skills; 4yr+ AI exp; active |
| 5 | CAND_0003791 | ML Engineer (6.6y) | 5 AI skills; multi-AI roles; product co |

---

## 👥 Team

**Team: Lazy4**  
Built for the Redrob Intelligent Candidate Discovery & Ranking Challenge — Hackathon 2026

---

## 📄 License

MIT License — feel free to adapt for your own hiring intelligence needs.
