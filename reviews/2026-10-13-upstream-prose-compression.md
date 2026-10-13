# Selective upstream prose compression

The approved change adopts editorial compression while preserving discovery triggers, necessary examples, evidence requirements, and portable tool and model guidance. It changes 10 skill entrypoints and keeps five principle entrypoints unchanged. The five separately approved additions are covered in the [behavior-update review](2026-10-13-upstream-behavior-updates.md).

## Source and decisions

All entries below use source ID `cursor-pstack` from [cursor/plugins](https://github.com/cursor/plugins).

- Review date: 2026-10-13
- Previous reviewed commit: `23e4138daa01c42d4969f7a5465f82704e64f798`
- New reviewed commit: `c86f349b102feb91f1966f8a6a60882a4e601b50`
- Evidence: [immutable upstream comparison](https://github.com/cursor/plugins/compare/23e4138daa01c42d4969f7a5465f82704e64f798...c86f349b102feb91f1966f8a6a60882a4e601b50)

| Skill | Decision | Selected changes or retained guidance |
| --- | --- | --- |
| `benchmark-checklist` | partial | Shorter measurement and reporting prose; retain all seven checks, tool portability, authorization, and evidence requirements. |
| `technical-writing` | partial | Remove repeated explanation; retain four standards, examples, real symbol names, discovery, and Unslop fallback. |
| `principle-build-the-lever` | partial | Remove redundant labels; retain reproducibility, rerun safety, delegate contracts, and artifact requirements. |
| `principle-explain-the-number` | partial | Move repeated rationale beside the relevant checks; retain limiter evidence, alternative explanations, and performance-only scope. |
| `principle-minimize-reader-load` | partial | Condense the introduction; retain both axes, six rules, and the 30-second test. |
| `principle-model-the-domain` | partial | Merge repeated rationale and shorten examples; retain ownership guidance and abstraction restraint. |
| `principle-never-block-on-the-human` | partial | Shorten the introduction; retain current authorization, host permissions, and human product direction. |
| `principle-subtract-before-you-add` | partial | Remove repeated rationale and labels; retain every actionable rule. |
| `principle-test-behavior-not-implementation` | partial | Shorter assertions and fixes; retain the local plausible-defect criterion and meaningful absence checks. |
| `principle-type-system-discipline` | partial | Fold diagnostic questions into their corresponding rules; retain eight rules, cross-language examples, and partiality limits. |
| `principle-encode-lessons-in-structure` | keep | Retain the correction procedure, enforcement hierarchy, feedback loop, and anti-patterns removed upstream. |
| `principle-exhaust-the-design-space` | keep | Retain distinct prototypes and applicability exclusions removed upstream. |
| `principle-guard-the-context-window` | keep | Retain bulk-output isolation and frequently used inline resources removed upstream. |
| `principle-laziness-protocol` | keep | Retain deletion, boundary-aware flattening, signal-threading scrutiny, and small-leak guidance removed upstream. |
| `principle-redesign-from-first-principles` | keep | Retain discovery context; the longer upstream opening offers no useful body compression. |

Frontmatter, Codex invocation policies, and supporting files retain their previous content. No new dependency, command, workflow, permission, or model choice is introduced.

## Registry result

The 15 entries advance `last_reviewed_revision` to the reviewed commit. The 10 partial adoptions also advance `last_incorporated_revision` to that commit. The five keep decisions preserve `last_incorporated_revision` at `23e4138daa01c42d4969f7a5465f82704e64f798`. Baseline revisions remain unchanged. Each entry records the final customization and reason in its maintenance notes.

## Validation

The 10 edited entrypoints contain 5,135 whitespace-delimited words, down from 5,690 at harness commit `c46213e3a7600250ca35d21703f0c45c4dd54557`. That removes 555 words, about 9.8 percent. This is a text-size comparison, not a tokenizer count or a measurement of agent quality.

Count the same files from the repository root:

```sh
python3 - <<'PY'
import subprocess
from pathlib import Path

baseline = "c46213e3a7600250ca35d21703f0c45c4dd54557"
names = (
	"benchmark-checklist", "technical-writing", "principle-build-the-lever",
	"principle-explain-the-number", "principle-minimize-reader-load",
	"principle-model-the-domain", "principle-never-block-on-the-human",
	"principle-subtract-before-you-add", "principle-test-behavior-not-implementation",
	"principle-type-system-discipline",
)
before = after = 0
for name in names:
	path = f"skills/{name}/SKILL.md"
	original = subprocess.run(["git", "show", f"{baseline}:{path}"],
							  capture_output=True, text=True, check=True).stdout
	current = Path(path).read_text()
	assert original.split("---", 2)[1] == current.split("---", 2)[1], name
	before += len(original.split())
	after += len(current.split())
print(f"{len(names)} entrypoints: {before} -> {after} words")
PY
```

`python3 scripts/check.py` passed for all 41 skills and the registry. `python3 -m unittest discover -s scripts/tests` passed all 221 tests using temporary fixtures outside the sandbox's known Node-to-Git execution restriction. `git diff --check` passed. Direct comparisons confirm unchanged frontmatter, inline code examples, unrelated registry records, and source baseline revisions.

This record covers prose-only changes. The parser change and subsequent combined verification are covered in the behavior-update review. No agent-behavior evaluation was performed.
