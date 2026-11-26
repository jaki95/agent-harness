"""Run the offline Statechart tests with a private temporary directory."""

import os
from pathlib import Path
import subprocess
import tempfile


SUITE = Path(__file__).resolve().parents[1] / "tests" / "statechart"
TESTS = ("chart", "cli", "messages", "pipeline")


def main():
    with tempfile.TemporaryDirectory(prefix="harness-statechart-") as scratch:
        env = {**os.environ, "TMPDIR": scratch, "TMP": scratch, "TEMP": scratch}
        return subprocess.run(
            [os.environ.get("npm_node_execpath") or "node", "--disable-warning=ExperimentalWarning",
             "--test", *(f"test/{name}.test.ts" for name in TESTS)],
            cwd=SUITE, env=env,
        ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
