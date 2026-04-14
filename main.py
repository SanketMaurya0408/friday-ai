import asyncio
import threading
import json
import sys
import time
import traceback
import warnings
import os
from pathlib import Path

# ── Suppress all SDK warnings ──────────────────────────────────────────────────
warnings.filterwarnings("ignore")
os.environ["GRPC_VERBOSITY"]       = "ERROR"
os.environ["GRPC_TRACE"]           = ""
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import io

class _SuppressSDKWarnings:
    _BLOCKED = ("non-data parts", "text", "thought", "returning concatenated")
    def __init__(self, original):
        self._original = original
    def write(self, msg):
        if any(b in msg for b in self._BLOCKED):
            return
        self._original.write(msg)
    def flush(self):
        self._original.flush()
    def isatty(self):
        return getattr(self._original, "isatty", lambda: False)()

sys.stdout = _SuppressSDKWarnings(sys.stdout)

import sounddevice as sd
from google import genai
from google.genai import types
from ui import JarvisUI
from memory.memory_manager import (
    load_memory, update_memory, format_memory_for_prompt,
    should_extract_memory, extract_memory
)
from actions.news_action import news_action
from actions.flight_finder     import flight_finder
from actions.open_app          import open_app
from actions.weather_report    import weather_action
from actions.send_message      import send_message
from actions.reminder          import reminder
from actions.computer_settings import computer_settings
from actions.screen_processor  import screen_process
from actions.youtube_video     import youtube_video
from actions.cmd_control       import cmd_control
from actions.desktop           import desktop_control
from actions.browser_control   import browser_control
from actions.file_controller   import file_controller
from actions.code_helper       import code_helper
from actions.dev_agent         import dev_agent
from actions.web_search        import web_search as web_search_action
from actions.computer_control  import computer_control
from actions.game_updater      import game_updater

from wake_manager import WakeManager


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR            = get_base_dir()
API_CONFIG_PATH     = BASE_DIR / "config" / "api_keys.json"
PROMPT_PATH         = BASE_DIR / "core" / "prompt.txt"
LIVE_MODEL          = "models/gemini-2.5-flash-native-audio-preview-12-2025"
CHANNELS            = 1
SEND_SAMPLE_RATE    = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE          = 1024

CREDIT_RETRY_WAIT          = 60
INTERRUPT_ENERGY_THRESHOLD = 6000


def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]


def _load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return (
            "You are FRIDAY, Tony Stark's AI assistant. "
            "Be concise, direct, and always use the provided tools to complete tasks. "
            "Never simulate or guess results — always call the appropriate tool."
        )


# ── Memory ─────────────────────────────────────────────────────────────────────
_last_memory_input = ""


def _update_memory_async(user_text: str, jarvis_text: str) -> None:
    global _last_memory_input

    user_text   = (user_text   or "").strip()
    jarvis_text = (jarvis_text or "").strip()

    if len(user_text) < 5 or user_text == _last_memory_input:
        return
    _last_memory_input = user_text

    try:
        api_key = _get_api_key()
        if not should_extract_memory(user_text, jarvis_text, api_key):
            return
        data = extract_memory(user_text, jarvis_text, api_key)
        if data:
            update_memory(data)
            print(f"[Memory] ✅ {list(data.keys())}")
    except Exception as e:
        if "429" not in str(e):
            print(f"[Memory] ⚠️ {e}")


