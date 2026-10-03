# Working on agent-harness

- Keep shared skills and scripts portable across personal and work projects.
- Never import or install existing skills unless the user requests that specific adaptation.
- Treat public skills as references. Customize instructions deliberately and record sources, pinned revisions, licenses, and the changes made.
- Keep skills narrowly scoped, with clear triggers, explicit tool assumptions, and representative evaluation cases.
- Keep employer-specific material, credentials, project paths, and private data out of shared assets. Store project-specific instructions with the project.
- Use Python's standard library for maintenance scripts unless a dependency provides a concrete benefit.
- Resolve filesystem paths relative to the repository or explicit arguments, never a particular user's home directory.
- Do not install into user-wide agent directories as a side effect of validation or tests.
- Before completing a change, run `python3 scripts/check.py` and `python3 -m unittest discover -s scripts/tests`.
- Update documentation when the repository's conventions or commands change.
