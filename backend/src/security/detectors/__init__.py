"""Deterministic layer-B detectors (ADR-039).

Regex + checksum for RU-PDN (``pii``) and heuristic patterns for prompt
injection (``injection``). Each implements a Protocol from ``security.ports`` so
a layer-A ML detector can replace it with zero call-site change.
"""
