"""Example chatbot agent: intent detection -> FAQ retrieval -> response generation."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...integration.config_utils import apply_overrides, config_version, load_yaml
from ...integration.tracing import MISSING, EventRecorder

STAGES = ("intent_detection", "retrieval", "response_generation")
_TOKEN = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "a", "an", "and", "are", "can", "do", "does", "for", "how", "i", "in", "is", "it", "me", "my",
    "of", "on", "please", "the", "to", "what", "which", "you", "your", "with", "get", "want", "need",
}
_PACKAGE = Path(__file__).parent


def tokens(text: str) -> set:
    return {t for t in _TOKEN.findall(text.lower()) if t not in _STOPWORDS}


def detect_intent(question: str, cfg: Dict[str, Any]) -> str:
    words = _TOKEN.findall(question.lower())
    if any(w in cfg["intents"]["greeting"] for w in words) and len(words) <= 4:
        return "greeting"
    if any(w in cfg["intents"]["thanks"] for w in words) and len(words) <= 4:
        return "thanks"
    return "question"


def retrieve(question: str, faq: List[Dict[str, Any]], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    query = tokens(question)
    results = []
    for entry in faq:
        doc = tokens(entry["question"]) | {k.lower() for k in entry["keywords"]}
        if not query or not doc:
            continue
        common = len(query & doc)
        overlap = common / min(len(query), len(doc))
        jaccard = common / len(query | doc)
        score = 0.7 * overlap + 0.3 * jaccard
        if score >= cfg["retrieval"]["min_score"]:
            results.append({"faq_id": entry["id"], "question": entry["question"], "score": round(score, 4)})
    results.sort(key=lambda r: (-r["score"], r["faq_id"]))
    return results[: cfg["retrieval"]["top_k"]]


class FaqAgent:
    def __init__(self, config: Optional[Dict[str, Any]] = None, faq: Optional[List[Dict[str, Any]]] = None) -> None:
        self.config = config if config is not None else load_yaml(_PACKAGE / "config.yaml")
        if faq is None:
            faq = json.loads((_PACKAGE / "faq.json").read_text(encoding="utf-8"))
        self.faq = faq
        self.faq_by_id = {e["id"]: e for e in faq}

    @property
    def version(self) -> str:
        return config_version(self.config)

    def run(
        self,
        question: str,
        stage_overrides: Optional[Dict[str, Any]] = None,
        config_overrides: Optional[Dict[str, Any]] = None,
        recorder: Optional[EventRecorder] = None,
    ) -> Dict[str, Any]:
        stage_overrides = stage_overrides or {}
        cfg = apply_overrides(self.config, config_overrides)
        version = config_version(cfg)
        recorder = recorder or EventRecorder()
        recorder.version = version

        def ov(name: str) -> Any:
            return stage_overrides.get(name, MISSING)

        intent = recorder.step(
            "intent_detection", lambda: detect_intent(question, cfg),
            input={"question": question}, override=ov("intent_detection"),
        )
        retrieved = recorder.step(
            "retrieval", lambda: retrieve(question, self.faq, cfg), kind="retrieval",
            input={"question": question, "faq_entries": len(self.faq)}, override=ov("retrieval"),
        )
        response = recorder.step(
            "response_generation", lambda: self._respond(intent, retrieved, cfg),
            input={"intent": intent, "retrieved_count": len(retrieved)}, override=ov("response_generation"),
        )
        return {
            "intent": intent,
            "retrieved": retrieved,
            "answer": response["answer"],
            "source_id": response.get("source_id"),
            "confidence": response.get("confidence", 0.0),
            "config_version": version,
        }

    def _respond(self, intent: str, retrieved: List[Dict[str, Any]], cfg: Dict[str, Any]) -> Dict[str, Any]:
        reply = cfg["response"]
        if intent == "greeting":
            return {"answer": reply["greeting_message"], "source_id": None, "confidence": 1.0}
        if intent == "thanks":
            return {"answer": reply["thanks_message"], "source_id": None, "confidence": 1.0}
        if retrieved and retrieved[0]["score"] >= reply["answer_threshold"]:
            top = retrieved[0]
            return {"answer": self.faq_by_id[top["faq_id"]]["answer"], "source_id": top["faq_id"], "confidence": top["score"]}
        return {"answer": reply["fallback_message"], "source_id": None, "confidence": 0.0}
