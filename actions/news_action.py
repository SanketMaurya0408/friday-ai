# actions/news_action.py
# ══════════════════════════════════════════════════════════════════════════════
# FRIDAY — Global News + Smart Browser Launcher
# ══════════════════════════════════════════════════════════════════════════════
#
# FEATURES:
#   1. Fetches latest global news using newsdata.io (FREE — 200 req/day)
#   2. Extracts top 5 trending headlines
#   3. Speaks a short summary via Friday's voice
#   4. Opens each article in a new Chrome tab (smart delay between tabs)
#   5. Categorised news: Tech, World, AI, India, Business, Science
#   6. Full error handling: no internet, API failure, bad response
#
# SETUP (one time only):
#   1. Go to https://newsdata.io/register
#   2. Sign up free — no credit card needed
#   3. Copy your API key
#   4. Open config/api_keys.json and add:
#      "newsdata_api_key": "your_key_here"
#
# USAGE (Friday will call this automatically):
#   "Hey Friday, show me the latest news"
#   "Friday, what's happening in the world?"
#   "Open today's tech news"
#   "Show me AI news"
#   "What's the latest news in India?"
# ══════════════════════════════════════════════════════════════════════════════

import json
import time
import webbrowser
import subprocess
import sys
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime

# ── Config ─────────────────────────────────────────────────────────────────────
MAX_TABS          = 10        # maximum Chrome tabs to open
TAB_DELAY         = 1.2      # seconds between opening each tab (avoids crash)
REQUEST_TIMEOUT   = 8        # seconds before API call times out
MAX_HEADLINES     = 5        # number of headlines to speak and show
SPEAK_DELAY       = 0.3      # pause between speaking headline and opening tab


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"


# ── Category config ────────────────────────────────────────────────────────────
# Maps user-friendly category names to newsdata.io category slugs
CATEGORY_MAP = {
    "tech":        "technology",
    "technology":  "technology",
    "ai":          "technology",
    "world":       "world",
    "global":      "world",
    "india":       "top",          # top news filtered by country=in
    "indian":      "top",
    "business":    "business",
    "finance":     "business",
    "science":     "science",
    "sports":      "sports",
    "health":      "health",
    "entertainment": "entertainment",
    "top":         "top",
    "latest":      "top",
    "trending":    "top",
}

# Default category when none specified
DEFAULT_CATEGORY = "top"


# ══════════════════════════════════════════════════════════════════════════════
# API key loader
# ══════════════════════════════════════════════════════════════════════════════
def _get_news_api_key() -> str | None:
    """Load newsdata.io API key from config/api_keys.json."""
    try:
        if not API_CONFIG_PATH.exists():
            return None
        data = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8"))
        return data.get("newsdata_api_key", "").strip() or None
    except Exception as e:
        print(f"[News] ⚠️ Could not load API key: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Internet check
# ══════════════════════════════════════════════════════════════════════════════
def _is_online() -> bool:
    import socket
    try:
        socket.setdefaulttimeout(2.0)
        with socket.create_connection(("8.8.8.8", 53)):
            return True
    except OSError:
        return False


# ══════════════════════════════════════════════════════════════════════════════
# News fetcher — newsdata.io
# ══════════════════════════════════════════════════════════════════════════════
def _fetch_news(api_key: str, category: str, country: str = None) -> list[dict]:
    """
    Fetch news from newsdata.io API.
    Returns list of article dicts: {title, url, source, description}
    """
    params = {
        "apikey":   api_key,
        "language": "en",
        "size":     10,
    }

    # Set category
    if category and category != "top":
        params["category"] = category

    # India-specific filter
    if country:
        params["country"] = country

    url = "https://newsdata.io/api/1/news?" + urllib.parse.urlencode(params)

    print(f"[News] 🌐 Fetching: category={category} country={country or 'global'}")

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "FridayAI/1.0"}
    )

    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        raw  = resp.read().decode("utf-8")
        data = json.loads(raw)

    if data.get("status") != "success":
        raise ValueError(f"API error: {data.get('message', 'Unknown error')}")

    articles = data.get("results", [])
    if not articles:
        raise ValueError("No articles returned from API")

    # Clean and filter articles
    clean = []
    for art in articles:
        title = (art.get("title") or "").strip()
        url   = (art.get("link")  or "").strip()
        desc  = (art.get("description") or "").strip()
        src   = (art.get("source_id") or "Unknown").strip()

        # Skip articles without title or URL
        if not title or not url:
            continue

        # Skip very short titles
        if len(title) < 15:
            continue

        clean.append({
            "title":       title,
            "url":         url,
            "source":      src.title(),
            "description": desc[:150] if desc else "",
        })

    return clean[:10]   # max 10 articles


