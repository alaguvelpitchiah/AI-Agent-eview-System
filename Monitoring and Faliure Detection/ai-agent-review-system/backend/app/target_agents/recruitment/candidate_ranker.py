"""Stage 3: score and rank the retrieved jobs for a candidate (0-100)."""
from __future__ import annotations

from typing import Any, Dict, List


def score_job(profile: Dict[str, Any], job: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    cfg = config["ranking"]
    weights = cfg["weights"]
    levels = config["education_levels"]

    have = set(profile["skills"])
    required, preferred = job["required_skills"], job["preferred_skills"]
    matched_required = [s for s in required if s in have]
    matched_preferred = [s for s in preferred if s in have]

    required_cov = len(matched_required) / len(required) if required else 1.0
    preferred_cov = len(matched_preferred) / len(preferred) if preferred else 1.0

    min_years = job["min_years"]
    experience = min(profile["years_experience"] / min_years, 1.0) if min_years > 0 else 1.0

    min_level = levels[job["min_education"]]
    education = min(profile["education_level"] / min_level, 1.0) if min_level > 0 else 1.0

    score = 100.0 * (
        weights["required_skills"] * required_cov
        + weights["preferred_skills"] * preferred_cov
        + weights["experience"] * experience
        + weights["education"] * education
    )

    flags = []
    if cfg["enforce_experience_filter"] and profile["years_experience"] < min_years:
        flags.append("below_min_experience")
    if cfg["enforce_education_filter"] and profile["education_level"] < min_level:
        flags.append("below_min_education")
    if flags:
        score = min(score, cfg["qualification_cap"])

    return {
        "job_id": job["id"],
        "title": job["title"],
        "match_score": round(score, 1),
        "breakdown": {
            "required_coverage": round(required_cov, 3),
            "preferred_coverage": round(preferred_cov, 3),
            "experience_score": round(experience, 3),
            "education_score": round(education, 3),
        },
        "matched_required": matched_required,
        "missing_required": [s for s in required if s not in have],
        "qualification_flags": flags,
    }


def rank_candidates(
    profile: Dict[str, Any],
    retrieved: List[Dict[str, Any]],
    jobs_by_id: Dict[str, Dict[str, Any]],
    config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    scored = []
    for item in retrieved:
        entry = score_job(profile, jobs_by_id[item["job_id"]], config)
        entry["retrieval_score"] = item["retrieval_score"]
        scored.append(entry)
    scored.sort(key=lambda r: (-r["match_score"], -r["retrieval_score"], r["job_id"]))
    for position, entry in enumerate(scored, start=1):
        entry["rank"] = position
    return scored
