# Installation and upgrades

## Requirements and current status

Use Node 22.20 or newer, npm/npx, Git, and access to the private `jaki95/agent-harness` GitHub repository. The tested Skills CLI version is `1.7.0`; commands below pin the installer independently of the harness version. Existing Git credentials, an authenticated GitHub CLI, or SSH can provide repository access. No public directory listing is required.

No skills have been added yet. The following read-only discovery command is usable now, but reports no skills until the first owned skill is added:

```sh
npx skills@1.7.0 add jaki95/agent-harness --list
```

The `grilling` examples below describe a future skill and future release tags. Neither currently exists in this repository.

## Personal installation: follow approved changes on main

Install globally for your personal Codex setup:

```sh
npx skills@1.7.0 add 'jaki95/agent-harness#main' --skill grilling --agent codex --global
npx skills@1.7.0 update grilling --global
```

For other supported tools, change `--agent`. For project-local installation, run inside the project and omit `--global`; use `--project` on the update command. The CLI uses symlinks to a canonical installed copy by default; `--copy` selects independent copies where preferred.

Select skill names explicitly so you control what is installed or updated. Make edits in the harness source repository, then distribute them through the CLI. An update can replace installed files, including edits made directly to those files.

## Work projects: pin a release

After a real `v0.1.0` release exists, run inside the consuming project:

```sh
npx skills@1.7.0 add 'jaki95/agent-harness#v0.1.0' --skill grilling --agent codex --copy
```

Commit `skills-lock.json` and the generated project skill files so the project records its selection. Review the consuming project's diff before committing updates. Use `--agent` selections appropriate to that project; avoid a global installation for a project-specific pin.

## Explicit upgrade and rollback

Pinned refs are preserved by the CLI. `skills update` does not select the next release tag. To adopt a newer release, install explicitly from that tag:

```sh
npx skills@1.7.0 add 'jaki95/agent-harness#v0.2.0' --skill grilling --agent codex --copy
```

To roll back, run the same command with the earlier tag and review the resulting files and lockfile. Upgrade commands target this harness repository, not the upstream authors recorded in the maintenance registry.

## Source and installation boundaries

The CLI distributes a skill's directory, including its runtime resources. It does not distribute sibling `registry/`, `evaluations/`, or `reviews/` directories, or this repository's `AGENTS.md`. Top-level maintenance scripts require a repository clone. Keep scripts needed by an installed skill inside `skills/<name>/scripts/`.

Our integration test verifies tagged installs and upgrades with disposable Git repositories. Private GitHub source discovery is checked separately; a real harness skill installation can be verified once the first skill exists.

## References

- [Skills CLI v1.7.0 documentation](https://github.com/vercel-labs/skills/blob/v1.7.0/README.md)
- [Source ref parsing](https://github.com/vercel-labs/skills/blob/v1.7.0/src/source-parser.ts)
- [Update source and ref handling](https://github.com/vercel-labs/skills/blob/v1.7.0/src/update-source.ts)
- [Project lockfile](https://github.com/vercel-labs/skills/blob/v1.7.0/src/local-lock.ts)
