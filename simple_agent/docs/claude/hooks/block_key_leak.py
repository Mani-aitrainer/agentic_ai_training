"""PreToolUse hook: stop Claude from writing an API key into a file.

Claude Code sends the tool call as JSON on stdin, for example:
    {"tool_name": "Write", "tool_input": {"file_path": "agent.py", "content": "..."}}

Exit 0 lets the edit go ahead.
Exit 2 blocks it, and the message on stderr is shown to Claude.
"""

import json
import re
import sys
from pathlib import Path

# Real-looking secrets, not just the variable names.
PATTERNS = {
    "Anthropic key": r"sk-ant-[A-Za-z0-9_\-]{20,}",
    "Google/Gemini key": r"AIza[0-9A-Za-z_\-]{30,}",
    "Hard-coded key variable": r"(ANTHROPIC|GEMINI|GOOGLE)_API_KEY\s*=\s*['\"][^'\"\s]{8,}['\"]",
}


def text_being_written(tool_input: dict) -> str:
    """Collect the new text from Write, Edit, and MultiEdit calls."""
    parts = [tool_input.get("content", ""), tool_input.get("new_string", "")]
    parts += [e.get("new_string", "") for e in tool_input.get("edits", [])]
    return "\n".join(parts)


def main() -> int:
    event = json.load(sys.stdin)
    path = event.get("tool_input", {}).get("file_path", "")
    if Path(path).name == ".env":
        return 0  # .env is gitignored: the right place for keys
    text = text_being_written(event.get("tool_input", {}))
    for label, pattern in PATTERNS.items():
        if re.search(pattern, text):
            print(
                f"Blocked: {label} found in the edit to {path}. "
                "Put keys in .env and read them with os.getenv instead.",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
