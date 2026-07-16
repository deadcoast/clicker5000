# /// script
# requires-python = ">=3.9"
# dependencies = ["pynput"]
# ///
"""
CLICKR — ASCII auto-clicker for Windows                          v1.1
=====================================================================
run:   uv run clickr.py          (PEP 723 inline deps, zero scaffold)
exe:   pyinstaller --onefile --noconsole clickr.py

  ┌─────────┬──────────┬──────────────────┬──────────┐
  │ [Speed] │ [Hotkey] │ [status] OFF:[○] │ [-]  [x] │
  └─────────┴──────────┴──────────────────┴──────────┘

v1.1 QOL:
[1] TOOLTIPS  — every interactive element. All tips extend from the
    RIGHT side of the app (never cover the UI). Hard-offset retro
    drop shadow (shadow geometry only — palette stays ours).
[2] DESIGN    — unchanged. Same grid, same colors, same balance.
[3] SPEED TAB — click the numeric readout [  50] to type an exact
    ms value. ENTER commits · ESC cancels · click-away commits.

- [Speed]  -> ASCII slider  [  50] ██░▒░████...  drag ░▒░, live ms
- [Hotkey] -> bind any keyboard key / mouse button (default MOUSE5)
- [status] -> click to toggle. OFF:[○] / ON: [●]  (hotkey = global)
- [-]/[x]  -> minimize / close · drag frame anywhere else to move
"""

import time
import threading
import tkinter as tk
import tkinter.font as tkfont

from pynput import mouse, keyboard
from pynput.mouse import Button, Controller as MouseController

# ----------------------------- config -----------------------------

FONT_NAME, FONT_SIZE = "Consolas", 12

BG   = "#0c0c0c"   # window background
FG   = "#c9c9c9"   # default text
DIM  = "#5f5f5f"   # borders / inactive
GRN  = "#39d353"   # ON status / live numeric
AMB  = "#e0af68"   # slider thumb / accents / edit mode

SHADOW    = "#000000"   # tooltip hard-offset shadow
SHADOW_PX = 6           # shadow offset (right+down), retro style
TIP_KEY   = "#010203"   # transparency key color for tooltip layer

ON_DOT, OFF_DOT = "●", "○"   # swap "●" for "⬤" if your font keeps it monospaced
TRACK  = 17                  # slider track width (chars)
THUMB  = "░▒░"               # the draggable slider button
MIN_MS, MAX_MS = 1, 1000     # click delay range (Logitech-style ms timing)

TIPS = {
    "speed":  "click delay panel",
    "hotkey": "bind toggle key",
    "status": "toggle clicker on/off",
    "min":    "minimize to taskbar",
    "close":  "exit clickr",
    "setkey": "press any key / mouse btn",
    "slider": "drag ░▒░ to adjust speed",
    "msfield": "click + type exact ms",
}

# ----------------------------- state ------------------------------

class State:
    interval_ms  = 50
    running      = False
    hotkey_type  = "mouse"        # "mouse" | "key"
    hotkey_mouse = Button.x2      # MOUSE5
    hotkey_key   = None
    capturing    = False
    speed_open   = False
    hotkey_open  = False
    editing      = False          # typing directly into the ms readout
    buf          = ""             # edit buffer

S = State()
mouse_ctl = MouseController()
_dirty = {"v": False}

def mark():
    _dirty["v"] = True

MOUSE_NAMES = {
    Button.x2: "MOUSE5", Button.x1: "MOUSE4",
    Button.middle: "MOUSE3", Button.right: "MOUSE2",
}

def hotkey_name():
    if S.hotkey_type == "mouse":
        return MOUSE_NAMES.get(S.hotkey_mouse, str(S.hotkey_mouse).upper())
    k = S.hotkey_key
    if k is None:
        return "NONE"
    try:
        return (k.char or "?").upper()
    except AttributeError:
        return str(k).replace("Key.", "").upper()

# ------------------------- clicker engine -------------------------

def click_loop():
    while True:
        if S.running:
            mouse_ctl.click(Button.left)
            time.sleep(max(S.interval_ms, MIN_MS) / 1000.0)
        else:
            time.sleep(0.02)

