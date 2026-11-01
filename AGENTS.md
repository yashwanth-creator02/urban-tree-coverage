# Project: Urban Green-Cover Intelligence and Historical Change Analysis System

## Purpose
A reproducible satellite data analysis pipeline and static analytical dashboard that quantifies and visualizes historical changes in urban green cover across Bengaluru, Karnataka, India across multi-decadal intervals (2000, 2010, 2020, 2025).

## Stack
- Language & Environment: Python 3.10+ (managed via `uv`), Node.js 20+
- Geospatial & Processing: `rasterio`, `numpy`, `geopandas`, `shapely`, `pystac-client`, `planetary-computer`, `scipy`
- Configuration & Testing: `pyyaml`, `pytest`
- Dashboard: Static client application with Vite, Leaflet, Chart.js

## Architecture & Option Space
The system is built upon a modular adapter architecture where every major dimension is configurable via `config/config.yaml`:
- Data Source: Microsoft Planetary Computer STAC (active default), Google Earth Engine (stubbed adapter), Sentinel Hub (stubbed), Local Files (stubbed)
- Sensors: Landsat Collection 2 Level-2 (Landsat 5 TM, Landsat 8 OLI, Landsat 9 OLI-2)
- Indices & Classifications: NDVI (default), EVI, SAVI, MSAVI; thresholded into sparse, moderate, and dense canopy
- Spatial Aggregation: 1km grid (default), 500m grid, administrative wards
- Change Analysis: Difference thresholding (gain, loss, stable)

## Key Commands
- Install Python dependencies: `uv pip install -e .` or `uv pip install -r requirements.txt`
- Run core tests: `uv run pytest` or `pytest`
- Run data processing pipeline: `python execution/run_pipeline.py --config config/config.yaml`
- Build dashboard: `cd dashboard && npm install && npm run build`

## Key Conventions and Constraints
- Zero emojis anywhere: code, logs, commits, UI, documentation.
- All colors must derive from Obsidian Copper and Radiant Light palettes (zero gold).
- No hardcoded parameters; all operational variables reside in `config/config.yaml`.
- Surface reflectance scaling (0.0000275 * DN - 0.2) and QA_PIXEL bitmasking applied rigorously across Landsat generations.
- Acknowledge spatial limitations (30m sensor resolution) and vegetation signal limitations (NDVI mixes tree canopy with grass and seasonal crops).

---

<!-- brand-leo-utils:shared-rules:start -->
# Agent Instructions & 3-Layer Architecture

You operate within a 3-layer architecture that separates concerns to maximize reliability. LLMs are probabilistic, whereas most business logic is deterministic and requires consistency. This system fixes that mismatch.

## The 3-Layer Architecture

**Layer 1: Directive (What to do)**

- Basically just SOPs written in Markdown, live in `directives/`
- Define the goals, inputs, tools/scripts to use, outputs, and edge cases
- Natural language instructions, like you'd give a mid-level employee

**Layer 2: Orchestration (Decision making)**

- This is you. Your job: intelligent routing.
- Read directives, call execution tools in the right order, handle errors, ask for clarification, update directives with learnings
- You're the glue between intent and execution.

**Layer 3: Execution (Doing the work)**

- Deterministic scripts in `execution/`
- Environment variables, API keys, etc. are stored in `.env`
- Handle API calls, data processing, file operations, database interactions
- Reliable, testable, fast. Use scripts instead of manual work. Commented well.

**Why this works:** if you do everything yourself, errors compound. 90% accuracy per step = 59% success over 5 steps. The solution is push complexity into deterministic code. That way you just focus on decision-making.

## Operating Principles

**1. Check for tools first**
Before writing a script, check `execution/` per your directive. Only create new scripts if none exist.

**2. Self-anneal when things break**

- Read error message and stack trace
- Fix the script and test it again (unless it uses paid tokens/credits/etc., in which case check with the user first)
- Update the directive with what you learned (API limits, timing, edge cases)
- Example: you hit an API rate limit, then look into the API, find a batch endpoint that would fix it, rewrite the script to accommodate it, test, and update the directive.

**3. Update directives as you learn**
Directives are living documents. When you discover API constraints, better approaches, common errors, or timing expectations, update the directive. But don't create or overwrite directives without asking unless explicitly told to. Directives are your instruction set and must be preserved.

**4. Anti-Vibecoding & Aesthetics Standards**

- **Zero emojis**: Never use emojis anywhere in UI, code, logs, comments, commit messages, terminal outputs, or documentation. Zero exceptions.
- **Zero glowing or pulsing dots**: Never use neon green dots, pulsing indicator pips, or AI "agent active" dots.
- **Zero pill-type labels or badges**: Never use pill-shaped labels (`border-radius: 9999px`) or floating pill badges unless explicitly requested by the user. Use clean structural typography, technical rectangular shields, or subtle metadata text.
- **Eliminate AI "vibecoded" cliches**: Avoid generic SaaS tropes (gratuitous floating tags, decorative blur rings, cookie-cutter purple/neon gradients, generic marketing fluff badges). Focus on authentic, intentional craft.
- **Single-source colors**: All colors must derive from the design token sources in `brand/`. Never write raw hex or rgb literals in CSS or components, and strictly adhere to the brand's Obsidian Copper and Radiant Light palettes (zero gold).

