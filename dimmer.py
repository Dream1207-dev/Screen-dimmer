# -*- coding: utf-8 -*-
"""
Screen Dimmer (Windows 11, multi-film / multi-monitor edition)

A translucent dark film that floats over part of the screen, like a
polarizer or ND filter: bright areas are pulled down a lot, dark areas
are scaled down by the same ratio, so shadow detail is never crushed
into solid black. It works by proportional dimming, exactly like a
camera ND filter.

Features:
- Darkness slider from 5% to 95%, plus three preset buttons
- Film color: preset swatches / system color picker / RGB sliders
- Multiple films (Add film); a new film lands on the next monitor
- Global, customizable maximize hotkey: every film fills the monitor
  it is currently on
- Always-on-top toggle, click-through toggle, minimizable panel

Pure Python 3 standard library. No third-party packages required.
"""

import sys
import ctypes
import json
import os
import tkinter as tk
from tkinter import colorchooser

IS_WIN = sys.platform.startswith("win")


# ---------------- Multi-monitor helpers (Win32) ----------------
class _RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class _MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_ulong), ("rcMonitor", _RECT),
                ("rcWork", _RECT), ("dwFlags", ctypes.c_ulong)]


def monitor_rects():
    """Return (left, top, right, bottom) for every monitor."""
    rects = []
    if not IS_WIN:
        return rects
    proc_type = ctypes.WINFUNCTYPE(
        ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p,
        ctypes.POINTER(_RECT), ctypes.c_ssize_t)

    def _cb(_hmon, _hdc, lprc, _data):
        r = lprc.contents
        rects.append((r.left, r.top, r.right, r.bottom))
        return True

    try:
        ctypes.windll.user32.EnumDisplayMonitors(
            None, None, proc_type(_cb), 0)
    except Exception:
        pass
    return rects


def monitor_rect_for(hwnd):
    """Return the (left, top, right, bottom) of the monitor a window is on."""
    if not IS_WIN:
        return None
    try:
        hmon = ctypes.windll.user32.MonitorFromWindow(hwnd, 2)
        mi = _MONITORINFO()
        mi.cbSize = ctypes.sizeof(_MONITORINFO)
        ctypes.windll.user32.GetMonitorInfoW(hmon, ctypes.byref(mi))
        r = mi.rcMonitor
        return (r.left, r.top, r.right, r.bottom)
    except Exception:
        return None