threading.Thread(target=click_loop, daemon=True).start()

# ----------------------- global input hooks -----------------------

def _toggle():
    S.running = not S.running
    mark()

def on_global_click(x, y, btn, pressed):
    if not pressed:
        return
    if S.capturing:
        if btn == Button.left:          # left is reserved for the clicker/UI
            return
        S.hotkey_type, S.hotkey_mouse = "mouse", btn
        S.capturing = False
        mark()
    elif S.hotkey_type == "mouse" and btn == S.hotkey_mouse:
        _toggle()

def _same_key(k):
    hk = S.hotkey_key
    if hk is None:
        return False
    if k == hk:
        return True
    try:
        return k.vk == hk.vk
    except AttributeError:
        return False

def on_global_press(key):
    if S.editing:                       # typing in the ms field — stand down
        return
    if S.capturing:
        if key == keyboard.Key.esc:
            S.capturing = False
            mark()
            return
        S.hotkey_type, S.hotkey_key = "key", key
        S.capturing = False
        mark()
    elif S.hotkey_type == "key" and _same_key(key):
        _toggle()

mouse_listener = mouse.Listener(on_click=on_global_click)
key_listener   = keyboard.Listener(on_press=on_global_press)
mouse_listener.start()
key_listener.start()

# ----------------------------- window -----------------------------

root = tk.Tk()
root.overrideredirect(True)
root.attributes("-topmost", True)
root.configure(bg=BG)

FONT = tkfont.Font(family=FONT_NAME, size=FONT_SIZE)
CW = FONT.measure("█")
CH = FONT.metrics("linespace")

canvas = tk.Canvas(root, bg=BG, highlightthickness=0, bd=0)
canvas.pack()

# ------------------------ tooltip layer ---------------------------
# Separate borderless toplevel so tips extend OFF the right edge of
# the app. Shadow = solid rect hard-offset down-right (retro style).

class Tooltip:
    def __init__(self):
        self.top = tk.Toplevel(root)
        self.top.overrideredirect(True)
        self.top.attributes("-topmost", True)
        self.cv = tk.Canvas(self.top, bg=TIP_KEY, highlightthickness=0, bd=0)
        self.cv.pack()
        try:                                   # Windows: key color -> transparent
            self.top.attributes("-transparentcolor", TIP_KEY)
        except tk.TclError:
            self.cv.configure(bg=BG)           # fallback: opaque, still shadowed
        self.top.withdraw()

    def show(self, text, row):
        box = ["┌" + "─" * (len(text) + 2) + "┐",
               "│ " + text + " │",
               "└" + "─" * (len(text) + 2) + "┘"]
        bw, bh = len(box[0]) * CW, 3 * CH
        self.cv.delete("all")
        self.cv.config(width=bw + SHADOW_PX, height=bh + SHADOW_PX)
        self.cv.create_rectangle(SHADOW_PX, SHADOW_PX,          # drop shadow
                                 SHADOW_PX + bw, SHADOW_PX + bh,
                                 fill=SHADOW, outline="")
        self.cv.create_rectangle(0, 0, bw, bh, fill=BG, outline="")
        for i, ln in enumerate(box):
            self.cv.create_text(0, i * CH, text=ln, font=FONT,
                                fill=DIM if i != 1 else FG, anchor="nw")
        x = root.winfo_rootx() + root.winfo_width() + 10       # from the right
        y = root.winfo_rooty() + row * CH - CH
        self.top.geometry(f"+{x}+{max(y, 0)}")
        self.top.deiconify()

    def hide(self):
        self.top.withdraw()

tooltip = Tooltip()

# ------------------------- grid renderer --------------------------

_regions = []      # (row, c0, c1, action)
_slider  = {"row": -1, "c0": 0}
_drag    = {"mode": None, "ox": 0, "oy": 0}
_hover   = {"action": None, "row": 0, "after": None}

