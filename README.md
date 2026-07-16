# CLICKER5000

> ASCII auto-clicker for Windows. One file. Zero scaffold. The UI **is** the character grid.

```plaintext
┌─────────┬──────────┬──────────────────┬──────────┐
│ [Speed] │ [Hotkey] │ [status] OFF:[○] │ [-]  [x] │
└─────────┴──────────┴──────────────────┴──────────┘
```

Borderless, always-on-top, draggable. Every glyph is live: the interface is rendered
as a character grid on a canvas with per-cell hit-testing — it is the ASCII spec,
not a widget skin approximating it.

---

## Quick Start

```ps1
# Install uv
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# Create venv with uv
uv venv
# Activate the enviorment
.venv\Scripts\activate
# Install Dependencies
uv add pynput
# (optional) uv add --dev types-pynput
```

> RUN CLICKER 5000
```ps1
uv run main.py
```

That's it. Dependencies are declared inline via **PEP 723** script metadata —
`uv` resolves `pynput` into an ephemeral cached env automatically. No `uv init`,
no venv activation, no `pyproject.toml`.

<details>
<summary>Alternative install paths</summary>

```bash
# classic pip
pip install pynput
python clickr.py

# uv project (if folding into a larger repo)
uv add pynput
uv add --dev types-pynput        # mypy stubs
uv run clickr.py
```

</details>

**Requirements:** Windows · Python ≥ 3.9 · [`pynput`](https://pypi.org/project/pynput/)

---

## Controls

| Element                | Action                                                                                   |
|------------------------|------------------------------------------------------------------------------------------|
| `[Speed]`              | Opens the click-delay panel (drop-down slider + numeric)                                 |
| `[  50]`               | **Click to type** an exact ms value · `ENTER` commit · `ESC` cancel · click-away commits |
| `░▒░`                  | Slider thumb — drag left/right; numeric readout is live-exact                            |
| `[Hotkey]`             | Opens the binding panel                                                                  |
| `> press key/btn <`    | Click, then hit any keyboard key or mouse button to bind · `ESC` cancels                 |
| `[status]` / `OFF:[○]` | Click to toggle the clicker · `ON: [●]` renders green                                    |
| `[-]`                  | Minimize to taskbar                                                                      |
| `[x]`                  | Exit                                                                                     |
| *(frame)*              | Drag any non-interactive cell to move the window                                         |

**Hotkey is global** — toggles the clicker whether or not the window has focus.
Default binding: `MOUSE5` (`Button.x2`). Left mouse is reserved (it's the button
being clicked) and cannot be bound.

Hover any element for a tooltip. Tips extend from the **right edge** of the app
on a transparent layer with a hard-offset retro drop shadow — zero UI occlusion.

---

## Speed Semantics

Delay between clicks in **milliseconds**, matching the Logitech macro standard
for click-timing delay.

|            |                                         |
|------------|-----------------------------------------|
| Range      | `1 – 1000 ms` (clamped)                 |
| Default    | `50 ms` (~20 CPS)                       |
| `1 ms`     | ~1000 CPS theoretical ceiling           |
| Click type | Left button, at current cursor position |

---

## Configuration

All knobs are constants at the top of `clickr.py` — no config file, no flags.

```python
FONT_NAME, FONT_SIZE = "Consolas", 12
BG, FG, DIM          = "#0c0c0c", "#c9c9c9", "#5f5f5f"
GRN, AMB             = "#39d353", "#e0af68"
ON_DOT, OFF_DOT      = "●", "○"      # swap ● for ⬤ if your font keeps it monospaced
TRACK                = 17            # slider track width (chars)
THUMB                = "░▒░"
MIN_MS, MAX_MS       = 1, 1000
SHADOW_PX            = 6             # tooltip shadow offset (right+down)
TIPS                 = {...}         # tooltip copy per element
```

---

## Architecture

Single file, four moving parts:

```plaintext
clicker thread ──▶ pynput MouseController · left-click loop @ interval_ms
global hooks   ──▶ pynput listeners · hotkey toggle + capture mode (any focus)
grid renderer  ──▶ build() emits colored segment rows + (row, c0, c1, action)
                   hit regions; canvas redraws the full grid per state change
event layer    ──▶ tk bindings · click dispatch, slider/window drag, motion
                   → tooltips, key events → numeric edit mode
```

Design notes:

- **Character-grid UI** — click coords divide by cell size (`x // CW, y // CH`)
  into `(row, col)`, resolved against hit regions registered at build time.
  Pixel-perfect ASCII with real interactivity.
- **Thread boundary** — pynput listeners never touch tk. They flip a dirty flag;
  the UI thread polls at 40 ms and rebuilds. No cross-thread tk calls.
- **Edit-mode guard** — while typing in the ms field, the global keyboard hook
  stands down so a keyboard-bound hotkey can't fire mid-entry; rearms on commit.
- **Borderless minimize** — `overrideredirect` windows can't iconify, so `[-]`
  temporarily restores the native frame, minimizes, and `<Map>` re-strips it.
- **Tooltip layer** — separate toplevel keyed transparent (`-transparentcolor`),
  letting tips float past the window bounds with a shadow over the desktop.

---

## Build a Standalone EXE

```bash
pyinstaller --onefile --noconsole clickr.py
# → dist/clickr.exe
```

---

## Type Checking

```bash
uv run --with mypy --with types-pynput mypy clickr.py
```

Stubs are added explicitly (`types-pynput`) rather than via `mypy --install-types`,
which shells out to pip behind uv's back.

---

## Changelog

### v1.1

- **Tooltips** on every interactive element — right-side extension, transparent
  layer, hard-offset retro drop shadow
- **Type-in speed** — click the numeric readout to enter an exact ms value
  (`▌` block cursor, digits only, clamped, click-away commits)
- **PEP 723** inline metadata — `uv run clickr.py` with zero project scaffold
- Global-hook guard during numeric edit

### v1.0

- ASCII bar UI per spec: `[Speed]` · `[Hotkey]` · `[status]` · `[-]` · `[x]`
- Drop-down ASCII slider with live-exact numeric readout
- Global hotkey bind (keyboard or mouse, default `MOUSE5`)
- Character-grid renderer with per-cell hit-testing
- Borderless topmost window, frame drag, taskbar minimize

---

## Roadmap (unslotted)

- `[settings]` column — click type (L/R/M), CPS jitter, hold-vs-toggle mode
- Profile save/load (per-game speed + binding presets)

---

**MIVIM** · single-file tooling · spec-driven
