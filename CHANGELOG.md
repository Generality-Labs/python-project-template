# Changelog

All notable changes to this template will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Two things are worth knowing about how versions work here, because this repo ships CI rather than a package:

- **`v1` is a moving major tag.** Consumers pin `python-ci.yml@v1` and `node-ci.yml@v1`, so a release is what actually delivers a change to them. Releases go through the **Prepare template release** workflow (see the README); merging its pull request tags the release and starts `.github/workflows/bump-v1.yml`, which moves `v1` onto it. A release published by hand from the GitHub UI starts bump-v1 too. Changes to the reusable workflows reach every project the moment that happens, with no `copier update` needed.
- **Release tags are annotated; `v1` stays lightweight.** They end up on the same commit, and copier reads a template's version through dunamai, which takes the commit's newest tag by date: an annotated tag's date is when it was tagged, a lightweight tag's is its commit's. So the annotated release tag outranks `v1`. Get this backwards and copier reads the version as `1` and refuses every consumer's update as a downgrade. `bump-v1.yml` maintains this on its own — it annotates the release tag if publishing left it lightweight, and creates `v1` lightweight — so releases can still be cut from the GitHub UI.
- **Changes to *scaffolded* files reach projects only through `copier update`.** `.pre-commit-config.yaml`, `biome.json`, `pyproject.toml` and friends are copied at scaffold time, so a project picks them up when it runs an update — automatically if it opted into `template-update.yml`.

Entries for 1.0.0 through 1.5.2 were backfilled from git history after the fact, so they describe what each tag contained rather than having been written alongside it.

<!-- scriv-insert-here -->

## [1.10.0] - 2026-10-03

Releases are automated, through two reusable workflows that generated projects call from thin `@v1` callers. Run "Prepare release" from the Actions tab, approve the CI on the pull request it opens, and merge. The merge tags the release and creates the GitHub release, and a library on PyPI is then published. Libraries now build with `uv_build`, with the version set once in `pyproject.toml`. Every project needs one repository setting and `copier update --trust`, and libraries should check their version and wheel after updating; see Upgrading.

### Added

- Automated releases. Run **Prepare release** from the Actions tab: it bumps `version` in `pyproject.toml` with `uv version --bump`, collects `changelog.d/` into `CHANGELOG.md`, and opens a "Release vX.Y.Z" pull request. Approve its CI and merge it, and **Release on merge** tags the merge commit, creates the GitHub release from the changelog section, and, for a library published to PyPI, starts `publish.yml`. The `auto` bump picks minor when a fragment adds, changes, deprecates or removes something, and patch when fragments only fix; it never picks major.
- The steps live in two reusable workflows in this repo, `prepare-release.yml` and `release-on-merge.yml`, and generated projects get thin callers pinned to `@v1`, as with `python-ci.yml`. Release fixes reach every project when `v1` moves, without a `copier update`.
- The safeguards: Prepare release refuses a run from another branch, with no fragments, with a fragment that has entries but no category heading or that quotes a scriv marker (scriv would silently drop the lines above it), with an existing tag, or with a release pull request already open, and is safe to re-run after a failure. Release on merge checks that `pyproject.toml` at the merge commit agrees with the release branch, refuses a tag already on another commit, and skips a tag or release that already exists, so it can be re-run. Its concurrency group is keyed on the branch, so an unrelated pull request closing can't cancel a pending release run.
- `publish.yml` takes a `workflow_dispatch` trigger, so Release on merge can start it. A tag created with the default Actions token triggers no workflows, and PyPI trusted publishing can't run from a reusable workflow, so the dispatched run is still `publish.yml`, the workflow the trusted publisher names. It refuses any ref but a `v*` tag, fails if the tag doesn't match the built wheel's version, and moves to checkout 7.0.1 and setup-uv 10.0.1.
- This template releases itself with the same reusable workflows, in a mode that takes the version from the latest `vX.Y.Z` tag, so every template release exercises them before `v1` moves. Its own changelog is now scriv fragments too, and `bump-v1.yml` can be started on a tag as well as by a published release. Started that way, it refuses anything but the newest final `v1.X.Y` tag, so `v1` only moves forward.

### Changed

