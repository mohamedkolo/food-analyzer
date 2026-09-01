---
name: find-skills
description: Search for, preview, and install agent skills from the public registry using the `skills` CLI. Use when the task needs a capability no installed skill covers, when the user asks to find/search/install/update/remove a skill, mentions `npx skills`, skills.sh, a `owner/repo` skill package, or asks "is there a skill for X?". Also use to list what is already installed before assuming a capability is missing.
---

# Finding and installing skills

A skill is a folder containing `SKILL.md` (plus optional helper files) that gives an
agent ready-made instructions for one kind of task. The `skills` CLI manages them.

## Before searching: check what is already installed

Do not install a duplicate. Check first:

```bash
npx skills list            # project-level skills
npx skills list --global   # user-level skills
```

Project skills live in `.claude/skills/<name>/SKILL.md`. Other agents use
`.codex/skills`, `.cursor/skills`, `.gemini/skills`, `.opencode/skills`.

## Search the registry

```bash
npx skills find "<query>"                    # e.g. "pdf forms", "terraform review"
npx skills find "<query>" --owner vercel-labs   # restrict to one GitHub owner
```

`find` is interactive by design. When running unattended, prefer `add -l` against a
known repo (below) over trying to drive the picker.

## Inspect before installing

Never install blind — list what a repo actually contains, then read the `SKILL.md`
of anything you install:

```bash
npx skills add <owner>/<repo> -l    # list skills in the repo, install nothing
```

To borrow one skill's instructions for a single task without installing it:

```bash
npx skills use <owner>/<repo>@<skill-name>
```

## Install

```bash
npx skills add <owner>/<repo>                      # interactive picker
npx skills add <owner>/<repo> -s <skill> -a claude-code -y   # one skill, this agent, no prompts
npx skills add <owner>/<repo> --all                # every skill, every agent, implies -y
npx skills add <owner>/<repo> -g                   # user-level instead of project-level
npx skills add <owner>/<repo> --copy               # copy files instead of symlinking
```

The CLI detects an agent context and switches to non-interactive mode on its own, but
pass `-y` explicitly when scripting. Accepts `owner/repo`, a full
`https://github.com/owner/repo` URL, or a GitLab URL.

Default is **project-level** (committed with the repo, shared with the team). Use
`-g` only for something personal to one machine.

## Maintain

```bash
npx skills update              # update all
npx skills update <skill>      # update one
npx skills remove <skill>      # remove one
npx skills remove --all        # remove everything (implies -y)
```

## Author a new skill

When no registry skill fits, write one instead of installing a near-miss:

```bash
npx skills init <name>    # scaffolds <name>/SKILL.md
```

Keep the frontmatter `description` trigger-rich — it is the only part the agent reads
when deciding whether to load the skill, so name the concrete words a user would say.

## Restoring on a fresh checkout

```bash
npx skills experimental_install   # restore from skills-lock.json
npx skills experimental_sync      # sync node_modules skills into agent dirs
```

## Network requirements

Every command here except `list` needs outbound HTTPS to:

| Host | Used for |
|---|---|
| `skills.sh` | registry search + download (`$SKILLS_API_URL`, `$SKILLS_DOWNLOAD_URL`) |
| `github.com`, `api.github.com`, `raw.githubusercontent.com` | clone / tree listing fallback |
| `registry.npmjs.org` | fetching the CLI itself via `npx` |

### Diagnosing failures

`Failed to clone repository — Authentication failed` is **misleading**: it is what a
blocked or scope-restricted network looks like, not necessarily a credentials problem.
Distinguish the two before acting:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' -m 20 https://skills.sh
```

- **`403` / `CONNECT tunnel failed, response 403`** — an egress policy is blocking the
  host. This is common in sandboxed or CI environments. Do not retry, and do not
  disable TLS verification or unset `HTTPS_PROXY` to route around it. Report the
  blocked host and install from an unrestricted machine instead, then commit the
  resulting `.claude/skills/` files so the skill ships with the repo.
- **`200`** — the network is fine; it really is an access problem. Check
  `gh auth status -h github.com`, or retry over SSH:
  `npx skills add git@github.com:<owner>/<repo>.git`.

In a Claude Code web session, git credentials are scoped to the repositories attached
to that session, so a skill repo owned by a different GitHub owner is unreachable even
when the repo is public.
