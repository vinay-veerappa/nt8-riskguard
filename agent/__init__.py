"""agent — registers this repo's agent-loop profile.

Only the NT8 profile lives here. The line that also imported
`python_tvdownloadohlc` was inherited from tvDownloadOHLC's
`scripts/agent_loop_config/__init__.py` and was dead on arrival at the
2026-08-12 split: that profile stayed behind with the Python code it
describes, so importing this package raised ModuleNotFoundError and
`--profile-module agent.nt8_riskguard` could not resolve. Every loop
invocation in this repo failed at import until 2026-08-13.

The split's verification checked the suite, both mutation batteries and
deploy parity, but never that the loop could still start -- which is why
this survived. `python -m agent_loop ... --list` is the free check that
catches it and belongs in CI.
"""
from .nt8_riskguard import NT8_RISKGUARD

__all__ = ["NT8_RISKGUARD"]