class Line:
    """One row of the character grid: colored segments + hit regions."""
    def __init__(self, row):
        self.row, self.col, self.segs = row, 0, []
    def add(self, text, color=FG, action=None):
        if action:
            _regions.append((self.row, self.col, self.col + len(text) - 1, action))
        self.segs.append((text, color))
        self.col += len(text)
        return self

def build():
    _regions.clear()
    lines = []
    r = 0

    run = S.running
    dot = f"ON: [{ON_DOT}]" if run else f"OFF:[{OFF_DOT}]"   # both 7 chars

    # ---- main bar ----
    lines.append(Line(r).add("┌─────────┬──────────┬──────────────────┬──────────┐", DIM)); r += 1
    L = Line(r)
    L.add("│ ", DIM)
    L.add("[Speed]", AMB if S.speed_open else FG, action="speed")
    L.add(" │ ", DIM)
    L.add("[Hotkey]", AMB if S.hotkey_open else FG, action="hotkey")
    L.add(" │ ", DIM)
    L.add("[status] ", FG, action="status")
    L.add(dot, GRN if run else FG, action="status")
    L.add(" │ ", DIM)
    L.add("[-]", FG, action="min")
    L.add("  ", DIM)
    L.add("[x]", FG, action="close")
    L.add(" │", DIM)
    lines.append(L); r += 1
    lines.append(Line(r).add("└─────────┴──────────┴──────────────────┴──────────┘", DIM)); r += 1

    # ---- [Speed] drop-down: editable numeric + draggable slider ----
    if S.speed_open:
        frac = (S.interval_ms - MIN_MS) / (MAX_MS - MIN_MS)
        pos  = round(frac * (TRACK - len(THUMB)))
        bar_l, bar_r = "█" * pos, "█" * (TRACK - len(THUMB) - pos)

        inner = 2 + 6 + 1 + TRACK + 2          # "│ [9999] <track> │"
        lines.append(Line(r).add("┌" + "─" * (inner - 2) + "┐", DIM)); r += 1
        L = Line(r)
        L.add("│ ", DIM)
        if S.editing:                          # type-in mode, block cursor
            disp = (S.buf + "▌").ljust(4)[:4]
            L.add("[", AMB, action="msfield")
            L.add(disp, AMB, action="msfield")
            L.add("]", AMB, action="msfield")
        else:                                  # live exact numeric (ms)
            L.add(f"[{S.interval_ms:>4}]", GRN, action="msfield")
        L.add(" ", DIM)
        _slider["row"], _slider["c0"] = r, L.col
        L.add(bar_l, FG, action="slider")
        L.add(THUMB, AMB, action="slider")
        L.add(bar_r, FG, action="slider")
        L.add(" │", DIM)
        lines.append(L); r += 1
        lines.append(Line(r).add("└" + "─" * (inner - 2) + "┘", DIM)); r += 1

    # ---- [Hotkey] drop-down: bound key + assign widget ----
    if S.hotkey_open:
        pad = " " * 10                          # align under the [Hotkey] column
        name = hotkey_name()[:11]
        setline = "> listening..   <" if S.capturing else "> press key/btn <"
        lines.append(Line(r).add(pad).add("┌───────────────────┐", DIM)); r += 1
        L = Line(r).add(pad).add("│ ", DIM)
        L.add("bound: ", DIM)
        L.add(f"{name:<10}", GRN)
        L.add(" │", DIM)
        lines.append(L); r += 1
        L = Line(r).add(pad).add("│ ", DIM)
        L.add(setline, AMB if S.capturing else FG, action="setkey")
        L.add(" │", DIM)
        lines.append(L); r += 1
        lines.append(Line(r).add(pad).add("└───────────────────┘", DIM)); r += 1

    # ---- render ----
    canvas.delete("all")
    max_cols = max(l.col for l in lines)
    canvas.config(width=max_cols * CW, height=len(lines) * CH)
    for L in lines:
        x = 0
        for text, color in L.segs:
            canvas.create_text(x * CW, L.row * CH, text=text, fill=color,
                               font=FONT, anchor="nw")
            x += len(text)
    root.geometry(f"{max_cols * CW}x{len(lines) * CH}")

# --------------------------- actions ------------------------------

