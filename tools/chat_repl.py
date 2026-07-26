"""
Tarka Developer REPL

A command-line interface for testing the Tarka backend during development.

Purpose:
- Test FastAPI endpoints
- Validate planner behavior
- Verify tool execution
- Debug runtime responses

This utility is intended for development only and may be replaced by the
official frontend in future releases.
"""
"""Interactive chat REPL for Tarka. Type 'exit' or 'quit' to leave."""

import urllib.request
import json
import sys

BASE = "http://localhost:8000/chat"


def chat(message: str) -> str:
    """Send a message to the agent."""
    data = json.dumps({"message": message}).encode("utf-8")
    req = urllib.request.Request(
        BASE,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read())["response"]


def main() -> None:
    print("=" * 60)
    print("  Aryntra Tarka — Interactive Chat")
    print("  Type your message. Type 'exit' or 'quit' to leave.")
    print("=" * 60)

    while True:
        try:
            message = input("\nYou > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not message:
            continue
        if message.lower() in {"exit", "quit", "bye"}:
            print("Goodbye!")
            break

        try:
            print("Tarka is thinking...")
            response = chat(message)
            print(f"\nTarka > {response}")
        except Exception as e:
            print(f"\n[ERROR] {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()