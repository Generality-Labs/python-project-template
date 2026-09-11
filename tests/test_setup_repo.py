"""Tests for the scaffolded scripts/setup_repo.py against a stubbed gh."""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "template"
    / "{% if use_repo_settings %}scripts{% endif %}"
    / "setup_repo.py"
)
spec = importlib.util.spec_from_file_location("setup_repo", SCRIPT)
assert spec is not None
assert spec.loader is not None
setup_repo = importlib.util.module_from_spec(spec)
# Dataclasses resolve postponed annotations through sys.modules[__module__].
sys.modules[spec.name] = setup_repo
spec.loader.exec_module(setup_repo)

REPO = "acme/widgets"
SETTINGS = {"delete_branch_on_merge": True, "has_wiki": False}
RULESET = {
    "name": "protect-main",
    "target": "branch",
    "enforcement": "active",
    "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
    "bypass_actors": [{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}],
    "rules": [
        {"type": "deletion"},
        {"type": "pull_request", "parameters": {"required_approving_review_count": 0}},
    ],
}


def as_github_returns(ruleset: dict, ruleset_id: int) -> dict:
    """GitHub's copy: same content plus ids, timestamps and defaults for unset parameters."""
    copy = json.loads(json.dumps(ruleset))
    copy.update({"id": ruleset_id, "source": REPO, "created_at": "2026-01-01T00:00:00Z"})
    for rule in copy["rules"]:
        if rule["type"] == "pull_request":
            rule["parameters"]["dismiss_stale_reviews_on_push"] = False
            rule["parameters"]["allowed_merge_methods"] = ["merge", "squash", "rebase"]
    return copy


class FakeGh:
    """Records every gh call and answers reads from a small in-memory GitHub."""

    def __init__(self, settings: dict, rulesets: list[dict]) -> None:
        self.settings = settings
        self.rulesets = rulesets
        self.writes: list[tuple[list[str], str | None]] = []
        self.plan_gated = False

    def __call__(self, args: Sequence[str], stdin: str | None) -> str:
        args = list(args)
        if args[:2] == ["auth", "status"]:
            return ""
        if args[:2] == ["repo", "view"]:
            return REPO + "\n"
        if "-X" in args:
            self.writes.append((args, stdin))
            return "{}"
        target = args[1]
        if target == f"repos/{REPO}":
            return json.dumps(self.settings)
        if target.startswith(f"repos/{REPO}/rulesets?"):
            if self.plan_gated:
                raise setup_repo.GhError(
                    "HTTP 403: Upgrade to GitHub Pro or make this repository public"
                )
            return json.dumps([{"id": r["id"], "name": r["name"]} for r in self.rulesets])
        if target.startswith(f"repos/{REPO}/rulesets/"):
            wanted = int(target.rsplit("/", 1)[1])
            return json.dumps(next(r for r in self.rulesets if r["id"] == wanted))
        raise AssertionError(f"unexpected gh call: {args}")


@pytest.fixture
def repo_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / ".github" / "rulesets").mkdir(parents=True)
    (tmp_path / ".github" / "repo-settings.json").write_text(json.dumps(SETTINGS))
    (tmp_path / ".github" / "rulesets" / "main.json").write_text(json.dumps(RULESET))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def run(gh: FakeGh, *argv: str, interactive: bool = False, answer: str = "n") -> tuple[int, str]:
    lines: list[str] = []
    code = setup_repo.main(
        [*argv, REPO],
        gh=gh,
        out=lines.append,
        interactive=interactive,
        ask=lambda _: answer,
    )
    return code, "\n".join(lines)


def test_project_drops_api_only_fields_but_keeps_extra_array_elements() -> None:
    current = {
        "id": 1,
        "a": {"x": 1, "y": 2},
        "rules": [{"t": "a", "extra": 1}, {"t": "b"}],
    }
    want = {"a": {"x": 0}, "rules": [{"t": "a"}]}
    assert setup_repo.project(current, want) == {
        "a": {"x": 1},
        "rules": [{"t": "a"}, {"t": "b"}],
    }


