### Fixed

- `python-ci.yml` installs Python 3.12 for the template's pre-commit hooks, so projects using another Python version can run them on Ubuntu 26.04. The workflow also includes the runner image in the cache key so that pre-commit rebuilds its hook environments when the image changes.
