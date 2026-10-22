"""Stage 1: turn resume text into a structured candidate profile."""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Dict, List, Tuple

_YEARS = re.compile(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b", re.IGNORECASE)

# Checked from the highest level downwards; the first match wins.
_EDUCATION_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("phd", re.compile(r"\b(ph\.?d|doctorate|doctor of philosophy)\b", re.I)),
    ("master", re.compile(r"\b(master'?s?|m\.?sc|m\.?tech|mba)\b", re.I)),
    ("bachelor", re.compile(r"\b(bachelor'?s?|b\.?tech|b\.?sc)\b|\bb\.e\.", re.I)),
    ("diploma", re.compile(r"\bdiploma\b", re.I)),
]


@lru_cache(maxsize=256)
def _alias_pattern(alias: str) -> re.Pattern:
    # Lookarounds (not \b) so "c++" style tokens and "java" vs "javascript" work.
    return re.compile(r"(?<![\w+#])" + re.escape(alias) + r"(?![\w+#])", re.IGNORECASE)


def extract_skills(text: str, config: Dict[str, Any]) -> List[str]:
    disabled = set(config.get("parser", {}).get("disabled_skills", []))
    found = set()
    for canonical, aliases in config["skills"].items():
        if canonical in disabled:
            continue
        if any(_alias_pattern(alias).search(text) for alias in aliases):
            found.add(canonical)
    return sorted(found)


def extract_years(text: str) -> float:
    values = [float(m.group(1)) for m in _YEARS.finditer(text)]
    return min(max(values), 50.0) if values else 0.0


def extract_education(text: str, config: Dict[str, Any]) -> Tuple[int, str]:
    levels = config["education_levels"]
    for label, pattern in _EDUCATION_PATTERNS:
        if pattern.search(text):
            return levels[label], label
    return levels["none"], "none"


def extract_headline(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def parse_resume(text: str, config: Dict[str, Any]) -> Dict[str, Any]:
    level, label = extract_education(text, config)
    return {
        "headline": extract_headline(text),
        "skills": extract_skills(text, config),
        "years_experience": extract_years(text),
        "education_level": level,
        "education_label": label,
    }
