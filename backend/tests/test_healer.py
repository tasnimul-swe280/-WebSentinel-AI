from app.healer import best_match, similarity
from app.models import Fingerprint


def fp(**kw) -> Fingerprint:
    return Fingerprint(**kw)


def test_similarity_is_perfect_for_same_element():
    a = fp(tag="button", id="login-btn", text="Sign in", classes=["btn", "primary"])
    assert similarity(a, fp(tag="button", id="login-btn", text="Sign in", classes=["btn", "primary"])) == 1.0


def test_heals_when_id_changes_but_other_attributes_match():
    original = fp(tag="button", id="login-btn", type="submit", text="Sign in", classes=["btn", "primary"])
    candidate = fp(tag="button", id="signin-submit", type="submit", text="Sign in", classes=["btn", "accent"])
    assert similarity(original, candidate) > 0.7


def test_tag_mismatch_lowers_score():
    original = fp(tag="button", id="login-btn", text="Sign in")
    candidate = fp(tag="a", id="login-btn", text="Sign in")
    assert similarity(original, candidate) < 0.5


def test_unrelated_elements_are_rejected_by_threshold():
    original = fp(tag="input", id="password", type="password", placeholder="Password", name="password")
    candidates = [
        ("#search", fp(tag="input", id="search", type="search", placeholder="Search products", name="q")),
        ("#full-name", fp(tag="input", id="full-name", type="text", name="name")),
    ]
    assert best_match(original, candidates) is None


def test_best_match_picks_highest_scoring_candidate():
    original = fp(tag="input", id="email", type="email", name="email", placeholder="you@example.com")
    candidates = [
        ("#name", fp(tag="input", id="name", type="text", name="name")),
        ("#mail", fp(tag="input", id="mail", type="email", name="email", placeholder="you@example.com")),
    ]
    match = best_match(original, candidates)
    assert match is not None
    css, score = match
    assert css == "#mail"
    assert score > 0.8


def test_ambiguous_candidates_are_not_auto_healed():
    original = fp(tag="button", type="submit", text="Continue", name="continue")
    candidates = [
        ("#continue-a", fp(tag="button", type="submit", text="Continue", name="continue")),
        ("#continue-b", fp(tag="button", type="submit", text="Continue", name="continue")),
    ]
    assert best_match(original, candidates) is None


def test_healing_rejects_candidates_below_stricter_threshold():
    original = fp(tag="input", id="email", type="email", name="email", placeholder="Email")
    candidates = [("#phone", fp(tag="input", id="phone", type="tel", name="phone", placeholder="Phone"))]
    assert best_match(original, candidates) is None