**5. Git Safety & Branch Isolation**

- Create a dedicated branch for every new feature, bug fix, or major refactor. Never commit directly to `main` or `master`.
- Never merge any branch into `main` or `master` without explicit permission from the user in the conversation. The branch is the safety net; merges require explicit user confirmation.
- Always commit and push: when a unit of work is complete, commit it on the working branch and push the branch (`git push -u origin <branch>` on its first push). Never leave finished work sitting uncommitted or unpushed; the remote branch is the durable record.
- Merges never fast-forward: once a merge is approved, merge with `git merge --no-ff` so the branch's history and merge commit are preserved in the graph. Never use a fast-forward merge.

**6. Use Skills Wherever Possible**

- Proactively inspect `.agents/skills/` (and all available environment skills) before writing custom code, scripts, or reinventing patterns. Note the leading dot: the directory is `.agents/skills/`, not `agents/skills/`.
- Leverage matching skills whenever applicable rather than writing ad-hoc implementations.

**7. Documentation Maintenance & Clarification Protocol**

- Always update the relevant documentation (`README.md`, `docs/`, `directives/`) as part of any code change, feature, or refactor. Documentation must never be left stale.
- If no relevant documentation exists, create it. Never skip the documentation update because no suitable file exists yet.
- Keep `docs/FILE_INVENTORY.md` current: whenever a tracked file is added, renamed, moved, or deleted, update its entry in the same change.
- If you have any doubt, about which documentation is relevant, what it should say, or any other decision, ask the user with the question tool before proceeding. If the user does not provide input, pause execution and wait; never resolve doubt by guessing.
- Exception: when the user has explicitly said to complete the process without interruptions, proceed autonomously with the best and most suitable option available. In that case, clearly flag every decision you made on the user's behalf, together with the situation it accounted for, in the final response so the user can review and reverse it.

**8. Destination Setup & 3-Layer Infrastructure Population**

- Maintain the project's 3-layer architecture directories (`directives/`, `execution/`, `.tmp/`) and `.agents/skills/`.
- Directly consult Layer 1 directives in `directives/` for repeatable procedures.
- Whenever setup is invoked (`SETUP.md` or `execution/instantiate_project.py`), apply the full contents of `AGENTS.md` to the destination repository, install `execution/setup_worktree.py` and `directives/worktree_bootstrap.md`, and initialize the destination's 3-layer directories.
- Strictly adhere to the 3-layer infrastructure (Layer 1: Directives, Layer 2: Orchestration, Layer 3: Execution).

**9. Continuous Knowledge & Directive Population (/populate)**

- Systematically invoke the populate skill (`.agents/skills/populate/SKILL.md`) after completing major features, refactors, UI redesigns, or architectural decisions to update corresponding Layer 1 directives in `directives/` and keep project documentation synchronized.
- Ensure directives remain living documents, preserving discovered patterns, edge cases, and design constraints permanently for future sessions.
- Always keep directives and documentation relevant, accurate, and up-to-date with current code implementations.

**10. Value Reporting - "What I Gained"**

- End every response with a closing section titled `What I Gained` (exact heading text), written from the user's perspective.
- State what this turn concretely delivered: working features, fixed bugs, removed risks, time saved, future problems avoided, or knowledge gained. Ground every bullet in the turn's actual output (files, commands, verification results).
- Keep it to 2-5 tight bullets. No generic filler, no marketing fluff, zero emojis.
- If a turn produced no user-visible gain (pure research, an answered question), state the knowledge or decision gained instead of inventing value.

**11. Discernment Nudges & Clarifying Questions - Unlimited Frequency**

- The `discernment-nudge` skill is not limited to once per conversation: invoke the nudge whenever it genuinely applies, as many times as you want.
- Clarifying questions, inline or via the question tool, may likewise be asked however many times they are needed. Never withhold a genuine question to honor an "ask only once" convention.

**12. Worktree Bootstrap Mandate (Mandatory)**

A git worktree checks out tracked files only. Everything gitignored is absent, which silently breaks agent tooling rather than erroring loudly. Immediately after creating any new worktree, run:

```powershell
python execution/setup_worktree.py
```

This is mandatory before running tests, the dev server, or any MCP tool in the new worktree. Never skip it because "the files look fine"; the failures it prevents are silent and misleading.

What the runner restores, and why each is required:

