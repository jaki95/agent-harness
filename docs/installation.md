# Installation and upgrades

## Requirements and current status

Use Node 22.20 or newer, npm/npx, Git, and access to the private `jaki95/agent-harness` GitHub repository. The tested Skills CLI version is `1.7.0`; commands below pin the installer independently of the harness version. Existing Git credentials, an authenticated GitHub CLI, or SSH can provide repository access. No public directory listing is required.

The collection includes `grill-me`, `harness`, `unslop`, and `technical-writing`. The following command lists skills at the remote revision, so unmerged local changes are not available through `main` yet:

```sh
npx skills@1.7.0 add jaki95/agent-harness --list
```

The `grill-me` examples on `main` are available now. Release-tag examples remain illustrative until those versions are published.

## Personal installation: follow approved changes on main

Install globally for your personal Codex setup:

```sh
npx skills@1.7.0 add 'jaki95/agent-harness#main' --skill grill-me --agent codex --global
npx skills@1.7.0 update grill-me --global
```

For Harness's full writing workflow, select all three communication skills. The CLI does not install other skills automatically.

```sh
npx skills@1.7.0 add 'jaki95/agent-harness#main' --skill harness unslop technical-writing --agent codex --global
npx skills@1.7.0 update harness --global
npx skills@1.7.0 update unslop --global
npx skills@1.7.0 update technical-writing --global
```

Harness can also be installed alone:

```sh
npx skills@1.7.0 add 'jaki95/agent-harness#main' --skill harness --agent codex --global
```

Harness resolves `unslop` and `technical-writing` by name through the host's skill catalog. Their installation directories can differ from Harness's directory. If a writing skill is unavailable, Harness reports its name and continues with its own communication rules. Bundled playbooks remain available. The [source collection](https://github.com/jaki95/agent-harness) identifies where the separate skills can be obtained; it does not load or install them automatically.

For other supported tools, change `--agent`. For project-local installation, run inside the project and omit `--global`; use `--project` on the update command. The CLI uses symlinks to a canonical installed copy by default; `--copy` selects independent copies where preferred.

Select skill names explicitly so you control what is installed or updated. Make edits in the harness source repository, then distribute them through the CLI. An update can replace installed files, including edits made directly to those files.

## Work projects: pin a release

After a real `v0.1.0` release exists, run inside the consuming project:

```sh
npx skills@1.7.0 add 'jaki95/agent-harness#v0.1.0' --skill grill-me --agent codex --copy
```

Commit `skills-lock.json` and the generated project skill files so the project records its selection. Review the consuming project's diff before committing updates. Use `--agent` selections appropriate to that project; avoid a global installation for a project-specific pin.

## Explicit upgrade and rollback

Pinned refs are preserved by the CLI. `skills update` does not select the next release tag. To adopt a newer release, install explicitly from that tag:

```sh
npx skills@1.7.0 add 'jaki95/agent-harness#v0.2.0' --skill grill-me --agent codex --copy
```

To roll back, run the same command with the earlier tag and review the resulting files and lockfile. Upgrade commands target this harness repository, not the upstream authors recorded in the maintenance registry.

## Source and installation boundaries

The CLI distributes a skill's directory, including its runtime resources. It does not distribute sibling `registry/` or `reviews/` directories, or this repository's `AGENTS.md`. Top-level maintenance scripts require a repository clone. Keep scripts needed by an installed skill inside `skills/<name>/scripts/`.

The Harness writing skills preserve explicit-only upstream metadata. They also provide Codex's `agents/openai.yaml` invocation policy. Invoke Harness as `$harness` in Codex. Hosts that expose slash commands can use `/harness`. Cursor's `mode` and `reminder` metadata is retained but does not implement those native features in other hosts.

Our integration test verifies tagged installs and upgrades with disposable Git repositories. It installs all owned skills into one temporary project and Harness alone into another. It checks that the standalone package includes its playbooks and invocation policy, that bundled file references stay inside the package, and that separate writing skills are not installed automatically. It does not modify user-wide skill directories or publish local changes.

## References

- [Skills CLI v1.7.0 documentation](https://github.com/vercel-labs/skills/blob/v1.7.0/README.md)
- [Source ref parsing](https://github.com/vercel-labs/skills/blob/v1.7.0/src/source-parser.ts)
- [Update source and ref handling](https://github.com/vercel-labs/skills/blob/v1.7.0/src/update-source.ts)
- [Project lockfile](https://github.com/vercel-labs/skills/blob/v1.7.0/src/local-lock.ts)
