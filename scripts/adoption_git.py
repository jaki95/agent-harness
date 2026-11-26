"""GitHub primitives used by the trusted upstream adoption worker."""

import base64
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import quote, urlencode

import monitor_upstream as monitor


class Stopped(ValueError):
    """The worker lacks evidence required to proceed with a change."""


def sha(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
        raise Stopped("GitHub did not return an exact commit or tree")
    return value


class AdoptionGit:
    def __init__(self, repository, github):
        if not re.fullmatch(r"[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+", repository):
            raise ValueError("Invalid GitHub repository")
        self.repo = repository
        self.github = github

    def api(self, method, resource, payload=None):
        return self.github.request(method, f"repos/{self.repo}/{resource}", payload)

    def ref(self, branch):
        ref = f"refs/heads/{branch}"
        rows = self.api("GET", "git/matching-refs/heads/" + quote(branch, safe="/"))
        matches = [r for r in rows if r["ref"] == ref]
        if not matches:
            return None
        if len(matches) != 1 or matches[0]["object"]["type"] != "commit":
            raise Stopped("Branch reference is ambiguous")
        return sha(matches[0]["object"]["sha"])

    def entries(self, base, paths):
        # Only visit directories on an approved path. A truncated tree cannot establish absence.
        tree = sha(self.api("GET", f"git/commits/{sha(base)}")["tree"]["sha"])
        cache, result = {}, {}
        for path in paths:
            parent = tree
            parts = path.split("/")
            selected = None
            for index, key in enumerate(parts):
                if parent not in cache:
                    data = self.api("GET", f"git/trees/{parent}")
                    if data.get("truncated") is not False:
                        raise Stopped("GitHub returned an incomplete tree")
                    cache[parent] = {entry["path"]: entry for entry in data["tree"]}
                selected = cache[parent].get(key)
                if selected is None:
                    break
                if index < len(parts) - 1:
                    if selected["type"] != "tree":
                        raise Stopped(f"Unexpected non-directory on path {path}")
                    parent = sha(selected["sha"])
                elif selected["type"] != "blob" or selected["mode"] not in ("100644", "100755"):
                    raise Stopped(f"Unexpected file type for {path}")
            result[path] = selected
        return tree, result

    def read_blob(self, entry):
        response = self.api("GET", f"git/blobs/{sha(entry['sha'])}")
        if response.get("encoding") != "base64" or response.get("truncated") or response["size"] > 1024 * 1024:
            raise Stopped("Expected a bounded regular text file")
        return base64.b64decode(response["content"]).decode("utf-8")

    def commit(self, base, old, tree, updates, title):
        entries = [{"path": p, "mode": mode, "type": "blob",
                    **({"sha": None} if text is None else {"content": text})}
                   for p, (mode, text) in sorted(updates.items())]
        new_tree = sha(self.api("POST", "git/trees", {"base_tree": tree, "tree": entries})["sha"])
        parents = list(dict.fromkeys([p for p in (old, base) if p]))
        commit = self.api("POST", "git/commits", {"message": title, "tree": new_tree, "parents": parents})
        return sha(commit["sha"])

    def publish(self, branch, old, new):
        current = self.ref(branch)
        if current == new:
            return
        if current != old:
            raise Stopped("The approval branch changed outside the worker")
        if old is None:
            self.api("POST", "git/refs", {"ref": "refs/heads/" + branch, "sha": new})
        else:
            self.api("PATCH", "git/refs/heads/" + branch, {"sha": new, "force": False})
        if self.ref(branch) != new:
            raise Stopped("GitHub did not confirm the published commit")

    def pull(self, branch, known=None):
        owner = self.repo.split("/")[0]
        if known:
            values = [self.api("GET", f"pulls/{int(known)}")]
        else:
            query = urlencode({"head": f"{owner}:{branch}", "state": "all", "per_page": 2})
            values = self.api("GET", "pulls?" + query)
        if not values:
            return None
        if len(values) != 1:
            raise Stopped("Multiple pull requests share the adoption branch")
        p = values[0]
        for side, ref in (("head", branch), ("base", "main")):
            if (not p[side].get("repo") or p[side]["repo"]["full_name"].casefold() != self.repo.casefold()
                    or p[side]["ref"] != ref):
                raise Stopped("Pull request repository or branch no longer matches")
        return {"pr": p["number"], "url": p["html_url"], "head": sha(p["head"]["sha"]),
                "merged": p.get("merged_at") is not None, "closed": p["state"] == "closed"}

    def open_pull(self, branch, title, body):
        self.api("POST", "pulls", {"head": branch, "base": "main", "title": title, "body": body})
        found = self.pull(branch)
        if not found:
            raise Stopped("GitHub did not confirm the adoption PR")
        return found

    def helper(self, name, args):
        # Use the existing publication/receipt tools from the trusted installation.
        root = Path(__file__).resolve().parents[1] / "skills/harness/scripts"
        gh = Path(shutil.which(self.github.gh) or self.github.gh).resolve()
        env = dict(os.environ, PATH=str(gh.parent) + os.pathsep + os.environ.get("PATH", ""))
        if shutil.which("gh", path=env["PATH"]) != str(gh):
            raise Stopped("The configured GitHub CLI must be available to the receipt and merge helpers")
        result = subprocess.run([sys.executable, str(root / name), *args], capture_output=True,
                                text=True, timeout=150, env=env)
        if result.returncode not in (0, 3) and not (name == "pr_receipt.py" and result.returncode == 2 and result.stdout):
            raise Stopped(f"{name} stopped: {result.stderr.strip()[:300]}")
        return json.loads(result.stdout)

    def checks(self, pr, head, base, workflows):
        receipt = self.helper("pr_receipt.py", [str(pr), "--repo", self.repo])
        after = receipt.get("after") or {}
        if (receipt["capture_status"] != "complete" or after.get("head_sha") != head
                or after.get("base_sha") != base or after.get("state") != "OPEN"):
            return "settling", [], "Waiting for a complete receipt on the current head and base"
        if after["review_decision"] == "CHANGES_REQUESTED" or any(not x["resolved"] for x in receipt["review_threads"]):
            return "blocked", [], "Resolve requested changes and outstanding review threads first"

        pending = False
        failures, passed_runs = [], []
        for workflow in workflows:
            query = urlencode({"head_sha": head, "event": "pull_request", "per_page": 10})
            result = self.api("GET", f"actions/workflows/{workflow}/runs?{query}")
            runs = [r for r in result["workflow_runs"] if r["head_sha"] == head and r["event"] == "pull_request"
                    and r["path"] == f".github/workflows/{workflow}"
                    and str(r.get("head_repository", {}).get("full_name", "")).casefold() == self.repo.casefold()]
            if not runs:
                pending = True
                continue
            run = max(runs, key=lambda r: (r["id"], r["run_attempt"]))
            if run["status"] != "completed":
                pending = True
            elif run.get("conclusion") != "success":
                failures.append({"workflow": workflow, "id": run["id"], "conclusion": run["conclusion"],
                                 "attempt": run["run_attempt"]})
            else:
                passed_runs.append(run["id"])
        if pending:
            return "waiting", [], "Waiting for final-head CI"
        if failures:
            return "failed", failures, "Final-head CI failed"
        failed = [c.get("name", "unnamed") for c in receipt["current_checks"] if c["observed_state"] == "fail"]
        if failed:
            return "blocked", [], "Additional final-head checks failed: " + ", ".join(failed)
        if any(c["observed_state"] != "pass" for c in receipt["current_checks"]):
            return "waiting", [], "Waiting for all reported final-head checks to pass"
        if after["merge_state"] == "UNKNOWN" or after["mergeable"] == "UNKNOWN":
            return "settling", [], "GitHub is computing final-head mergeability"
        if after["merge_state"] != "CLEAN" or after["mergeable"] != "MERGEABLE":
            return "blocked", [], "Repository rules or merge conflicts prevent automatic merge"
        return "passed", passed_runs, "Final-head CI is green"

    def witnesses(self, head, run_ids):
        cases = []
        for run_id in run_ids:
            run = self.api("GET", f"actions/runs/{int(run_id)}")
            if run["head_sha"] != head or run["conclusion"] != "success":
                raise Stopped("CI witness no longer matches a passing run at this head")
            output = monitor.run([self.github.gh, "run", "view", str(run_id), "--repo", self.repo, "--log"],
                                 limit=8 * 1024 * 1024).decode(errors="replace")
            for line in output.splitlines():
                fields = line.split("\t", 2)
                if (len(fields) != 3 or fields[1] not in ("Test maintenance scripts", "Run npm run test:statechart")
                        or re.search(r"#\s*(SKIP|TODO)\b", fields[2], re.IGNORECASE)):
                    continue
                case = re.search(r"(?:[0-9]Z\s+)(?:✔ (.{1,500})|ok [1-9][0-9]* - (.{1,500})|"
                                 r"(test_[^ ]{1,200} \([^)]{1,200}\) \.\.\. ok))$", line)
                if case:
                    cases.append(f"run {run_id}: " + next(part for part in case.groups() if part))
                if len(cases) >= 1200:
                    return cases
        return cases

    def failure_evidence(self, failures):
        result = []
        for run in failures:
            jobs = self.api("GET", f"actions/runs/{int(run['id'])}/attempts/{int(run['attempt'])}/jobs?per_page=100")
            steps = [{"job": job["name"], "step": step["name"]} for job in jobs["jobs"]
                     for step in job.get("steps", []) if step["conclusion"] == "failure"]
            lines = []
            try:
                log = monitor.run([self.github.gh, "run", "view", str(run["id"]), "--repo", self.repo,
                                   "--attempt", str(run["attempt"]), "--log-failed"], limit=4 * 1024 * 1024)
                for line in log.decode(errors="replace").splitlines():
                    if re.search(r"(?:FAIL:|FAILED |AssertionError|Assertion failed|Error:|not ok [0-9]+)", line):
                        lines.append(line[-800:])
                        if len(lines) == 12:
                            break
            except monitor.MonitorError:
                # Workflow and failing step names remain available when logs have expired.
                pass
            result.append({**run, "failed_steps": steps, "diagnostics": lines})
        return result

    def rerun(self, run_id):
        # This endpoint returns 201 with an empty body.
        monitor.run([self.github.gh, "api", "--silent", "--method", "POST",
                     f"repos/{self.repo}/actions/runs/{int(run_id)}/rerun-failed-jobs"])

    def merge(self, pr, head):
        result = self.helper("pr_publish.py", ["merge", "--repo", self.repo, str(pr), "--expected-head", head])
        if result.get("head_sha") != head or result.get("number") != pr:
            raise Stopped("Merge helper returned an unexpected PR or head")
        if result["status"] not in ("merged", "pending", "enqueued"):
            raise Stopped("Unexpected GitHub merge request state")
        details = result.get("details", {})
        return {"status": result["status"], "uuid": details.get("uuid")}

    def merge_status(self, pr, head, request):
        identity = request.get("uuid")
        if identity and re.fullmatch(r"[a-f0-9-]{36}", identity):
            value = self.api("GET", f"pulls/{int(pr)}/merge-async/{identity}")
            details = value.get("details", {})
            if details.get("expected_head_sha", head) != head:
                raise Stopped("Merge request belongs to a different head")
            return value["status"]
        query = ("query($o:String!,$r:String!,$p:Int!) {repository(owner:$o,name:$r) "
                 "{pullRequest(number:$p){headRefOid merged mergeQueueEntry{state}}}}")
        owner, repo = self.repo.split("/")
        value = self.github.request("POST", "graphql", {"query": query, "variables": {"o": owner, "r": repo, "p": pr}})
        try:
            entry = value["data"]["repository"]["pullRequest"]
        except (KeyError, TypeError):
            raise Stopped("GitHub did not confirm merge queue membership") from None
        if entry["headRefOid"] != head:
            raise Stopped("Merge queue head no longer matches the approved commit")
        if entry["merged"]:
            return "merged"
        queue = entry["mergeQueueEntry"]
        if not queue:
            return "unconfirmed"
        if queue.get("state") in ("QUEUED", "AWAITING_CHECKS", "MERGEABLE", "LOCKED"):
            return "enqueued"
        return "failed" if queue.get("state") == "UNMERGEABLE" else "unconfirmed"

    def attempt(self, run):
        value = self.api("GET", f"actions/runs/{int(run)}")
        return value["run_attempt"], value["status"]