# ══════════════════════════════════════════════════════════════════════════════
# Chrome tab opener
# ══════════════════════════════════════════════════════════════════════════════
def _open_in_chrome(url: str) -> bool:
    """
    Opens a URL in Chrome. Tries multiple methods.
    Returns True if successful.
    """
    # Method 1: subprocess with chrome directly
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "google-chrome",    # Linux
        "google-chrome-stable",
        "chromium-browser",
    ]

    for path in chrome_paths:
        try:
            subprocess.Popen(
                [path, url],
                creationflags=subprocess.DETACHED_PROCESS
                if sys.platform == "win32" else 0,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except (FileNotFoundError, OSError):
            continue

    # Method 2: webbrowser module fallback
    try:
        webbrowser.open(url, new=2)
        return True
    except Exception:
        pass

    return False


# ══════════════════════════════════════════════════════════════════════════════
# Summary builder for TTS
# ══════════════════════════════════════════════════════════════════════════════
def _build_spoken_summary(articles: list[dict], category: str) -> str:
    """Build a natural-sounding spoken summary of the headlines."""
    cat_label = {
        "technology":    "technology and AI",
        "world":         "world news",
        "top":           "top stories",
        "business":      "business and finance",
        "science":       "science",
        "sports":        "sports",
        "health":        "health",
        "entertainment": "entertainment",
    }.get(category, "latest news")

    count = min(len(articles), MAX_HEADLINES)
    lines = [f"Here are the top {count} {cat_label} headlines, sir."]

    for i, art in enumerate(articles[:MAX_HEADLINES], 1):
        title = art["title"]
        # Remove excessive punctuation and shorten for TTS
        title = title.replace(" - ", " from ").replace(" | ", ". ")
        if len(title) > 120:
            title = title[:117] + "..."
        lines.append(f"Number {i}: {title}.")

    lines.append(f"Opening the top {min(count, MAX_TABS)} articles in Chrome now.")
    return " ".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# Display formatter for log panel
# ══════════════════════════════════════════════════════════════════════════════
def _build_display_output(articles: list[dict], category: str,
                          country: str = None) -> str:
    """Build formatted text for the UI log panel."""
    cat_label = category.upper() if category else "TOP"
    loc_label = f" ({country.upper()})" if country else " (GLOBAL)"

    lines = [
        f"━━ NEWS: {cat_label}{loc_label} ━━",
        f"Fetched: {datetime.now().strftime('%H:%M %d %b')}",
        "",
    ]

    for i, art in enumerate(articles[:MAX_HEADLINES], 1):
        title = art["title"]
        if len(title) > 80:
            title = title[:77] + "..."
        lines.append(f"{i}. {title}")
        lines.append(f"   ↳ {art['source']}")
        lines.append("")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# Main entry point — called by Friday
# ══════════════════════════════════════════════════════════════════════════════
def news_action(
    parameters=None,
    player=None,
    speak=None,
) -> str:
    """
    Main news action called by Friday.

    Parameters:
      category  : "tech" | "world" | "india" | "ai" | "business" | "science" | "top"
      open_tabs : True/False — whether to open Chrome tabs (default: True)
      speak_news: True/False — whether to speak headlines (default: True)
    """
    params      = parameters or {}
    category_raw = params.get("category", "top").lower().strip()
    open_tabs   = params.get("open_tabs", True)
    speak_news  = params.get("speak_news", True)

    # Resolve category
    category = CATEGORY_MAP.get(category_raw, DEFAULT_CATEGORY)

    # Country filter for India news
    country = None
    if category_raw in ("india", "indian"):
        country  = "in"
        category = "top"

    # ── Step 1: Check internet ─────────────────────────────────────────────
    if not _is_online():
        msg = "No internet connection available, sir. Cannot fetch news."
        print(f"[News] ❌ {msg}")
        if player:
            player.write_log(f"SYS: {msg}")
        if speak:
            speak(msg)
        return msg

    # ── Step 2: Load API key ───────────────────────────────────────────────
    api_key = _get_news_api_key()

    if not api_key:
        msg = (
            "News API key not configured, sir. "
            "Please add your newsdata.io API key to config/api_keys.json "
            "under the key 'newsdata_api_key'."
        )
        print(f"[News] ❌ {msg}")
        if player:
            player.write_log(f"SYS: {msg}")
        if speak:
            speak(
                "News API key not found, sir. "
                "Please add your newsdata.io key to the config file."
            )
        return msg

    # ── Step 3: Fetch news ─────────────────────────────────────────────────
    print(f"[News] 📰 Fetching {category} news...")
    if player:
        player.set_state("THINKING")
        player.write_log(f"SYS: Fetching {category_raw} news...")

    try:
        articles = _fetch_news(api_key, category, country)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            msg = "Invalid news API key, sir. Please check your newsdata.io key."
        elif e.code == 429:
            msg = "News API rate limit reached, sir. Please try again later."
        else:
            msg = f"News API error {e.code}, sir. Please try again."
        print(f"[News] ❌ HTTP {e.code}")
        if speak:
            speak(msg)
        if player:
            player.write_log(f"SYS: {msg}")
        return msg

    except urllib.error.URLError as e:
        msg = "Could not connect to news service, sir. Check your internet connection."
        print(f"[News] ❌ URL error: {e}")
        if speak:
            speak(msg)
        if player:
            player.write_log(f"SYS: {msg}")
        return msg

    except json.JSONDecodeError:
        msg = "News service returned invalid data, sir. Please try again."
        print(f"[News] ❌ JSON decode error")
        if speak:
            speak(msg)
        return msg

    except ValueError as e:
        msg = f"News fetch failed, sir: {e}"
        print(f"[News] ❌ {e}")
        if speak:
            speak(f"Sorry sir, {e}")
        return msg

    except Exception as e:
        msg = f"Unexpected error fetching news, sir: {str(e)[:80]}"
        print(f"[News] ❌ Unexpected: {e}")
        if speak:
            speak("Sorry sir, something went wrong fetching the news.")
        return msg

    if not articles:
        msg = "No news articles found for that category, sir."
        if speak:
            speak(msg)
        return msg

    print(f"[News] ✅ Got {len(articles)} articles")

    # ── Step 4: Display in log panel ───────────────────────────────────────
    display = _build_display_output(articles, category, country)
    if player:
        for line in display.split("\n"):
            if line.strip():
                player.write_log(f"SYS: {line}")

    # ── Step 5: Speak summary ──────────────────────────────────────────────
    if speak_news and speak:
        summary = _build_spoken_summary(articles, category)
        print(f"[News] 🔊 Speaking summary...")
        speak(summary)
        time.sleep(SPEAK_DELAY)

    # ── Step 6: Open Chrome tabs ───────────────────────────────────────────
    if open_tabs:
        tabs_to_open = min(len(articles), MAX_TABS)
        print(f"[News] 🌐 Opening {tabs_to_open} Chrome tabs...")

        opened = 0
        for i, art in enumerate(articles[:tabs_to_open]):
            url   = art["url"]
            title = art["title"][:50]

            print(f"[News] 📖 Tab {i+1}: {title}...")

            success = _open_in_chrome(url)

            if success:
                opened += 1
                if player:
                    player.write_log(f"SYS: Opened tab {i+1}: {title[:40]}...")
            else:
                print(f"[News] ⚠️ Could not open tab for: {url}")

            # Smart delay between tabs to avoid Chrome crash
            if i < tabs_to_open - 1:
                time.sleep(TAB_DELAY)

        result_msg = (
            f"Opened {opened} of {tabs_to_open} news articles in Chrome, sir."
        )
        print(f"[News] ✅ {result_msg}")
        return result_msg

    return f"Fetched {len(articles)} {category_raw} headlines successfully, sir."