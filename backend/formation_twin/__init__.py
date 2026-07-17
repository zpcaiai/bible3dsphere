"""Formation Twin bounded context.

Batch 2 intentionally stores user-reported and observed facts only.  It does
not infer spiritual condition, hidden motives, or divine intent.
"""

from .contracts import CanonicalLifeEvent

__all__ = ["CanonicalLifeEvent"]