# ── Tool declarations ──────────────────────────────────────────────────────────
TOOL_DECLARATIONS = [
    {
        "name": "get_news",
        "description": (
            "Fetches latest global news headlines and opens them in Chrome. "
            "Use when user asks for news, headlines, what's happening, trending topics. "
            "Can filter by category: tech, world, india, ai, business, science, sports, health."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category":   {
                    "type": "STRING",
                    "description": "News category: top | tech | world | india | ai | business | science | sports | health | entertainment (default: top)"
                },
                "open_tabs":  {
                    "type": "BOOLEAN",
                    "description": "Whether to open articles in Chrome tabs (default: true)"
                },
                "speak_news": {
                    "type": "BOOLEAN",
                    "description": "Whether to speak the headlines aloud (default: true)"
                },
            },
            "required": []
        }
    },
    {
        "name": "open_app",
        "description": (
            "Opens any application on the Windows computer. "
            "Use this whenever the user asks to open, launch, or start any app, "
            "website, or program. Always call this tool — never just say you opened it."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Exact name of the application (e.g. 'WhatsApp', 'Chrome', 'Spotify')"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "web_search",
        "description": "Searches the web for any information.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query":  {"type": "STRING", "description": "Search query"},
                "mode":   {"type": "STRING", "description": "search (default) or compare"},
                "items":  {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Items to compare"},
                "aspect": {"type": "STRING", "description": "price | specs | reviews"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "weather_report",
        "description": "Gets real-time weather information for a city.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "city": {"type": "STRING", "description": "City name"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "send_message",
        "description": "Sends a text message via WhatsApp, Telegram, or other messaging platform.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "receiver":     {"type": "STRING", "description": "Recipient contact name"},
                "message_text": {"type": "STRING", "description": "The message to send"},
                "platform":     {"type": "STRING", "description": "Platform: WhatsApp, Telegram, etc."}
            },
            "required": ["receiver", "message_text", "platform"]
        }
    },
    {
        "name": "reminder",
        "description": "Sets a timed reminder using Windows Task Scheduler.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "date":    {"type": "STRING", "description": "Date in YYYY-MM-DD format"},
                "time":    {"type": "STRING", "description": "Time in HH:MM format (24h)"},
                "message": {"type": "STRING", "description": "Reminder message text"}
            },
            "required": ["date", "time", "message"]
        }
    },
    {
        "name": "youtube_video",
        "description": (
            "Controls YouTube. Use for: playing videos, summarizing a video's content, "
            "getting video info, or showing trending videos."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "play | summarize | get_info | trending (default: play)"},
                "query":  {"type": "STRING", "description": "Search query for play action"},
                "save":   {"type": "BOOLEAN", "description": "Save summary to Notepad (summarize only)"},
                "region": {"type": "STRING", "description": "Country code for trending e.g. TR, US"},
                "url":    {"type": "STRING", "description": "Video URL for get_info action"},
            },
            "required": []
        }
    },
    {
        "name": "screen_process",
        "description": (
            "Captures and analyzes the screen or webcam image. "
            "MUST be called when user asks what is on screen, what you see, "
            "analyze my screen, look at camera, etc. "
            "You have NO visual ability without this tool. "
            "After calling this tool, stay SILENT — the vision module speaks directly."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "angle": {"type": "STRING", "description": "'screen' to capture display, 'camera' for webcam. Default: 'screen'"},
                "text":  {"type": "STRING", "description": "The question or instruction about the captured image"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "computer_settings",
        "description": (
            "Controls the computer: volume, brightness, window management, keyboard shortcuts, "
            "typing text on screen, closing apps, fullscreen, dark mode, WiFi, restart, shutdown, "
            "scrolling, tab management, zoom, screenshots, lock screen, refresh/reload page. "
            "Use for ANY single computer control command. NEVER route to agent_task."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "The action to perform"},
                "description": {"type": "STRING", "description": "Natural language description of what to do"},
                "value":       {"type": "STRING", "description": "Optional value: volume level, text to type, etc."}
            },
            "required": []
        }
    },
    {
        "name": "browser_control",
        "description": (
            "Controls the web browser. Use for: opening websites, searching the web, "
            "clicking elements, filling forms, scrolling, any web-based task."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "go_to | search | click | type | scroll | fill_form | smart_click | smart_type | get_text | press | close"},
                "url":         {"type": "STRING", "description": "URL for go_to action"},
                "query":       {"type": "STRING", "description": "Search query for search action"},
                "selector":    {"type": "STRING", "description": "CSS selector for click/type"},
                "text":        {"type": "STRING", "description": "Text to click or type"},
                "description": {"type": "STRING", "description": "Element description for smart_click/smart_type"},
                "direction":   {"type": "STRING", "description": "up or down for scroll"},
                "key":         {"type": "STRING", "description": "Key name for press action"},
                "incognito":   {"type": "BOOLEAN", "description": "Open in private/incognito mode"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "file_controller",
        "description": "Manages files and folders: open, list, create, delete, move, copy, rename, read, write, find, disk usage.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "open | list | create_file | create_folder | delete | move | copy | rename | read | write | find | largest | disk_usage | organize_desktop | info"},
                "path":        {"type": "STRING", "description": "File/folder path or shortcut: desktop, downloads, documents, home"},
                "destination": {"type": "STRING", "description": "Destination path for move/copy"},
                "new_name":    {"type": "STRING", "description": "New name for rename"},
                "content":     {"type": "STRING", "description": "Content for create_file/write"},
                "name":        {"type": "STRING", "description": "File name to search for or open"},
                "extension":   {"type": "STRING", "description": "File extension to search (e.g. .pdf)"},
                "count":       {"type": "INTEGER", "description": "Number of results for largest"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "cmd_control",
        "description": (
            "Runs CMD/terminal commands via natural language: disk space, processes, "
            "system info, network, find files, or anything in the command line."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "task":    {"type": "STRING", "description": "Natural language description of what to do"},
                "visible": {"type": "BOOLEAN", "description": "Open visible CMD window. Default: true"},
                "command": {"type": "STRING", "description": "Optional: exact command if already known"},
            },
            "required": ["task"]
        }
    },
    {
        "name": "desktop_control",
        "description": "Controls the desktop: wallpaper, organize, clean, list, stats.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "wallpaper | wallpaper_url | organize | clean | list | stats | task"},
                "path":   {"type": "STRING", "description": "Image path for wallpaper"},
                "url":    {"type": "STRING", "description": "Image URL for wallpaper_url"},
                "mode":   {"type": "STRING", "description": "by_type or by_date for organize"},
                "task":   {"type": "STRING", "description": "Natural language desktop task"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "code_helper",
        "description": "Writes, edits, explains, runs, or builds code files.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "write | edit | explain | run | build | auto (default: auto)"},
                "description": {"type": "STRING", "description": "What the code should do or what change to make"},
                "language":    {"type": "STRING", "description": "Programming language (default: python)"},
                "output_path": {"type": "STRING", "description": "Where to save the file"},
                "file_path":   {"type": "STRING", "description": "Path to existing file for edit/explain/run/build"},
                "code":        {"type": "STRING", "description": "Raw code string for explain"},
                "args":        {"type": "STRING", "description": "CLI arguments for run/build"},
                "timeout":     {"type": "INTEGER", "description": "Execution timeout in seconds (default: 30)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "dev_agent",
        "description": "Builds complete multi-file projects from scratch: plans, writes files, installs deps, opens VSCode, runs and fixes errors.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "description":  {"type": "STRING", "description": "What the project should do"},
                "language":     {"type": "STRING", "description": "Programming language (default: python)"},
                "project_name": {"type": "STRING", "description": "Optional project folder name"},
                "timeout":      {"type": "INTEGER", "description": "Run timeout in seconds (default: 30)"},
            },
            "required": ["description"]
        }
    },
    {
        "name": "agent_task",
        "description": (
            "Executes complex multi-step tasks requiring multiple different tools. "
            "Examples: 'research X and save to file', 'find and organize files'. "
            "DO NOT use for single commands. NEVER use for Steam/Epic — use game_updater."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "goal":     {"type": "STRING", "description": "Complete description of what to accomplish"},
                "priority": {"type": "STRING", "description": "low | normal | high (default: normal)"}
            },
            "required": ["goal"]
        }
    },
    {
        "name": "computer_control",
        "description": "Direct computer control: type, click, hotkeys, scroll, move mouse, screenshots, find elements on screen.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "type | smart_type | click | double_click | right_click | hotkey | press | scroll | move | copy | paste | screenshot | wait | clear_field | focus_window | screen_find | screen_click | random_data | user_data"},
                "text":        {"type": "STRING", "description": "Text to type or paste"},
                "x":           {"type": "INTEGER", "description": "X coordinate"},
                "y":           {"type": "INTEGER", "description": "Y coordinate"},
                "keys":        {"type": "STRING", "description": "Key combination e.g. 'ctrl+c'"},
                "key":         {"type": "STRING", "description": "Single key e.g. 'enter'"},
                "direction":   {"type": "STRING", "description": "up | down | left | right"},
                "amount":      {"type": "INTEGER", "description": "Scroll amount (default: 3)"},
                "seconds":     {"type": "NUMBER",  "description": "Seconds to wait"},
                "title":       {"type": "STRING",  "description": "Window title for focus_window"},
                "description": {"type": "STRING",  "description": "Element description for screen_find/screen_click"},
                "type":        {"type": "STRING",  "description": "Data type for random_data"},
                "field":       {"type": "STRING",  "description": "Field for user_data: name|email|city"},
                "clear_first": {"type": "BOOLEAN", "description": "Clear field before typing (default: true)"},
                "path":        {"type": "STRING",  "description": "Save path for screenshot"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "game_updater",
        "description": (
            "THE ONLY tool for ANY Steam or Epic Games request. "
            "Use for: installing, downloading, updating games, listing installed games, "
            "checking game status, or any Steam/Epic related task."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":    {"type": "STRING", "description": "install | update | list | status | launch"},
                "game_name": {"type": "STRING", "description": "Name of the game"},
                "platform":  {"type": "STRING", "description": "steam | epic"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "flight_finder",
        "description": "Finds and compares flight options between cities.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "origin":       {"type": "STRING", "description": "Departure city or airport code"},
                "destination":  {"type": "STRING", "description": "Arrival city or airport code"},
                "date":         {"type": "STRING", "description": "Departure date YYYY-MM-DD"},
                "return_date":  {"type": "STRING", "description": "Return date for round trips YYYY-MM-DD"},
                "passengers":   {"type": "INTEGER","description": "Number of passengers (default: 1)"},
            },
            "required": ["origin", "destination", "date"]
        }
    },
    {
        "name": "save_memory",
        "description": "Silently saves a fact or preference about the user to long-term memory.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {"type": "STRING", "description": "Memory category: user_info | preferences | notes"},
                "key":      {"type": "STRING", "description": "Short identifier for this memory"},
                "value":    {"type": "STRING", "description": "The value to remember"},
            },
            "required": ["category", "key", "value"]
        }
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# ConnectionMonitor — API quota only, zero offline logic
# ══════════════════════════════════════════════════════════════════════════════
class ConnectionMonitor:

    def __init__(self, ui=None):
        self.ui                = ui
        self._credit_exhausted = False
        self._credit_retry_at  = 0.0
        self._lock             = threading.Lock()

    def is_online(self) -> bool:
        with self._lock:
            if self._credit_exhausted:
                if time.time() >= self._credit_retry_at:
                    self._credit_exhausted = False
                    print("[Monitor] ✅ Retry window passed — reconnecting")
                    return True
                return False
            return True

    def report_api_error(self, err):
        err_str  = str(err).lower()
        is_quota = any(k in err_str for k in ("429", "quota", "resource_exhausted", "rateerror"))
        if is_quota:
            with self._lock:
                self._credit_exhausted = True
                self._credit_retry_at  = time.time() + CREDIT_RETRY_WAIT
            msg = f"API quota hit — waiting {CREDIT_RETRY_WAIT}s before retry."
            print(f"[Monitor] ⚠️ {msg}")
            if self.ui:
                self.ui.write_log(f"SYS: {msg}")
                self.ui.set_state("THINKING")


