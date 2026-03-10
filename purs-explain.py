#!/usr/bin/env python3
"""purs-explain: AI-powered PureScript compiler error explainer.

Usage:
  # Wrap a spago build — runs the build, explains any errors
  python3 purs-explain.py

  # Pipe errors directly
  spago build 2>&1 | python3 purs-explain.py --stdin

  # Explain a single error from clipboard / paste
  python3 purs-explain.py --paste

Requires ANTHROPIC_API_KEY environment variable.
"""

import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.error
import textwrap

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = "claude-haiku-4-5-20251001"  # fast and cheap for error explanation

SYSTEM_PROMPT = """\
You are a PureScript compiler error explainer. A developer has encountered a \
compiler error and needs to understand what went wrong and how to fix it.

Rules:
- Read the error bottom-up: the specific mismatch is at the end, the context is above.
- Explain in 2-4 sentences. Lead with what's wrong, then say how to fix it.
- If the error involves a type mismatch, state the two types clearly.
- If it's a kind error, explain what kind was expected vs provided.
- If it's a missing instance, say which instance is needed and suggest where to add it.
- If it's an import/module error, be specific about what's missing.
- Reference the specific file and line if present in the error.
- Do NOT repeat the error back. The developer can see it.
- Do NOT explain PureScript basics unless directly relevant to this specific error.
- Be concise and direct. No filler.
"""

def call_claude(error_text: str) -> str:
    """Send an error to Claude and get an explanation."""
    if not API_KEY:
        return "(Set ANTHROPIC_API_KEY to enable AI explanations)"

    payload = json.dumps({
        "model": MODEL,
        "max_tokens": 512,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": error_text}]
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read())
            return body["content"][0]["text"]
    except urllib.error.HTTPError as e:
        return f"(API error: {e.code} {e.reason})"
    except Exception as e:
        return f"(Error calling API: {e})"


def split_errors(text: str) -> list[str]:
    """Split compiler output into individual errors."""
    # PureScript errors start with "[ERROR ...]" or "Error found:" or a file path with line number
    # spago prefixes with "[n of m] Compiling ...
    # Actual errors have this shape:
    #   Error found:
    #   in module Foo.Bar
    #   at src/Foo/Bar.purs:10:5 - 10:20 (line 10, column 5 - line 10, column 20)
    #
    #     <context lines>
    #
    #     <actual error>

    # Split on blank-line-separated "Error found:" blocks
    errors = []
    current = []

    for line in text.split("\n"):
        if line.strip().startswith("Error found:") and current:
            errors.append("\n".join(current))
            current = []
        current.append(line)

    if current:
        # Only add if it looks like an error (not just build success messages)
        block = "\n".join(current)
        if "Error found:" in block or "Could not match" in block or "Unknown" in block:
            errors.append(block)

    # If no structured errors found, treat the whole thing as one block
    # (handles edge cases like purs compile output without "Error found:")
    if not errors and ("error" in text.lower() or "could not" in text.lower()):
        errors = [text]

    return errors


def format_explanation(error: str, explanation: str) -> str:
    """Format an error with its explanation."""
    # Extract file/line for a header if possible
    loc_match = re.search(r'at (\S+\.purs:\d+:\d+)', error)
    header = loc_match.group(1) if loc_match else "Error"

    separator = "\033[36m" + "─" * 60 + "\033[0m"  # cyan line
    err_lines = error.strip()
    expl = "\033[33m" + explanation + "\033[0m"  # yellow explanation

    return f"""{separator}
{err_lines}

\033[1m→ {header}\033[0m
{expl}
"""


def run_build() -> str:
    """Run spago build and capture output."""
    result = subprocess.run(
        ["spago", "build"],
        capture_output=True,
        text=True,
    )
    # PureScript errors go to stderr
    output = result.stderr
    if result.stdout and not output:
        output = result.stdout
    return output, result.returncode


def main():
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        print(__doc__)
        sys.exit(0)

    # Get error text
    if "--stdin" in args:
        text = sys.stdin.read()
    elif "--paste" in args:
        print("Paste the error (Ctrl-D when done):")
        text = sys.stdin.read()
    else:
        # Default: run spago build
        print("\033[2mRunning spago build...\033[0m")
        text, code = run_build()
        if code == 0 and "Error found:" not in text:
            print("\033[32mBuild succeeded.\033[0m")
            if text.strip():
                print(text)
            sys.exit(0)

    errors = split_errors(text)

    if not errors:
        print("No errors found in output.")
        sys.exit(0)

    print(f"\033[1m{len(errors)} error{'s' if len(errors) != 1 else ''} found. Explaining...\033[0m\n")

    for i, error in enumerate(errors):
        explanation = call_claude(error)
        print(format_explanation(error, explanation))

    # Summary
    if len(errors) > 1:
        print(f"\033[2m{len(errors)} errors explained.\033[0m")


if __name__ == "__main__":
    main()
