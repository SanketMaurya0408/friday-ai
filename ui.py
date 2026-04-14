import os, json, time, math, random, threading
import tkinter as tk
from collections import deque
from PIL import Image, ImageTk, ImageDraw
import sys
from pathlib import Path

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR   = get_base_dir()
CONFIG_DIR = BASE_DIR / "config"
API_FILE   = CONFIG_DIR / "api_keys.json"

SYSTEM_NAME = "F.R.I.D.A.Y"
MODEL_BADGE = "FRIDAY AI"
FULL_NAME   = "Female Replacement Intelligent Digital Assistant Youth"
WEATHER_CITY    = "Meerut Modipuram"
WEATHER_COUNTRY = "IN"

# ── Arctic Ice Blue palette ────────────────────────────────────────────────────
C_BG       = "#04080f"
C_BG2      = "#060c14"
C_ICE      = "#e8f4ff"
C_ICE2     = "#b8d8f0"
C_FROST    = "#7ab8e0"
C_DEEP     = "#1a3a5c"
C_DEEP2    = "#0d2035"
C_GLOW     = "#00c8ff"
C_GLOW2    = "#40e0ff"
C_POLAR    = "#a0f0ff"
C_AURORA   = "#00ffcc"
C_AURORA2  = "#00e5b0"
C_SNOW     = "#ffffff"
C_STEEL    = "#2a4a6a"
C_STEEL2   = "#1a2f45"
C_WARN     = "#ff9040"
C_ERR      = "#ff4466"
C_DIM      = "#1e3a52"
C_MUTED_FG = "#ff3366"
C_TEXT     = "#c0e8ff"


def _hx(r, g, b, a=255):
    f = max(0.0, min(1.0, a / 255.0))
    return f"#{int(r*f):02x}{int(g*f):02x}{int(b*f):02x}"


# ══════════════════════════════════════════════════════════════════════════════
# REAL SYSTEM STATS — CPU, RAM, Battery, Network, Disk, Temperature
# ══════════════════════════════════════════════════════════════════════════════
class SystemStats:
    def __init__(self, interval=2.0):
        self._lock     = threading.Lock()
        self._interval = interval
        self._data = {
            "cpu": 0.0, "ram": 0.0, "battery": None, "plugged": False,
            "net_sent": 0.0, "net_recv": 0.0,
            "disk": 0.0, "temp": None,
            "ram_used_gb": 0.0, "ram_total_gb": 0.0,
            "disk_used_gb": 0.0, "disk_total_gb": 0.0,
        }
        self._prev_net = None
        threading.Thread(target=self._loop, daemon=True, name="SysStats").start()

    def _loop(self):
        if _PSUTIL:
            psutil.cpu_percent(interval=None)
            time.sleep(0.5)
        while True:
            if _PSUTIL:
                try:
                    cpu  = psutil.cpu_percent(interval=None)
                    vm   = psutil.virtual_memory()
                    ram  = vm.percent
                    ram_used  = vm.used  / (1024**3)
                    ram_total = vm.total / (1024**3)

                    bat     = psutil.sensors_battery()
                    bat_pct = round(bat.percent) if bat else None
                    plugged = bat.power_plugged if bat else False

                    nets = psutil.net_io_counters()
                    if self._prev_net:
                        dt   = self._interval
                        sent = (nets.bytes_sent - self._prev_net.bytes_sent) / dt / 1024
                        recv = (nets.bytes_recv - self._prev_net.bytes_recv) / dt / 1024
                    else:
                        sent = recv = 0.0
                    self._prev_net = nets

                    disk      = psutil.disk_usage('/')
                    disk_pct  = disk.percent
                    disk_used = disk.used  / (1024**3)
                    disk_tot  = disk.total / (1024**3)

                    temp = None
                    try:
                        temps = psutil.sensors_temperatures()
                        if temps:
                            for name, entries in temps.items():
                                if entries:
                                    temp = entries[0].current
                                    break
                    except Exception:
                        pass

                    with self._lock:
                        self._data.update({
                            "cpu": cpu, "ram": ram,
                            "ram_used_gb": ram_used, "ram_total_gb": ram_total,
                            "battery": bat_pct, "plugged": plugged,
                            "net_sent": max(0.0, sent), "net_recv": max(0.0, recv),
                            "disk": disk_pct, "disk_used_gb": disk_used,
                            "disk_total_gb": disk_tot, "temp": temp,
                        })
                except Exception:
                    pass
            time.sleep(self._interval)

    def get(self):
        with self._lock:
            return dict(self._data)


