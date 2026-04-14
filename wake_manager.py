# wake_manager.py — Friday Wake System
# ══════════════════════════════════════════════════════════════════════════════
# Features:
#   1. DOUBLE CLAP TO WAKE  — two quick claps wake Friday from mute
#   2. AUTO-MUTE            — after silence timeout, Friday auto-mutes
#
# Vosk completely removed — clap detection only.
# Zero RAM overhead. Instant startup.
# ══════════════════════════════════════════════════════════════════════════════

import threading
import time
import numpy as np
import sounddevice as sd

# ── Tuning constants ───────────────────────────────────────────────────────────

AUTO_MUTE_TIMEOUT = 500         # seconds of silence before auto-mute

CLAP_ENERGY_HIGH  = 2500        # minimum RMS to count as a clap
CLAP_ENERGY_LOW   = 350         # silence level between / after claps
CLAP_DURATION_MAX = 0.30        # max seconds a single clap burst lasts
CLAP_GAP_MIN      = 0.10        # min seconds between two claps
CLAP_GAP_MAX      = 0.70        # max seconds between two claps
CLAP_COOLDOWN     = 1.5         # seconds to ignore after double clap fires

WAKE_SAMPLE_RATE  = 16000
WAKE_CHUNK        = 512


# ══════════════════════════════════════════════════════════════════════════════
# WakeManager
# ══════════════════════════════════════════════════════════════════════════════
class WakeManager:
    """
    Manages wake / sleep for Friday.

    Mic stream is ONLY open when Friday is muted.
    When Friday is active, FridayLive owns the mic exclusively.

    Usage:
        wm = WakeManager(ui=ui, on_wake=unmute_fn, on_mute=mute_fn)
        wm.start()

    Call wm.notify_activity() every time user speaks or Friday responds.
    """

    def __init__(self, ui=None, on_wake=None, on_mute=None):
        self.ui             = ui
        self._on_wake       = on_wake
        self._on_mute       = on_mute
        self._running       = False
        self._last_activity = time.time()
        self._lock          = threading.Lock()
        self._clap_cooldown = 0.0
        self._automute_thread = None
        self._wake_thread     = None

    # ── Public API ─────────────────────────────────────────────────────────────

    def start(self):
        self._running       = True
        self._last_activity = time.time()

        self._automute_thread = threading.Thread(
            target=self._automute_loop, daemon=True, name="AutoMuteLoop"
        )
        self._automute_thread.start()

        self._wake_thread = threading.Thread(
            target=self._wake_loop, daemon=True, name="WakeDetectLoop"
        )
        self._wake_thread.start()

        print(f"[Wake] 🚀 Started — auto-mute after {AUTO_MUTE_TIMEOUT}s silence")
        print("[Wake] 👏 Double clap to wake from mute")

    def stop(self):
        self._running = False

    def notify_activity(self):
        """Call when user speaks — resets auto-mute countdown."""
        with self._lock:
            self._last_activity = time.time()

    def notify_friday_spoke(self):
        """Call when Friday finishes speaking — resets auto-mute countdown."""
        with self._lock:
            self._last_activity = time.time()

    # ── Auto-mute loop ─────────────────────────────────────────────────────────

    def _automute_loop(self):
        print("[Wake] ⏱️  Auto-mute monitor running")
        while self._running:
            time.sleep(1.0)
            if not self._running:
                break
            if self.ui and self.ui.muted:
                continue
            with self._lock:
                elapsed = time.time() - self._last_activity
            if elapsed >= AUTO_MUTE_TIMEOUT:
                print(f"[Wake] 😴 {AUTO_MUTE_TIMEOUT}s silence — auto-muting")
                self._log(f"SYS: Auto-muted after {AUTO_MUTE_TIMEOUT}s silence.")
                self._log("SYS: Double clap to wake.")
                if self._on_mute:
                    threading.Thread(
                        target=self._safe_call,
                        args=(self._on_mute,),
                        daemon=True
                    ).start()
                with self._lock:
                    self._last_activity = time.time()

    # ── Wake detection loop ────────────────────────────────────────────────────

    def _wake_loop(self):
        """
        Sleeps while Friday is active.
        Only opens mic when Friday is muted.
        """
        print("[Wake] 👁️  Wake detection loop running")
        while self._running:
            if not (self.ui and self.ui.muted):
                time.sleep(0.5)
                continue
            print("[Wake] 🎤 Opening wake mic (Friday is muted)")
            self._listen_for_wake()

    def _listen_for_wake(self):
        """
        Opens mic and listens for double clap.
        Closes mic as soon as wake is triggered or Friday is unmuted.
        """
        clap_state      = "IDLE"
        clap_start      = 0.0
        first_clap_time = 0.0
        prev_rms        = 0.0
        wake_triggered  = threading.Event()

        def audio_callback(indata, frames, time_info, status):
            nonlocal clap_state, clap_start, first_clap_time, prev_rms

            # Exit immediately if Friday was unmuted externally
            if not self._running or (self.ui and not self.ui.muted):
                wake_triggered.set()
                return

            now = time.time()
            arr = np.frombuffer(indata, dtype=np.int16).astype(np.float32)
            rms = float(np.sqrt(np.mean(arr ** 2)))

            # ── Double clap state machine ──────────────────────────────────
            if now > self._clap_cooldown:

                if clap_state == "IDLE":
                    if rms > CLAP_ENERGY_HIGH and prev_rms < CLAP_ENERGY_LOW:
                        clap_state = "IN_CLAP"
                        clap_start = now

                elif clap_state == "IN_CLAP":
                    duration = now - clap_start
                    if rms < CLAP_ENERGY_LOW:
                        if duration <= CLAP_DURATION_MAX:
                            first_clap_time = now
                            clap_state = "WAITING_SECOND"
                            print("[Wake] 👏 First clap — waiting for second...")
                        else:
                            clap_state = "IDLE"
                    elif duration > CLAP_DURATION_MAX * 2:
                        clap_state = "IDLE"

                elif clap_state == "WAITING_SECOND":
                    gap = now - first_clap_time
                    if gap > CLAP_GAP_MAX:
                        clap_state = "IDLE"
                    elif rms > CLAP_ENERGY_HIGH and prev_rms < CLAP_ENERGY_LOW:
                        clap_state = "IN_SECOND_CLAP"
                        clap_start = now

                elif clap_state == "IN_SECOND_CLAP":
                    duration = now - clap_start
                    if rms < CLAP_ENERGY_LOW:
                        if duration <= CLAP_DURATION_MAX:
                            gap = clap_start - first_clap_time
                            if gap >= CLAP_GAP_MIN:
                                print(f"[Wake] 👏👏 Double clap! gap={gap:.2f}s")
                                self._clap_cooldown = now + CLAP_COOLDOWN
                                clap_state = "IDLE"
                                threading.Thread(
                                    target=self._trigger_wake,
                                    args=(wake_triggered,),
                                    daemon=True
                                ).start()
                            else:
                                clap_state = "IDLE"
                        else:
                            clap_state = "IDLE"
                    elif duration > CLAP_DURATION_MAX * 2:
                        clap_state = "IDLE"

            prev_rms = rms

        try:
            with sd.RawInputStream(
                samplerate = WAKE_SAMPLE_RATE,
                channels   = 1,
                dtype      = "int16",
                blocksize  = WAKE_CHUNK,
                callback   = audio_callback,
            ):
                print("[Wake] 🎤 Wake mic stream open")
                while self._running:
                    if self.ui and not self.ui.muted:
                        break
                    if wake_triggered.is_set():
                        break
                    time.sleep(0.1)

        except Exception as e:
            print(f"[Wake] ❌ Wake mic error: {e}")

        print("[Wake] 🎤 Wake mic stream closed")

    # ── Wake trigger ───────────────────────────────────────────────────────────

    def _trigger_wake(self, wake_event: threading.Event = None):
        print("[Wake] ✅ Double clap — waking Friday")
        self._log("SYS: Double clap detected — Friday online.")

        with self._lock:
            self._last_activity = time.time()

        if wake_event:
            wake_event.set()

        # Let mic stream close cleanly before FridayLive opens it
        time.sleep(0.3)

        if self._on_wake:
            self._safe_call(self._on_wake)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _safe_call(self, fn):
        try:
            fn()
        except Exception as e:
            print(f"[Wake] ⚠️ Callback error: {e}")

    def _log(self, msg: str):
        if self.ui:
            try:
                self.ui.write_log(msg)
            except Exception:
                pass