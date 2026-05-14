# Checklist — DS tokens audit (designer)

**Used by:** Workflow 3 (DS token-change request) — perform before approving any change к
`_meta/ui/design-tokens.md`. Block change if any P0 item fails.

---

## A. Change classification (P0)

- [ ] **A1.** Change type identified: **additive** / **modifying** / **removing**
- [ ] **A2.** Affected tokens enumerated (list specific token names — не "spacing tokens" в общем)
- [ ] **A3.** Affected semantic roles enumerated (e.g. `--bg-page`, `--text-secondary`)
- [ ] **A4.** Rationale documented (1-2 sentences — почему need exists, что existing tokens не cover)

---

## B. Blast radius assessment (P0)

- [ ] **B1.** Token category identified (color / spacing / type / radius / shadow / motion / z-index)
- [ ] **B2.** Blast level assigned per UI-DESIGN-PLAYBOOK §2.3:
   - High: color / type
   - Medium: spacing
   - Low: radius / shadow / motion / z-index
- [ ] **B3.** Affected surfaces estimated (grep frontend/src/features для current token usage)
- [ ] **B4.** Validation strategy noted:
   - High blast → visual regression (Storybook Wave 1+, manual visual check Wave 0)
   - Medium → layout-shift check (selected pages)
   - Low → cosmetic acceptance

---

## C. Route gating (P0)

### Additive route (designer LGTM solo)

- [ ] **C1a.** New token name follows convention (`--<category>-<role>`, e.g. `--bg-muted`, `--color-primary-450`)
- [ ] **C2a.** New token aliases to existing scale value OR semantic role (no raw new hex unless approved scale extension)
- [ ] **C3a.** No semantic role collision (new role doesn't overlap с existing `--text-secondary`)
- [ ] **C4a.** Dark + light mode both have mappings (для semantic role tokens в §2.4 table)
- [ ] **C5a.** §12 change log entry drafted (version bump 0.X.Y patch)
- [ ] **C6a.** Memory.md DS Decisions entry drafted

### Modifying route (architect consult required)

- [ ] **C1m.** Architect consult event emitted (`tech.oriion.conflict.escalation.v1` `conflict_type: ds-modifying-change`)
- [ ] **C2m.** Architect verdict received: approve / reject / escalate-to-founder
- [ ] **C3m.** Если approve — migration playbook drafted (которые surfaces affected, how to migrate)
- [ ] **C4m.** Frontend-implementer notified via `tech.oriion.design.tokens_patch.v1` с migration_notes
- [ ] **C5m.** Potential ADR-001 revision identified (если semantic shift Wave-level)
- [ ] **C6m.** §12 change log entry drafted (version bump 0.X.0 minor)

### Removing route (deprecation cycle)

- [ ] **C1r.** Removal motivation documented (replaced by newer token? superseded by semantic shift?)
- [ ] **C2r.** Deprecation marker added в design-tokens.md table: `// @deprecated since: <wave> remove: <wave-N+1>`
- [ ] **C3r.** Replacement token identified (every deprecated token MUST have replacement OR explicit removal justification)
- [ ] **C4r.** Migration deadline set (1 wave grace period minimum)
- [ ] **C5r.** Existing usage audit triggered (grep frontend/src + flag к reviewer-frontend)
- [ ] **C6r.** Removal PR scheduled на subsequent wave
- [ ] **C7r.** §12 change log entry с "Deprecated X — remove Y"

---

## D. Output artifacts (P0)

- [ ] **D1.** `design-tokens.md` patch drafted (markdown delta)
- [ ] **D2.** Memory.md DS Decisions entry includes: decision, rationale, blast assessment, route taken
- [ ] **D3.** Handoff envelope `tech.oriion.design.tokens_patch.v1` includes:
   - `patch_type`: additive / modifying / removing
   - `tokens_diff`: markdown delta
   - `migration_notes` (if modifying/removing)
   - `reviewer_co_sign_required: reviewer-frontend`
   - `architect_consult_required: <bool>`

---

## E. Outcomes (verdict)

### ✅ Approve change (additive route)
- All P0 items C1a-C6a passed
- Emit `tech.oriion.design.tokens_patch.v1` к reviewer-frontend для co-sign
- Frontend-implementer materializes в `frontend/src/styles/tokens.css` (Phase 00.7 deliverable)

### 🤝 Request architect consult (modifying route)
- C1m-C2m engaged
- Wait architect verdict ДО proceeding с C3m-C6m

### ⏳ Initiate deprecation cycle (removing route)
- C1r-C7r executed
- Deprecation grace period 1 wave (minimum)
- Removal PR на subsequent wave

### 🔄 Reject change
- Rationale insufficient (A4 failed)
- Blast assessment indicates breaking change без migration plan
- Existing token already covers the need (proposer didn't survey)
- Return rejection с justification к requester

---

## Quick reference

```bash
# Find existing token usage в frontend
grep -rE "var\(--<token-name>" frontend/src --include="*.tsx" --include="*.css"

# Find existing usage в design-tokens.md (cross-reference)
grep -n "<token-name>" .planning/_meta/ui/design-tokens.md
```

---

## References

- `.claude/agents/designer/workflows.md` Workflow 3
- `.planning/_meta/ui/UI-DESIGN-PLAYBOOK.md` §2.2 (change-arbiter protocol) + §2.3 (blast radius)
- `.planning/_meta/ui/design-tokens.md` (target file)
- `.claude/agents/designer/memory.md` (DS Decisions log destination)
