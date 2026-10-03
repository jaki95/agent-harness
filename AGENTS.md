# Working on agent-harness

- Keep shared skills and scripts portable across personal and work projects.
- Never import or install existing skills unless the user requests that specific adaptation.
- Treat public skills as references. Customize instructions deliberately and record sources, pinned revisions, and the changes made.
- Begin upstream imports with a faithful baseline and only the user's explicitly requested edits. Present proposed instruction or behavior changes separately and apply them only after agreement.
- Keep skills narrowly scoped, with clear triggers and explicit tool assumptions.
- Keep runtime content in `skills/`. Store provenance, customizations, and upstream revision tracking in `registry/skills.json`. Use optional `reviews/` records for consequential upstream adoption decisions; use Git and PRs for ordinary change history. Do not copy maintenance records into runtime skill packages.
- Keep employer-specific material, credentials, project paths, and private data out of shared assets. Store project-specific instructions with the project.
- Use Python's standard library for maintenance scripts unless a dependency provides a concrete benefit.
- Resolve filesystem paths relative to the repository or explicit arguments, never a particular user's home directory.
- Do not install into user-wide agent directories as a side effect of validation or tests.
- Before completing a change, run `python3 scripts/check.py` and `python3 -m unittest discover -s scripts/tests`.
- For installation, release, or CLI dependency changes, also run `npm ci --ignore-scripts` and `npm run test:skills`. The test uses temporary fixtures and project-local installs.
- Release through the manual Release harness workflow on `main`. Never move an existing release tag or publish an empty skill collection.
- Update documentation when the repository's conventions or commands change.
