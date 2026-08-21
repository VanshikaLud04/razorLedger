"""
generator/corruption.py — Synthetic noise functions.

Explicitly separated from event creation so corruption logic is
testable independently and the noise model is transparent.
"""
import random
import re


def apply_corruption(text: str | None, rate: float, rng: random.Random) -> str | None:
    """
    Apply synthetic noise to a string field at the given rate.
    
    Corruption modes:
    - truncate: drop last 2–4 characters (common in bank narrations)
    - swap: transpose two adjacent characters (OCR / typo simulation)
    - space: add or remove a space (inconsistent formatting)
    - prefix: prepend a common bank prefix that obscures the reference
    
    Returns original string if rng roll exceeds rate or text is None/empty.
    """
    if not text or rng.random() > rate:
        return text

    mode = rng.choice(['truncate', 'swap', 'space', 'prefix'])

    if mode == 'truncate' and len(text) > 4:
        trunc = rng.randint(2, 4)
        return text[:-trunc]

    elif mode == 'swap' and len(text) >= 2:
        idx = rng.randint(0, len(text) - 2)
        chars = list(text)
        chars[idx], chars[idx + 1] = chars[idx + 1], chars[idx]
        return ''.join(chars)

    elif mode == 'space':
        # Either collapse a space or insert one
        if ' ' in text:
            return text.replace(' ', '', 1)
        else:
            mid = len(text) // 2
            return text[:mid] + ' ' + text[mid:]

    elif mode == 'prefix':
        # Bank narrations often prepend "NEFT/" or "IMPS/" before ref
        prefixes = ['NEFT/', 'IMPS/', 'UPI/', 'CR/']
        return rng.choice(prefixes) + text

    return text


def normalize_reference(ref: str | None) -> str:
    """
    Canonical reference normalization used by both corruption and matching.
    Uppercase, strip spaces, hyphens, slashes.
    """
    if not ref:
        return ''
    return re.sub(r'[\s\-/]', '', ref.upper())


def normalize_counterparty(name: str | None) -> str:
    """
    Canonical counterparty normalization.
    Lowercase, strip punctuation, collapse whitespace.
    """
    if not name:
        return ''
    cleaned = re.sub(r'[^\w\s]', '', name.lower())
    return re.sub(r'\s+', ' ', cleaned).strip()
