"""Security guard services (ADR-039).

``dlp.DlpGuard`` — A3 output hard-block (audit + raise). Injection B1 is a
stateless pass applied directly at the runtime chokepoint via
``security.detectors.injection.scan_injection`` (no service wrapper needed).
"""