# ---------------- A single film ----------------
class Film:
    def __init__(self, app, x, y, w, h):
        self.app = app
        self.win = tk.Toplevel(app.ctrl)
        self.win.configure(bg="#8a8a8a")
        self.win.geometry(f"{w}x{h}+{x}+{y}")
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", app.top_var.get())
        self.win.attributes("-alpha", app.alpha_var.get() / 100.0)
        self.inner = tk.Frame(self.win, bg=app.current_color)
        self.inner.place(x=1, y=1, relwidth=1.0, relheight=1.0,
                         width=-2, height=-2)
        self.maximized = False
        self.saved_geo = None
        self._drag_data = None
        self.win.bind("<ButtonPress-1>", self._press)
        self.win.bind("<B1-Motion>", self._drag)
        self.win.bind("<Motion>", self._hover)
        app._apply_clickthrough_to(self)

    def top_hwnd(self):
        try:
            parent = ctypes.windll.user32.GetParent(self.win.winfo_id())
            return parent if parent else self.win.winfo_id()
        except Exception:
            return self.win.winfo_id()

    def maximize(self):
        if self.maximized:
            return
        self.saved_geo = (self.win.winfo_width(), self.win.winfo_height(),
                          self.win.winfo_x(), self.win.winfo_y())
        rect = monitor_rect_for(self.top_hwnd())
        if rect:
            l, t, r, b = rect
            self.win.geometry(f"{r - l}x{b - t}+{l}+{t}")
        else:
            sw = self.win.winfo_screenwidth()
            sh = self.win.winfo_screenheight()
            self.win.geometry(f"{sw}x{sh}+0+0")
        self.maximized = True

    def restore(self):
        if not self.maximized:
            return
        if self.saved_geo:
            w, h, x, y = self.saved_geo
            self.win.geometry(f"{w}x{h}+{x}+{y}")
        self.maximized = False

    def destroy(self):
        self.win.destroy()

    # ---- Drag / resize for a borderless window ----
    def _zone(self, x_root, y_root):
        grip = 8
        fx, fy = self.win.winfo_x(), self.win.winfo_y()
        fw, fh = self.win.winfo_width(), self.win.winfo_height()
        lx, ly = x_root - fx, y_root - fy
        left, right = lx < grip, lx > fw - grip
        top, bottom = ly < grip, ly > fh - grip
        if left and top:
            return "tl"
        if right and top:
            return "tr"
        if left and bottom:
            return "bl"
        if right and bottom:
            return "br"
        if left:
            return "l"
        if right:
            return "r"
        if top:
            return "t"
        if bottom:
            return "b"
        return "move"

    def _hover(self, event):
        cursors = {
            "move": "fleur", "l": "sb_h_double_arrow",
            "r": "sb_h_double_arrow", "t": "sb_v_double_arrow",
            "b": "sb_v_double_arrow", "tl": "size_nw_se",
            "br": "size_nw_se", "tr": "size_ne_sw", "bl": "size_ne_sw",
        }
        zone = self._zone(event.x_root, event.y_root)
        self.win.configure(cursor=cursors.get(zone, "arrow"))

    def _press(self, event):
        self._drag_data = (
            self._zone(event.x_root, event.y_root),
            event.x_root, event.y_root,
            self.win.winfo_x(), self.win.winfo_y(),
            self.win.winfo_width(), self.win.winfo_height(),
        )

    def _drag(self, event):
        if not self._drag_data:
            return
        zone, x0, y0, fx, fy, fw, fh = self._drag_data
        dx, dy = event.x_root - x0, event.y_root - y0
        x, y, w, h = fx, fy, fw, fh
        if zone == "move":
            x, y = fx + dx, fy + dy
        else:
            if "r" in zone:
                w = max(60, fw + dx)
            if "b" in zone:
                h = max(60, fh + dy)
            if "l" in zone:
                w = max(60, fw - dx)
                x = fx + fw - w
            if "t" in zone:
                h = max(60, fh - dy)
                y = fy + fh - h
        self.win.geometry(f"{w}x{h}+{x}+{y}")


