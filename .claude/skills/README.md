# Vendored skills

Founder's personal skills, copied into the repo so that **cloud sessions** (claude.ai/code,
scheduled runs, `/autonomy:run` in the cloud) see them. Locally they also live in
`~/.claude/skills/`; in the cloud that directory does not exist, so without this copy the
agents would silently lose them.

`.claude/skills/<name>/SKILL.md` is the only layout Claude Code auto-discovers: each skill's
`name` + `description` is loaded into every session's context, and the skill is invocable via
the Skill tool or `/<name>`. Anything outside this path is invisible unless something explicitly
points an agent at it.

## What is here (19 skills)

| Source | Skills |
|---|---|
| `matt-pocock-skills` (flattened) | `caveman` · `diagnose` · `find-skills` · `grill-me` · `grill-with-docs` · `improve-codebase-architecture` · `tdd` · `to-issues` · `to-prd` · `triage` · `write-a-skill` · `zoom-out` |
| `Skills HYP` (flattened) | `startup-analyst` · `startup-reporter` · `startup-researcher` · `startup-validator` |
| standalone | `ui-ux-pro-max` · `graphify` · `skill-builder` |

The collections were **flattened** — `.claude/skills/grill-me/SKILL.md`, not
`.claude/skills/matt-pocock-skills/grill-me/SKILL.md` — because discovery does not recurse into
nested collection directories.

## What was deliberately left out

The ~22 claude-flow / RuFlo bundle skills in `~/.claude/skills/` (`agentdb-*`, `v3-*`,
`sparc-*`, `swarm-*`, `reasoningbank-*`, `github-*`, `hooks-automation`, `stream-chain`,
`pair-programming`, `verification-quality`, `browser`). They drive the `claude-flow` CLI, which
this project does not use; vendoring them would put 22 skills in front of every cloud agent
offering commands that do not exist here.

`setup-matt-pocock-skills` was also dropped — it is an installer for the very skills already
vendored here, and running it in the repo would be a no-op at best.

## Wave-2 relevance

- `ui-ux-pro-max` — the redesign phase (02.2, ADR-042) and its DS v0.3 work.
- `grill-me` / `to-prd` / `zoom-out` — turning seed-specs into full specs at the
  `/autonomy:discuss` step.
- `tdd` / `diagnose` / `improve-codebase-architecture` — 02.1-retro, incl. the
  `dispatch.py` 1073→≤500-line split.

## Updating

These are **copies, not symlinks** — editing `~/.claude/skills/` does not update them.
Re-copy the changed skill and commit. Keep `name:` in the frontmatter a kebab-case slug that
matches the directory (`skill-builder`'s upstream `name: "Skill Builder"` was normalised here).
