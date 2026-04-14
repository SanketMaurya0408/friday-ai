# actions/open_app.py
# MARK XXV — Fast App Launcher
#
# FIX: Replaced slow Win-key simulation (4.4s delay) with
#      direct subprocess launch (milliseconds).
#      Win key search is only used as a last resort fallback.

import time
import subprocess
import platform
import shutil
import os
from pathlib import Path

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

# ── Windows app registry paths — direct launch, zero delay ────────────────────
_WINDOWS_PATHS = {
    "chrome":             r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "google chrome":      r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "firefox":            r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "edge":               r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "msedge":             r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "brave":              r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    "notepad":            r"C:\Windows\System32\notepad.exe",
    "calculator":         r"C:\Windows\System32\calc.exe",
    "calc":               r"C:\Windows\System32\calc.exe",
    "cmd":                r"C:\Windows\System32\cmd.exe",
    "powershell":         r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
    "explorer":           r"C:\Windows\explorer.exe",
    "file explorer":      r"C:\Windows\explorer.exe",
    "paint":              r"C:\Windows\System32\mspaint.exe",
    "mspaint":            r"C:\Windows\System32\mspaint.exe",
    "task manager":       r"C:\Windows\System32\taskmgr.exe",
    "taskmgr":            r"C:\Windows\System32\taskmgr.exe",
    "wordpad":            r"C:\Program Files\Windows NT\Accessories\wordpad.exe",
    "snipping tool":      r"C:\Windows\System32\SnippingTool.exe",
}

# ── UWP / Microsoft Store apps — launched via shell: protocol ─────────────────
_UWP_APPS = {
    "whatsapp":    "shell:appsFolder\\5319275A.WhatsApp_cv1g1gvanyjgm!App",
    "instagram":   "shell:appsFolder\\Facebook.Instagram_8xx8rvfyw5nnt!App",
    "tiktok":      "shell:appsFolder\\BytedancePte.Ltd.TikTok_6yccndn6064se!App",
    "settings":    "ms-settings:",
    "store":       "ms-windows-store:",
    "mail":        "outlook:",
    "calendar":    "outlookcal:",
    "photos":      "ms-photos:",
    "clock":       "ms-clock:",
    "maps":        "bingmaps:",
    "news":        "bingnews:",
    "weather":     "bingweather:",
    "xbox":        "xbox:",
    "spotify":     "spotify:",
}

# ── Apps found via PATH (shutil.which) ────────────────────────────────────────
_PATH_APPS = {
    "code":               "code",
    "vscode":             "code",
    "visual studio code": "code",
    "vlc":                "vlc",
    "steam":              "steam",
    "discord":            "discord",
    "telegram":           "telegram",
    "zoom":               "zoom",
    "slack":              "slack",
    "blender":            "blender",
    "postman":            "postman",
    "figma":              "figma",
    "obsidian":           "obsidian",
    "notion":             "notion",
    "git":                "git-bash",
    "anaconda":           "anaconda-navigator",
}

# ── macOS aliases ──────────────────────────────────────────────────────────────
_MACOS_ALIASES = {
    "chrome":       "Google Chrome",
    "vscode":       "Visual Studio Code",
    "vs code":      "Visual Studio Code",
    "whatsapp":     "WhatsApp",
    "terminal":     "Terminal",
    "calculator":   "Calculator",
    "settings":     "System Preferences",
}


def _normalize_key(raw: str) -> str:
    return raw.lower().strip()