def commit_edit():
    if not S.editing:
        return
    S.editing = False
    if S.buf:
        S.interval_ms = min(max(int(S.buf), MIN_MS), MAX_MS)
    S.buf = ""

def do_speed():
    commit_edit()
    S.speed_open = not S.speed_open
    S.hotkey_open = False
    build()

def do_hotkey():
    commit_edit()
    S.hotkey_open = not S.hotkey_open
    S.speed_open = False
    if not S.hotkey_open:
        S.capturing = False
    build()

def do_status():
    _toggle()
    build()

def do_min():
    commit_edit()
    tooltip.hide()
    root.overrideredirect(False)
    root.iconify()

def do_close():
    mouse_listener.stop()
    key_listener.stop()
    root.destroy()

def do_setkey():
    S.capturing = True
    build()

def do_msfield():
    if not S.editing:                  # [3] click numeric -> type exact ms
        S.editing, S.buf = True, ""
        root.focus_force()
        build()

ACTIONS = {"speed": do_speed, "hotkey": do_hotkey, "status": do_status,
           "min": do_min, "close": do_close, "setkey": do_setkey,
           "msfield": do_msfield}

def _hit(row, col):
    for r, c0, c1, action in _regions:
        if r == row and c0 <= col <= c1:
            return action
    return None

def _set_ms_from_col(col):
    span = TRACK - 1
    frac = min(max((col - _slider["c0"]) / span, 0.0), 1.0)
    S.interval_ms = round(MIN_MS + frac * (MAX_MS - MIN_MS))
    build()

# --------------------------- events -------------------------------

def on_down(e):
    tooltip.hide()
    row, col = e.y // CH, e.x // CW
    action = _hit(row, col)
    if S.editing and action != "msfield":
        commit_edit()                  # click-away commits typed value
        build()
        action = _hit(row, col)        # regions rebuilt; re-resolve
    if action == "slider":
        _drag["mode"] = "slider"
        _set_ms_from_col(col)
    elif action:
        ACTIONS[action]()
    else:
        _drag["mode"], _drag["ox"], _drag["oy"] = "window", e.x, e.y

def on_move(e):
    if _drag["mode"] == "slider":
        _set_ms_from_col(e.x // CW)
    elif _drag["mode"] == "window":
        root.geometry(f"+{e.x_root - _drag['ox']}+{e.y_root - _drag['oy']}")

def on_up(_):
    _drag["mode"] = None

def _cancel_hover():
    if _hover["after"]:
        root.after_cancel(_hover["after"])
        _hover["after"] = None

def on_motion(e):
    if _drag["mode"]:
        return
    row, col = e.y // CH, e.x // CW
    action = _hit(row, col)
    if action != _hover["action"]:
        _cancel_hover()
        tooltip.hide()
        _hover["action"], _hover["row"] = action, row
        if action in TIPS:
            _hover["after"] = root.after(
                380, lambda a=action, r=row: tooltip.show(TIPS[a], r))

def on_leave(_):
    _cancel_hover()
    _hover["action"] = None
    tooltip.hide()

def on_key(e):
    if not S.editing:
        return
    if e.keysym == "Return":
        commit_edit()
    elif e.keysym == "Escape":
        S.editing, S.buf = False, ""
    elif e.keysym == "BackSpace":
        S.buf = S.buf[:-1]
    elif e.char.isdigit() and len(S.buf) < 4:
        S.buf += e.char
    build()

def on_map(_):
    if root.state() == "normal":       # restore borderless after un-minimize
        root.overrideredirect(True)
        root.attributes("-topmost", True)

canvas.bind("<Button-1>", on_down)
canvas.bind("<B1-Motion>", on_move)
canvas.bind("<ButtonRelease-1>", on_up)
canvas.bind("<Motion>", on_motion)
canvas.bind("<Leave>", on_leave)
root.bind("<Key>", on_key)
root.bind("<Map>", on_map)

def poll():                            # listener threads flag; UI thread redraws
    if _dirty["v"]:
        _dirty["v"] = False
        build()
    root.after(40, poll)

build()
poll()
root.mainloop()