# ══════════════════════════════════════════════════════════════════════════════
# JarvisLive
# ══════════════════════════════════════════════════════════════════════════════
class JarvisLive:

    def __init__(self, ui: JarvisUI, monitor: ConnectionMonitor, wake_manager: WakeManager):
        self.ui             = ui
        self.monitor        = monitor
        self.wake_manager   = wake_manager
        self.session        = None
        self._loop          = None
        self._speaking_lock = threading.Lock()
        self._is_speaking   = False
        self.audio_in_queue = None
        self.out_queue      = None
        self._interrupted   = threading.Event()
        self._bg_results : list[str] = []
        self._bg_lock    = threading.Lock()

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
        if value:
            self._interrupted.clear()
            self.ui.set_state("SPEAKING")
        elif not self.ui.muted:
            self.ui.set_state("LISTENING")

    def is_speaking(self) -> bool:
        with self._speaking_lock:
            return self._is_speaking

    def interrupt(self):
        if self.is_speaking():
            print("[FRIDAY] 🛑 Interrupted by user")
            self._interrupted.set()
            self.set_speaking(False)
            if self.audio_in_queue:
                while not self.audio_in_queue.empty():
                    try:
                        self.audio_in_queue.get_nowait()
                    except Exception:
                        break
            self.ui.set_state("LISTENING")

    def speak(self, text: str):
        if not self._loop or not self.session:
            return
        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True
            ),
            self._loop
        )

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")
        self.speak(f"Sir, {tool_name} encountered an error. {short}")

    def report_bg_result(self, tool_name: str, result: str):
        with self._bg_lock:
            self._bg_results.append(f"{tool_name} completed: {result}")
        print(f"[FRIDAY] 📬 BG result queued: {tool_name}")

    def _flush_bg_results(self):
        with self._bg_lock:
            results = list(self._bg_results)
            self._bg_results.clear()
        for msg in results:
            self.speak(msg)

    def _build_config(self) -> types.LiveConnectConfig:
        from datetime import datetime

        memory     = load_memory()
        mem_str    = format_memory_for_prompt(memory)
        sys_prompt = _load_system_prompt()

        now      = datetime.now()
        time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")
        time_ctx = (
            f"[CURRENT DATE & TIME]\n"
            f"Right now it is: {time_str}\n"
            f"Use this to calculate exact times for reminders.\n\n"
        )

        parts = [time_ctx]
        if mem_str:
            parts.append(mem_str)
        parts.append(sys_prompt)

        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription={},
            system_instruction="\n".join(parts),
            tools=[{"function_declarations": TOOL_DECLARATIONS}],
            session_resumption=types.SessionResumptionConfig(),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="kore"
                    )
                )
            ),
        )

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        name = fc.name
        args = dict(fc.args or {})

        print(f"[FRIDAY] 🔧 {name}  {args}")
        self.ui.set_state("THINKING")

        if name == "save_memory":
            category = args.get("category", "notes")
            key      = args.get("key", "")
            value    = args.get("value", "")
            if key and value:
                update_memory({category: {key: {"value": value}}})
                print(f"[Memory] 💾 save_memory: {category}/{key} = {value}")
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": "ok", "silent": True}
            )

        loop   = asyncio.get_event_loop()
        result = "Done."

        try:
            if name == "open_app":
                r = await loop.run_in_executor(None, lambda: open_app(parameters=args, response=None, player=self.ui))
                result = r or f"Opened {args.get('app_name')}."
            elif name == "weather_report":
                r = await loop.run_in_executor(None, lambda: weather_action(parameters=args, player=self.ui))
                result = r or "Weather delivered."
            elif name == "browser_control":
                r = await loop.run_in_executor(None, lambda: browser_control(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "file_controller":
                r = await loop.run_in_executor(None, lambda: file_controller(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "send_message":
                r = await loop.run_in_executor(None, lambda: send_message(parameters=args, response=None, player=self.ui, session_memory=None))
                result = r or f"Message sent to {args.get('receiver')}."
            elif name == "reminder":
                r = await loop.run_in_executor(None, lambda: reminder(parameters=args, response=None, player=self.ui))
                result = r or "Reminder set."
            elif name == "youtube_video":
                r = await loop.run_in_executor(None, lambda: youtube_video(parameters=args, response=None, player=self.ui))
                result = r or "Done."
            elif name == "screen_process":
                threading.Thread(
                    target=screen_process,
                    kwargs={"parameters": args, "response": None,
                            "player": self.ui, "session_memory": None},
                    daemon=True
                ).start()
                result = "Vision module activated. Stay completely silent — vision module will speak directly."
            elif name == "get_news":
                r = await loop.run_in_executor(
                    None,
                    lambda: news_action(
                        parameters = args,
                        player     = self.ui,
                        speak      = self.speak,
                    )
                )
                result = r or "News fetched."

            elif name == "computer_settings":
                r = await loop.run_in_executor(None, lambda: computer_settings(parameters=args, response=None, player=self.ui))
                result = r or "Done."
            elif name == "cmd_control":
                r = await loop.run_in_executor(None, lambda: cmd_control(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "desktop_control":
                r = await loop.run_in_executor(None, lambda: desktop_control(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "code_helper":
                r = await loop.run_in_executor(None, lambda: code_helper(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."
            elif name == "dev_agent":
                r = await loop.run_in_executor(None, lambda: dev_agent(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."
            elif name == "agent_task":
                from agent.task_queue import get_queue, TaskPriority
                priority_map = {"low": TaskPriority.LOW, "normal": TaskPriority.NORMAL, "high": TaskPriority.HIGH}
                priority     = priority_map.get(args.get("priority", "normal").lower(), TaskPriority.NORMAL)
                task_id      = get_queue().submit(goal=args.get("goal", ""), priority=priority, speak=self.speak)
                result       = f"Task started (ID: {task_id})."
            elif name == "web_search":
                r = await loop.run_in_executor(None, lambda: web_search_action(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "computer_control":
                r = await loop.run_in_executor(None, lambda: computer_control(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "game_updater":
                r = await loop.run_in_executor(None, lambda: game_updater(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."
            elif name == "flight_finder":
                r = await loop.run_in_executor(None, lambda: flight_finder(parameters=args, player=self.ui))
                result = r or "Done."
            else:
                result = f"Unknown tool: {name}"

        except Exception as e:
            result = f"Tool '{name}' failed: {e}"
            traceback.print_exc()
            self.speak_error(name, e)

        if not self.ui.muted:
            self.ui.set_state("LISTENING")

        print(f"[FRIDAY] 📤 {name} → {str(result)[:80]}")

        return types.FunctionResponse(
            id=fc.id, name=name,
            response={"result": result}
        )

    async def _send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send_realtime_input(media=msg)

    async def _listen_audio(self):
        print("[FRIDAY] 🎤 Mic started")
        loop = asyncio.get_event_loop()
        import numpy as np

        def callback(indata, frames, time_info, status):
            with self._speaking_lock:
                jarvis_speaking = self._is_speaking

            if jarvis_speaking:
                audio_array = np.frombuffer(indata, dtype=np.int16).astype(np.float32)
                rms = float(np.sqrt(np.mean(audio_array ** 2)))
                if rms > INTERRUPT_ENERGY_THRESHOLD:
                    loop.call_soon_threadsafe(self.interrupt)
                    data = indata.tobytes()
                    loop.call_soon_threadsafe(
                        self.out_queue.put_nowait,
                        {"data": data, "mime_type": "audio/pcm"}
                    )
            else:
                if not self.ui.muted:
                    data = indata.tobytes()
                    loop.call_soon_threadsafe(
                        self.out_queue.put_nowait,
                        {"data": data, "mime_type": "audio/pcm"}
                    )

        try:
            with sd.InputStream(
                samplerate=SEND_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=CHUNK_SIZE,
                callback=callback,
            ):
                print("[FRIDAY] 🎤 Mic stream open")
                while True:
                    await asyncio.sleep(0.1)
        except Exception as e:
            print(f"[FRIDAY] ❌ Mic: {e}")
            raise

    async def _receive_audio(self):
        print("[FRIDAY] 👂 Recv started")
        out_buf, in_buf = [], []

        try:
            while True:
                async for response in self.session.receive():

                    if hasattr(response, "type") and response.type in ("text", "thought"):
                        continue

                    if response.data:
                        if not self._interrupted.is_set():
                            self.audio_in_queue.put_nowait(response.data)

                    if response.server_content:
                        sc = response.server_content

                        if hasattr(sc, "model_turn") and sc.model_turn:
                            for part in (sc.model_turn.parts or []):
                                if hasattr(part, "thought") and part.thought:
                                    continue
                                if hasattr(part, "text") and part.text and not getattr(part, "inline_data", None):
                                    continue

                        if sc.output_transcription and sc.output_transcription.text:
                            if not self._interrupted.is_set():
                                self.set_speaking(True)
                            txt = sc.output_transcription.text.strip()
                            if txt:
                                out_buf.append(txt)

                        if sc.input_transcription and sc.input_transcription.text:
                            txt = sc.input_transcription.text.strip()
                            if txt:
                                in_buf.append(txt)

                        if sc.turn_complete:
                            self.set_speaking(False)
                            self._interrupted.clear()

                            full_in = " ".join(in_buf).strip()
                            if full_in:
                                self.ui.write_log(f"You: {full_in}")
                                self.wake_manager.notify_activity()
                            in_buf = []

                            full_out = " ".join(out_buf).strip()
                            if full_out:
                                self.ui.write_log(f"Friday: {full_out}")
                                self.wake_manager.notify_friday_spoke()
                            out_buf = []

                            if full_in and len(full_in) > 5:
                                threading.Thread(
                                    target=_update_memory_async,
                                    args=(full_in, full_out),
                                    daemon=True
                                ).start()

                            self._flush_bg_results()

                    if response.tool_call:
                        fn_responses = []
                        for fc in response.tool_call.function_calls:
                            print(f"[FRIDAY] 📞 {fc.name}")
                            fr = await self._execute_tool(fc)
                            fn_responses.append(fr)
                        await self.session.send_tool_response(
                            function_responses=fn_responses
                        )

        except Exception as e:
            print(f"[FRIDAY] ❌ Recv: {e}")
            traceback.print_exc()
            self.monitor.report_api_error(e)
            raise

    async def _play_audio(self):
        print("[FRIDAY] 🔊 Play started")

        stream = sd.RawOutputStream(
            samplerate=RECEIVE_SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=CHUNK_SIZE,
        )
        stream.start()

        try:
            while True:
                chunk = await self.audio_in_queue.get()

                if self._interrupted.is_set():
                    while not self.audio_in_queue.empty():
                        try:
                            self.audio_in_queue.get_nowait()
                        except Exception:
                            break
                    continue

                self.set_speaking(True)
                await asyncio.to_thread(lambda c=chunk: stream.write(c))

                if self._interrupted.is_set():
                    self.set_speaking(False)
                    continue

                self.set_speaking(False)

        except Exception as e:
            print(f"[FRIDAY] ❌ Play: {e}")
            raise

        finally:
            self.set_speaking(False)
            stream.stop()
            stream.close()

    async def run_once(self):
        client = genai.Client(
            api_key=_get_api_key(),
            http_options={"api_version": "v1beta"}
        )

        print("[FRIDAY] 🔌 Connecting to Gemini…")
        self.ui.set_state("THINKING")
        config = self._build_config()

        async with (
            client.aio.live.connect(model=LIVE_MODEL, config=config) as session,
            asyncio.TaskGroup() as tg,
        ):
            self.session        = session
            self._loop          = asyncio.get_event_loop()
            self.audio_in_queue = asyncio.Queue()
            self.out_queue      = asyncio.Queue(maxsize=50)

            print("[FRIDAY] ✅ Connected.")
            self.ui.set_state("LISTENING")
            self.ui.write_log("SYS: FRIDAY online.")

            tg.create_task(self._send_realtime())
            tg.create_task(self._listen_audio())
            tg.create_task(self._receive_audio())
            tg.create_task(self._play_audio())


# ══════════════════════════════════════════════════════════════════════════════
# SmartRunner — online only, no offline fallback
# ══════════════════════════════════════════════════════════════════════════════
class SmartRunner:

    def __init__(self, ui: JarvisUI):
        self.ui      = ui
        self.monitor = ConnectionMonitor(ui=ui)

        self.wake_manager = WakeManager(
            ui      = ui,
            on_wake = self._on_wake,
            on_mute = self._on_auto_mute,
        )
        self.wake_manager.start()

        self._current_jarvis: JarvisLive | None = None

    def _on_wake(self):
        if self.ui.muted:
            self.ui.muted = False
            self.ui._draw_mute_button()
            self.ui.set_state("LISTENING")
            self.ui.write_log("SYS: Friday woken up — listening.")
            if self._current_jarvis:
                self._current_jarvis.speak("Yes sir, I'm here. How can I help?")

    def _on_auto_mute(self):
        if self.ui.muted:
            return
        if self._current_jarvis:
            self._current_jarvis.speak("Going quiet sir. Clap or say Friday to wake me.")
            time.sleep(2.5)
        self.ui.muted = True
        self.ui._draw_mute_button()
        self.ui.set_state("MUTED")

    def run(self):
        while True:
            if self.monitor.is_online():
                self._run_session()
            else:
                self.ui.set_state("THINKING")
                time.sleep(5)

    def _run_session(self):
        jarvis = JarvisLive(self.ui, self.monitor, self.wake_manager)
        self._current_jarvis = jarvis
        try:
            asyncio.run(self._session_loop(jarvis))
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"[Runner] Session ended: {e}")
            self.monitor.report_api_error(e)
        finally:
            self._current_jarvis = None

    async def _session_loop(self, jarvis: JarvisLive):
        while self.monitor.is_online():
            try:
                await jarvis.run_once()
            except Exception as e:
                self.monitor.report_api_error(e)
                if not self.monitor.is_online():
                    break
                print("[Runner] 🔄 Reconnecting in 3s…")
                await asyncio.sleep(3)

        jarvis.set_speaking(False)
        self.ui.set_state("THINKING")


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════
def main():
    ui = JarvisUI("face.png")

    def runner():
        ui.wait_for_api_key()
        smart = SmartRunner(ui)

        # Connect weather speak to Friday's voice
        def _weather_speak(text: str):
            if smart._current_jarvis:
                smart._current_jarvis.speak(text)
        ui._weather_speak = _weather_speak

        try:
            smart.run()
        except KeyboardInterrupt:
            print("\n🔴 Shutting down…")

    threading.Thread(target=runner, daemon=True).start()
    ui.root.mainloop()


if __name__ == "__main__":
    main()