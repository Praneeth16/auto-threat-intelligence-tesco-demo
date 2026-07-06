"""Shared helpers: the single defang() function and the seeded RNG factory.

defang() is the one helper used everywhere text renders an indicator (PLAN
Section 0, rule 5). Plain form is allowed only inside data tables where matching
is demonstrated.
"""

from __future__ import annotations

import random

from datagen.config import SEED


def defang(text: str) -> str:
    """Return a display-safe form of an indicator or free text.

    Neutralizes clickable/resolvable indicators: `https` becomes `hxxps`,
    `http` becomes `hxxp`, and every dot becomes `[.]`. Idempotent: already
    defanged text (containing `[.]` or `hxxp`) passes through unchanged because
    it has no bare dot or plain scheme left to rewrite.
    """
    if text is None:
        return text
    # Protect existing [.] so the dot inside it is not re-wrapped.
    placeholder = "\x00DOT\x00"
    out = text.replace("[.]", placeholder)
    out = out.replace("https://", "hxxps://").replace("http://", "hxxp://")
    out = out.replace(".", "[.]")
    return out.replace(placeholder, "[.]")


def rng(stream: str = "") -> random.Random:
    """Return a deterministic Random seeded from SEED plus a stream label.

    Distinct stream labels give independent-but-reproducible sequences so
    modules do not share or perturb one another's draws. An empty label
    yields the base seed.
    """
    if not stream:
        return random.Random(SEED)
    # Derive a stable per-stream seed without Python hash randomization.
    h = 0
    for ch in stream:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return random.Random(SEED ^ h)
