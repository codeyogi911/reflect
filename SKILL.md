---
name: self-improving-agents
description: >
  Scaffold a self-improving agentic harness into any project. Creates
  orchestrator, builder, verifier, e2e-tester, researcher, and session-analyzer
  agents with iterative build loops, two-gate verification, gap tracking, and
  Entire.io-driven learning. Use when: user asks to set up self-improving agents,
  create an agent harness, add build loops, scaffold agent infrastructure, wants
  agents that learn from session transcripts, or wants an iterative
  build-verify-test workflow. Also trigger when user mentions "build loop",
  "agent harness", "self-improving", or wants to add structured agent
  coordination to their project.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, WebSearch, WebFetch
metadata:
  author: shashwatjain
  version: '5.0'
---

# Self-Improving Agents Harness

You are scaffolding a self-improving agentic harness into the user's project.
The harness runs iterative build loops — agents build, verify, test, and
improve, learning from each cycle and getting better across sessions.

If $ARGUMENTS is provided, use it as the initial goal.
If empty, scaffold in generic mode and ask the user for their goal afterward.

---

## Step 1: Deep Project Analysis

Don't just detect the stack — understand the project. The agents you create
should feel like they were written by someone who knows this codebase.

1. Read `CLAUDE.md` if it exists — understand project conventions
2. Detect stack by checking for: `package.json`, `pyproject.toml`, `Cargo.toml`,
   `go.mod`, `Gemfile`, `pom.xml`, `Makefile`
3. **Study the codebase** — this is what makes agents effective from day 1:
   - Scan directory structure with `ls` and `Glob`
   - Read 2-3 representative source files to understand code style, patterns,
     naming conventions, and architecture
   - Check test files: how are tests structured? What patterns do they follow?
     What test utilities exist?
   - Check for e2e test setup (Playwright, Cypress, Selenium, etc.)
   - Look at recent git history: what kind of changes are typical?
   - Note any CI/CD config (.github/workflows, .gitlab-ci.yml, etc.)
4. **Build a project profile** — you'll use this to customize every agent:
   - Language, framework, test runner, package manager, linter
   - Directory conventions (where does new code go? where do tests live?)
   - Key patterns (how are API routes defined? how is state managed? ORM?)
   - E2E framework or "none"
   - Common pitfalls visible from the code (e.g., complex build steps,
     environment-dependent tests, monorepo structure)
   - **Project type**: what kind of project is this? (see Agent Selection below)

### Agent Selection

Not every project needs all 5 agents. Decide which agents to create based on
what the project actually is:

**Always create:**
- **orchestrator** — every harness needs coordination
- **builder** — every project has code to write
- **verifier** — every project benefits from review
- **session-analyzer** — mines Entire session transcripts for agent improvement

**Create only if relevant:**
- **e2e-tester** — only if the project has user-facing surfaces:
  - YES: web apps, APIs with endpoints, mobile apps, desktop apps, CLIs with
    interactive flows
  - NO: libraries, skills/plugins, config-only repos, documentation, pure
    data pipelines, markdown-only projects
- **researcher** — only if the project involves external dependencies or
  complex domains:
  - YES: apps using external APIs, projects with multiple frameworks,
    unfamiliar tech stacks, large codebases
  - NO: small single-file utilities, projects where everything is self-contained
**Consider creating project-specific agents** when the project has a clear
specialized need that none of the standard agents cover. Examples:
- **api-tester** for API-only projects (replaces e2e-tester with focused API
  contract testing)
- **migrator** for projects doing a major migration
- **docs-reviewer** for documentation-heavy projects
- **skill-evaluator** for Claude Code skill projects

Use the templates as a starting point, but adapt the role and instructions to
match the actual need. Give custom agents the same structure: Process section,
Output format, `## Project-Specific Rules`.

### Detect Existing Harness

5. Scan `.claude/` directory thoroughly:
   - `ls .claude/` and `ls .claude/agents/` if they exist
   - Check for symlinks (`ls -la .claude/`) — some projects link to external
     agent directories
   - Read each existing agent file to understand its purpose, format, and
     any knowledge it has accumulated

