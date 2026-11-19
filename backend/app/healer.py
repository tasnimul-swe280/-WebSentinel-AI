"""Self-healing locators: when a selector breaks, find the most similar element on the page."""

from difflib import SequenceMatcher

from .models import Fingerprint

HEAL_THRESHOLD = 0.65
HEAL_AMBIGUITY_MARGIN = 0.05

WEIGHTS: dict[str, float] = {
    "type": 0.10,
    "name": 0.20,
    "id": 0.15,
    "text": 0.20,
    "label": 0.15,
    "placeholder": 0.08,
    "aria_label": 0.08,
    "href": 0.15,
    "role": 0.04,
    "form": 0.15,
    "path": 0.10,
}
CLASSES_WEIGHT = 0.05
TAG_MISMATCH_PENALTY = 0.4


def text_similarity(a: str, b: str) -> float:
    a, b = a.strip().lower(), b.strip().lower()
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / len(sa | sb)


def similarity(original: Fingerprint, candidate: Fingerprint) -> float:
    """Weighted similarity in [0, 1]. Only attributes present on the original element count."""
    total_weight = 0.0
    score = 0.0
    for attr, weight in WEIGHTS.items():
        expected = getattr(original, attr)
        if not expected:
            continue
        total_weight += weight
        score += weight * text_similarity(expected, getattr(candidate, attr))
    if original.classes:
        total_weight += CLASSES_WEIGHT
        score += CLASSES_WEIGHT * jaccard(original.classes, candidate.classes)
    if total_weight == 0:
        return 0.0
    result = score / total_weight
    if original.tag and original.tag != candidate.tag:
        result *= TAG_MISMATCH_PENALTY
    return round(result, 3)


def best_match(
    original: Fingerprint,
    candidates: list[tuple[str, Fingerprint]],
    threshold: float = HEAL_THRESHOLD,
    ambiguity_margin: float = HEAL_AMBIGUITY_MARGIN,
) -> tuple[str, float] | None:
    """Return the best safe match; reject weak or ambiguous candidates.

    A wrong automatic click/fill is more dangerous than a test failing clearly, so
    close-scoring candidates are treated as ambiguous and are not auto-healed.
    """
    ranked = sorted(
        ((css, similarity(original, fingerprint)) for css, fingerprint in candidates),
        key=lambda item: item[1],
        reverse=True,
    )
    if not ranked or ranked[0][1] < threshold:
        return None
    if len(ranked) > 1 and ranked[0][1] - ranked[1][1] < ambiguity_margin:
        return None
    return ranked[0]
