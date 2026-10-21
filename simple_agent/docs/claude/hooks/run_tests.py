"""PostToolUse hook: run pytest after Claude edits a Python file.

The edit has already happened, so this hook cannot undo it.
Exit 2 sends the failing test output back to Claude so it can fix the problem.
Exit 0 means all is fine (or the file was not Python).
"""

import json
import os
import subprocess
import sys


def main() -> int:
    event = json.load(sys.stdin)
    path = event.get("tool_input", {}).get("file_path", "")
    if not path.endswith(".py"):
        return 0  # only test after Python edits

    # Never call real LLM APIs from tests.
    env = {k: v for k, v in os.environ.items()
           if k not in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")}

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-x", "--no-header"],
        cwd=os.environ.get("CLAUDE_PROJECT_DIR", "."),
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode in (0, 5):  # 5 = no tests found yet
        return 0

    print("Tests failed after this edit:\n" + result.stdout[-3000:], file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
