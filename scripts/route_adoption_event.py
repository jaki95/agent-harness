"""Select a numeric wake hint from a public GitHub event. The worker verifies its source again."""

import json
import os
from pathlib import Path
import re

from monitor_upstream import MARKER, authored_by, monitor_publishers


def adoption_issue(event_name, event, repository, owner, monitor_login=None):
    if event.get("repository", {}).get("full_name") != repository:
        return None
    if event_name == "issue_comment":
        issue = event["issue"]
        comment = event["comment"]
        if (event["action"] != "created" or "pull_request" in issue or issue["state"] != "open"
                or not owner or comment["user"]["login"].casefold() != owner.casefold()
                or not comment.get("created_at") or comment["created_at"] != comment.get("updated_at")
                or not authored_by(issue, monitor_publishers(repository, monitor_login))
                or (issue.get("body") or "").splitlines()[:1] != [MARKER]):
            return None
        number = issue["number"]
        return number if type(number) is int and number > 0 else None

    if event_name == "workflow_run" and event["action"] == "completed":
        run = event["workflow_run"]
        if (run["name"] not in {"Check harness", "Check Statechart", "Release harness"}
                or (run.get("head_repository") or {}).get("full_name") != repository):
            return None
        branch = run["head_branch"]
    elif event_name == "pull_request_target" and event["action"] == "closed":
        pr = event["pull_request"]
        if (pr["base"]["ref"] != "main" or (pr["head"].get("repo") or {}).get("full_name") != repository):
            return None
        branch = pr["head"]["ref"]
    else:
        return None
    match = re.fullmatch(r"adoption/issue-([1-9][0-9]*)-approval-[1-9][0-9]*", branch or "")
    return int(match[1]) if match else None


if __name__ == "__main__":
    issue = adoption_issue(os.environ["GITHUB_EVENT_NAME"],
                           json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text()),
                           os.environ["GITHUB_REPOSITORY"], os.environ["ADOPTION_OWNER"],
                           os.environ.get("UPSTREAM_MONITOR_LOGIN"))
    if issue:
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
            out.write(f"issue={issue}\n")
