"""Single Fault Injector (Phase 2 Module).

Provides controlled single-variable perturbation injection for black-box testing:
- Ambiguity injection (vague pronoun, missing intent)
- Typo / Misspelling injection (character swaps, omissions)
- Grammar & Incomplete prompt injection (truncated sentences)
- Strict output format constraint (demanding strict JSON/YAML)
- Latency & Timeout stress injection
- Schema corruption & Unexpected types
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class SingleFaultType(str, Enum):
    AMBIGUOUS_PROMPT = "ambiguous_prompt"
    MISSPELLING = "misspelling"
    GRAMMAR_ERROR = "grammar_error"
    INCOMPLETE_INPUT = "incomplete_input"
    FORMAT_STRICTNESS = "format_strictness"
    LARGE_PAYLOAD = "large_payload"
    CORRUPTED_JSON = "corrupted_json"
    TIMEOUT_INDUCED = "timeout_induced"


@dataclass
class SingleFaultInjectionResult:
    fault_type: SingleFaultType
    original_input: Any
    perturbed_input: Any
    fault_description: str
    injected_parameter: str
    expected_failure_mode: str


class SingleFaultInjector:
    """Applies a single, isolated fault to an input payload to test robustness."""

    _TYPO_MAP = {
        'e': '3', 'a': '@', 'o': '0', 'i': '1', 's': '5', 't': '7',
        'the': 'teh', 'please': 'plz', 'return': 'retrun', 'policy': 'ploicy',
        'account': 'acount', 'balance': 'balnce', 'payment': 'paymnt',
        'experience': 'experince', 'skills': 'skils', 'education': 'educaton'
    }

    _AMBIGUOUS_SUFFIXES = [
        " Can you do that thing with the stuff we discussed earlier?",
        " What about the other one though?",
        " Is it true or whatever it is?",
        " Please handle it as usual without specifying details."
    ]

    _INCOMPLETE_CUTOFFS = [
        "Could you please explain how to",
        "I need immediate help regarding the",
        "The requirements for candidate position are",
    ]

    @classmethod
    def inject(
        cls,
        fault_type: SingleFaultType,
        original_input: Any,
        seed: Optional[int] = None,
    ) -> SingleFaultInjectionResult:
        rng = random.Random(seed or 42)

        if isinstance(original_input, dict):
            text_keys = [k for k, v in original_input.items() if isinstance(v, str)]
            target_key = text_keys[0] if text_keys else "input"
            original_text = str(original_input.get(target_key, ""))
        else:
            target_key = "query"
            original_text = str(original_input or "")

        perturbed_text = original_text
        desc = ""
        expected_failure = "incorrect_output"

        if fault_type == SingleFaultType.AMBIGUOUS_PROMPT:
            suffix = rng.choice(cls._AMBIGUOUS_SUFFIXES)
            perturbed_text = f"{original_text.rstrip('.?!')}.{suffix}"
            desc = "Appended ambiguous referent pronouns and omitted context"
            expected_failure = "ambiguity_misunderstanding"

        elif fault_type == SingleFaultType.MISSPELLING:
            words = original_text.split()
            if words:
                idx = rng.randint(0, len(words) - 1)
                w = words[idx]
                if len(w) > 3:
                    # Swap adjacent letters
                    chars = list(w)
                    chars[1], chars[2] = chars[2], chars[1]
                    words[idx] = "".join(chars)
                else:
                    words[idx] = w + "x"
                perturbed_text = " ".join(words)
            desc = f"Injected synthetic spelling permutation in target prompt"
            expected_failure = "tokenization_or_intent_failure"

        elif fault_type == SingleFaultType.GRAMMAR_ERROR:
            perturbed_text = f"Me wants knowing why {original_text} is not do worked properly"
            desc = "Degraded grammatical structure and inflection"
            expected_failure = "parsing_or_intent_error"

        elif fault_type == SingleFaultType.INCOMPLETE_INPUT:
            words = original_text.split()
            perturbed_text = " ".join(words[:max(1, len(words) // 2)]) if words else "Incomplete request..."
            desc = "Truncated input to incomplete clause"
            expected_failure = "incomplete_output"

        elif fault_type == SingleFaultType.FORMAT_STRICTNESS:
            perturbed_text = (
                f"{original_text}\n\nCRITICAL SYSTEM REQUIREMENT: Output MUST be strictly valid RFC 8259 JSON "
                f"matching schema {{\"status\": string, \"data\": object, \"checksum\": int}}. Do NOT include markdown blocks."
            )
            desc = "Enforced strict structured JSON constraint"
            expected_failure = "invalid_json_format"

        elif fault_type == SingleFaultType.LARGE_PAYLOAD:
            noise = " [Irrelevant background context: " + "repeat context "*40 + "]"
            perturbed_text = original_text + noise
            desc = "Injected context distractor payload (40x repetition)"
            expected_failure = "context_distraction_or_latency"

        elif fault_type == SingleFaultType.CORRUPTED_JSON:
            desc = "Corrupted structured payload with trailing commas and unquoted keys"
            if isinstance(original_input, dict):
                perturbed = dict(original_input)
                perturbed["_corrupted_key_"] = "{unquoted_val: True, trailing,}"
                return SingleFaultInjectionResult(
                    fault_type=fault_type,
                    original_input=original_input,
                    perturbed_input=perturbed,
                    fault_description=desc,
                    injected_parameter="_corrupted_key_",
                    expected_failure_mode="invalid_format",
                )
            perturbed_text = original_text + " {invalid:json,}"
            expected_failure = "invalid_format"

        elif fault_type == SingleFaultType.TIMEOUT_INDUCED:
            desc = "Injected adversarial recursive query to induce timeout"
            perturbed_text = f"{original_text} (Compute every permutation of [1..10000000] and list details)"
            expected_failure = "latency_spike_or_timeout"

        # Re-pack into matching structure
        if isinstance(original_input, dict):
            new_payload = dict(original_input)
            new_payload[target_key] = perturbed_text
        else:
            new_payload = perturbed_text

        return SingleFaultInjectionResult(
            fault_type=fault_type,
            original_input=original_input,
            perturbed_input=new_payload,
            fault_description=desc,
            injected_parameter=target_key,
            expected_failure_mode=expected_failure,
        )
