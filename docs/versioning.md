# Versioning and releases

## Version policy

Version the harness as one collection. Skill directories stay stable; do not add a separate runtime version field to each `SKILL.md`. The CLI's lockfiles record per-skill source and content details.

- `main` contains reviewed changes and is the personal update source.
- Tags use `vMAJOR.MINOR.PATCH`, starting with `v0.1.0` after the first useful owned skill is added and validated.
- Patch versions cover corrections that preserve intended behavior.
- Minor versions add skills or backward-compatible capabilities.
- Major versions cover removals, renames, prerequisite changes, or changes that break established workflows. Before 1.0, a minor release can contain these changes if its notes identify them clearly.
- Never move an existing release tag. Publish a new version for corrections; consumers can explicitly roll back.
- Record meaningful changes under Unreleased in `CHANGELOG.md`. When ready to release, move those notes into one new section headed `## vMAJOR.MINOR.PATCH - YYYY-MM-DD`. The text under that heading becomes the GitHub release description.

Tags identify reviewed repository snapshots. Upstream author revisions remain independently tracked in the registry. Detecting an upstream change does not itself create a harness release.

## Publish a release

1. Choose the next version using the policy above. Add its dated section to `CHANGELOG.md` with the changes consumers will receive. Prepare one new version per push to `main`.
2. Check the release locally. For the first release, run:

   ```sh
   python3 scripts/check_release.py v0.1.0
   ```

   Add `--notes-file PATH` to inspect the exact release text.
3. Merge the change to `main`. The [Release harness workflow](https://github.com/jaki95/agent-harness/actions/workflows/release.yml) detects the new version, runs the collection, installation, and offline Statechart checks, then tags the tested commit and publishes the changelog section on GitHub.

Pull requests targeting `main` get a read-only check when the changelog changes. Edits under Unreleased and changes to existing sections leave published releases alone. The publisher needs the workflow token to write repository contents and create the version tag under the repository's tag rules.

## Recover a failed release

Re-run the failed jobs in the original Actions run after a transient failure. The run keeps the original commit and version. If the tag already points to that commit, publication can finish from it. A completed publication is safe to retry. A conflicting tag or an existing draft or prerelease requires inspection.

If a failing check needs a code change and the version has **no tag yet**, merge the fix and run the recovery workflow on the corrected `main` commit:

```sh
gh workflow run release.yml --ref main -f version=v0.1.0
```

Use the version from your dated changelog section. The recovery run applies the same checks as automatic publication. If a version is already tagged, rerun the original commit's workflow to finish publication, or prepare a new version for corrections.

## Upgrade the installer

The installer is pinned separately in `package.json` and `package-lock.json`. To change it, select a reviewed published version, update both files, run the compatibility test, and update the install commands in documentation. The development package is private and is not the skill distribution artifact.

## References

- [GitHub CLI release creation](https://cli.github.com/manual/gh_release_create)
- [GitHub Actions workflow triggers](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#on)
