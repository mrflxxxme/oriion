#!/usr/bin/env python3
"""Classify a PR diff against the autonomy tripwire (ADR-037 D2).

The autonomous runner calls this BEFORE auto-merging a green phase. If any
changed file matches a tripwire category (DB migrations · auth/RBAC/sessions ·
billing · secrets/keys · public contracts), the phase must NOT auto-merge:
it goes to RUN-QUEUE + notify + wait for founder ``/ack``. No match → auto-merge.

Exit codes:
  0  clean — no tripwire category matched → auto-merge allowed
  10 tripwire matched → pause-and-ack required (NOT an error; a decision signal)
  1  usage / IO error

Reads ``.claude/autonomy/tripwire.yaml``. Needs PyYAML → run via the backend
venv: ``uv run --project backend python scripts/autonomy/classify_tripwire.py``.

Changed files come from (in priority order): ``--files a b c``, or ``--diff-base
<ref>`` (runs ``git diff --name-only <ref>...HEAD``), default base ``origin/main``.
Emits a JSON verdict to stdout for the runner to consume.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

_DEFAULT_CONFIG = Path(".claude/autonomy/tripwire.yaml")


def _glob_to_regex(glob: str) -> re.Pattern[str]:
    """Translate a path glob (with ``**``) to an anchored regex on '/'-paths.

    ``**`` matches across directory separators; ``*`` matches within a segment;
    ``?`` matches a single non-separator char.
    """
    i = 0
    out: list[str] = ["^"]
    n = len(glob)
    while i < n:
        c = glob[i]
        if c == "*":
            if i + 1 < n and glob[i + 1] == "*":
                # ** → any chars incl '/'. Swallow an optional trailing '/'.
                i += 2
                if i < n and glob[i] == "/":
                    out.append("(?:.*/)?")
                    i += 1
                else:
                    out.append(".*")
            else:
                out.append("[^/]*")
                i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    out.append("$")
    return re.compile("".join(out))


def _changed_files(args: argparse.Namespace) -> list[str]:
    if args.files:
        return [f.strip().replace("\\", "/") for f in args.files if f.strip()]
    base = args.diff_base
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", f"{base}...HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"[tripwire] cannot compute git diff against {base}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    return [ln.strip().replace("\\", "/") for ln in out.stdout.splitlines() if ln.strip()]


def classify(files: list[str], config: dict[str, Any]) -> list[dict[str, Any]]:
    """Return matched categories: [{category, reason, matched_files:[...]}]."""
    matches: list[dict[str, Any]] = []
    for name, spec in (config.get("categories") or {}).items():
        patterns = [_glob_to_regex(g) for g in (spec.get("globs") or [])]
        hit = sorted({f for f in files if any(p.match(f) for p in patterns)})
        if hit:
            matches.append(
                {"category": name, "reason": spec.get("reason", ""), "matched_files": hit}
            )
    return matches


# --- db_migrations content downgrade (ADR-037 D2, grill 2026-07-03) -----------
# The v1 tripwire acked EVERY migration. v2 lets the classifier AUTO-DOWNGRADE a
# migration whose upgrade() is provably a pure greenfield CREATE (new schema /
# tables / their-own RLS from scratch) — no ALTER/DROP of existing objects, no
# backfill DML, no index on a not-here table, no dynamic SQL. FAIL-CLOSED: any
# doubt keeps the ack. Only db_migrations is content-inspected; auth/billing/
# secrets/contracts stay path-based and never downgrade.

# Risky raw-SQL tokens anywhere in upgrade() -> keep ack (existing-object surgery
# or data migration). DROP appears legitimately in downgrade(), so we scope to
# upgrade() only (see _upgrade_body).
_RISKY_SQL = re.compile(
    r"\b(?:DROP\s+TABLE|DROP\s+COLUMN|ADD\s+COLUMN|ALTER\s+COLUMN|DROP\s+POLICY"
    r"|ALTER\s+POLICY|DROP\s+INDEX|DROP\s+CONSTRAINT|ADD\s+CONSTRAINT|RENAME"
    r"|DELETE\s+FROM|TRUNCATE|UPDATE\s+[\w.\"]+\s+SET)\b",
    re.IGNORECASE,
)
# Risky alembic ops (surgery on existing tables / bulk data).
_RISKY_OP = re.compile(
    r"\bop\.(?:add_column|drop_column|alter_column|drop_table|drop_constraint"
    r"|create_check_constraint|rename_table|bulk_insert|create_foreign_key)\b",
    re.IGNORECASE,
)
# Any f-string is un-inspectable (a variable table name) -> keep ack. New
# cell-scoped migrations avoid this by calling migrations/_rls.py helpers with
# literal table names (grill 2026-07-03, option C) instead of an f-string loop.
_FSTRING = re.compile(r"\b(?:f|F|rf|fr|Rf|fR|rF|Fr|RF|FR)(?:\"\"\"|'''|\"|')")
# Strip Python string literals so SQL functions like gen_random_uuid() inside a
# string are not mistaken for Python calls when we allow-list the real calls.
_STRIP_STRINGS = re.compile(r"[rRbBuU]{0,2}(\"\"\"|'''|\"|')(?:\\.|(?!\1).)*?\1", re.DOTALL)
_CALL = re.compile(r"(?:(\w+)\s*\.\s*)?(\w+)\s*\(")
# The migration's upgrade() may ONLY call these. op.<risky> is caught here too.
_SAFE_OPS = frozenset(
    {"execute", "create_table", "create_index", "create_primary_key",
     "create_unique_constraint", "create_table_comment", "get_bind"}
)
# House RLS/trigger emitters (migrations/_rls.py); trusted like op.create_table.
_SAFE_HELPERS = frozenset({"cell_scoped_rls", "updated_at_trigger"})
_HELPER_IMPORT = re.compile(r"(?:from\s+migrations\._rls\s+import|import\s+migrations\._rls)")
_CREATE_TABLE = re.compile(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([\w.\"]+)", re.IGNORECASE)
_OP_CREATE_TABLE = re.compile(r"op\.create_table\(\s*['\"]([\w.]+)['\"]", re.IGNORECASE)
_ALTER_TABLE = re.compile(
    r"ALTER\s+TABLE\s+(?:ONLY\s+)?([\w.\"]+)\s+(.+?)(?=;|$)", re.IGNORECASE | re.DOTALL
)
_CREATE_INDEX_ON = re.compile(
    r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:CONCURRENTLY\s+)?(?:IF\s+NOT\s+EXISTS\s+)?"
    r"[\w.\"]+\s+ON\s+([\w.\"]+)",
    re.IGNORECASE,
)
_INSERT_INTO = re.compile(r"INSERT\s+INTO\s+([\w.\"]+)", re.IGNORECASE)
# The only ALTER TABLE allowed on a here-created table: enabling/forcing RLS.
_RLS_ONLY = re.compile(r"^\s*(?:ENABLE|FORCE|DISABLE|NO\s+FORCE)\s+ROW\s+LEVEL\s+SECURITY\s*$", re.IGNORECASE)


def _upgrade_body(source: str) -> str | None:
    """Isolate the ``upgrade()`` function body; None if it can't be found."""
    m = re.search(r"\ndef\s+upgrade\s*\(", source)
    if m is None:
        return None
    start = m.end()
    nxt = re.search(r"\ndef\s+\w+\s*\(", source[start:])
    return source[start : start + nxt.start()] if nxt else source[start:]


