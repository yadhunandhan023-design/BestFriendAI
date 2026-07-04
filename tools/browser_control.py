"""
tools/browser_control.py

Lets VARNI open a real Firefox browser and search/play videos on
YouTube. Uses Selenium to drive an actual browser session — not
just launching the app icon.

SAFETY DESIGN: same pattern as system_control.py — this module only
describes actions; main.py asks for confirmation before calling
execute_browser_action(). The browser session is kept open in memory
so VARNI can be asked to do follow-up things later (future step).
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from scripts.logger import get_logger

logger = get_logger(__name__)

# Kept at module level so the same browser window can be reused
# across multiple commands in one VARNI session, instead of opening
# a new window every time.
_driver = None


def _get_driver():
    """Returns the existing browser session, or starts a new one
    if none is open yet."""
    global _driver
    if _driver is None:
        logger.info("Starting new Firefox browser session for automation")
        options = Options()
        _driver = webdriver.Firefox(options=options)
    return _driver


def describe_play_youtube(query: str) -> dict:
    """Describes the action of searching and playing a video on
    YouTube, without executing it yet."""
    query = query.strip()
    if not query:
        return {"allowed": False, "reason": "No search query provided."}

    return {
        "allowed": True,
        "action_type": "play_youtube",
        "query": query,
        "description": f"Open YouTube and play a video for \"{query}\"",
    }


def execute_browser_action(action: dict) -> str:
    """Actually performs a previously-described browser action.
    Only called after explicit user confirmation."""
    if not action.get("allowed"):
        return "This action was not permitted."

    action_type = action.get("action_type")

    if action_type == "play_youtube":
        query = action["query"]
        try:
            driver = _get_driver()
            search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
            driver.get(search_url)
            logger.info("Searched YouTube for: %s", query)

            wait = WebDriverWait(driver, 10)
            first_video = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a#video-title"))
            )
            first_video.click()
            logger.info("Clicked first YouTube result for: %s", query)

            return f"Playing a YouTube video for \"{query}\"."
        except Exception as e:
            logger.error("Failed to play YouTube video: %s", e)
            return f"Something went wrong trying to play that on YouTube: {e}"

    return "Unknown browser action type — nothing was done."


def close_browser():
    """Closes the browser session if one is open. Call this on
    VARNI shutdown to clean up properly."""
    global _driver
    if _driver is not None:
        try:
            _driver.quit()
            logger.info("Closed browser automation session")
        except Exception as e:
            logger.warning("Error closing browser: %s", e)
        finally:
            _driver = None
