### Fixed

- `python-ci.yml` installs the Python versions that `.pre-commit-config.yaml` names (`python3.12` by default) with uv before running pre-commit. GitHub moved `ubuntu-latest` to Ubuntu 26.04, which has no `python3.12`, and pre-commit failed with `failed to find interpreter for Builtin discover of python_spec='python3.12'` while building the first hook environment. The pre-commit cache key now includes the runner image name, so environments built on Ubuntu 24.04 are rebuilt and saved once.
