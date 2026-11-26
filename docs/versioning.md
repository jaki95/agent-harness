# Versioning and releases

## Version policy

Version the harness as one collection. Skill directories stay stable; do not add a separate runtime version field to each `SKILL.md`. The CLI's lockfiles record per-skill source and content details.

- `main` contains reviewed changes and is the personal update source.
- Tags use `vMAJOR.MINOR.PATCH`, starting with `v0.1.0` after the first useful owned skill is added and validated.
- Patch versions cover corrections that preserve intended behavior.
- Minor versions add skills or backward-compatible capabilities.
- Major versions cover removals, renames, prerequisite changes, or changes that break established workflows. Before 1.0, a minor release can contain these changes if its notes identify them clearly.
- Never move an existing release tag. Publish a new version for corrections; consumers can explicitly roll back.
- Record meaningful changes under Unreleased in `CHANGELOG.md`. Before dispatch, move the notes under a heading of the form `## vMAJOR.MINOR.PATCH - YYYY-MM-DD`. The text under that heading becomes the GitHub release description.

Tags identify reviewed repository snapshots. Upstream author revisions remain independently tracked in the registry. Detecting an upstream change does not itself create a harness release.

## Publish a release

1. Incorporate the chosen changes, verify affected behavior, and update the changelog. Record actual evidence and limitations in the PR; automated release checks cover structure and packaging.
2. Commit and push to `main`.
3. Open [Release harness](https://github.com/jaki95/agent-harness/actions/workflows/release.yml), select `main`, and enter the new version.

Alternatively, dispatch from the authenticated GitHub CLI:

```sh
gh workflow run release.yml --repo jaki95/agent-harness --ref main -f version=v0.1.0
```

The workflow runs the repository checks, maintenance tests, and pinned Skills CLI integration test. It validates the version, requires at least one owned skill and a nonempty dated changelog section for that version, and rejects an existing tag. It tags the commit checked by that run and publishes its changelog section on GitHub.

Run the read-only release preflight locally:

```sh
python3 scripts/check_release.py v0.1.0
```

Pass `--notes-file PATH` to save the validated notes for inspection. The preflight runs locally. The release workflow checks for an existing tag.

If the tag push succeeds and GitHub release creation fails, recover from the existing tag. Fetch the tag and open a clean worktree at that tag. Compare `git rev-parse HEAD` there with the failed run's commit SHA. Stop if they differ. From that worktree, for the example version:

```sh
version=v0.1.0
notes=$(mktemp)
python3 scripts/check_release.py "$version" --notes-file "$notes" &&
  gh release create "$version" --verify-tag --title "$version" --notes-file "$notes" --latest
```

## Upgrade the installer

The installer is pinned separately in `package.json` and `package-lock.json`. To change it, select a reviewed published version, update both files, run the compatibility test, and update the install commands in documentation. The development package is private and is not the skill distribution artifact.

## References

- [GitHub CLI release creation](https://cli.github.com/manual/gh_release_create)
- [Manual workflow dispatch](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)
