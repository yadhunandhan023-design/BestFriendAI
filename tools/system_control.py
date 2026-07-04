"""
tools/system_control.py

Lets VARNI open applications and search files on your system.
SAFETY DESIGN: this module only ever DESCRIBES an action — it never
executes anything on its own. The caller (main.py) is responsible
for asking the user for confirmation before calling execute_action().
This keeps "decide to act" and "actually act" as two separate,
auditable steps.
"""

import glob
import os
import subprocess

from scripts.logger import get_logger

logger = get_logger(__name__)

# Only these apps can be opened — an explicit allowlist, not a
# free-for-all "run any command" system. Add more as you need them.
ALLOWED_APPS = {
    "firefox": "firefox",
    "chrome": "google-chrome",
    "chromium": "chromium",
    "terminal": "kitty",
    "files": "nautilus",
    "file manager": "nautilus",
    "text editor": "gedit",
    "calculator": "gnome-calculator",
    "vs code": "code",
    "vscode": "code",
    "spotify": "spotify",
}

# Only these folders can be searched — prevents scanning your
# entire filesystem, including sensitive system directories.
SEARCHABLE_DIRS = [
    os.path.expanduser("~/Documents"),
    os.path.expanduser("~/Downloads"),
    os.path.expanduser("~/Desktop"),
    os.path.expanduser("~/Pictures"),
]


def describe_open_app(app_name: str) -> dict:
    """
    Checks if the requested app is allowed and returns a description
    of the action WITHOUT executing it. The caller decides whether
    to actually run it via execute_action().
    """
    normalized = app_name.strip().lower()

    if normalized not in ALLOWED_APPS:
        return {
            "allowed": False,
            "reason": f"'{app_name}' is not in the allowed app list.",
            "available_apps": list(ALLOWED_APPS.keys()),
        }

    return {
        "allowed": True,
        "action_type": "open_app",
        "app_display_name": normalized,
        "command": ALLOWED_APPS[normalized],
        "description": f"Open {normalized}",
    }


def describe_search_files(query: str) -> dict:
    """
    Searches allowed directories for files matching the query and
    returns the results. Searching is read-only and safe to run
    immediately (no confirmation needed) — only OPENING something
    found requires confirmation.
    """
    query = query.strip()
    if not query:
        return {"allowed": False, "reason": "No search query provided."}

    matches = []
    for directory in SEARCHABLE_DIRS:
        if not os.path.isdir(directory):
            continue
        pattern = os.path.join(directory, "**", f"*{query}*")
        found = glob.glob(pattern, recursive=True)
        matches.extend(found)

    matches = matches[:15]  # cap results to keep things manageable

    return {
        "allowed": True,
        "action_type": "search_files",
        "query": query,
        "matches": matches,
        "description": f"Found {len(matches)} file(s) matching '{query}'",
    }


def execute_action(action: dict) -> str:
    """
    Actually performs a previously-described action. Only called
    AFTER the user has explicitly confirmed. Returns a result message.
    """
    if not action.get("allowed"):
        return "This action was not permitted."

    action_type = action.get("action_type")

    if action_type == "open_app":
        command = action["command"]
        try:
            subprocess.Popen(
                [command],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            logger.info("Opened app: %s (command: %s)", action["app_display_name"], command)
            return f"Opened {action['app_display_name']}."
        except FileNotFoundError:
            logger.warning("App command not found: %s", command)
            return f"Couldn't find '{command}' installed on this system."
        except Exception as e:
            logger.error("Failed to open app %s: %s", command, e)
            return f"Something went wrong opening {action['app_display_name']}."

    return "Unknown action type — nothing was done."