def _launch_windows(app_name: str) -> str:
    key = _normalize_key(app_name)

    # 1. Direct .exe path — fastest, instant
    for alias, path in _WINDOWS_PATHS.items():
        if alias in key or key in alias:
            if os.path.exists(path):
                subprocess.Popen([path], creationflags=subprocess.DETACHED_PROCESS)
                return f"Opened {app_name} successfully, sir."

    # 2. UWP / Store app via explorer shell protocol
    for alias, protocol in _UWP_APPS.items():
        if alias in key or key in alias:
            subprocess.Popen(["explorer", protocol],
                             creationflags=subprocess.DETACHED_PROCESS)
            time.sleep(0.5)
            return f"Opened {app_name} successfully, sir."

    # 3. PATH lookup — apps installed globally
    for alias, cmd in _PATH_APPS.items():
        if alias in key or key in alias:
            binary = shutil.which(cmd)
            if binary:
                subprocess.Popen([binary],
                                 creationflags=subprocess.DETACHED_PROCESS,
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
                return f"Opened {app_name} successfully, sir."

    # 4. Try shutil.which directly with the raw name
    binary = shutil.which(app_name) or shutil.which(key)
    if binary:
        subprocess.Popen([binary],
                         creationflags=subprocess.DETACHED_PROCESS,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        return f"Opened {app_name} successfully, sir."

    # 5. Try PowerShell Start-Process — handles most installed apps
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden",
             "-Command", f"Start-Process '{app_name}'"],
            capture_output=True, timeout=6
        )
        if result.returncode == 0:
            return f"Opened {app_name} successfully, sir."
    except Exception as e:
        print(f"[open_app] PowerShell failed: {e}")

    # 6. Last resort — Win key search (slow, but catches everything)
    print(f"[open_app] ⚠️ Falling back to Win key search for: {app_name}")
    return _launch_windows_search(app_name)


def _launch_windows_search(app_name: str) -> str:
    """Last resort only — simulates Win key press and search."""
    try:
        import pyautogui
        pyautogui.PAUSE = 0.05
        pyautogui.press("win")
        time.sleep(0.5)
        pyautogui.write(app_name, interval=0.04)
        time.sleep(0.6)
        pyautogui.press("enter")
        time.sleep(1.5)
        return f"Opened {app_name} successfully, sir."
    except Exception as e:
        return f"Could not open {app_name}, sir. It may not be installed. Error: {e}"


def _launch_macos(app_name: str) -> str:
    key = _normalize_key(app_name)
    resolved = _MACOS_ALIASES.get(key, app_name)

    try:
        result = subprocess.run(
            ["open", "-a", resolved],
            capture_output=True, timeout=8
        )
        if result.returncode == 0:
            return f"Opened {app_name} successfully, sir."
    except Exception:
        pass

    # Spotlight fallback
    try:
        import pyautogui
        pyautogui.hotkey("command", "space")
        time.sleep(0.5)
        pyautogui.write(app_name, interval=0.04)
        time.sleep(0.6)
        pyautogui.press("enter")
        time.sleep(1.0)
        return f"Opened {app_name} successfully, sir."
    except Exception as e:
        return f"Could not open {app_name}, sir: {e}"


def _launch_linux(app_name: str) -> str:
    key = _normalize_key(app_name)

    binary = (
        shutil.which(app_name) or
        shutil.which(key) or
        shutil.which(key.replace(" ", "-")) or
        shutil.which(key.replace(" ", ""))
    )
    if binary:
        subprocess.Popen(
            [binary],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return f"Opened {app_name} successfully, sir."

    try:
        subprocess.Popen(
            ["xdg-open", app_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return f"Opened {app_name} successfully, sir."
    except Exception as e:
        return f"Could not open {app_name}, sir: {e}"


_OS_LAUNCHERS = {
    "Windows": _launch_windows,
    "Darwin":  _launch_macos,
    "Linux":   _launch_linux,
}


def open_app(
    parameters=None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    app_name = (parameters or {}).get("app_name", "").strip()

    if not app_name:
        return "Please specify which application to open, sir."

    system   = platform.system()
    launcher = _OS_LAUNCHERS.get(system)

    if launcher is None:
        return f"Unsupported OS: {system}"

    print(f"[open_app] 🚀 Launching: {app_name} ({system})")

    if player:
        player.write_log(f"[open_app] {app_name}")

    try:
        return launcher(app_name)
    except Exception as e:
        print(f"[open_app] ❌ {e}")
        return f"Failed to open {app_name}, sir: {e}"