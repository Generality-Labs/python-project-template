# python-project-template

A [Copier](https://copier.readthedocs.io/) template for Generality Labs Python
projects, plus the shared reusable CI workflow they all call. It encodes one
standard so the repos don't drift:

- **uv** for dependency management (`uv sync`, `uv run`), pinned Python via
  `.python-version`
- **uv_build** build backend for libraries, with the version set once in
  `pyproject.toml` and bumped by `uv version`; apps stay `package = false`
- **pre-commit** stack: ruff (lint + format), [zizmor](https://docs.zizmor.sh/)
  (Actions security), mdformat, optionally typos — plus
  **[basedpyright](https://docs.basedpyright.com/)** (always) and **pytest**
- Shared **`python-ci`** reusable workflow (`uv sync` → basedpyright → pytest →
  pre-commit), so every repo's CI is a three-line caller
- Optional TypeScript/JavaScript side: **Biome** (lint + format) in the
  pre-commit stack, plus a shared **`node-ci`** workflow for type-check and
  build
- **Keep a Changelog** `CHANGELOG.md`, written from per-PR fragments in
  `changelog.d/` by [scriv](https://scriv.readthedocs.io/), so concurrent PRs
  never conflict on it; libraries also get PyPI trusted publishing
  (`publish.yml` + `RELEASING.md`)
- A Claude Code `SessionStart` hook that pre-warms the toolchain. With a
  frontend it also points corepack at `registry.npmjs.org`, since some sandbox
  egress proxies block `repo.yarnpkg.com` and corepack then fails before Yarn or
  pnpm starts — which leaves the frontend impossible to install, build or
  type-check. Plain npm ignores the setting.

## Scaffold a new project

```bash
uvx copier copy gh:Generality-Labs/python-project-template my-new-project
```

You'll be asked for the name, description, whether it's an app or a library,
Python version, whether to enable a coverage gate, whether the project has a
TypeScript/JavaScript frontend, whether to run the typos spell-checker, whether to
open template-update PRs automatically, and whether to manage repo settings
and a branch ruleset from files (off by default).

### Turning off `typos`

Answer no to `use_typos` and the hook is left out of the generated
`.pre-commit-config.yaml`. Worth doing for projects whose vocabulary the
checker doesn't know — medical, legal or scientific terms, non-English proper
nouns — or that commit generated data such as serialised fixtures and
extraction output.

Note the hook is configured **report-only**, with `args: [--force-exclude]`.
Its own defaults are `[--write-changes, --force-exclude]`, which edit files
rather than reporting: on the wrong corpus that means silent, incorrect
rewrites. In one repo it renamed `Miliary` (as in miliary tuberculosis) to
`Military`, `PASH` to `HASH`, and every `...Ser` serializer class to `...Set`,
alongside ~900 edits inside hex digests — all committed before anyone noticed.
A spelling correction should need a human to approve it, so the template drops
`--write-changes`. Add it back per-project if you want the autofix.

## Update an existing project when the template changes

From inside a project that was generated from this template (it has a
`.copier-answers.yml`):

```bash
uvx copier update --trust
```

`--trust` lets the template run its migrations, such as the one in 1.10.0 that keeps a library's version when its version moves into `pyproject.toml`. Without it, an update that crosses a migration stops and changes nothing.

Copier does a 3-way merge between the old template output, the new output, and
your local edits — so you get template improvements without losing your
customizations.

## The reusable CI workflow

Generated projects call
[`.github/workflows/python-ci.yml`](.github/workflows/python-ci.yml) rather than
duplicating CI. To bump CI for every repo at once, change it here and move the
`v1` tag.

```yaml
jobs:
  ci:
    uses: Generality-Labs/python-project-template/.github/workflows/python-ci.yml@v1
    with:
      python-version: "3.12"
```

### The TypeScript side

Answer yes to `use_frontend` and the scaffold also gets `biome.json`, a Biome
hook in the pre-commit stack, and a second CI job calling
[`node-ci.yml`](.github/workflows/node-ci.yml):

```yaml
  frontend:
    uses: Generality-Labs/python-project-template/.github/workflows/node-ci.yml@v1
    with:
      working-directory: "frontend"
```

`working-directory` is the point of the input: it defaults to the repo root
for a standalone package, and takes a subdirectory for a hybrid repo (a Django
app at the root with a Vite frontend under `frontend/`). `node-ci` also accepts
`node-version`, `package-manager` (yarn/npm/pnpm — it runs `corepack enable`,
so Yarn Berry and pnpm pin themselves through `packageManager` in
package.json), and `run-build`.

Note what `node-ci` does *not* do: lint and format. Biome runs as a pre-commit
hook, and `python-ci` already runs the whole pre-commit stack, so a hybrid repo
gets TS lint/format without paying for a second Node job. `node-ci` covers only
the parts that need the project's own dependencies installed.

`biome.json` excludes `.yarn`. Yarn Berry projects commit `.yarn/sdks` and
`.yarn/releases` (their `.gitignore` un-ignores them), so `useIgnoreFile`
alone doesn't keep Biome out of Yarn's own vendored code — without the
exclusion it reformats those files. Add your own exclusions there for any
generated data the project commits, such as serialised test fixtures.

Two smaller details in the generated config. The rule preset is spelled
`"preset": "recommended"` rather than `"recommended": true`, which Biome 2.5.5
deprecates. And a frontend scaffold excludes `tsconfig*.json` from the
`check-json` pre-commit hook: TypeScript has always allowed comments in
tsconfig, and Biome parses it as JSONC, but `check-json` uses Python's stdlib
`json` module and fails on them.

Biome is chosen for the same reason as ruff on the Python side — one fast Rust
binary doing both jobs, one config file, no plugin ecosystem to keep in sync.

Biome v2 added [type-aware
linting](https://biomejs.dev/blog/biome-v2/) using its own inference, so the
rules that used to require typescript-eslint no longer do. `noFloatingPromises`
works without a `tsconfig` or a type-checker in the loop — verified against
2.5.5. Those rules are still in the `nursery` group, so they aren't on by
default and have to be named:

```json
"linter": { "rules": { "nursery": { "noFloatingPromises": "error" } } }
```

The template leaves them off: nursery rules are explicitly unstable and may
change between releases. Turn them on per-project when you want them, and keep
`tsc --noEmit` under `strict` as the backstop either way — Biome's inference is
newer and less complete than a full type-checker's.

## The reusable release workflows

Generated projects release through two reusable workflows here, called from thin scaffolded callers pinned to `@v1`:

- [`prepare-release.yml`](.github/workflows/prepare-release.yml), run from the project's Actions tab, bumps the version, collects `changelog.d/` into `CHANGELOG.md`, and opens a "Release vX.Y.Z" pull request.
- [`release-on-merge.yml`](.github/workflows/release-on-merge.yml), on that pull request's merge, tags the merge commit, creates the GitHub release, and can start another workflow on the tag. Generated PyPI libraries pass `dispatch-workflow: publish.yml`.

Both take `version-source`: `pyproject` for generated projects, where the version is `[project] version`, or `tags`, where it comes from the latest `vX.Y.Z` tag. Publishing stays in each project's own `publish.yml`, because PyPI trusted publishing can't run from a reusable workflow. The callers grant the permissions; the reusable workflows declare none of their own.

## Repo settings as code

GitHub keeps repository settings and rulesets in the UI and API rather than in
files, so the scaffold can ship the files *and* the thing that applies them.
This is **opt-in**: answer yes to `use_repo_settings` (default no). Nothing
changes on GitHub until someone runs the script, but the default is off so a
`copier update` never drops the files, or the invitation to run them, into a
downstream repo that didn't ask. An existing project opts in by setting
`use_repo_settings: true` in `.copier-answers.yml` and running `copier update`.

- `.github/repo-settings.json` is sent verbatim as the body of
  `PATCH /repos/{owner}/{repo}`, so any key [that endpoint
  accepts](https://docs.github.com/rest/repos/repos#update-a-repository) can be
  managed there: merge methods, `has_wiki` / `has_projects`, and notably
  `delete_branch_on_merge: true` (stacked PRs only retarget when merged base
  branches are deleted). If a key turns out to be plan-gated for a repo the
  whole PATCH 403s; remove the key and re-run.
- `.github/rulesets/*.json` are rulesets in the exact shape the GitHub UI
  imports and exports (Settings -> Rules -> Rulesets), so they round-trip
  through the dashboard.
- `scripts/setup_repo.py` (standard library only; needs `gh` authenticated
  as a repo admin) applies both. It first fetches what the repo has now and
  prints the difference: settings keys whose value would change, and a unified
  diff of each ruleset against GitHub's copy, projected onto the keys the file
  sets so ids, timestamps and GitHub's filled-in defaults never show as
  changes. Nothing is applied until you confirm; `--dry-run` only shows,
  `--yes` skips the prompt (and is required when not run from a terminal).
  Re-runs are safe: unchanged keys are skipped and rulesets are updated in
  place by name, never duplicated.

The scaffolded `protect-main` ruleset stops deletion and force-pushes of the
default branch, requires changes to arrive by PR (0 approvals, so a solo
maintainer isn't blocked), and requires the `ci / Lint, type-check, and test`
check (plus `frontend / Type-check and build` when the project has a frontend).
Repository **admins bypass it** (`actor_id: 5` is the built-in Admin role) so a
release commit can still be pushed directly; tighten that as the team grows.
A required check only takes effect once it has run at least once on the repo,
so run CI before you rely on it.

Plan gating: the rulesets API refuses private repos on the Free plan (403). The
script applies the plain settings, says so, and exits 0; re-run it after the
plan changes. Generality-Labs is on Team, so org repos are unaffected.

This repo carries its own copies of both files and applies them with the
scaffolded script, from the repo root:

```bash
python3 'template/{% if use_repo_settings %}scripts{% endif %}/setup_repo.py' Generality-Labs/python-project-template
```

The script is unit-tested against a stubbed `gh` in `tests/test_setup_repo.py`,
which template CI runs.

## Keeping projects up to date

Answer yes to `use_template_update` (the default) and the scaffold gets a
`template-update.yml` workflow that runs `copier update` weekly (and on demand)
and opens a PR when the template's *scaffolded files* have changed. Copier does
a three-way merge between the old template output, the new output, and the
project's local edits, so customisations survive.

Answering no leaves the workflow out. It does **not** cut the project off from
template updates: `.copier-answers.yml` is written either way, so
`uvx copier update` still works by hand whenever you want it. Worth declining
for a repo that should pull template changes on its own schedule rather than
weekly — one in a release freeze, or one whose local edits have diverged far
enough that every update run conflicts and the PRs become noise.

Two things worth knowing about the scope:

- **Reusable workflow changes need no update run.** Consumers pin
  `python-ci.yml@v1` and `node-ci.yml@v1`, so moving the `v1` tag propagates
  those immediately. The update workflow exists only for the copied files —
  `.pre-commit-config.yaml`, `biome.json`, `pyproject.toml` and friends.
- **It requires `.copier-answers.yml`.** A project adapted by hand rather than
  scaffolded has no baseline for copier to merge from, and the workflow fails
  with a message saying so. Adopt the template properly first.

Where copier's merge conflicts it leaves ordinary conflict markers and labels
the PR. Setting `resolve-conflicts-with-claude: true` (plus an
`ANTHROPIC_API_KEY` secret) has the Claude Code action attempt them instead.
It's off by default: copier's merge is deterministic and usually clean, and a
conflict is often exactly the thing a human should look at.

One GitHub quirk the PR body also mentions: it's opened with the default
`GITHUB_TOKEN`, so GitHub starts its CI in an approval-required state. Click
**Approve workflows to run** on the PR, or swap in a PAT or GitHub App token
if you want that automatic. The same applies to release pull requests.

## Releasing this template

The template releases itself with the same reusable workflows, so each release exercises them before `v1` moves to it:

One-time setup: _Settings → Actions → General_ → **Allow GitHub Actions to create and approve pull requests**, or step 1 fails when it opens the pull request.

1. _Actions_ → **Prepare template release** → _Run workflow_. It takes the next version from the latest `vX.Y.Z` tag, collects `changelog.d/` into `CHANGELOG.md`, and opens a **Release vX.Y.Z** pull request.
2. On the pull request's Checks tab, click **Approve workflows to run**, then review it. Add a summary paragraph under the new heading if the release needs one.
3. Merge it. **Template release on merge** tags the merge commit and creates the GitHub release, then starts `bump-v1.yml`, which checks the changelog, annotates the tag, and moves `v1`.

Each pull request to this repo adds a fragment under `changelog.d/` (`uvx --from scriv scriv create`), configured by `changelog.d/scriv.ini`. Publishing a release by hand from the GitHub UI still works: `bump-v1.yml` runs on the release event as before.

## Versioning

Tagged `v1.0.0` with a moving `v1`. Generated projects pin the reusable workflow
to `@v1`; a repo-local `.github/zizmor.yml` allows tag-pinned refs from
`Generality-Labs/*` while still requiring commit-SHA pins for third-party
actions.

The generated `.github/dependabot.yml` also ignores `Generality-Labs/*` for the
github-actions ecosystem. Without it, Dependabot rewrites `@v1` to a fixed
`@v1.x.y` and then opens a bump PR on every release — and the next `copier
update` restores the moving tag, so the two fight indefinitely. Third-party
actions are unaffected: still SHA-pinned, still bumped weekly.