# ══════════════════════════════════════════════════════════════════════════════
# BOOT ANIMATION — Arctic Ice charge-up
# ══════════════════════════════════════════════════════════════════════════════
class BootAnimation:
    BOOT_LINES = [
        "ARCTIC CORE INITIALISING...",
        "NEURAL ICE MATRIX LOADING...",
        "CRYO-SYNC CALIBRATED...",
        "POLAR UPLINK ESTABLISHED...",
        "VOICE SYNTHESIS ONLINE...",
        "ENVIRONMENT SCAN COMPLETE...",
        "MEMORY LATTICE RESTORED...",
        "ALL SYSTEMS NOMINAL.",
        "F.R.I.D.A.Y  —  ONLINE.",
    ]

    def __init__(self, root, W, H, on_complete):
        self.root = root; self.W = W; self.H = H
        self.on_complete = on_complete
        self.canvas = tk.Canvas(root, width=W, height=H,
                                bg="#000508", highlightthickness=0)
        self.canvas.place(x=0, y=0)
        self.tick = 0; self.phase = 0; self.phase_start = 0
        self.lines_shown = 0; self.fade_out = 0.0; self.done = False
        self.charge = 0.0; self.charge_spd = 0.010
        self.ring_angles = [0.0] * 6
        self.ring_spds   = [0.8, -0.5, 1.2, -0.7, 1.8, -1.0]
        self.crystals = []; self.snowflakes = []
        self.corner_prog = 0.0; self.name_alpha = 0.0
        self._spawn_crystals()
        self._animate()

    def _spawn_crystals(self):
        cx, cy = self.W // 2, self.H // 2
        for _ in range(10):
            angle = random.uniform(0, 2 * math.pi)
            dist  = random.uniform(70, min(cx, cy) * 0.88)
            self.crystals.append({
                "angle": angle, "dist": dist,
                "spd": random.uniform(0.3, 1.1),
                "life": random.randint(40, 100), "max": 100,
                "size": random.randint(2, 5)
            })

    def _animate(self):
        if self.done: return
        self.tick += 1; t = self.tick
        cx, cy = self.W // 2, self.H // 2

        if self.phase == 0 and t > 8:
            self.phase = 1; self.phase_start = t
        elif self.phase == 1:
            self.charge = min(1.0, self.charge + self.charge_spd)
            if self.charge >= 1.0: self.phase = 2; self.phase_start = t
        elif self.phase == 2 and t - self.phase_start > 18:
            self.phase = 3; self.phase_start = t
        elif self.phase == 3:
            elapsed = t - self.phase_start
            if elapsed > self.lines_shown * 15 and self.lines_shown < len(self.BOOT_LINES):
                self.lines_shown += 1
            if self.lines_shown >= len(self.BOOT_LINES) and t - self.phase_start > 155:
                self.phase = 4; self.phase_start = t
        elif self.phase == 4 and t - self.phase_start > 12:
            self.phase = 5; self.phase_start = t
        elif self.phase == 5:
            self.corner_prog = min(1.0, self.corner_prog + 0.08)
            if t - self.phase_start > 18: self.phase = 6; self.phase_start = t
        elif self.phase == 6:
            self.name_alpha = min(1.0, self.name_alpha + 0.04)
            if t - self.phase_start > 55: self.phase = 7; self.phase_start = t
        elif self.phase == 7:
            self.fade_out += 0.035
            if self.fade_out >= 1.0:
                self.done = True; self.canvas.destroy(); self.on_complete(); return

        spd_m = 1.0 + self.charge * 2.5
        for i in range(len(self.ring_angles)):
            self.ring_angles[i] = (self.ring_angles[i] + self.ring_spds[i] * spd_m) % 360

        for cr in self.crystals:
            cr["angle"] += cr["spd"] * 0.02; cr["life"] -= 1
        self.crystals = [c for c in self.crystals if c["life"] > 0]
        if random.random() < self.charge * 0.28: self._spawn_crystals()

        if self.phase == 1 and random.random() < self.charge * 0.38:
            self.snowflakes.append({
                "x": cx + random.uniform(-110, 110),
                "y": cy + random.uniform(-110, 110),
                "vx": random.uniform(-0.8, 0.8), "vy": random.uniform(-1.5, 0),
                "life": random.randint(20, 45), "max": 45,
                "size": random.randint(1, 3)
            })
        for sf in self.snowflakes:
            sf["x"] += sf["vx"]; sf["y"] += sf["vy"]; sf["life"] -= 1
        self.snowflakes = [s for s in self.snowflakes if s["life"] > 0]

        self._draw()
        self.root.after(16, self._animate)

    def _draw(self):
        c = self.canvas; W, H = self.W, self.H
        cx, cy = W // 2, H // 2; t = self.tick
        c.delete("all")
        c.create_rectangle(0, 0, W, H, fill="#000508", outline="")

        if self.charge > 0.05:
            ga = int(self.charge * 16)
            for x in range(0, W, 40):
                c.create_line(x, 0, x, H, fill=_hx(0, 100, 160, ga), width=1)
            for y in range(0, H, 40):
                c.create_line(0, y, W, y, fill=_hx(0, 100, 160, ga), width=1)

        max_r = int(min(cx, cy) * 0.50)

        if self.charge > 0:
            for i in range(10, 0, -1):
                hr = int(max_r * 2.0 * self.charge * (i / 10))
                ha = int(16 * (i / 10) * self.charge)
                c.create_oval(cx-hr, cy-hr, cx+hr, cy+hr,
                              fill=_hx(0, 70, 140, ha), outline="")

        ring_cfgs = [(1.35, 65, 1, 5), (1.20, 50, 2, 4), (1.05, 42, 2, 6),
                     (0.90, 32, 1, 3), (0.76, 24, 1, 4), (0.63, 18, 1, 5)]
        for idx, (rf, arc_len, w, n) in enumerate(ring_cfgs):
            r = int(max_r * rf); ca = int(self.charge * 185)
            if ca < 8: continue
            ang = self.ring_angles[idx]; step = 360 // n
            for i in range(n):
                start = (ang + i * step) % 360
                col_r = _hx(180, 225, 255, ca) if idx % 2 == 0 else _hx(0, 195, 255, ca)
                c.create_arc(cx-r, cy-r, cx+r, cy+r, start=start,
                             extent=arc_len, outline=col_r, width=w, style="arc")

        if self.charge > 0.25:
            tk_out = int(max_r * 1.42); tk_in = int(max_r * 1.32)
            for deg in range(0, 360, 10):
                rad = math.radians(deg + t * 0.9)
                a_t = int((155 if deg % 30 == 0 else 55) * self.charge)
                c.create_line(
                    cx + tk_out * math.cos(rad), cy - tk_out * math.sin(rad),
                    cx + tk_in  * math.cos(rad), cy - tk_in  * math.sin(rad),
                    fill=_hx(180, 225, 255, a_t),
                    width=2 if deg % 30 == 0 else 1)

        for cr in self.crystals:
            px = cx + cr["dist"] * math.cos(cr["angle"])
            py = cy + cr["dist"] * math.sin(cr["angle"])
            lf = cr["life"] / cr["max"]; a = int(190 * lf * self.charge)
            sz = cr["size"]
            c.create_rectangle(int(px)-sz, int(py)-sz, int(px)+sz, int(py)+sz,
                               fill=_hx(180, 235, 255, a), outline="")

        for sf in self.snowflakes:
            lf = sf["life"] / sf["max"]; a = int(210 * lf)
            sz = sf["size"]
            c.create_oval(sf["x"]-sz, sf["y"]-sz, sf["x"]+sz, sf["y"]+sz,
                          fill=_hx(215, 240, 255, a), outline="")

        core_r = int(max_r * 0.38)
        for i in range(10, 0, -1):
            r2 = int(core_r * i / 10)
            a2 = int(215 * (i / 10) * self.charge)
            col_i = _hx(155, 215, 255, a2) if i > 5 else _hx(215, 240, 255, a2)
            c.create_oval(cx-r2, cy-r2, cx+r2, cy+r2, fill=col_i, outline="")
        for rf2, w2 in [(0.32, 2), (0.22, 1), (0.14, 1)]:
            r3 = int(max_r * rf2); ca3 = int(195 * self.charge)
            c.create_oval(cx-r3, cy-r3, cx+r3, cy+r3,
                          outline=_hx(180, 225, 255, ca3), width=w2)

        if self.phase == 1:
            bw = int(W * 0.32); bh = 6; bx = (W - bw) // 2
            by = cy + int(max_r * 1.50)
            c.create_rectangle(bx, by, bx+bw, by+bh, fill="#0a1520", outline=C_STEEL)
            c.create_rectangle(bx, by, bx+int(bw*self.charge), by+bh,
                               fill=_hx(180, 225, 255, 225), outline="")
            c.create_text(W//2, by+bh+14,
                          text=f"ARCTIC CORE CHARGING...  {int(self.charge*100)}%",
                          fill=_hx(180, 225, 255, 195), font=("Courier", 9, "bold"))

        if self.phase >= 3:
            ty_start = cy + int(max_r * 1.40)
            for i in range(self.lines_shown):
                fade = min(1.0, (self.lines_shown - i) * 0.27); a = int(195 * fade)
                last = (i == len(self.BOOT_LINES) - 1)
                col  = _hx(0, 250, 195, a) if last else _hx(180, 225, 255, a)
                c.create_text(W//2, ty_start + i * 20,
                              text=f"›  {self.BOOT_LINES[i]}",
                              fill=col, font=("Courier", 9, "bold"), anchor="center")

        if self.corner_prog > 0:
            margin = 35; blen = int(55 * self.corner_prog)
            ba = int(255 * self.corner_prog); bc = _hx(180, 225, 255, ba)
            for bx2, by2, sdx, sdy in [
                    (margin, margin, 1, 1), (W-margin, margin, -1, 1),
                    (margin, H-margin, 1, -1), (W-margin, H-margin, -1, -1)]:
                c.create_line(bx2, by2, bx2+sdx*blen, by2, fill=bc, width=2)
                c.create_line(bx2, by2, bx2, by2+sdy*blen, fill=bc, width=2)
                c.create_rectangle(bx2-3, by2-3, bx2+3, by2+3, fill=bc, outline="")

        if self.name_alpha > 0:
            na = int(255 * self.name_alpha); na2 = int(165 * self.name_alpha)
            c.create_text(cx, cy - int(max_r * 0.57), text=SYSTEM_NAME,
                          fill=_hx(215, 240, 255, na), font=("Courier", 30, "bold"))
            c.create_text(cx, cy - int(max_r * 0.36), text=FULL_NAME,
                          fill=_hx(135, 195, 235, na2), font=("Courier", 8))
            c.create_text(cx, cy - int(max_r * 0.21), text="ALL SYSTEMS ONLINE",
                          fill=_hx(0, 250, 195, na2), font=("Courier", 8, "bold"))

        if self.phase == 7 and self.fade_out > 0:
            fa = int(self.fade_out * 255)
            c.create_rectangle(0, 0, W, H, fill=_hx(4, 8, 15, fa), outline="")