6. Classify into one of these scenarios:

   **A. Fresh project** — no `.claude/agents/` directory, or it exists but
   is empty (settings files don't count)
   → Full scaffolding with deep customization (Steps 2-5)

   **B. Our harness already installed** — `.claude/agents/` has files matching
   our structure (`## Project-Specific Rules` sections)
   → **Upgrade**: preserve all accumulated knowledge, refresh core instructions

   **C. Different agents exist** — `.claude/agents/` has agent files that
   don't match our templates (different structure, YAML format, or different
   names like `cap-developer.md`, `michael.md`)
   → **Fuse**: merge the best of both (see Fusion Protocol below)

   **D. External orchestration** — `.claude/` has symlinks to external agent
   directories, OR `config.yaml`/`AGENTS.md` registries indicating a
   higher-level orchestration system
   → **ESCALATE** to user with what you found. Ask whether to add alongside
   or skip.

7. Check for existing state files:
   - If `gaps.md` exists → **do NOT overwrite**
   - If `progress.md` exists → **do NOT overwrite**
   - If `run-journal.md` or similar tracking exists → note it, don't touch it

---

## Step 2: Create Directory Structure

```bash
mkdir -p .claude/agents
```

---

## Step 2.5: Configure Entire Telemetry

Entire.io captures session transcripts into checkpoint branches — this is how
agents learn. It is required for the self-improvement loop.

1. Run `which entire` or check if `~/.local/bin/entire` exists
2. If NOT found → tell the user: "Entire.io CLI is required for session-based
   agent learning. Install it from https://entire.io and re-run." Stop here.
3. If found → **ask the user**: "Entire.io detected. Ready to configure session
   telemetry for this project?"
4. If user says **yes**:
   a. Check if `.entire/settings.json` already exists → skip configuration,
      Entire is already set up
   b. If not configured: run `entire configure --agent claude-code --telemetry=false`
   c. Verify `.claude/settings.json` has the deny permission:
      `Read(./.entire/metadata/**)`
      - If `permissions.deny` array exists, append to it if missing
      - If not, create the deny array with this entry
   d. Add `.entire/` to `.gitignore` if not already present
5. If user says **no** → explain that Entire is needed for agent learning and
   ask if they'd like to proceed without the self-improvement loop

Do NOT modify existing hooks or MCP servers in settings.json — only ADD the
Entire hooks if they are missing.

---

## Step 3: Write Agent Files

**Only create agents selected in Step 1.** The templates in `templates/` are
starting points, not finished products. Read each relevant template, then
customize it with real knowledge from the project analysis. If you decided to
create a custom agent (api-tester, skill-evaluator, etc.), use the closest
template as a base and adapt the role.

The skill's templates directory is at the same path as this SKILL.md file,
under `templates/`. Read each template file listed below.

### Scenario A — Fresh: Customize for This Project

For each **selected** agent, read the template from `templates/{agent}.md`,
then tailor it:

**orchestrator.md** — Add to Startup Protocol:
- The project's directory layout and where key code lives
- Available test commands and how to run them
- Any CI checks that must pass

**builder.md** — Customize the Process section with project specifics:
- Which test runner to use and the exact command (e.g., `pytest -xvs`, `npm test`)
- Which linter to run and the exact command (e.g., `npx eslint .`, `ruff check`)
- Where new code should go (directory conventions)
- Patterns to follow (e.g., "API routes go in `src/routes/`, each with a
  corresponding test in `tests/routes/`")
- Any build steps required before testing

**verifier.md** — Add project-relevant checks to Gate 2:
- Framework-specific concerns (e.g., "check for N+1 queries in Django ORM",
  "verify React hooks follow rules-of-hooks")
- Security patterns specific to this stack
- Test coverage expectations if the project has coverage tooling

**e2e-tester.md** — Configure for the project's test infrastructure:
- Which e2e framework is installed, where tests live, how to run them
- Key user flows in this application
- Test environment setup (dev server command, seed data)

**researcher.md** — Add project context:
- Key dependencies and where their docs live
- Architecture decisions visible in the code
- Where to look first for different types of questions

### Scenario B — Upgrade: Refresh Core, Keep Knowledge

For each of our 5 agents:
1. Read the existing `.claude/agents/{agent}.md`
2. Extract everything under `## Project-Specific Rules`
3. Also extract any project-specific customizations that were added to core
   sections (test commands, directory conventions, framework checks, etc.)
4. Read the latest template from `templates/{agent}.md`
5. Write the new template, re-applying ALL extracted customizations and rules
6. Do NOT touch custom agent files that aren't part of our standard 5

### Scenario C — Fuse: Best of Both Worlds

When the project has agents that overlap with ours, the goal is to create a
unified agent that combines:
- **Their project knowledge**: custom instructions, conventions, domain expertise,
  accumulated learnings — things that took real sessions to figure out
- **Our structured workflow**: the build loop, output formats, retry protocol,
  two-gate verification, Entire-driven self-improvement system

**Fusion process for each overlapping agent:**

1. Read their existing agent file completely
2. Read our template for the same role
3. Identify what each brings:
   - **Theirs**: project-specific instructions, custom checks, domain knowledge,
     accumulated learnings, tool preferences, naming conventions
   - **Ours**: structured output format, retry protocol, self-improvement
     sections (Project-Specific Rules + Learnings), state machine integration
4. Write a fused agent that:
   - Keeps their core instructions and project knowledge as the foundation
   - Adds our structured sections: Output format, On Retry (builder), Gates
     (verifier), failure classification (e2e-tester)
   - Adds `## Project-Specific Rules` section for the self-improvement system
   - Integrates with the orchestrator's state machine (uses our status codes:
     COMPLETE, NEEDS_CLARIFICATION, BLOCKED, APPROVED, CHANGES_REQUIRED, etc.)
