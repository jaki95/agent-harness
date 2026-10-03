# Versioning and releases

## Version policy

Version the harness as one collection. Skill directories stay stable; do not add a separate runtime version field to each `SKILL.md`. The CLI's lockfiles record per-skill source and content details.

- `main` contains reviewed changes and is the personal update source.
- Tags use `vMAJOR.MINOR.PATCH`, starting with `v0.1.0` after the first useful owned skill is added and evaluated.
- Patch versions cover corrections that preserve intended behavior.
- Minor versions add skills or backward-compatible capabilities.
- Major versions cover removals, renames, prerequisite changes, or changes that break established workflows. Before 1.0, a minor release can contain these changes if its notes identify them clearly.
- Never move an existing release tag. Publish a new version for corrections; consumers can explicitly roll back.
- Record meaningful changes under Unreleased in `CHANGELOG.md`. Move them to a dated version section before dispatching that release. GitHub also generates commit/PR-based release notes.

Tags identify reviewed repository snapshots. Upstream author revisions remain independently tracked in the registry. Detecting an upstream change does not itself create a harness release.

## Publish a release

1. Incorporate the chosen changes, run the relevant manual evaluation cases, and update their records and the changelog.
2. Commit and push to `main`.
3. Open [Release harness](https://github.com/jaki95/agent-harness/actions/workflows/release.yml), select `main`, and enter the new version.

Alternatively, dispatch from the authenticated GitHub CLI:

```sh
gh workflow run release.yml --repo jaki95/agent-harness --ref main -f version=v0.1.0
```

The workflow runs the repository checks, maintenance tests, and pinned Skills CLI integration test. It then validates the version, requires at least one owned skill, and rejects an existing tag. It tags the exact commit checked by that run and creates a GitHub release with generated notes. No npm package or additional skills.sh publication is produced.

Run the read-only release preflight locally:

```sh
python3 scripts/check_release.py v0.1.0
```

It checks the current collection and rejects invalid versions or empty collections. It does not create tags, query the remote, or publish anything; existing-tag checks occur in the release workflow.

The workflow pushes without force, so a conflicting tag push fails. If tag creation succeeds but GitHub release creation fails, preserve the tag and complete its release using `gh release create <version> --verify-tag --generate-notes`. Verify the tag's commit first; do not rerun the workflow with the same tag.

## Upgrade the installer

The installer is pinned separately in `package.json` and `package-lock.json`. To change it, select a reviewed published version, update both files, run the compatibility test, and update the install commands in documentation. The development package is private and is not the skill distribution artifact.

## References

- [GitHub CLI release creation](https://cli.github.com/manual/gh_release_create)
- [Manual workflow dispatch](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)