def test_nothing_to_apply_when_everything_matches(repo_dir: Path) -> None:
    gh = FakeGh(dict(SETTINGS, description="x"), [as_github_returns(RULESET, 7)])
    code, out = run(gh, "--yes")
    assert code == 0
    assert "no changes (.github/repo-settings.json already matches)" in out
    assert "ruleset 'protect-main' (id 7): no changes" in out
    assert "Nothing to apply." in out
    assert gh.writes == []


def test_first_run_creates_ruleset_and_patches_only_changed_keys(
    repo_dir: Path,
) -> None:
    gh = FakeGh({"delete_branch_on_merge": False, "has_wiki": False}, [])
    code, out = run(gh, "--yes")
    assert code == 0
    assert "repo settings: 1 change(s)" in out
    assert "delete_branch_on_merge: false -> true" in out
    assert "does not exist yet; would be created" in out
    (patch_args, patch_body), (post_args, post_body) = gh.writes
    assert patch_args[:4] == ["api", "-X", "PATCH", f"repos/{REPO}"]
    assert json.loads(patch_body or "") == {"delete_branch_on_merge": True}
    assert post_args[:4] == ["api", "-X", "POST", f"repos/{REPO}/rulesets"]
    assert json.loads(post_body or "") == RULESET


def test_drift_shows_diff_and_updates_in_place(repo_dir: Path) -> None:
    drifted = as_github_returns(RULESET, 9)
    drifted["rules"][1]["parameters"]["required_approving_review_count"] = 2
    gh = FakeGh(SETTINGS, [drifted])
    code, out = run(gh, "--yes")
    assert code == 0
    assert "(id 9): would be updated" in out
    assert '-        "required_approving_review_count": 2' in out
    assert '+        "required_approving_review_count": 0' in out
    assert "allowed_merge_methods" not in out  # API-only default, not a difference
    assert len(gh.writes) == 1
    assert gh.writes[0][0][:4] == ["api", "-X", "PUT", f"repos/{REPO}/rulesets/9"]


def test_dry_run_applies_nothing(repo_dir: Path) -> None:
    gh = FakeGh({}, [])
    code, out = run(gh, "--dry-run")
    assert code == 0
    assert "Dry run; nothing applied." in out
    assert gh.writes == []


def test_non_interactive_without_yes_refuses(repo_dir: Path) -> None:
    gh = FakeGh({}, [])
    code, out = run(gh)
    assert code == 2
    assert "Re-run with --yes" in out
    assert gh.writes == []


def test_prompt_no_aborts_and_yes_applies(repo_dir: Path) -> None:
    gh = FakeGh({}, [])
    code, out = run(gh, interactive=True, answer="n")
    assert code == 1
    assert "Aborted" in out
    assert gh.writes == []
    code, _ = run(gh, interactive=True, answer="y")
    assert code == 0
    assert len(gh.writes) == 2


def test_plan_gate_skips_rulesets_but_applies_settings(repo_dir: Path) -> None:
    gh = FakeGh({}, [])
    gh.plan_gated = True
    code, out = run(gh, "--yes")
    assert code == 0
    assert "refuses private repos" in out
    assert len(gh.writes) == 1
    assert gh.writes[0][0][2] == "PATCH"


def test_missing_settings_file_is_skipped(repo_dir: Path) -> None:
    (repo_dir / ".github" / "repo-settings.json").unlink()
    gh = FakeGh({}, [])
    code, out = run(gh, "--yes")
    assert code == 0
    assert "not found; skipping repo settings" in out
    assert [w[0][2] for w in gh.writes] == ["POST"]


def test_explicit_repo_wins_over_origin(repo_dir: Path) -> None:
    gh = FakeGh(SETTINGS, [as_github_returns(RULESET, 1)])
    calls: list[list[str]] = []

    def spy(args: Sequence[str], stdin: str | None) -> str:
        calls.append(list(args))
        return gh(args, stdin)

    assert setup_repo.main([REPO, "--yes"], gh=spy, out=lambda _: None) == 0
    assert not any(c[:2] == ["repo", "view"] for c in calls)
