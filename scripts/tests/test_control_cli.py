"""Exercise the shipped PTY recipe against a real interactive child."""

import os
from pathlib import Path
import subprocess
import sys
import unittest


SKILL = Path(__file__).resolve().parents[2] / "skills/control-cli/SKILL.md"


@unittest.skipUnless(os.name == "posix", "PTY recipe needs a POSIX terminal")
class PtyRecipeTests(unittest.TestCase):
    def probe(self, child):
        recipe = SKILL.read_text().split("```python\n", 1)[1].split("\n```", 1)[0]
        recipe = recipe.replace('["<command>", "<arg>"]', repr([sys.executable, "-uc", child]))
        recipe = recipe.replace("<ready text>", "READY").replace("<help response text>", "Available commands")
        recipe = recipe.replace("+ 30", "+ 0.5")
        return subprocess.run([sys.executable, "-c", recipe], capture_output=True, text=True, timeout=5)

    def test_reads_response_after_sending_help(self):
        child = """print('Available commands at startup')
print('READY')
if input() == 'help':
    print('Available commands after help')
"""
        result = self.probe(child)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Available commands after help", result.stdout)

    def test_missing_readiness_or_reply_fails(self):
        for startup in ("", "print('Available commands at startup'); print('READY')"):
            with self.subTest(startup=startup):
                child = f"{startup}\nimport time\ntime.sleep(10)"
                result = self.probe(child)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("timed out", result.stderr.lower())
