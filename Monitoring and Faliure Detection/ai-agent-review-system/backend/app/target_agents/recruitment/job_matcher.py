"""Stage 2: retrieve the jobs most relevant to a candidate profile."""
from __future__ import annotations

import re
from typing import Any, Dict, List

_TOKEN = re.compile(r"[a-z0-9+#]+")
_IGNORED_TITLE_WORDS = {"a", "an", "and", "the", "of", "for", "in", "senior", "junior", "sr", "jr", "lead"}


def _title_tokens(text: str) -> set:
    return {t for t in _TOKEN.findall(text.lower()) if t not in _IGNORED_TITLE_WORDS}


def title_similarity(headline: str, job_title: str) -> float:
    """Jaccard overlap between the candidate headline and the job title."""
    a, b = _title_tokens(headline), _title_tokens(job_title)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def skill_overlap(profile_skills: List[str], job: Dict[str, Any]) -> Dict[str, Any]:
    wanted = list(job["required_skills"]) + list(job["preferred_skills"])
    have = set(profile_skills)
    matched = [s for s in wanted if s in have]
    score = len(matched) / len(wanted) if wanted else 0.0
    return {"score": score, "matched": matched}


def retrieve_jobs(profile: Dict[str, Any], jobs: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    cfg = config["retrieval"]
    results = []
    for job in jobs:
        overlap = skill_overlap(profile["skills"], job)
        title_score = title_similarity(profile["headline"], job["title"])
        score = cfg["skill_weight"] * overlap["score"] + cfg["title_weight"] * title_score
        if score < cfg["min_score"]:
            continue
        results.append(
            {
                "job_id": job["id"],
                "title": job["title"],
                "retrieval_score": round(score, 4),
                "skill_score": round(overlap["score"], 4),
                "title_score": round(title_score, 4),
                "matched_skills": overlap["matched"],
            }
        )
    results.sort(key=lambda r: (-r["retrieval_score"], r["job_id"]))
    return results[: cfg["top_k"]]