5. Tell the user what you fused and what each side contributed

**For agents with no overlap** (custom agents like `deployer.md`, `michael.md`):
- Don't touch them
- Add `## Project-Specific Rules` section to them so they can participate
  in the self-improvement system
- Register them in the orchestrator's Startup Protocol

**For our agents with no collision** (e.g., project has no verifier):
- Write our template with full customization (same as Scenario A)

### Agent templates:

| Template | When to create | Purpose |
|----------|---------------|---------|
| `templates/orchestrator.md` | Always | Coordinates build loops, dispatches to other agents |
| `templates/builder.md` | Always | Writes code, runs tests, reports changes |
| `templates/verifier.md` | Always | Two-gate review: spec compliance then code quality |
| `templates/e2e-tester.md` | If project has user-facing surfaces | End-to-end testing, failure classification |
| `templates/researcher.md` | If complex deps or large codebase | Pre-build investigation of APIs, patterns, docs |
| `templates/session-analyzer.md` | Always | Mines Entire session transcripts for data-driven agent improvement |

---

## Step 4: Write State Files

### `.claude/gaps.md`

**Skip if `.claude/gaps.md` already exists** — it contains cross-session state.

Read `templates/gaps.md` and write to `.claude/gaps.md`.

### `.claude/progress.md`

**Skip if `.claude/progress.md` already exists** — it contains cross-session state.

Read `templates/progress.md` and write to `.claude/progress.md`.

---

## Step 5: Update CLAUDE.md

Append the following section to CLAUDE.md. Create the file if it doesn't exist.
**If a "Self-Improving Agent Harness" section already exists, update it rather
than duplicating it.**

Adapt the template below — list only the agents you actually created:

```markdown

## Self-Improving Agent Harness

Agents in `.claude/agents/`: [list the agents you created].
State files: `.claude/gaps.md` (blockers/decisions), `.claude/progress.md` (task tracking).

### Usage
- Start a build loop: "Use the orchestrator to build [goal]"
- Continue where you left off: "Use the orchestrator to continue"
- Evolve agents from session data: "Evolve the agents"
- Analyze past sessions: "Analyze session history"
- Check open blockers: "Read .claude/gaps.md"
- Check progress: "Read .claude/progress.md"

### How It Works
1. Orchestrator reads agent rules + state files, then decomposes goal into tasks
2. Each task cycles: RESEARCH? → BUILD → VERIFY → TEST with up to 3 retries
3. After 3 failures on a task, the orchestrator escalates to you with options
4. Entire captures full session transcripts into checkpoint branches
5. After each build loop, the EVOLVE phase mines session transcripts and bakes improvements into agent instructions
6. Gaps and progress persist across sessions — the harness picks up where it left off
```

---

## Step 6: Report to User

1. List every file created, updated, fused, or skipped — with one-line explanation
2. For fused agents: explain what each side contributed
3. Highlight project-specific customizations applied (test commands, directory
   conventions, framework checks)
4. Show usage examples:
   - `Use the orchestrator to build [goal]`
   - `Use the orchestrator to continue`
   - `Evolve the agents` (mine session transcripts and bake improvements into agents)
   - `Read .claude/gaps.md`
5. If $ARGUMENTS was provided: "Ready to start the first build loop with goal: **$ARGUMENTS**?"
6. If $ARGUMENTS was empty: "What would you like the agents to build?"
7. Confirm Entire is configured and session telemetry is active