- Libraries build with uv's own backend, `uv_build`, instead of hatchling, and keep a static `version` in `pyproject.toml`, so `uv version --bump` manages it. `__version__` reads it back from the installed package metadata (`"unknown"` in a source tree that was never installed). hatchling was there to read the version from `__init__.py`, which uv can't bump; with the version in `pyproject.toml` it isn't needed. `[tool.scriv]` reads the version from `pyproject.toml` for every project kind. MIT projects set `license-files = ["LICENSE"]`, since uv_build ships only the license files it is told about.

### Upgrading

- A manual `copier update` across 1.10.0 needs `--trust`, because the template now runs a migration. Without it copier stops with `Template uses potentially unsafe feature: migrations.` and changes nothing, for apps as well as libraries. The weekly template-update workflow already passes it.
- Turn on _Settings → Actions → General_ → **Allow GitHub Actions to create and approve pull requests**, or Prepare release fails when it opens the pull request. The weekly template-update workflow needs the same setting. CI on each release pull request then starts once you click **Approve workflows to run** on it.
- For a library, `copier update` changes `pyproject.toml` to uv_build and a static `version`, and a migration then sets that `version` to the `__version__` the project's `__init__.py` had before the update. Without it the template's `0.1.0` would merge in silently. Check `uv version --short` before merging the update. `__init__.py` itself conflicts: keep the template's metadata lookup, plus any other code the file had.
- For a library, check that the wheel's contents don't change: uv_build expects the package under `src/<package>/`, and any hatch build options (includes, excludes, force-include) need their `[tool.uv.build-backend]` equivalents.
- No PyPI change is needed. The trusted publisher still names `publish.yml`. A project that publishes from a differently named workflow should rename it to `publish.yml` and update the publisher.

## [1.9.1] - 2026-10-02

Repairs 1.9.0, which was tagged before `CHANGELOG.md` had a `[1.9.0]` section. `bump-v1.yml` refuses a release it can't find described, so it left `v1` on 1.8.1 and the 1.9.0 tag lightweight. Consumers land on 1.9.1 rather than 1.9.0; the contents are the same bar this changelog.

## [1.9.0] - 2026-10-02

### Added

