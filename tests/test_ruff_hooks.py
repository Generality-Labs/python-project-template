"""Exercise rendered hooks with two local Ruff stub wheels and no network access."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

import pytest
import yaml
from copier import run_copy

ROOT = Path(__file__).resolve().parents[1]


def ruff_wheel(directory: Path, version: str) -> None:
    info = f"ruff-{version}.dist-info"
    files = {
        "ruff.py": (
            "import json, sys\n"
            "from importlib.metadata import version\n"
            "def main():\n"
            "    print(json.dumps({'version': version('ruff'), 'args': sys.argv[1:]}))\n"
        ),
        f"{info}/METADATA": f"Metadata-Version: 2.1\nName: ruff\nVersion: {version}\n",
        f"{info}/WHEEL": "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        f"{info}/entry_points.txt": "[console_scripts]\nruff = ruff:main\n",
    }
    files[f"{info}/RECORD"] = "".join(f"{name},,\n" for name in [*files, f"{info}/RECORD"])
    with zipfile.ZipFile(directory / f"ruff-{version}-py3-none-any.whl", "w") as wheel:
        for name, content in files.items():
            wheel.writestr(name, content)


@pytest.mark.parametrize("kind", ["app", "library"])
def test_ruff_hooks_follow_lockfile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    source = tmp_path / "template"
    source.mkdir()
    shutil.copy(ROOT / "copier.yml", source)
    shutil.copytree(ROOT / "template", source / "template")
    project = tmp_path / "project"
    run_copy(
        str(source),
        project,
        data={
            "project_name": "ruff-hook-test",
            "project_description": "Ruff hook test",
            "project_kind": kind,
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
        },
        defaults=True,
        quiet=True,
    )
    pyproject = project / "pyproject.toml"
    dependencies = tomllib.loads(pyproject.read_text())["dependency-groups"]["dev"]
    version = next(dep.removeprefix("ruff==") for dep in dependencies if dep.startswith("ruff=="))
    major, minor, patch = version.split(".")
    upgraded = f"{major}.{minor}.{int(patch) + 1}"

    config_file = project / ".pre-commit-config.yaml"
    config = yaml.safe_load(config_file.read_text())
    repos = []
    for repo in config["repos"]:
        hooks = [hook for hook in repo["hooks"] if hook["id"] in {"ruff-check", "ruff-format"}]
        if hooks:
            assert repo["repo"] == "local"
            repos.append({**repo, "hooks": hooks})
    assert {hook["id"] for repo in repos for hook in repo["hooks"]} == {
        "ruff-check",
        "ruff-format",
    }
    config_file.write_text(yaml.safe_dump({"repos": repos}))

    wheels = tmp_path / "wheels"
    wheels.mkdir()
    for release in (version, upgraded):
        ruff_wheel(wheels, release)
    for name, value in {
        "UV_OFFLINE": "true",
        "UV_NO_INDEX": "true",
        "UV_FIND_LINKS": str(wheels),
        "UV_CACHE_DIR": str(tmp_path / "uv-cache"),
        "UV_PYTHON": sys.executable,
        "UV_PYTHON_DOWNLOADS": "never",
        "PRE_COMMIT_HOME": str(tmp_path / "pre-commit"),
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("UV_PROJECT_ENVIRONMENT", raising=False)

    def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(args, cwd=project, text=True, capture_output=True, check=check)

    def pin(release: str) -> None:
        # Other development tools are outside this offline hook test.
        pyproject.write_text(
            '[project]\nname = "ruff-hook-test"\nversion = "0.0.0"\n'
            f'requires-python = ">={sys.version_info.major}.{sys.version_info.minor}"\n'
            f'[dependency-groups]\ndev = ["ruff=={release}"]\n'
            "[tool.uv]\npackage = false\n"
        )

    files = ("sample.py", "sample.pyi", "sample.ipynb", "sample.txt")
    for name in files:
        (project / name).write_text("\n")
    run("git", "init", "-q")
    run("git", "add", *files)
    command = (sys.executable, "-m", "pre_commit", "run", "--verbose", "--files", *files)

    for release in (version, upgraded):
        pin(release)
        if release == upgraded:
            locked = (project / "uv.lock").read_bytes()
            stale = run(*command, check=False)
            assert stale.returncode != 0
            assert "lockfile" in stale.stdout.lower(), stale.stdout
            assert (project / "uv.lock").read_bytes() == locked
        run("uv", "lock")
        result = run(*command)
        calls = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{"')]
        assert len(calls) == 2, result.stdout
        for call, subcommand in zip(calls, ("check", "format"), strict=True):
            assert call["version"] == release
            assert call["args"][0] == subcommand
            assert "--force-exclude" in call["args"]
            assert ("--fix" in call["args"]) == (subcommand == "check")
            assert {arg for arg in call["args"][1:] if not arg.startswith("--")} == set(files[:3])