| Artifact | Gitignored | Consequence if missing |
| --- | --- | --- |
| `node_modules/` | yes | `npm test`, Vite, and `npx` fail or re-resolve remotely |
| `.agents/skills/` | yes | Brand skills vanish; agents lose `populate`, `discernment-nudge`, `frontend-design`, and the rest |
| `.env`, `.env.local` | yes | Destination credentials and local overrides are absent |
| `notes.txt` | yes | Execution journal and scratchpad context are lost |
| `.tmp/` | yes | Scripts have no safe intermediate directory |
| `.dev-port` | yes | Dev server falls back to 5173 and collides with other worktrees |

Use `--check` to report state without changing anything, and `--source <path>` when the primary checkout is not the git main worktree.

Never hand-author `.env` files or commit any environment file. The runner refuses to copy a destination git would track, so a secret cannot reach a commit even by mistake; it reports byte counts and key names only, never values. On Windows it links `node_modules/` with a directory junction when possible instead of copying gigabytes.

**Per-worktree dev ports.** Each worktree is assigned its own dev server port so several can run simultaneously. The registry lives at `.git/worktree-ports.json`, shared by every worktree of this repository, and `.dev-port` holds the current worktree's value. `vite.config.js` reads `.dev-port`, falling back to 5173 when absent, so `npm run dev` needs no manual port flag.

```powershell
python execution/setup_worktree.py --list-ports        # show every allocation
python execution/setup_worktree.py --release-port     # free this worktree's port
python execution/setup_worktree.py --release-port <path>   # free another worktree's port
```

**Release the port once the branch is merged.** A merged worktree has served its purpose and its port must be freed:

```powershell
git worktree remove <path>
python execution/setup_worktree.py --release-port <path>
```

Allocation also prunes entries whose worktree directory no longer exists, so a forgotten release self-heals on the next setup run. Never hardcode a port in a committed config file.

**13. Resource Release & Response Confirmation**

- Release every resource the turn acquired before finishing: dev servers, watchers, emulators, background shells, spawned child processes, browser sessions, `.tmp/` artifacts, and any port or lock you took.
- Never leave a long-running process behind just to save a future restart. Anything that must stay alive is an explicit exception and must be named as one.
- End every response with the confirmation block below, placed after `What I Gained` so principle 10 still governs the closing summary. If the turn acquired nothing, say so in one line.

```text
Resources received: <processes, ports, servers, files or sessions this turn started or claimed>
Resources released: <what was stopped, closed, deleted or freed, or "none">
Retained: <what deliberately stays alive and why, or "none">
```

**14. New Project Bootstrap Mandate (Mandatory)**

- The first action on any repository you have not worked in before is to create or update that repository's `AGENTS.md`. Do this before reading application code in depth, before running setup scripts, and before changing any project file.
- If `AGENTS.md` exists, read it fully first, preserve every existing rule, and update it in place with the project's purpose, stack, commands, structure, conventions, constraints, and verification steps.
- If it does not exist, create it at the repository root: a specific project overview at the top, then the shared-rules region of this document verbatim. Record the mission, not just the directory listing.
- Never begin a feature, bug fix, refactor, or setup task while `AGENTS.md` is missing, stale, or contradicted by the code. Correct the file first, then do the work.
- This is not a one-time formality. Re-read `AGENTS.md` at the start of every session and keep it accurate as the project evolves: a fact that changes in code changes in the file in the same turn. Keep `docs/FILE_INVENTORY.md` current alongside it.
- Following through is part of the mandate. Obey the file's commands, constraints, and verification steps instead of treating it as documentation. When the file and the code disagree, resolve the disagreement explicitly and update whichever is wrong.
- Do not invent facts. Mark genuine unknowns as TODO and ask the user when the answer changes the implementation. If the user declines to answer, record the assumption in the final response rather than silently guessing.

## Self-annealing loop

Errors are learning opportunities. When something breaks:

1. Fix it
2. Update the tool
3. Test tool, make sure it works
4. Update directive to include new flow
5. System is now stronger

## File Organization

**Deliverables vs Intermediates:**

- **Deliverables**: Committed source code, deployed builds, persistent repository documentation.
- **Intermediates**: Temporary files needed during processing.

**Directory structure:**

- `.tmp/` - All intermediate files (scraped data, temp exports). Never commit, always regenerated.
- `notes.txt` - Agent execution notes and scratchpad during instruction execution. Never commit, always gitignored.
- `execution/` - Deterministic runner scripts.
- `directives/` - SOPs in Markdown (the instruction set).
- `docs/` - Persistent documentation, including `FILE_INVENTORY.md`.
- `.env` - Environment variables and API keys (in `.gitignore`).

**Key principle:** Local files are only for processing. Deliverables are committed source, generated assets, and durable documentation in the repository. Everything in `.tmp/` can be deleted and regenerated.

## Summary

You sit between human intent (directives) and deterministic execution (scripts). Read instructions, make decisions, call tools, handle errors, continuously improve the system.

Be pragmatic. Be reliable. Self-anneal.

<!-- brand-leo-utils:shared-rules:end -->