# ══════════════════════════════════════════════════════════════════════════════
# WEATHER FETCHER
# ══════════════════════════════════════════════════════════════════════════════
class WeatherFetcher:
    def __init__(self):
        self.data = {"temp":"--","feels":"--","condition":"Loading...",
                     "humidity":"--","wind":"--","city":WEATHER_CITY,
                     "icon":"◈","loaded":False,"error":False}
        self._lock = threading.Lock()

    def fetch_async(self, on_done=None):
        threading.Thread(target=self._fetch, args=(on_done,),
                         daemon=True, name="WeatherFetch").start()

    def _fetch(self, on_done=None):
        try:
            import urllib.request, urllib.parse
            city_enc = urllib.parse.quote(f"{WEATHER_CITY},{WEATHER_COUNTRY}")
            url = f"https://wttr.in/{city_enc}?format=j1"
            req = urllib.request.Request(url, headers={"User-Agent":"Friday-AI"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            cur  = data["current_condition"][0]
            temp = cur["temp_C"]; feels = cur["FeelsLikeC"]
            desc = cur["weatherDesc"][0]["value"]
            hum  = cur["humidity"]; wind = cur["windspeedKmph"]
            icon_map = {"sunny":"☀","clear":"☀","cloud":"☁","rain":"🌧",
                        "drizzle":"🌦","thunder":"⛈","snow":"❄","fog":"🌫",
                        "mist":"🌫","haze":"🌫","overcast":"☁"}
            icon = "◈"
            for key, val in icon_map.items():
                if key in desc.lower(): icon = val; break
            with self._lock:
                self.data.update({"temp":f"{temp}°C","feels":f"{feels}°C",
                    "condition":desc,"humidity":f"{hum}%","wind":f"{wind} km/h",
                    "icon":icon,"loaded":True,"error":False})
        except Exception as e:
            print(f"[Weather] ⚠️ {e}")
            with self._lock:
                self.data.update({"condition":"Unavailable","loaded":True,"error":True})
        if on_done:
            try: on_done(self.data.copy())
            except Exception: pass

    def get(self):
        with self._lock: return self.data.copy()


# ══════════════════════════════════════════════════════════════════════════════
# JARVIS UI — Arctic Ice Blue  |  Split-screen layout
# ══════════════════════════════════════════════════════════════════════════════
class JarvisUI:
    def __init__(self, face_path, size=None):
        self.root = tk.Tk()
        self.root.title("F.R.I.D.A.Y — FRIDAY AI")
        self.root.resizable(False, False)

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        W  = min(sw, 1200)
        H  = min(sh, 720)
        self.root.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
        self.root.configure(bg=C_BG)
        self.W, self.H = W, H

        # Layout: left 52% = AI face, right 48% = data
        self.SPLIT = int(W * 0.52)
        self.FCX   = self.SPLIT // 2
        self.FCY   = H // 2 - 8
        self.ARC_R = min(int(H * 0.255), 165)

        # ── State ──────────────────────────────────────────────────────────
        self.speaking      = False
        self.muted         = False
        self.tick          = 0
        self.last_t        = time.time()
        self.status_blink  = True
        self._jarvis_state = "INITIALISING"
        self.status_text   = "INITIALISING"

        # ── Animation ─────────────────────────────────────────────────────
        self.ring_angles  = [0.0, 60.0, 120.0, 180.0]
        self.ring_speeds  = [0.5, -0.35, 0.72, -0.48]
        self.scan_angle   = 0.0
        self.halo_a       = 52.0; self.target_halo   = 52.0
        self.scale        = 1.0;  self.target_scale  = 1.0
        self.hex_angle    = 0.0
        self.breath_phase = 0.0
        self.pulse_rings  = []
        self.particles    = []
        self.sparks       = []
        self.bolts        = []
        self.waveform     = [0.0] * 52
        self.holo_angle   = 0.0
        self.holo_trail   = []

        # Smoothed bar values
        self._bv = {"cpu":0.0,"ram":0.0,"bat":0.0,
                    "disk":0.0,"net":0.0,"temp":0.0}
        # Sparkline histories
        self._cpu_h = [0.0]*40
        self._ram_h = [0.0]*40
        self._net_h = [0.0]*40

        # ── System stats ───────────────────────────────────────────────────
        self._sys = SystemStats() if _PSUTIL else None

        # ── Weather ────────────────────────────────────────────────────────
        self.weather        = WeatherFetcher()
        self._weather_speak = None
        self._weather_done  = False
        self._boot_done     = False

        for _ in range(10): self._spawn_particle()

        self._face_pil         = None
        self._has_face         = False
        self._face_scale_cache = None
        self._load_face(face_path)

        self.typing_queue    = deque()
        self.is_typing       = False
        self.on_text_command = None

        # ── Canvas ────────────────────────────────────────────────────────
        self.bg = tk.Canvas(self.root, width=W, height=H,
                            bg=C_BG, highlightthickness=0)
        self.bg.place(x=0, y=0)

        # ── Log panel (bottom-right) ───────────────────────────────────────
        LOG_X = self.SPLIT + 10; LOG_W = W - self.SPLIT - 18
        LOG_Y = H - 150;         LOG_H = 90
        self.log_frame = tk.Frame(self.root, bg=C_BG2,
                                  highlightbackground=C_STEEL,
                                  highlightthickness=1)
        self.log_frame.place(x=LOG_X, y=LOG_Y, width=LOG_W, height=LOG_H)
        self.log_text = tk.Text(self.log_frame, fg=C_TEXT, bg=C_BG2,
                                insertbackground=C_GLOW2, borderwidth=0,
                                wrap="word", font=("Courier", 8), padx=6, pady=4)
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state="disabled")
        self.log_text.tag_config("you",     foreground=C_SNOW)
        self.log_text.tag_config("ai",      foreground=C_GLOW2)
        self.log_text.tag_config("sys",     foreground=C_FROST)
        self.log_text.tag_config("err",     foreground=C_ERR)
        self.log_text.tag_config("weather", foreground=C_AURORA)

        # ── Input bar ─────────────────────────────────────────────────────
        INP_Y = LOG_Y + LOG_H + 4
        self._build_input_bar(LOG_W, LOG_X, INP_Y)
        self._build_mute_button()
        self.root.bind("<F4>", lambda e: self._toggle_mute())

        self._api_key_ready = self._api_keys_exist()
        if not self._api_key_ready: self._show_setup_ui()

        self._play_boot()
        self.root.protocol("WM_DELETE_WINDOW", lambda: os._exit(0))

    # ── Helpers ────────────────────────────────────────────────────────────────
    def _spawn_particle(self):
        angle = random.uniform(0, 2*math.pi)
        dist  = random.uniform(self.ARC_R*0.90, self.ARC_R*1.72)
        self.particles.append({
            "angle":angle,"dist":dist,
            "speed":random.uniform(0.14,0.60),
            "life":random.randint(60,160),"max":160,
            "size":random.randint(1,3),
            "col":random.choice([C_GLOW,C_GLOW2,C_POLAR,C_ICE2,C_AURORA])
        })

    def _spawn_spark_burst(self, n=5):
        cx, cy = self.FCX, self.FCY; r = self.ARC_R
        for _ in range(n):
            angle = random.uniform(0, 2*math.pi)
            dist  = random.uniform(r*0.3, r*0.7); spd = random.uniform(1.5,4.5)
            self.sparks.append({
                "x":cx+math.cos(angle)*dist,"y":cy+math.sin(angle)*dist,
                "vx":math.cos(angle)*spd,"vy":math.sin(angle)*spd-0.8,
                "life":random.randint(12,30),"max":30,
                "col":random.choice([(180,228,255),(0,200,255),(160,242,255)])
            })

    def _make_bolt(self):
        cx,cy = self.FCX,self.FCY; max_r=int(self.ARC_R*1.32)
        angle = random.uniform(0,2*math.pi)
        length= random.uniform(max_r*0.5,max_r*1.35)
        pts   = [cx,cy]
        for i in range(random.randint(5,11)):
            frac=(i+1)/11; tx=cx+math.cos(angle)*length*frac
            ty=cy+math.sin(angle)*length*frac; perp=angle+math.pi/2
            jitter=random.uniform(-16,16)*(1-frac)
            pts+=[tx+math.cos(perp)*jitter,ty+math.sin(perp)*jitter]
        col=random.choice([_hx(180,228,255,235),_hx(215,242,255,195),_hx(0,198,255,215)])
        return {"pts":pts,"life":random.randint(2,5),"col":col,"width":random.randint(1,2)}

    def _trigger_ripple(self, kind="speak"):
        for i in range(3):
            self.pulse_rings.append({"r":0.0,"kind":kind,"delay":i*7})

    # ── Mute ───────────────────────────────────────────────────────────────────
    def _build_mute_button(self):
        self._mute_canvas = tk.Canvas(self.root,width=120,height=28,
                                      bg=C_BG,highlightthickness=0,cursor="hand2")
        self._mute_canvas.place(x=10,y=self.H-40)
        self._mute_canvas.bind("<Button-1>",lambda e:self._toggle_mute())
        self._draw_mute_button()

    def _draw_mute_button(self):
        c=self._mute_canvas; c.delete("all")
        if self.muted:
            bc,fc,ic,lbl,fg = C_MUTED_FG,"#12000a","🔇"," MUTED",C_MUTED_FG
        else:
            bc,fc,ic,lbl,fg = C_STEEL,C_BG2,"🎙"," LIVE",C_AURORA
        c.create_rectangle(0,0,120,28,outline=bc,fill=fc,width=1)
        c.create_text(60,14,text=f"{ic}{lbl}",fill=fg,font=("Courier",8,"bold"))

    def _toggle_mute(self):
        self.muted=not self.muted; self._draw_mute_button()
        if self.muted: self.set_state("MUTED"); self.write_log("SYS: Microphone muted.")
        else:          self.set_state("LISTENING"); self.write_log("SYS: Microphone active.")

    # ── Input ──────────────────────────────────────────────────────────────────
    def _build_input_bar(self,lw,lx,y):
        BTN_W=72; INP_W=lw-BTN_W-4
        self._input_var=tk.StringVar()
        self._input_entry=tk.Entry(self.root,textvariable=self._input_var,
            fg=C_ICE,bg=C_BG2,insertbackground=C_GLOW2,borderwidth=0,
            font=("Courier",9),highlightthickness=1,
            highlightbackground=C_STEEL,highlightcolor=C_GLOW)
        self._input_entry.place(x=lx,y=y,width=INP_W,height=26)
        self._input_entry.bind("<Return>",self._on_input_submit)
        self._input_entry.bind("<KP_Enter>",self._on_input_submit)
        self._send_btn=tk.Button(self.root,text="SEND ›",
            command=self._on_input_submit,fg=C_GLOW,bg=C_BG2,
            activeforeground=C_BG,activebackground=C_GLOW,
            font=("Courier",8,"bold"),borderwidth=0,cursor="hand2",
            highlightthickness=1,highlightbackground=C_STEEL)
        self._send_btn.place(x=lx+INP_W+4,y=y,width=BTN_W,height=26)

    def _on_input_submit(self,event=None):
        text=self._input_var.get().strip()
        if not text: return
        self._input_var.set(""); self.write_log(f"You: {text}")
        self._trigger_ripple("msg")
        if self.on_text_command:
            threading.Thread(target=self.on_text_command,args=(text,),daemon=True).start()

    # ── State ──────────────────────────────────────────────────────────────────
    def set_state(self,state:str):
        prev=self._jarvis_state; self._jarvis_state=state
        if state=="MUTED":     self.status_text="MUTED";      self.speaking=False
        elif state=="SPEAKING":
            self.status_text="SPEAKING"; self.speaking=True
            if prev!="SPEAKING": self._trigger_ripple("speak"); self._spawn_spark_burst(6)
        elif state=="THINKING":   self.status_text="THINKING";    self.speaking=False
        elif state=="PROCESSING": self.status_text="PROCESSING";  self.speaking=False
        elif state=="LISTENING":  self.status_text="LISTENING";   self.speaking=False
        else:                     self.status_text="ONLINE";      self.speaking=False

    # ── Face ───────────────────────────────────────────────────────────────────
    def _load_face(self,path):
        D=self.ARC_R*2
        try:
            img=Image.open(path).convert("RGBA").resize((D,D),Image.LANCZOS)
            mask=Image.new("L",(D,D),0)
            ImageDraw.Draw(mask).ellipse((2,2,D-2,D-2),fill=255)
            img.putalpha(mask); self._face_pil=img; self._has_face=True
        except Exception: self._has_face=False

    # ── Boot ───────────────────────────────────────────────────────────────────
    def _play_boot(self):
        BootAnimation(root=self.root,W=self.W,H=self.H,on_complete=self._on_boot_complete)

    def _on_boot_complete(self):
        self._boot_done=True; self._animate()
        self.weather.fetch_async(on_done=self._on_weather_loaded)

    def _on_weather_loaded(self,data):
        if data.get("error"): self.write_log("SYS: Weather unavailable."); return
        self.write_log(
            f"WEATHER: {data['icon']} {WEATHER_CITY} — {data['temp']} "
            f"({data['condition']}) Hum {data['humidity']} Wind {data['wind']}")
        if self._weather_speak and not self._weather_done:
            self._weather_done=True
            now_h=time.localtime().tm_hour
            greeting=("Good morning sir" if now_h<12 else
                      "Good afternoon sir" if now_h<17 else "Good evening sir")
            msg=(f"{greeting}. Meerut Modipuram — {data['temp']}, feels like "
                 f"{data['feels']}. {data['condition']}. "
                 f"Humidity {data['humidity']}, wind {data['wind']}.")
            threading.Thread(target=self._weather_speak,args=(msg,),daemon=True).start()

    # ── Draw helpers ───────────────────────────────────────────────────────────
    def _draw_arc_ring(self,c,cx,cy,r,angle,arc_len,color,width=2,n=3):
        step=360//n
        for i in range(n):
            start=(angle+i*step)%360
            c.create_arc(cx-r,cy-r,cx+r,cy+r,start=start,extent=arc_len,
                         outline=color,width=width,style="arc")

    def _draw_hex(self,c,cx,cy,r,color,angle=0,width=1):
        pts=[]
        for i in range(6):
            a=math.radians(angle+i*60); pts+=[cx+r*math.cos(a),cy+r*math.sin(a)]
        c.create_polygon(pts,outline=color,fill="",width=width)

    def _draw_stat_row(self,c,x,y,w,h,value,color,label,val_str,spark=None):
        """Single stat row: label | animated bar | value text"""
        lw=48
        c.create_text(x,y+h//2,text=label,fill=C_FROST,
                      font=("Courier",8),anchor="w")
        bx=x+lw; bw=w-lw-58
        c.create_rectangle(bx,y,bx+bw,y+h,fill=C_DEEP2,outline=C_STEEL2)
        bar_col=(C_ERR if value>0.85 else C_WARN if value>0.65 else color)
        fw=max(2,int(bw*value))
        c.create_rectangle(bx,y,bx+fw,y+h,fill=bar_col,outline="")
        if fw>4:
            c.create_line(bx,y,bx+fw,y,fill=_hx(255,255,255,45),width=1)
        c.create_text(bx+bw+5,y+h//2,text=val_str,fill=color,
                      font=("Courier",8,"bold"),anchor="w")
        if spark and len(spark)>=4:
            sy0=y+h+2; sh2=9; pts2=[]
            n2=len(spark)
            for i,v in enumerate(spark):
                sx=bx+int(i*bw/n2); sv=sy0+sh2-int(v*sh2); pts2+=[sx,sv]
            if len(pts2)>=4:
                c.create_line(pts2,fill=_hx(0,175,255,75),width=1,smooth=True)

    # ── Animate ────────────────────────────────────────────────────────────────
    def _animate(self):
        if not self._boot_done: return
        self.tick+=1; t=self.tick; now=time.time()

        if now-self.last_t>(0.08 if self.speaking else 0.42):
            if self.speaking:
                self.target_scale=random.uniform(1.03,1.09)
                self.target_halo =random.uniform(145,198)
            elif self.muted:
                self.target_scale=1.0; self.target_halo=random.uniform(10,22)
            else:
                self.target_scale=random.uniform(1.0,1.004)
                self.target_halo =random.uniform(48,68)
            self.last_t=now

        sp=0.27 if self.speaking else 0.09
        self.scale  +=(self.target_scale-self.scale)*sp
        self.halo_a +=(self.target_halo -self.halo_a)*sp

        for i in range(len(self.ring_angles)):
            spd=self.ring_speeds[i]*(2.4 if self.speaking else 1.0)
            self.ring_angles[i]=(self.ring_angles[i]+spd)%360
        self.scan_angle=(self.scan_angle+(2.6 if self.speaking else 0.75))%360
        self.hex_angle =(self.hex_angle+0.33)%360
        self.breath_phase+=0.038 if self.speaking else 0.011

        self.holo_angle=(self.holo_angle+(1.5 if self.speaking else 0.55))%360
        self.holo_trail.append(self.holo_angle)
        if len(self.holo_trail)>20: self.holo_trail.pop(0)

        limit=self.ARC_R*2.1; new_rings=[]
        for rr in self.pulse_rings:
            delay=rr.get("delay",0)
            if delay>0: rr["delay"]-=1; new_rings.append(rr); continue
            spd=4.4 if rr["kind"]=="speak" else 5.4
            rr["r"]+=spd
            if rr["r"]<limit: new_rings.append(rr)
        self.pulse_rings=new_rings

        if self.speaking:
            if random.random()<0.09: self.bolts.append(self._make_bolt())
            if random.random()<0.055: self._spawn_spark_burst(3)
        self.bolts=[b for b in self.bolts if b["life"]>0]
        for b in self.bolts: b["life"]-=1

        for s in self.sparks:
            s["x"]+=s["vx"]; s["y"]+=s["vy"]; s["vy"]+=0.18; s["life"]-=1
        self.sparks=[s for s in self.sparks if s["life"]>0]

        for p in self.particles:
            p["angle"]+=p["speed"]*0.016*(1.38 if self.speaking else 1.0); p["life"]-=1
        self.particles=[p for p in self.particles if p["life"]>0]
        if random.random()<(0.17 if self.speaking else 0.04): self._spawn_particle()
        while len(self.particles)>22: self.particles.pop(0)

        for i in range(len(self.waveform)):
            if self.speaking: target=random.uniform(0.1,1.0)
            elif self.muted:  target=0.02
            else: target=abs(math.sin(t*0.053+i*0.37))*0.19
            self.waveform[i]+=(target-self.waveform[i])*0.35

        if self._sys:
            ss=self._sys.get()
            cpu=ss["cpu"]; ram=ss["ram"]; bat=ss["battery"]; plugged=ss["plugged"]
            net_s=ss["net_sent"]; net_r=ss["net_recv"]; disk=ss["disk"]; temp=ss["temp"]
            ram_used=ss.get("ram_used_gb",0); ram_total=ss.get("ram_total_gb",0)
            disk_used=ss.get("disk_used_gb",0); disk_total=ss.get("disk_total_gb",0)
        else:
            cpu=random.uniform(20,40); ram=random.uniform(40,60)
            bat=75; plugged=False; net_s=net_r=1.0; disk=50; temp=None
            ram_used=ram_total=disk_used=disk_total=0

        targets={"cpu":cpu/100,"ram":ram/100,"bat":(bat/100 if bat else 0),
                 "disk":disk/100,"net":min(1.0,(net_s+net_r)/200),
                 "temp":min(1.0,(temp/100 if temp else 0))}
        for k in self._bv: self._bv[k]+=(targets[k]-self._bv[k])*0.14

        if t%5==0:
            self._cpu_h.append(cpu/100); self._cpu_h=self._cpu_h[-40:]
            self._ram_h.append(ram/100); self._ram_h=self._ram_h[-40:]
            nv=min(1.0,(net_s+net_r)/200)
            self._net_h.append(nv);     self._net_h=self._net_h[-40:]

        if t%35==0: self.status_blink=not self.status_blink

        breath=math.sin(self.breath_phase)*0.5+0.5
        self._draw(breath,cpu,ram,bat,plugged,net_s,net_r,disk,temp,
                   ram_used,ram_total,disk_used,disk_total)
        self.root.after(16,self._animate)

    # ── Draw ───────────────────────────────────────────────────────────────────
    def _draw(self,breath,cpu,ram,bat,plugged,
              net_s,net_r,disk,temp,ram_used,ram_total,disk_used,disk_total):
        c=self.bg; W,H=self.W,self.H; t=self.tick
        FCX=self.FCX; FCY=self.FCY; AR=self.ARC_R; SP=self.SPLIT
        c.delete("all")

        # ── Background ────────────────────────────────────────────────────
        c.create_rectangle(0,0,W,H,fill=C_BG,outline="")
        # Subtle radial on left
        for i in range(7,0,-1):
            r=int(AR*2.4*i/7); a=int(10*(i/7))
            c.create_oval(FCX-r,FCY-r,FCX+r,FCY+r,fill=_hx(0,55,115,a),outline="")
        # Left grid
        for y in range(0,H,36):
            a=9+int(4*math.sin(t*0.013+y*0.035))
            c.create_line(0,y,SP,y,fill=_hx(0,70,130,a),width=1)
        for x in range(0,SP,36):
            a=7+int(3*math.sin(t*0.013+x*0.035))
            c.create_line(x,0,x,H,fill=_hx(0,70,130,a),width=1)

        # ── Split divider ─────────────────────────────────────────────────
        c.create_line(SP,0,SP,H,fill=C_STEEL,width=1)
        for gi in range(4,0,-1):
            c.create_line(SP-gi,0,SP-gi,H,fill=_hx(0,155,215,int(35*(gi/4))),width=1)

        # Right bg + grid
        c.create_rectangle(SP,0,W,H,fill=C_BG,outline="")
        for y in range(0,H,36):
            c.create_line(SP,y,W,y,fill=_hx(0,55,95,7),width=1)
        for x in range(SP,W,36):
            c.create_line(x,0,x,H,fill=_hx(0,55,95,6),width=1)

        # ── Header ────────────────────────────────────────────────────────
        c.create_rectangle(0,0,W,32,fill=C_BG2,outline="")
        c.create_line(0,32,W,32,fill=C_STEEL,width=1)
        c.create_line(0,32,int(self.halo_a/200*W),32,fill=_hx(0,175,255,70),width=2)
        shx=int((t*2.4)%(W+80))-40
        c.create_line(shx,0,shx+48,32,fill=_hx(0,155,215,16),width=26)
        c.create_text(FCX,10,text=SYSTEM_NAME,fill=C_ICE,font=("Courier",13,"bold"))
        c.create_text(FCX,23,text=FULL_NAME,fill=C_STEEL,font=("Courier",7))
        c.create_text(10,16,text=MODEL_BADGE,fill=C_FROST,font=("Courier",8,"bold"),anchor="w")
        c.create_text(W-10,10,text=time.strftime("%H:%M:%S"),
                      fill=C_ICE,font=("Courier",12,"bold"),anchor="e")
        c.create_text(W-10,23,text=time.strftime("%a %b %d"),
                      fill=C_FROST,font=("Courier",7),anchor="e")

        # ── Breathing glow ────────────────────────────────────────────────
        br=math.sin(self.breath_phase)*0.5+0.5
        for gi in range(6,0,-1):
            gr=int(AR*(1.88+br*0.22)*gi/6)
            ga=int(br*(28 if self.speaking else 12)*(gi/6))
            gc=_hx(255,55,95,ga) if self.muted else _hx(0,135,215,ga)
            c.create_oval(FCX-gr,FCY-gr,FCX+gr,FCY+gr,fill=gc,outline="")

        # ── Ripple rings ──────────────────────────────────────────────────
        for rr in self.pulse_rings:
            if rr.get("delay",0)>0: continue
            r=int(rr["r"]); pct=rr["r"]/(AR*2.1); a=int(225*(1.0-pct))
            col=(_hx(255,55,95,a) if self.muted else _hx(0,195,255,a)) if rr["kind"]=="speak" else _hx(255,155,0,a)
            c.create_oval(FCX-r,FCY-r,FCX+r,FCY+r,outline=col,width=2)

        # ── Holo scan trail ───────────────────────────────────────────────
        holo_r=int(AR*1.21)
        for idx,ang in enumerate(self.holo_trail):
            fade=idx/max(len(self.holo_trail),1); a=int(fade*(145 if self.speaking else 55))
            rad=math.radians(ang); ex=FCX+holo_r*math.cos(rad); ey=FCY-holo_r*math.sin(rad)
            col=_hx(255,95,45,a) if self.muted else _hx(0,235,195,a)
            c.create_line(FCX,FCY,ex,ey,fill=col,width=1)

        # ── Arc reactor rings ─────────────────────────────────────────────
        for idx,(rf,arc_len,_,n_arcs) in enumerate(
                [(AR*1.13,3,75,2),(AR*1.03,2,53,3),(AR*0.93,2,40,2),(AR*0.83,1,30,4)]):
            ring_r=int(rf)
            a_val=max(0,min(255,int(self.halo_a*(1.0-idx*0.13))))
            col=_hx(255,55,95,a_val) if self.muted else _hx(180,225,255,a_val)
            self._draw_arc_ring(c,FCX,FCY,ring_r,self.ring_angles[idx],arc_len,col,width=2,n=n_arcs)

        # Degree ticks
        tk_out=int(AR*1.16); tk_in=int(AR*1.10)
        for deg in range(0,360,10):
            rad=math.radians(deg+self.ring_angles[0]*0.33)
            inn=tk_in if deg%30==0 else tk_in+4
            a_tk=115 if deg%30==0 else 48
            c.create_line(FCX+tk_out*math.cos(rad),FCY-tk_out*math.sin(rad),
                          FCX+inn  *math.cos(rad),FCY-inn  *math.sin(rad),
                          fill=_hx(180,225,255,a_tk),width=2 if deg%30==0 else 1)

        # Sweep
        sc_r=int(AR*1.08); sc_a=int(self.halo_a*1.1); sweep=58 if self.speaking else 30
        sc_col=_hx(255,95,45,sc_a//2) if self.muted else _hx(0,250,195,sc_a)
        c.create_arc(FCX-sc_r,FCY-sc_r,FCX+sc_r,FCY+sc_r,
                     start=self.scan_angle,extent=sweep,outline=sc_col,width=3,style="arc")

        # Crosshair
        ch_r=int(AR*1.19); gap=int(AR*0.15); ca=int(self.halo_a*0.42)
        chc=_hx(255,55,95,ca) if self.muted else _hx(180,225,255,ca)
        for x1,y1,x2,y2 in [(FCX-ch_r,FCY,FCX-gap,FCY),(FCX+gap,FCY,FCX+ch_r,FCY),
                              (FCX,FCY-ch_r,FCX,FCY-gap),(FCX,FCY+gap,FCX,FCY+ch_r)]:
            c.create_line(x1,y1,x2,y2,fill=chc,width=1)

        # Hex rings
        hex_a=int(self.halo_a*0.38); hc=_hx(180,225,255,hex_a)
        self._draw_hex(c,FCX,FCY,int(AR*0.83),hc,self.hex_angle,1)
        self._draw_hex(c,FCX,FCY,int(AR*0.56),hc,-self.hex_angle*1.52,1)

        # Face corner brackets
        hl=FCX-AR; hr=FCX+AR; ht=FCY-AR; hb=FCY+AR; blen=18
        bc_a=int(self.halo_a*1.38)
        bc=_hx(255,55,95,bc_a) if self.muted else _hx(180,225,255,bc_a)
        for bx2,by2,sdx,sdy in [(hl,ht,1,1),(hr,ht,-1,1),(hl,hb,1,-1),(hr,hb,-1,-1)]:
            c.create_line(bx2,by2,bx2+sdx*blen,by2,fill=bc,width=2)
            c.create_line(bx2,by2,bx2,by2+sdy*blen,fill=bc,width=2)
            c.create_oval(bx2-3,by2-3,bx2+3,by2+3,fill=bc,outline="")

        # Lightning
        for b in self.bolts:
            if len(b["pts"])>=4:
                c.create_line(b["pts"],fill=b["col"],width=b["width"],smooth=False,joinstyle="round")

        # Face / core
        if self._has_face:
            fw=int(AR*2*self.scale)
            if self._face_scale_cache is None or abs(self._face_scale_cache[0]-self.scale)>0.004:
                scaled=self._face_pil.resize((fw,fw),Image.BILINEAR)
                tk_img=ImageTk.PhotoImage(scaled)
                self._face_scale_cache=(self.scale,tk_img)
            c.create_image(FCX,FCY,image=self._face_scale_cache[1])
        else:
            for i in range(10,0,-1):
                r2=int(AR*0.37*i/10); ga=int(self.halo_a*(i/10))
                oc=(255,55,95) if self.muted else (0,155,215)
                c.create_oval(FCX-r2,FCY-r2,FCX+r2,FCY+r2,
                              fill=_hx(int(oc[0]*(i/10)),int(oc[1]*(i/10)),int(oc[2]*(i/10)),ga),outline="")
            for r_f in [0.29,0.21,0.13]:
                c.create_oval(FCX-int(AR*r_f),FCY-int(AR*r_f),FCX+int(AR*r_f),FCY+int(AR*r_f),
                              outline=_hx(180,225,255,155),width=2)
            c.create_text(FCX,FCY,text=SYSTEM_NAME,
                          fill=_hx(215,240,255,min(255,int(self.halo_a*2.2))),font=("Courier",12,"bold"))

        # Sparks
        for s in self.sparks:
            lf=s["life"]/s["max"]; a=int(215*lf); rb,gb,bb=s["col"]; sz=max(1,int(4*lf))
            c.create_oval(s["x"]-sz,s["y"]-sz,s["x"]+sz,s["y"]+sz,fill=_hx(rb,gb,bb,a),outline="")

        # Particles + tails
        for p in self.particles:
            px=FCX+p["dist"]*math.cos(p["angle"]); py=FCY+p["dist"]*math.sin(p["angle"])
            lf=p["life"]/p["max"]; a=int(195*lf)
            hv=int.from_bytes(bytes.fromhex(p["col"][1:]),"big")
            rb=(hv>>16)&0xff; gb=(hv>>8)&0xff; bb=hv&0xff; sz=p["size"]
            c.create_oval(px-sz,py-sz,px+sz,py+sz,fill=_hx(rb,gb,bb,a),outline="")
            tx=FCX+p["dist"]*math.cos(p["angle"]-p["speed"]*4)
            ty=FCY+p["dist"]*math.sin(p["angle"]-p["speed"]*4)
            c.create_line(px,py,tx,ty,fill=_hx(rb,gb,bb,int(a*0.32)),width=1)

        # ── Status badge ──────────────────────────────────────────────────
        sy=FCY+AR+20
        if self.muted:     stat,sc="⊘  MUTED",C_MUTED_FG
        elif self.speaking:stat,sc="●  SPEAKING",_hx(255,120,120,255)
        elif self._jarvis_state=="THINKING":
            sym="◈" if self.status_blink else "◇"; stat,sc=f"{sym}  THINKING",C_WARN
        elif self._jarvis_state=="PROCESSING":
            sym="▷" if self.status_blink else "▶"; stat,sc=f"{sym}  PROCESSING",C_WARN
        elif self._jarvis_state=="LISTENING":
            sym="●" if self.status_blink else "○"; stat,sc=f"{sym}  LISTENING",C_AURORA
        else:
            sym="●" if self.status_blink else "○"; stat,sc=f"{sym}  {self.status_text}",C_GLOW2
        c.create_rectangle(FCX-86,sy-10,FCX+86,sy+10,fill=_hx(4,8,15,215),outline=sc,width=1)
        c.create_text(FCX,sy,text=stat,fill=sc,font=("Courier",10,"bold"))

        # ── Waveform ──────────────────────────────────────────────────────
        wy=sy+18; N=len(self.waveform); bw2=6; tot=N*bw2; wx0=FCX-tot//2; BH=11
        for i,lv in enumerate(self.waveform):
            bh=max(1,int(BH*lv)); bx=wx0+i*bw2
            col=(C_MUTED_FG if self.muted else C_GLOW if lv>0.6 else C_FROST if lv>0.3 else C_STEEL)
            c.create_rectangle(bx,wy+BH-bh,bx+bw2-1,wy+BH,fill=col,outline="")

        # ══ RIGHT PANEL — DATA ════════════════════════════════════════════
        RX=SP+12; RW=W-SP-20

        # ── SYSTEM VITALS section ─────────────────────────────────────────
        sy2=36
        c.create_line(RX,sy2+13,RX+RW,sy2+13,fill=C_STEEL,width=1)
        c.create_rectangle(RX,sy2,RX+95,sy2+13,fill=C_BG2,outline="")
        c.create_text(RX+4,sy2+6,text="SYSTEM VITALS",
                      fill=C_FROST,font=("Courier",7,"bold"),anchor="w")
        sy2+=18

        BAR_H=9; ROW_H=22
        if bat is not None:
            bat_str=f"{bat}% {'⚡' if plugged else '🔋'}"
        else:
            bat_str="N/A"
        net_total=net_s+net_r

        stats_rows=[
            ("CPU",  self._bv["cpu"],  C_GLOW2,
             f"{cpu:.0f}%", self._cpu_h),
            ("RAM",  self._bv["ram"],  C_POLAR,
             f"{ram:.0f}%  {ram_used:.1f}/{ram_total:.0f}G", self._ram_h),
            ("DISK", self._bv["disk"], C_AURORA,
             f"{disk:.0f}%  {disk_used:.0f}/{disk_total:.0f}G", None),
            ("BAT",  self._bv["bat"],  C_ICE2,
             bat_str, None),
            ("NET",  self._bv["net"],  C_WARN,
             f"↑{net_s:.0f} ↓{net_r:.0f} KB", self._net_h),
            ("TEMP", self._bv["temp"], C_ERR,
             (f"{temp:.0f}°C" if temp else "N/A"), None),
        ]
        for lbl,val,col,val_str,spark in stats_rows:
            self._draw_stat_row(c,RX,sy2,RW,BAR_H,val,col,lbl,val_str,spark)
            sy2+=ROW_H+(13 if spark else 0)

        sy2+=6

        # ── ENVIRONMENT section ───────────────────────────────────────────
        c.create_line(RX,sy2+13,RX+RW,sy2+13,fill=C_STEEL,width=1)
        c.create_rectangle(RX,sy2,RX+105,sy2+13,fill=C_BG2,outline="")
        c.create_text(RX+4,sy2+6,text="ENVIRONMENT",
                      fill=C_FROST,font=("Courier",7,"bold"),anchor="w")
        sy2+=18

        wd=self.weather.get()
        if wd["loaded"] and not wd["error"]:
            env_rows=[
                (f"{wd['icon']} TEMP",wd["temp"],    C_GLOW2),
                ("FEEL",             wd["feels"],   C_ICE2),
                ("HUM",              wd["humidity"],C_AURORA),
                ("WIND",             wd["wind"],    C_FROST),
                ("COND",             wd["condition"][:14],C_POLAR),
            ]
        elif not wd["loaded"]:
            env_rows=[("WTHR","LOADING...",C_FROST)]
        else:
            env_rows=[("WTHR","UNAVAILABLE",C_ERR)]

        for lbl,val,col in env_rows:
            c.create_text(RX,sy2+5,text=lbl,fill=C_STEEL,font=("Courier",7),anchor="w")
            c.create_text(RX+RW,sy2+5,text=val,fill=col,font=("Courier",8,"bold"),anchor="e")
            sy2+=15
        sy2+=6

        # ── MISSION CLOCK section ─────────────────────────────────────────
        c.create_line(RX,sy2+13,RX+RW,sy2+13,fill=C_STEEL,width=1)
        c.create_rectangle(RX,sy2,RX+110,sy2+13,fill=C_BG2,outline="")
        c.create_text(RX+4,sy2+6,text="MISSION CLOCK",
                      fill=C_FROST,font=("Courier",7,"bold"),anchor="w")
        sy2+=22

        c.create_text(RX+RW//2,sy2,text=time.strftime("%H:%M:%S"),
                      fill=C_ICE,font=("Courier",22,"bold"),anchor="n")
        sy2+=30
        c.create_text(RX+RW//2,sy2,text=time.strftime("%A, %B %d %Y"),
                      fill=C_FROST,font=("Courier",8),anchor="n")
        sy2+=18

        mode_col=(C_MUTED_FG if self.muted else
                  C_ERR if self.speaking else
                  C_WARN if "THINK" in self.status_text or "PROC" in self.status_text
                  else C_AURORA)
        sym2="●" if self.status_blink else "○"
        c.create_text(RX+RW//2,sy2,text=f"{sym2}  {self.status_text}",
                      fill=mode_col,font=("Courier",9,"bold"),anchor="n")

        # ── Footer ────────────────────────────────────────────────────────
        c.create_rectangle(0,H-22,W,H,fill=C_BG2,outline="")
        c.create_line(0,H-22,W,H-22,fill=C_STEEL,width=1)
        c.create_text(W//2,H-11,
                      text="Sanket Maurya  ·  CLASSIFIED  ·  FRIDAY AI",
                      fill=C_DIM,font=("Courier",7))
        c.create_text(W-10,H-11,text="[F4] MUTE",fill=C_DIM,font=("Courier",7),anchor="e")
        c.create_text(10,H-11,text="v2.0 ARCTIC",fill=C_DIM,font=("Courier",7),anchor="w")

    # ── Log ────────────────────────────────────────────────────────────────────
    def write_log(self,text:str):
        self.typing_queue.append(text); tl=text.lower()
        if tl.startswith("you:"): self.set_state("PROCESSING")
        elif tl.startswith(("friday:","ai:","jarvis:")): self.set_state("SPEAKING")
        if not self.is_typing: self._start_typing()

    def _start_typing(self):
        if not self.typing_queue:
            self.is_typing=False
            if not self.speaking and not self.muted: self.set_state("LISTENING")
            return
        self.is_typing=True; text=self.typing_queue.popleft(); tl=text.lower()
        if tl.startswith("you:"): tag="you"
        elif tl.startswith(("friday:","ai:","jarvis:")): tag="ai"
        elif tl.startswith("weather:"): tag="weather"
        elif tl.startswith("err:") or "error" in tl or "failed" in tl: tag="err"
        else: tag="sys"
        self.log_text.configure(state="normal")
        self._type_char(text,0,tag)

    def _type_char(self,text,i,tag):
        if i<len(text):
            self.log_text.insert(tk.END,text[i],tag)
            self.log_text.see(tk.END)
            self.root.after(7,self._type_char,text,i+1,tag)
        else:
            self.log_text.insert(tk.END,"\n")
            self.log_text.configure(state="disabled")
            self.root.after(20,self._start_typing)

    # ── Compat ─────────────────────────────────────────────────────────────────
    def start_speaking(self): self.set_state("SPEAKING")
    def stop_speaking(self):
        if not self.muted: self.set_state("LISTENING")

    # ── API key ────────────────────────────────────────────────────────────────
    def _api_keys_exist(self): return API_FILE.exists()
    def wait_for_api_key(self):
        while not self._api_key_ready: time.sleep(0.1)

    def _show_setup_ui(self):
        self.setup_frame=tk.Frame(self.root,bg=C_BG2,
                                  highlightbackground=C_GLOW,highlightthickness=1)
        self.setup_frame.place(relx=0.5,rely=0.5,anchor="center")
        tk.Label(self.setup_frame,text="◈  INITIALISATION REQUIRED",
                 fg=C_GLOW,bg=C_BG2,font=("Courier",13,"bold")).pack(pady=(18,4))
        tk.Label(self.setup_frame,text="Enter your Gemini API key to boot F.R.I.D.A.Y.",
                 fg=C_FROST,bg=C_BG2,font=("Courier",9)).pack(pady=(0,10))
        tk.Label(self.setup_frame,text="GEMINI API KEY",
                 fg=C_FROST,bg=C_BG2,font=("Courier",9)).pack(pady=(8,2))
        self.gemini_entry=tk.Entry(self.setup_frame,width=52,fg=C_ICE,bg=C_BG,
                                   insertbackground=C_GLOW,borderwidth=0,
                                   font=("Courier",10),show="*",
                                   highlightthickness=1,highlightbackground=C_STEEL)
        self.gemini_entry.pack(pady=(0,4))
        tk.Button(self.setup_frame,text="›  INITIALISE SYSTEMS",
                  command=self._save_api_keys,bg=C_BG,fg=C_GLOW,
                  activebackground=C_DEEP,font=("Courier",10),
                  borderwidth=0,pady=8).pack(pady=14)

    def _save_api_keys(self):
        gemini=self.gemini_entry.get().strip()
        if not gemini: return
        os.makedirs(CONFIG_DIR,exist_ok=True)
        with open(API_FILE,"w",encoding="utf-8") as f:
            json.dump({"gemini_api_key":gemini},f,indent=4)
        self.setup_frame.destroy(); self._api_key_ready=True
        self.set_state("LISTENING"); self.write_log("SYS: Systems initialised. FRIDAY online.")