def _norm(name: str) -> set[str]:
    """A table token -> {full 'schema.table', bare 'table'} lowercased, quotes off."""
    t = name.replace('"', "").lower()
    return {t, t.rsplit(".", 1)[-1]}


def migration_is_pure_create(source: str) -> bool:
    """True iff upgrade() only CREATEs new objects (+ their own RLS). Fail-closed."""
    body = _upgrade_body(source)
    if body is None:
        return False
    # SQL-content gates (scan the body WITH strings — risky verbs live in SQL).
    if _FSTRING.search(body) or _RISKY_OP.search(body) or _RISKY_SQL.search(body):
        return False

    # Call gate: strip string literals, then every remaining Python call must be
    # allow-listed (op.<safe>, sa.*, or a house RLS helper). An unknown call
    # could hide surgery inside its own body -> fail-closed to ack.
    code = _STRIP_STRINGS.sub(" ", body)
    uses_helper = False
    for obj, fn in _CALL.findall(code):
        if obj == "op":
            if fn not in _SAFE_OPS:
                return False
        elif obj in ("sa", "sqlalchemy"):
            continue  # type constructors (sa.Column, sa.Text, ...)
        elif fn in _SAFE_HELPERS:  # bare `cell_scoped_rls(` or `rls.cell_scoped_rls(`
            uses_helper = True
        else:
            return False
    if uses_helper and not _HELPER_IMPORT.search(source):
        return False  # spoof guard: helper name must come from the known module

    created: set[str] = set()
    for rx in (_CREATE_TABLE, _OP_CREATE_TABLE):
        for m in rx.finditer(body):
            created |= _norm(m.group(1))
    if not created:  # a migration that creates nothing is doing something else
        return False

    # Every literal ALTER TABLE must target a here-created table AND do only RLS.
    for m in _ALTER_TABLE.finditer(body):
        target, tail = _norm(m.group(1)), m.group(2).strip().rstrip(";").strip()
        if not (target & created) or not _RLS_ONLY.match(tail):
            return False
    # Every literal CREATE INDEX / INSERT must target a here-created table (no
    # hot-table index, no backfill into an existing table).
    for rx in (_CREATE_INDEX_ON, _INSERT_INTO):
        for m in rx.finditer(body):
            if not (_norm(m.group(1)) & created):
                return False
    return True


