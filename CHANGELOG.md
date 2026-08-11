# Changelog

All notable changes to this template will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Two things are worth knowing about how versions work here, because this repo ships CI rather than a package:

- **`v1` is a moving major tag.** Consumers pin `python-ci.yml@v1` and `node-ci.yml@v1`, so publishing a release is what actually delivers a change to them — `.github/workflows/bump-v1.yml` moves `v1` onto each published `v1.x` release. Changes to the reusable workflows reach every project the moment that happens, with no `copier update` needed.
- **Release tags are annotated; `v1` stays lightweight.** They end up on the same commit, and copier reads a template's version with `git describe --tags`, which prefers the annotated tag. Get this backwards and copier reads the version as `1` and refuses every consumer's update as a downgrade. `bump-v1.yml` maintains this on its own — it annotates the release tag if publishing left it lightweight, and creates `v1` lightweight — so releases can still be cut from the GitHub UI.
- **Changes to *scaffolded* files reach projects only through `copier update`.** `.pre-commit-config.yaml`, `biome.json`, `pyproject.toml` and friends are copied at scaffold time, so a project picks them up when it runs an update — automatically if it opted into `template-update.yml`.

Entries for 1.0.0 through 1.5.2 were backfilled from git history after the fact, so they describe what each tag contained rather than having been written alongside it.

## [Unreleased]

### Changed

- Rebranded for the Generality-Labs fork: `github_owner` now defaults to
  `Generality-Labs`, so scaffolded projects call the reusable workflows and
  pin their zizmor/Dependabot exceptions against this repo. README, LICENSE
  and workflow header comments updated to match.

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
[unreleased]: https://github.com/Generality-Labs/python-project-template/compare/v1.8.1...HEAD
