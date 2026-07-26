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

import json
import os
import sys
import urllib.request

# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

REPL_VERSION = "0.3.3"

# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------

BASE_URL = "http://localhost:8000/chat"


def chat(message: str) -> str:
    """Send a message to the Tarka backend and return the response."""
    data = json.dumps({"message": message}).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read())["response"]


# ---------------------------------------------------------------------------
# Built-in command handlers
# ---------------------------------------------------------------------------

def cmd_help() -> None:
    """Print available REPL commands."""
    print(
        "\nAvailable Commands\n"
        "\n"
        "  help\n"
        "  clear\n"
        "  exit\n"
        "  version\n"
        "\n"
        "Type anything else to chat with Tarka."
    )


def cmd_clear() -> None:
    """Clear the terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")


def cmd_exit() -> None:
    """Exit the REPL gracefully."""
    print("\nGoodbye!\n")
    print("Session ended.")
    sys.exit(0)


def cmd_version() -> None:
    """Print the REPL version."""
    print(f"\nTarka Developer REPL\n")
    print(f"Version:\n{REPL_VERSION}")


# ---------------------------------------------------------------------------
# Command registry
#
# Maps every recognized command keyword to its handler function.
# To add a new command: add an entry here. No other changes required.
# ---------------------------------------------------------------------------

COMMANDS: dict[str, callable] = {
    "help":    cmd_help,
    "clear":   cmd_clear,
    "cls":     cmd_clear,
    "exit":    cmd_exit,
    "quit":    cmd_exit,
    "bye":     cmd_exit,
    "version": cmd_version,
}


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def dispatch_command(raw: str) -> bool:
    """
    Check whether raw input matches a built-in command.

    If it does, execute the handler and return True.
    If it does not, return False so the caller can forward to the backend.

    Normalization:
        - Strip surrounding whitespace
        - Lowercase
        - Single-token match only (commands are never multi-word)
    """
    normalized = raw.strip().lower()

    handler = COMMANDS.get(normalized)

    if handler is None:
        return False

    handler()
    return True


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("  Tarka Developer REPL  -  v" + REPL_VERSION)
    print("  Type 'help' for available commands.")
    print("=" * 60)

    while True:
        try:
            raw = input("\nYou > ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!\n")
            print("Session ended.")
            break

        if not raw.strip():
            continue

        if dispatch_command(raw):
            continue

        try:
            print("\nTarka is thinking...")
            response = chat(raw.strip())
            print(f"\nTarka > {response}")
        except Exception as exc:
            print(f"\n[ERROR] {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