# ---------------- Main app / control panel ----------------
class Dimmer:
    def __init__(self):
        # ---------------- Control panel window ----------------
        self.ctrl = tk.Tk()
        self.ctrl.title("Screen Dimmer - Control Panel")
        self.ctrl.attributes("-topmost", True)
        self.ctrl.resizable(False, False)
        self.ctrl.configure(bg="#22252a")
        self.ctrl.geometry("+40+40")

        # ---------------- State ----------------
        self.hotkey = self._load_hotkey()
        self._capture = False
        self._combo_down = False
        self._syncing = False
        self.current_color = "#000000"
        self.films = []

        # ---------------- Panel widgets ----------------
        fg = "#e8e8e8"
        bg = "#22252a"

        tk.Label(self.ctrl, text="Darkness", fg=fg, bg=bg,
                 font=("Segoe UI", 10)).grid(
                     row=0, column=0, padx=8, pady=(10, 0), sticky="w")

        self.alpha_var = tk.IntVar(value=60)
        self.scale = tk.Scale(
            self.ctrl, from_=5, to=95, orient="horizontal", length=240,
            variable=self.alpha_var, command=self._on_scale,
            fg=fg, bg=bg, troughcolor="#3a3f47", highlightthickness=0,
            font=("Segoe UI", 9))
        self.scale.grid(row=0, column=1, padx=4, pady=(10, 0), sticky="we")

        self.pct_label = tk.Label(self.ctrl, text="60%", fg=fg, bg=bg,
                                  font=("Segoe UI", 10), width=5)
        self.pct_label.grid(row=0, column=2, padx=8, pady=(10, 0))

        preset_frame = tk.Frame(self.ctrl, bg=bg)
        preset_frame.grid(row=1, column=0, columnspan=3, pady=(2, 6))
        for text, val in (("Light 30%", 30), ("Medium 60%", 60), ("Extra Dark 85%", 85)):
            tk.Button(preset_frame, text=text,
                      command=lambda v=val: self._set_alpha(v),
                      font=("Segoe UI", 9)).pack(side="left", padx=4)

        color_frame = tk.Frame(self.ctrl, bg=bg)
        color_frame.grid(row=2, column=0, columnspan=3, pady=(0, 6))
        tk.Label(color_frame, text="Film color", fg=fg, bg=bg,
                 font=("Segoe UI", 9)).pack(side="left", padx=(0, 4))
        for name, hexv in (("Black", "#000000"), ("Warm", "#2a1608"),
                           ("Navy", "#0a1430"), ("Green", "#0a2418"),
                           ("Plum", "#1e0a24")):
            tk.Button(color_frame, text="", width=3, bg=hexv,
                      activebackground=hexv,
                      command=lambda c=hexv: self._set_color(c)).pack(
                          side="left", padx=2)
        tk.Button(color_frame, text="Custom...",
                  command=self._pick_color,
                  font=("Segoe UI", 9)).pack(side="left", padx=(6, 0))

        rgb_frame = tk.Frame(self.ctrl, bg=bg)
        rgb_frame.grid(row=3, column=0, columnspan=3, pady=(0, 6),
                       sticky="w", padx=8)
        self.rgb_vars = []
        self.rgb_labels = []
        for i, name in enumerate(("R", "G", "B")):
            tk.Label(rgb_frame, text=name, fg=fg, bg=bg,
                     font=("Segoe UI", 9)).grid(row=i, column=0, sticky="w")
            var = tk.IntVar(value=0)
            self.rgb_vars.append(var)
            tk.Scale(rgb_frame, from_=0, to=255, orient="horizontal",
                     length=200, variable=var, command=self._on_rgb,
                     fg=fg, bg=bg, troughcolor="#3a3f47",
                     highlightthickness=0, showvalue=False,
                     font=("Segoe UI", 9)).grid(row=i, column=1, padx=4)
            lab = tk.Label(rgb_frame, text="0", fg=fg, bg=bg, width=4,
                           font=("Segoe UI", 9))
            lab.grid(row=i, column=2, sticky="w")
            self.rgb_labels.append(lab)
        self.rgb_preview = tk.Label(rgb_frame, text="      ", bg="#000000")
        self.rgb_preview.grid(row=0, column=3, rowspan=3, padx=(8, 0))

        self.top_var = tk.BooleanVar(value=True)
        tk.Checkbutton(self.ctrl, text="Always on top", variable=self.top_var,
                       command=self._apply_topmost,
                       fg=fg, bg=bg, selectcolor="#3a3f47",
                       activebackground=bg, activeforeground=fg,
                       font=("Segoe UI", 9)).grid(
                           row=4, column=0, columnspan=3, sticky="w", padx=8)

        self.ct_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            self.ctrl,
            text="Click-through (lets you click windows under the film; turn off before moving/resizing the film)",
            variable=self.ct_var, command=self._apply_clickthrough,
            fg=fg, bg=bg, selectcolor="#3a3f47",
            activebackground=bg, activeforeground=fg,
            font=("Segoe UI", 9), wraplength=380,
            justify="left").grid(row=5, column=0, columnspan=3,
                                 sticky="w", padx=8)

        hot_frame = tk.Frame(self.ctrl, bg=bg)
        hot_frame.grid(row=6, column=0, columnspan=3, pady=(4, 0),
                       sticky="w", padx=8)
        tk.Label(hot_frame, text="Maximize hotkey", fg=fg, bg=bg,
                 font=("Segoe UI", 9)).pack(side="left")
        self.hotkey_label = tk.Label(
            hot_frame, text=self._combo_text(), fg="#ffd479", bg=bg,
            font=("Segoe UI", 9, "bold"))
        self.hotkey_label.pack(side="left", padx=6)
        self.set_key_btn = tk.Button(hot_frame, text="Set...",
                                     command=self._start_capture,
                                     font=("Segoe UI", 9))
        self.set_key_btn.pack(side="left", padx=2)
        tk.Button(hot_frame, text="Maximize",
                  command=self._toggle_maximize,
                  font=("Segoe UI", 9)).pack(side="left", padx=2)

        film_frame = tk.Frame(self.ctrl, bg=bg)
        film_frame.grid(row=7, column=0, columnspan=3, pady=(4, 0),
                        sticky="w", padx=8)
        tk.Label(film_frame, text="Films", fg=fg, bg=bg,
                 font=("Segoe UI", 9)).pack(side="left")
        self.film_count = tk.Label(film_frame, text="1", fg="#ffd479",
                                   bg=bg, font=("Segoe UI", 9, "bold"))
        self.film_count.pack(side="left", padx=6)
        tk.Button(film_frame, text="Add film", command=self._add_film,
                  font=("Segoe UI", 9)).pack(side="left", padx=2)
        tk.Button(film_frame, text="Remove film",
                  command=self._remove_film,
                  font=("Segoe UI", 9)).pack(side="left", padx=2)

        btn_frame = tk.Frame(self.ctrl, bg=bg)
        btn_frame.grid(row=8, column=0, columnspan=3, pady=(6, 10))
        tk.Button(btn_frame, text="Hide panel", command=self.ctrl.iconify,
                  font=("Segoe UI", 9)).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Exit", command=self.ctrl.destroy,
                  font=("Segoe UI", 9)).pack(side="left", padx=4)

        # First film (created once the panel variables exist)
        self._add_film(first=True)

        self.ctrl.protocol("WM_DELETE_WINDOW", self.ctrl.destroy)
        self.ctrl.after(120, self._poll_hotkey)

    # ---------------- Adding / removing films ----------------
    def _add_film(self, first=False):
        if first or not self.films:
            film = Film(self, 120, 120, 900, 600)
        else:
            rects = monitor_rects()
            last = self.films[-1]
            if len(rects) > 1:
                cur = monitor_rect_for(last.top_hwnd())
                try:
                    idx = rects.index(cur)
                except ValueError:
                    idx = 0
                l, t, r, b = rects[(idx + 1) % len(rects)]
                w = max(120, min(900, r - l - 80))
                h = max(120, min(600, b - t - 80))
                film = Film(self, l + 40, t + 40, w, h)
            else:
                film = Film(self,
                            last.win.winfo_x() + 40,
                            last.win.winfo_y() + 40,
                            last.win.winfo_width(),
                            last.win.winfo_height())
        self.films.append(film)
        self.film_count.config(text=str(len(self.films)))

    def _remove_film(self):
        if len(self.films) <= 1:
            return
        self.films.pop().destroy()
        self.film_count.config(text=str(len(self.films)))

    # ---------------- Logic ----------------
    def _on_scale(self, _value=None):
        self._set_alpha(self.alpha_var.get())

    def _set_alpha(self, val):
        val = max(5, min(95, int(val)))
        self.alpha_var.set(val)
        self.pct_label.config(text=f"{val}%")
        for film in self.films:
            try:
                film.win.attributes("-alpha", val / 100.0)
            except tk.TclError:
                pass

    def _set_color(self, hexv):
        self.current_color = hexv
        for film in self.films:
            film.inner.configure(bg=hexv)
        try:
            r = int(hexv[1:3], 16)
            g = int(hexv[3:5], 16)
            b = int(hexv[5:7], 16)
        except (ValueError, IndexError):
            return
        self._syncing = True
        try:
            for var, val, lab in zip(self.rgb_vars, (r, g, b),
                                     self.rgb_labels):
                var.set(val)
                lab.config(text=str(val))
            self.rgb_preview.config(bg=hexv)
        finally:
            self._syncing = False

    def _on_rgb(self, _value=None):
        if self._syncing:
            return
        r, g, b = (v.get() for v in self.rgb_vars)
        for var, lab in zip(self.rgb_vars, self.rgb_labels):
            lab.config(text=str(var.get()))
        hexv = "#%02x%02x%02x" % (r, g, b)
        self.current_color = hexv
        for film in self.films:
            film.inner.configure(bg=hexv)
        self.rgb_preview.config(bg=hexv)

    def _pick_color(self):
        _rgb, hexv = colorchooser.askcolor(
            color=self.current_color, title="Pick a film color")
        if hexv:
            self._set_color(hexv)

    # ---------------- Maximize hotkey (global, works in any window) ----------------
    _SETTINGS = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "dimmer-settings.json")

    def _load_hotkey(self):
        default = {"ctrl": True, "alt": True, "shift": False,
                   "vk": 0x4D, "label": "M"}
        try:
            with open(self._SETTINGS, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {**default, **data.get("hotkey", {})}
        except Exception:
            return default

    def _save_hotkey(self):
        try:
            with open(self._SETTINGS, "w", encoding="utf-8") as f:
                json.dump({"hotkey": self.hotkey}, f)
        except Exception:
            pass

    def _combo_text(self):
        parts = []
        if self.hotkey["ctrl"]:
            parts.append("Ctrl")
        if self.hotkey["alt"]:
            parts.append("Alt")
        if self.hotkey["shift"]:
            parts.append("Shift")
        parts.append(self.hotkey["label"])
        return "+".join(parts)

    def _start_capture(self):
        self._capture = True
        self.set_key_btn.config(text="Press keys...")
        self.hotkey_label.config(text="...")
        self.ctrl.focus_force()
        self.ctrl.bind("<KeyPress>", self._on_capture_key)

    def _on_capture_key(self, event):
        if event.keysym in ("Control_L", "Control_R", "Alt_L", "Alt_R",
                            "Shift_L", "Shift_R"):
            return
        self.ctrl.unbind("<KeyPress>")
        self._capture = False
        self.set_key_btn.config(text="Set...")
        if event.keysym == "Escape":
            self.hotkey_label.config(text=self._combo_text())
            return
        ctrl = bool(event.state & 0x4)
        alt = bool(event.state & 0x20000)
        shift = bool(event.state & 0x1)
        if not (ctrl or alt):
            self.hotkey_label.config(
                text="Needs Ctrl or Alt — click Set and try again")
            return
        vk, label = self._vk_for_keysym(event.keysym)
        if vk is None:
            self.hotkey_label.config(
                text="Use a letter, number, F1-F12, or Space")
            return
        self.hotkey = {"ctrl": ctrl, "alt": alt, "shift": shift,
                       "vk": vk, "label": label}
        self._save_hotkey()
        self.hotkey_label.config(text=self._combo_text())

    @staticmethod
    def _vk_for_keysym(keysym):
        if len(keysym) == 1 and keysym.isalnum():
            return ord(keysym.upper()), keysym.upper()
        if keysym.startswith("F") and keysym[1:].isdigit():
            n = int(keysym[1:])
            if 1 <= n <= 12:
                return 0x70 + n - 1, keysym
        if keysym == "space":
            return 0x20, "Space"
        return None, None

    def _key_down(self, vk):
        try:
            return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)
        except Exception:
            return False

    def _poll_hotkey(self):
        try:
            if not self._capture:
                hk = self.hotkey
                down = self._key_down(hk["vk"])
                if hk["ctrl"]:
                    down = down and self._key_down(0x11)
                if hk["alt"]:
                    down = down and self._key_down(0x12)
                if hk["shift"]:
                    down = down and self._key_down(0x10)
                if down and not self._combo_down:
                    self._toggle_maximize()
                self._combo_down = down
        finally:
            self.ctrl.after(90, self._poll_hotkey)

    def _toggle_maximize(self):
        if self.films and all(f.maximized for f in self.films):
            for film in self.films:
                film.restore()
        else:
            for film in self.films:
                film.maximize()

    def _apply_topmost(self):
        top = self.top_var.get()
        for film in self.films:
            film.win.attributes("-topmost", top)
        self.ctrl.attributes("-topmost", top)

    def _apply_clickthrough_to(self, film):
        if not IS_WIN:
            return
        try:
            hwnd = film.top_hwnd()
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if self.ct_var.get():
                style |= WS_EX_LAYERED | WS_EX_TRANSPARENT
            else:
                style &= ~WS_EX_TRANSPARENT
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        except Exception:
            pass

    def _apply_clickthrough(self):
        for film in self.films:
            self._apply_clickthrough_to(film)

    def run(self):
        self.ctrl.mainloop()


if __name__ == "__main__":
    Dimmer().run()