- Scaffolded projects keep their changelog as [scriv](https://scriv.readthedocs.io/) fragments: each PR adds a file under `changelog.d/` (`uv run scriv create`) instead of editing `CHANGELOG.md`, and `uv run scriv collect` writes them into `CHANGELOG.md` at release time. Two PRs that both edited `## [Unreleased]` conflicted on every merge; fragments are separate files, so they never do. The scaffold gains `[tool.scriv]` in `pyproject.toml` (Keep a Changelog categories, `## [X.Y.Z] - YYYY-MM-DD` headings, the version read from `__init__.py` for libraries or `pyproject.toml` for apps), `scriv` in the dev group, `changelog.d/TEMPLATE.md`, and a `<!-- scriv-insert-here -->` marker in place of `## [Unreleased]`. `RELEASING.md` and the README say how to use them.
- `CHANGELOG.md` is listed in `_skip_if_exists`, so `copier update` leaves an existing changelog alone. It does create one if the file is missing, so a project that keeps its changelog elsewhere gets a new `CHANGELOG.md` proposed on each update.
- **Upgrading an existing project:** `copier update` brings in the config and `changelog.d/TEMPLATE.md` but not the marker. By hand: - Replace the `## [Unreleased]` heading in `CHANGELOG.md` with `<!-- scriv-insert-here -->`, and move any unreleased entries into a fragment under `changelog.d/`. Skipping this makes `scriv collect` fail with `Entry 'Changelog' is not a valid version!`; its hint about `scriv-end-here` is not the fix. - Check that `[tool.scriv] version` reads the file your build backend reads. Libraries get `src/<pkg>/__init__.py`, which is right for the template's hatchling setup. A project that moved to a static `version` in `pyproject.toml` (for example, uv_build) needs `literal: pyproject.toml: project.version`, or collect writes a stale version.
- `python-ci.yml` and `node-ci.yml` take an `lfs` input, passed through to `actions/checkout`. It defaults to `false`, because an LFS pull costs bandwidth against the account quota on every run and most projects have nothing in LFS. Turn it on for a repo whose tests read LFS-tracked fixtures: without it the checkout produces pointer files, and the failure surfaces as whatever the reading library says about malformed input — `FzErrorFormat: no objects found` from PyMuPDF, in the case that prompted this — with nothing anywhere in the output mentioning LFS.
- Repo settings as code, opt-in via `use_repo_settings` (default off, so `copier update --defaults` leaves existing projects alone): the scaffold ships `.github/repo-settings.json` (the literal `PATCH /repos/{owner}/{repo}` body: merge methods, `delete_branch_on_merge: true` so stacked PRs retarget, wiki/projects off) and `.github/rulesets/main.json` (protect the default branch: PRs required, no force-pushes or deletion, the `ci / Lint, type-check, and test` check required, plus the frontend check when there is one; repository Admins bypass), and `scripts/setup_repo.py`, which fetches the repo's current settings and rulesets, prints what would change (a unified diff per ruleset, projected onto the keys the file sets), and applies only after confirmation or `--yes`; `--dry-run` only shows. The post-copy message points at it, and this repo carries and applies its own copies.

### Changed

- The reusable workflows move to new major versions of two actions: `python-ci.yml` uses `astral-sh/setup-uv` v10 (was v8.3.2), and `node-ci.yml` uses `actions/setup-node` v7 (was v6.5.0). Both also take `actions/checkout` 7.0.1. These reach every `@v1` consumer as soon as `v1` moves, with no `copier update`.
- Rebranded for the Generality-Labs fork: `github_owner` now defaults to `Generality-Labs`, so scaffolded projects call the reusable workflows and pin their zizmor/Dependabot exceptions against this repo. README, LICENSE and workflow header comments updated to match.

### Fixed

- The scaffolded typos hook skips `.copier-answers.yml`. The file is generated, and its `_commit` is whatever ref the last update used — when that is a short SHA rather than a tag, its leading hex characters are a coin flip away from a word typos reads as misspelled, and `ba338ef` duly tripped `ba` → `by`, `be`. Nothing in the file is prose, so checking it could only ever produce false positives, on a schedule nobody controls.

## [1.8.1] - 2026-08-07

Repairs 1.8.0, which shipped a lightweight tag and left every project unable to update. Consumers land on 1.8.1 rather than 1.8.0; the contents are the same bar this fix.

### Fixed

- `bump-v1.yml` annotates the release tag before moving `v1` onto the same commit. Copier reads a template's version with `git describe --tags`, which prefers an annotated tag and otherwise takes the newest — so with both lightweight it answered `v1`, copier parsed that as version `1`, and every consumer above 1.0.0 failed `copier update` with "Downgrades are not supported". This stranded projects completely: an explicit `--vcs-ref v1.8.0` reads the same commit and failed identically, so there was no working update path at all. Publishing a release for a tag that doesn't exist yet creates a lightweight one, so the annotation is applied here rather than asked of whoever cuts the release. It has been wrong since 1.6.0, the first release tagged this way.

## [1.8.0] - 2026-08-07

Swaps the type checker. Consumers pinned to `v1` keep passing without doing anything — the workflow's type-check step falls back to mypy — so the migration happens per project, on its next `copier update`.

### Changed

- Type checking is now [basedpyright](https://docs.basedpyright.com/) instead of mypy: pip-installable with no Node bootstrap (uv locks it like any other dev dependency), faster, and it matches the Pyright-based language servers editors actually run, so CI enforces the same diagnostics the editor shows. Scaffolds get `[tool.basedpyright]` with `typeCheckingMode = "strict"` — deliberately pyright's `strict`, not basedpyright's stricter `recommended` default — and `reportMissingTypeStubs = false` standing in for mypy's `ignore_missing_imports`. The scaffolded `.gitignore` drops the mypy cache entries. Existing projects pick all this up on their next `copier update`.
- `python-ci.yml`'s type-check step runs basedpyright when the project's environment has it and falls back to mypy (with a deprecation note in the log) when it doesn't — `v1` is a moving tag, so the step keeps working for projects scaffolded before this change until they update. The `mypy-paths` input is deprecated in favour of `typecheck-paths`; it still works, and wins when set.

## [1.7.0] - 2026-08-07

### Added

- This changelog, backfilled from git history.
- `bump-v1.yml` refuses to move `v1` for a release that has no changelog section, or that leaves entries under `[Unreleased]`. The check runs before the tag moves, so an undocumented release delivers nothing to consumers.

### Fixed

- `template-update.yml` runs `uv lock` after the merge, so a template update that changes `pyproject.toml`'s dependencies doesn't open a PR with a stale `uv.lock`. Consumers' CI begins with `uv sync --locked`, so those PRs failed there before reaching a single real check. The step tolerates a failed lock — an unresolved conflict leaves markers `uv` can't parse, and the PR is still worth opening with its existing conflict warning.

## [1.6.0] - 2026-07-27

The largest release so far: an optional TypeScript side, automated template updates, and a substantial pass over how the template verifies itself.

### Added

- Optional TypeScript/JavaScript support via `use_frontend`, adding `biome.json`, a Biome hook in the pre-commit stack, and a second CI job calling the new shared `node-ci.yml` (type-check and build). `frontend_dir` says where `package.json` lives. Lint and format deliberately stay in pre-commit so a hybrid repo doesn't pay for a second Node job. (#4)
- `template-update.yml`, scaffolded by default, running `copier update` weekly and opening a PR when the template's scaffolded files change. Decline with `use_template_update`; `.copier-answers.yml` is written either way, so `uvx copier update` still works by hand. (#4)
- `use_typos`, to decline the typos hook for projects whose vocabulary the checker doesn't know. (#3)
- `working-directory` input on `python-ci.yml`, mirroring the one `node-ci.yml` already had, for repos whose Python project isn't at the top. (#6)
- `bump-v1.yml`, moving the `v1` tag when a release is published. It refuses prereleases, refuses tags outside `v1.x`, and refuses to move `v1` to a commit not contained in `main`. (#6)
- Template CI now runs each rendered scaffold's own pre-commit stack, and executes both reusable workflows against fixtures under `tests/smoke/`. Previously nothing ever ran them, so a change to either shipped to every consumer untested. (#6)

### Changed

- `dependabot.yml` is templated and tells Dependabot to leave the project's own `@v1` references alone. Left un-ignored it rewrote them to fixed versions and `copier update` restored the moving tag, so the two fought indefinitely. (#5)
- The scaffolded `SessionStart` hook points corepack at `registry.npmjs.org` when the project has a frontend. corepack's default host is blocked by some sandbox egress proxies, which fails before Yarn or pnpm starts and leaves the frontend impossible to install, build or type-check. (#4)
- The shellcheck hook is pinned to `python3.12`, independently of `default_language_version`. shellcheck-py builds from source and its build cannot verify the CA some sandboxes present once Python 3.13 enables `ssl.VERIFY_X509_STRICT`, which breaks `git commit` outright rather than merely failing a hook run. (#6)

### Fixed

- `biome.json` shipped a Yarn exclusion (`!**/.yarn/**`) that Biome normalises to `!**/.yarn`, so the first `biome check` in a new frontend project rewrote a file nobody had touched and left every scaffold red before its first commit. (#6)
- Template CI rendered the latest *tag* rather than the branch under review — copier's default when the source is a git repo. Every assertion passed while proving nothing about the change; it only worked because `actions/checkout` fetches no tags. All copier calls now pass `--vcs-ref=HEAD`. (#6)
- `biome.json` excludes `.yarn` and generated fixture data. Yarn Berry projects commit `.yarn/sdks`, so `vcs.useIgnoreFile` alone left Biome reformatting Yarn's own vendored TypeScript shims. (#4)
- `node-ci.yml` enables corepack *before* `setup-node`. With `cache` set, setup-node probes the package manager for its cache folder, which fails when `packageManager` pins Yarn 4 and the runner's bare `yarn` is still 1.x — it failed outright and every later step skipped, for every Yarn Berry and pnpm consumer. (#4)
- The scaffolded `check-json` hook skips `tsconfig*.json`. TypeScript has always permitted comments there and Biome parses it as JSONC, but `check-json` uses the stdlib `json` module and fails on them. (#4)
- Biome's rule preset is spelled `"preset": "recommended"` rather than the `"recommended": true` deprecated in Biome 2.5.5. (#4)
- The typos hook runs report-only. Its own defaults include `--write-changes`, which edits source rather than reporting it; on a domain-heavy corpus that means silent, incorrect rewrites. (#3)

## [1.5.2] - 2026-07-21

### Fixed

- The pre-commit cache in `python-ci.yml` is keyed by OS and Python version. `pre-commit/action` keys on `env.pythonLocation`, which only `setup-python` populates — with `setup-uv` the segment is empty and the key collapses to the config hash alone, shared across every Python version and OS in a caller's matrix. A macOS job then restored a Linux-built cache and failed with `InvalidManifestError`. (#2)

## [1.5.1] - 2026-07-18

### Added

- A `license` question, including a proprietary option that writes no `LICENSE` file. (#1)
- An MIT `LICENSE` for the template repo itself.

## [1.5.0] - 2026-07-17

### Added

- `runs-on` input on the reusable CI workflow, so callers can matrix over operating systems.

## [1.4.0] - 2026-07-17

### Changed

- Coverage is always measured; `use_coverage_gate` now controls only whether falling below the floor fails the build.

## [1.3.2] - 2026-07-17

### Changed

- Expanded the scaffolded `.gitignore`: `.env`, build and dist directories, coverage output, `.claude/settings.local.json`, and common editor files.

## [1.3.1] - 2026-07-17

### Fixed

- The scaffolded `.gitignore` was missing `.venv/`, `.DS_Store` and `.coverage`.
- Dev-dependency group indentation under the coverage gate conditional.

## [1.3.0] - 2026-07-16

### Added

- `publish_to_pypi`, separated from `project_kind`, so a library can be packaged without being published.

## [1.2.2] - 2026-07-16

### Changed

- All pre-commit hook revisions are hash-pinned.

## [1.2.1] - 2026-07-16

### Fixed

- Hardened the template's own workflows: template-injection-safe `run:` steps, explicit permissions, workflow names, and concurrency groups.

## [1.2.0] - 2026-07-16

### Added

- More ruff rule families (C4, PT, DTZ, RUF and others), plus typos and shellcheck hooks and a Dependabot config.
- A Dependabot cooldown, so a release isn't adopted until it has had time to be vetted or yanked.

## [1.1.1] - 2026-07-16

### Changed

- Stopped banning relative imports, which was specific to an earlier project rather than generally useful.

## [1.1.0] - 2026-07-16

### Added

- A stricter lint stack: ruff `D` rules, strict mypy, more pre-commit hooks, and `.mdformat.toml`.

### Fixed

- A static concurrency group, avoiding the clash between copier's and GitHub Actions' `${{ }}` syntax.

## [1.0.0] - 2026-07-16

### Added

- Initial template: uv, ruff, mypy, pytest, pre-commit, a shared `python-ci.yml` reusable workflow, Keep a Changelog, and PyPI trusted publishing for libraries.

### Fixed

- Conditional filenames keep the `.jinja` suffix outside the `if`.
- Cache-poisoning in `publish.yml`, and `trim_blocks` for clean rendered markdown.

[1.0.0]: https://github.com/MattFisher/python-project-template/releases/tag/v1.0.0
[1.1.0]: https://github.com/MattFisher/python-project-template/compare/v1.0.0...v1.1.0
[1.1.1]: https://github.com/MattFisher/python-project-template/compare/v1.1.0...v1.1.1
[1.2.0]: https://github.com/MattFisher/python-project-template/compare/v1.1.1...v1.2.0
[1.2.1]: https://github.com/MattFisher/python-project-template/compare/v1.2.0...v1.2.1
[1.2.2]: https://github.com/MattFisher/python-project-template/compare/v1.2.1...v1.2.2
[1.3.0]: https://github.com/MattFisher/python-project-template/compare/v1.2.2...v1.3.0
[1.3.1]: https://github.com/MattFisher/python-project-template/compare/v1.3.0...v1.3.1
[1.3.2]: https://github.com/MattFisher/python-project-template/compare/v1.3.1...v1.3.2
[1.4.0]: https://github.com/MattFisher/python-project-template/compare/v1.3.2...v1.4.0
[1.5.0]: https://github.com/MattFisher/python-project-template/compare/v1.4.0...v1.5.0
[1.5.1]: https://github.com/MattFisher/python-project-template/compare/v1.5.0...v1.5.1
[1.5.2]: https://github.com/MattFisher/python-project-template/compare/v1.5.1...v1.5.2
[1.6.0]: https://github.com/MattFisher/python-project-template/compare/v1.5.2...v1.6.0
[1.7.0]: https://github.com/MattFisher/python-project-template/compare/v1.6.0...v1.7.0
[1.8.0]: https://github.com/MattFisher/python-project-template/compare/v1.7.0...v1.8.0
[1.8.1]: https://github.com/MattFisher/python-project-template/compare/v1.8.0...v1.8.1
[1.9.0]: https://github.com/Generality-Labs/python-project-template/compare/v1.8.1...v1.9.0
[1.9.1]: https://github.com/Generality-Labs/python-project-template/compare/v1.9.0...v1.9.1
[1.10.0]: https://github.com/Generality-Labs/python-project-template/compare/v1.9.1...v1.10.0
[unreleased]: https://github.com/Generality-Labs/python-project-template/compare/v1.10.0...HEAD
