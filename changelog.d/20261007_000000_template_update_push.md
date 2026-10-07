### Fixed

- `template-update.yml` no longer fails every run once its update branch exists. It pushed with a bare `--force-with-lease` to a URL, which gives git no remote-tracking ref to lease against, so the push was refused with `stale info` whenever the branch was already there. A run that pushed the branch but couldn't open its PR (for example, before the Actions pull-request setting was on) left every later run failing. The push now leases against the branch as checkout fetched it, so it still refuses to overwrite a commit pushed during the run.
