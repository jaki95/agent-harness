# Restore the requested upstream baseline

- Skill: `grill-me`
- Source ID: `matt-pocock-grilling`
- Review date: 2026-10-03
- Previous and current reviewed commit: `d81f3a183412e71a5b1e84ca21bc1a35eea03a60`
- Decision: adopt the upstream files unchanged except for the requested names

The user rejected the agent's unrequested rewrites. Restored the recorded upstream `SKILL.md` and `agents/openai.yaml`, changing only `name: grilling` to `name: grill-me` and `display_name: "Grilling"` to `display_name: "Grill Me"`.

The instructions, description, round formatting, subagent requirement, and completion condition are preserved verbatim. Removed the conditional-delegation and explicit-deferral additions. The original implementation record remains in Git and in the earlier review note for historical accuracy.

Compared both runtime files byte for byte with the pinned upstream after reversing only those two naming substitutions. Updated the harness validator to accept the upstream plain description without quoting or rewriting it. Evaluation cases now describe the upstream behavior; live multi-turn evaluation remains pending.

Upstream baseline, last reviewed, and last incorporated revisions remain unchanged because this correction uses the same source commit. Future customizations must be presented separately and agreed with the user.