def _read_worktree_file(path: str) -> str | None:
    p = Path(path)
    if not p.exists():  # deleted/renamed migration -> can't verify -> ack
        return None
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def apply_migration_downgrade(matches: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Drop the db_migrations category iff every matched migration is pure-CREATE.

    Returns a note dict describing the downgrade (for the verdict), or None if
    nothing changed. Mutates ``matches`` in place.
    """
    dbm = next((m for m in matches if m["category"] == "db_migrations"), None)
    if dbm is None:
        return None
    verdicts: dict[str, bool] = {}
    for f in dbm["matched_files"]:
        src = _read_worktree_file(f)
        verdicts[f] = bool(src) and migration_is_pure_create(src)
    if verdicts and all(verdicts.values()):
        matches.remove(dbm)
        return {"category": "db_migrations", "downgraded": True, "files": verdicts}
    if any(verdicts.values()):  # mixed batch: kept ack, but record which were clean
        return {"category": "db_migrations", "downgraded": False, "files": verdicts}
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(_DEFAULT_CONFIG))
    parser.add_argument("--diff-base", default="origin/main")
    parser.add_argument("--files", nargs="*", default=None, help="Explicit file list (skips git).")
    args = parser.parse_args(argv)

    try:
        import yaml
    except ImportError:
        print("[tripwire] PyYAML required — run via `uv run --project backend python ...`", file=sys.stderr)
        return 1

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"[tripwire] config not found: {config_path}", file=sys.stderr)
        return 1
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    files = _changed_files(args)
    matches = classify(files, config)
    downgrade_note = apply_migration_downgrade(matches)  # fail-closed content check
    verdict = {
        "changed_files": len(files),
        "tripwire_matched": bool(matches),
        "decision": "pause-and-ack" if matches else "auto-merge",
        "categories": matches,
    }
    if downgrade_note is not None:
        verdict["db_migrations_content_check"] = downgrade_note
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    return 10 if matches else 0


if __name__ == "__main__":
    sys.exit(main())
