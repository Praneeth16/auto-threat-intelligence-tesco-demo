"""Synthetic world generator for the FreshCart PhishOps SOC demo.

Pure Python + pandas. Ground-truth-first: the attack storyline is built as
explicit objects, data is rendered from them, and the ground truth is written
as tables. Every detection, score, and agent decision in the demo is
rediscoverable from what this package plants.

Deterministic: one seeded RNG (seed=42). Two runs produce identical output.
"""

from datagen.config import CONFIG

__all__ = ["CONFIG"]
