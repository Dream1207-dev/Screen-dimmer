# Screen Dimmer

A translucent dark film that floats over part of your screen — like a
polarizer or an ND filter for your monitor.

It dims by proportion, exactly like a camera ND filter: glaring bright
areas are pulled down a lot, while dark areas are scaled down by the
same ratio, so shadow detail never gets crushed into solid black. Put
it over a too-bright window, read comfortably, and leave the rest of
the screen untouched.

Pure Python 3 standard library (tkinter + ctypes). No third-party
packages, no network access, no registry changes, nothing running in
the background after you close it.

## Features

- **Darkness slider** from 5% to 95%, with Light 30% / Medium 60% /
  Extra Dark 85% presets
- **Film color** — preset swatches (black, warm brown, navy, green,
  plum), a full system color picker, or direct **RGB sliders**
  (0–255 per channel, with a live preview)
- **Multiple films** — add as many as you like; on multi-monitor
  setups a new film automatically appears on the next monitor
- **Global maximize hotkey** (default `Ctrl+Alt+M`, customizable):
  every film fills the monitor it is currently on; press again to
  restore all films to their previous size and position
- **Click-through** mode: work with the windows under the film as if
  it weren't there
- **Always on top** toggle, and a control panel you can hide to the
  taskbar while the films stay up

## Requirements

- Windows 11 (Windows 10 should also work)
- Python 3 — the launcher installs it for you if it's missing

## Quick start

1. Put `dimmer.py` and `run-dimmer.bat` in the same folder.
2. Double-click **`run-dimmer.bat`**.
   - First run only: if Python isn't installed, the launcher installs
     the official python.org build automatically via `winget`
     (per-user, usually no admin password needed). This takes a few
     minutes — don't close the black window.
   - After that, every double-click just opens the dimmer.
3. Drag the film over whatever is glaring, adjust, done.

If you already have Python, `python dimmer.py` works too.

## Using it

### Move and resize the film

The film has no title bar (a title bar would cover whatever is under
it). Drag anywhere on the film to move it; drag its edges or corners
to resize — the cursor changes shape over the edges. A thin gray
outline shows where the film ends.

### Darkness

Use the slider or the preset buttons. 60% is the starting point. If
text under the film gets hard to read, lower the darkness.

### Color

- Click a **swatch** for a ready-made tint.
- Drag the **R / G / B sliders** to mix any color precisely; the film
  updates live and the numbers are shown beside each slider.
- **Custom...** opens the system color picker.

A colored film tints everything under it, like tinted glasses. Warm
brown (around R 42, G 22, B 8) is gentle for long reading; plain black
keeps colors most neutral.

### Multiple films and monitors

The **Films** row shows how many films exist.

- **Add film** creates another film. With several monitors, it lands
  on the next monitor over; with one monitor, it appears slightly
  offset so you can drag it into place.
- **Remove film** deletes the most recently added one (one film
  always remains).
- Darkness, color, click-through and always-on-top apply to **all**
  films at once. Position and size are per film.

### Maximize hotkey

- Default: **`Ctrl+Alt+M`**, works in any window, no need to focus
  the panel.
- Press once: every film fills its own monitor. Press again: all
  films return to their previous size and position.
- To change it: click **Set...** in the panel, then press your
  combination. It is remembered across restarts (stored in
  `dimmer-settings.json` next to `dimmer.py`).
- Rules: the combination must include **Ctrl** or **Alt** (so the
  film doesn't jump while you type), and the main key can be a
  letter, a digit, F1–F12, or Space.

### Click-through

Turn **Click-through** on when the film is positioned and you want to
click, type, and scroll in the windows underneath. While it's on, the
mouse ignores the film completely — so to move or resize the film,
turn click-through off first.

### Hiding the panel / exiting

- **Hide panel** shrinks the control panel to the taskbar; the films
  stay on screen and the maximize hotkey keeps working. Click the
  taskbar icon to bring the panel back.
- **Exit** closes everything.

## Why a Python script and not an .exe?

An unsigned home-made `.exe` gets blocked by Windows 11's **Smart
App Control**: it only trusts programs that carry a commercial code
signing certificate *and* have built up download reputation, and a
freshly built personal tool has neither. Python itself is signed and
widely trusted, and the script simply runs inside it — so this
version starts reliably. Please don't turn Smart App Control off for
a tool like this: turning it off is a one-way switch that can only be
reversed by resetting Windows.

## Files

| File | What it is |
| --- | --- |
| `dimmer.py` | The whole app (single file) |
| `run-dimmer.bat` | Launcher: checks for Python, installs it if missing, starts the app |
| `dimmer-settings.json` | Created automatically; stores your hotkey choice |

## Uninstall

Close the app and delete the folder. If Python was installed by the
launcher and you don't need it otherwise, uninstall it from Windows
Settings → Apps like any other program.
