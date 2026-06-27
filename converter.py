"""
MagicKit Image Converter
World-class JPG → WebP / AVIF converter with quality controls and bulk operations.
"""

import os
import sys
import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox
import tkinter as tk

# ── Optional: rich CustomTkinter UI ──────────────────────────────────────────
try:
    import customtkinter as ctk
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    HAS_CTK = True
except ImportError:
    HAS_CTK = False

from PIL import Image

# ── Register AVIF support with Pillow (must be imported, not just installed) ─
try:
    import pillow_avif  # noqa: F401  (side-effect import registers the codec)
    HAS_AVIF = True
except ImportError:
    HAS_AVIF = False

# ─────────────────────────────────────────────────────────────────────────────
# Palette / brand tokens
# ─────────────────────────────────────────────────────────────────────────────
C = {
    "bg":        "#0E0F13",   # deep void
    "surface":   "#16181F",   # card surface
    "border":    "#2A2D3A",   # subtle separator
    "accent":    "#5B6AF7",   # electric indigo
    "accent2":   "#A78BFA",   # soft violet
    "success":   "#34D399",   # mint green
    "warn":      "#FBBF24",   # amber
    "danger":    "#F87171",   # coral red
    "fg":        "#E8EAF6",   # near-white
    "muted":     "#6B7280",   # grey
    "webp_col":  "#3B82F6",   # blue tag
    "avif_col":  "#8B5CF6",   # violet tag
}

SUPPORTED_EXTS = {".jpg", ".jpeg", ".JPG", ".JPEG"}

# ─────────────────────────────────────────────────────────────────────────────
# Core conversion logic
# ─────────────────────────────────────────────────────────────────────────────

def convert_image(
    src_path: Path,
    dst_dir: Path,
    fmt: str,            # "webp" | "avif"
    quality: int,        # 1-100
    lossless: bool,
    rel_dir: Path = None,  # subfolder (relative to scan root) to mirror, or None
) -> dict:
    """Convert one image. Returns result dict."""
    t0 = time.perf_counter()
    try:
        with Image.open(src_path) as img:
            # Preserve colour profile; strip metadata the user doesn't need
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGBA")
            elif img.mode != "RGB":
                img = img.convert("RGB")

            stem = src_path.stem
            out_name = f"{stem}.{fmt}"
            out_subdir = dst_dir / rel_dir if rel_dir else dst_dir
            out_subdir.mkdir(parents=True, exist_ok=True)
            out_path = out_subdir / out_name

            # Avoid silently clobbering an existing file with the same stem
            counter = 1
            while out_path.exists() and out_path.resolve() != src_path.resolve():
                out_path = out_subdir / f"{stem}_{counter}.{fmt}"
                counter += 1

            save_kwargs: dict = {}
            if fmt == "webp":
                save_kwargs = {
                    "format": "WEBP",
                    "lossless": lossless,
                    "quality": quality,
                    "method": 6,          # slowest = best compression
                }
            elif fmt == "avif":
                save_kwargs = {
                    "format": "AVIF",
                    "quality": quality if not lossless else 100,
                    "speed": 4,           # balanced encode speed vs ratio
                }

            img.save(out_path, **save_kwargs)

        src_sz = src_path.stat().st_size
        dst_sz = out_path.stat().st_size
        ratio  = (1 - dst_sz / src_sz) * 100 if src_sz else 0
        elapsed = time.perf_counter() - t0

        return {
            "ok": True,
            "src": src_path,
            "dst": out_path,
            "src_kb": src_sz / 1024,
            "dst_kb": dst_sz / 1024,
            "ratio": ratio,
            "elapsed": elapsed,
        }
    except Exception as exc:
        return {"ok": False, "src": src_path, "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# GUI
# ─────────────────────────────────────────────────────────────────────────────

if HAS_CTK:
    BaseApp   = ctk.CTk
    BaseFrame = ctk.CTkFrame
    BaseLabel = ctk.CTkLabel
    BaseBtn   = ctk.CTkButton
    BaseSlider= ctk.CTkSlider
    BaseCheck = ctk.CTkCheckBox
    BaseEntry = ctk.CTkEntry
    BaseSb    = ctk.CTkScrollableFrame
    BaseOpt   = ctk.CTkOptionMenu
    BaseProg  = ctk.CTkProgressBar
    BaseTb    = ctk.CTkTextbox
else:
    BaseApp   = tk.Tk
    BaseFrame = tk.Frame
    BaseLabel = tk.Label
    BaseBtn   = tk.Button
    BaseSlider= tk.Scale
    BaseCheck = tk.Checkbutton
    BaseEntry = tk.Entry
    BaseSb    = tk.Frame
    BaseOpt   = tk.OptionMenu
    BaseProg  = tk.ttk.Progressbar if hasattr(tk, 'ttk') else tk.Frame
    BaseTb    = tk.Text


class MagicKitConverter(BaseApp):
    def __init__(self):
        super().__init__()
        self.title("MagicKit · Image Converter")
        self.geometry("920x780")
        self.minsize(860, 700)
        self.configure(fg_color=C["bg"] if HAS_CTK else C["bg"])
        self.resizable(True, True)

        # State
        self.src_folder   = tk.StringVar()
        self.dst_folder   = tk.StringVar()
        self.quality_var  = tk.IntVar(value=85)
        self.lossless_var = tk.BooleanVar(value=False)
        self.fmt_webp     = tk.BooleanVar(value=True)
        self.fmt_avif     = tk.BooleanVar(value=True)
        self.single_files : list[Path] = []
        self._running     = False

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.report_callback_exception = self._on_tk_exception

        self._build_ui()

    def _on_close(self):
        if self._running:
            if messagebox.askyesno(
                "Conversion In Progress",
                "A conversion is still running. Closing now may leave it incomplete.\n\n"
                "Quit anyway?"
            ):
                self.destroy()
            return
        self.destroy()

    def _on_tk_exception(self, exc_type, exc_value, exc_tb):
        # Default Tk behaviour just prints to stderr (invisible in a packaged
        # .exe) and can leave the app in a half-broken state. Surface it.
        import traceback
        traceback.print_exception(exc_type, exc_value, exc_tb)
        try:
            messagebox.showerror("Unexpected Error", f"{exc_type.__name__}: {exc_value}")
        except Exception:
            pass

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Header ────────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=C["surface"], corner_radius=0) if HAS_CTK else tk.Frame(self, bg=C["surface"])
        hdr.pack(fill="x")

        lbl_icon = ctk.CTkLabel(hdr, text="⚡", font=("SF Pro Display", 28), text_color=C["accent"]) if HAS_CTK else tk.Label(hdr, text="⚡", font=("Helvetica", 28), bg=C["surface"], fg=C["accent"])
        lbl_icon.pack(side="left", padx=(24, 6), pady=16)

        lbl_title = ctk.CTkLabel(hdr, text="MagicKit Image Converter", font=("SF Pro Display", 20, "bold"), text_color=C["fg"]) if HAS_CTK else tk.Label(hdr, text="MagicKit Image Converter", font=("Helvetica", 20, "bold"), bg=C["surface"], fg=C["fg"])
        lbl_title.pack(side="left", pady=16)

        lbl_sub = ctk.CTkLabel(hdr, text="JPG → WebP · AVIF", font=("SF Pro Display", 12), text_color=C["muted"]) if HAS_CTK else tk.Label(hdr, text="JPG → WebP · AVIF", font=("Helvetica", 12), bg=C["surface"], fg=C["muted"])
        lbl_sub.pack(side="left", padx=12, pady=16)

        # ── Main body split ────────────────────────────────────────────────────
        body = ctk.CTkFrame(self, fg_color=C["bg"]) if HAS_CTK else tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=0, pady=0)

        left = ctk.CTkFrame(body, fg_color=C["bg"]) if HAS_CTK else tk.Frame(body, bg=C["bg"])
        left.pack(side="left", fill="both", expand=True, padx=(20, 8), pady=20)

        right = ctk.CTkFrame(body, fg_color=C["bg"]) if HAS_CTK else tk.Frame(body, bg=C["bg"])
        right.pack(side="right", fill="both", expand=True, padx=(8, 20), pady=20)

        # ── LEFT: Input / Output / Formats / Quality ──────────────────────────
        self._section(left, "SOURCE")
        self._folder_row(left, "Source Folder", self.src_folder, self._pick_src)

        self._btn_row = ctk.CTkFrame(left, fg_color=C["bg"]) if HAS_CTK else tk.Frame(left, bg=C["bg"])
        self._btn_row.pack(fill="x", pady=(4, 0))
        self._make_btn(self._btn_row, "＋ Add Individual Files", self._pick_files, C["muted"]).pack(side="left")
        self.lbl_file_count = ctk.CTkLabel(self._btn_row, text="", font=("SF Pro Display", 11), text_color=C["accent2"]) if HAS_CTK else tk.Label(self._btn_row, text="", font=("Helvetica", 11), bg=C["bg"], fg=C["accent2"])
        self.lbl_file_count.pack(side="left", padx=10)

        self._section(left, "DESTINATION")
        self._folder_row(left, "Output Folder", self.dst_folder, self._pick_dst)

        self._section(left, "OUTPUT FORMATS")
        fmt_row = ctk.CTkFrame(left, fg_color=C["bg"]) if HAS_CTK else tk.Frame(left, bg=C["bg"])
        fmt_row.pack(fill="x", pady=4)

        self._make_check(fmt_row, "WebP", self.fmt_webp, C["webp_col"]).pack(side="left", padx=(0, 16))
        avif_check = self._make_check(fmt_row, "AVIF", self.fmt_avif, C["avif_col"])
        avif_check.pack(side="left")
        if not HAS_AVIF:
            self.fmt_avif.set(False)
            try:
                avif_check.configure(state="disabled")
            except Exception:
                pass
            avif_note = (ctk.CTkLabel(fmt_row, text="(pillow-avif-plugin not installed)",
                                       font=("SF Pro Display", 10), text_color=C["muted"])
                          if HAS_CTK else
                          tk.Label(fmt_row, text="(pillow-avif-plugin not installed)",
                                   font=("Helvetica", 10), bg=C["bg"], fg=C["muted"]))
            avif_note.pack(side="left", padx=(10, 0))

        self._section(left, "QUALITY")

        # Lossless toggle
        loss_row = ctk.CTkFrame(left, fg_color=C["bg"]) if HAS_CTK else tk.Frame(left, bg=C["bg"])
        loss_row.pack(fill="x", pady=(0, 8))
        self._make_check(loss_row, "Lossless (ignores quality slider)", self.lossless_var, C["success"]).pack(side="left")
        self.lossless_var.trace_add("write", self._on_lossless_toggle)

        # Quality slider
        q_row = ctk.CTkFrame(left, fg_color=C["bg"]) if HAS_CTK else tk.Frame(left, bg=C["bg"])
        q_row.pack(fill="x", pady=4)

        self.q_label = ctk.CTkLabel(q_row, text="Quality: 85%", font=("SF Pro Display", 13, "bold"), text_color=C["accent2"], width=120) if HAS_CTK else tk.Label(q_row, text="Quality: 85%", font=("Helvetica", 13, "bold"), bg=C["bg"], fg=C["accent2"], width=12)
        self.q_label.pack(side="left")

        if HAS_CTK:
            self.slider = ctk.CTkSlider(q_row, from_=1, to=100, number_of_steps=99,
                                        variable=self.quality_var, command=self._on_quality,
                                        button_color=C["accent"], progress_color=C["accent"],
                                        fg_color=C["border"])
        else:
            self.slider = tk.Scale(q_row, from_=1, to=100, orient="horizontal",
                                   variable=self.quality_var, command=self._on_quality,
                                   bg=C["bg"], fg=C["fg"], highlightthickness=0)
        self.slider.pack(side="left", fill="x", expand=True, padx=(12, 0))

        # Quality presets
        preset_row = ctk.CTkFrame(left, fg_color=C["bg"]) if HAS_CTK else tk.Frame(left, bg=C["bg"])
        preset_row.pack(fill="x", pady=(4, 0))
        for label, val in [("Web Fast (70)", 70), ("Balanced (85)", 85), ("High (92)", 92), ("Max (100)", 100)]:
            self._make_btn(preset_row, label, lambda v=val: self._set_quality(v), C["border"]).pack(side="left", padx=(0, 6), pady=2)

        # ── Convert buttons ────────────────────────────────────────────────────
        self._section(left, "ACTIONS")
        act_row = ctk.CTkFrame(left, fg_color=C["bg"]) if HAS_CTK else tk.Frame(left, bg=C["bg"])
        act_row.pack(fill="x", pady=4)

        self.btn_convert = self._make_btn(act_row, "▶  Convert Now", self._start_conversion, C["accent"], text_color="white", height=40)
        self.btn_convert.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.btn_clear = self._make_btn(act_row, "✕ Clear", self._clear_all, C["danger"], text_color="white", height=40)
        self.btn_clear.pack(side="left")

        # Progress bar
        if HAS_CTK:
            self.progress = ctk.CTkProgressBar(left, fg_color=C["border"], progress_color=C["accent"])
            self.progress.set(0)
        else:
            self.progress = None
        if self.progress:
            self.progress.pack(fill="x", pady=(12, 0))

        self.lbl_status = ctk.CTkLabel(left, text="Ready.", font=("SF Pro Display", 11), text_color=C["muted"]) if HAS_CTK else tk.Label(left, text="Ready.", font=("Helvetica", 11), bg=C["bg"], fg=C["muted"])
        self.lbl_status.pack(anchor="w", pady=(4, 0))

        # ── RIGHT: Log ─────────────────────────────────────────────────────────
        self._section(right, "CONVERSION LOG")

        if HAS_CTK:
            self.log = ctk.CTkTextbox(right, fg_color=C["surface"], text_color=C["fg"],
                                      font=("JetBrains Mono", 11), corner_radius=10,
                                      border_width=1, border_color=C["border"])
        else:
            self.log = tk.Text(right, bg=C["surface"], fg=C["fg"],
                               font=("Courier", 10), relief="flat")
        self.log.pack(fill="both", expand=True)
        self.log.configure(state="disabled")

        # ── Stats bar ─────────────────────────────────────────────────────────
        self.stats_frame = ctk.CTkFrame(right, fg_color=C["surface"], corner_radius=10) if HAS_CTK else tk.Frame(right, bg=C["surface"])
        self.stats_frame.pack(fill="x", pady=(8, 0))

        for attr, label, color in [
            ("lbl_total", "Total", C["fg"]),
            ("lbl_ok",    "Done",  C["success"]),
            ("lbl_fail",  "Failed",C["danger"]),
            ("lbl_saved", "Saved", C["accent2"]),
            ("lbl_time",  "Time",  C["muted"]),
        ]:
            col = ctk.CTkFrame(self.stats_frame, fg_color="transparent") if HAS_CTK else tk.Frame(self.stats_frame, bg=C["surface"])
            col.pack(side="left", expand=True, padx=8, pady=8)
            lbl_l = ctk.CTkLabel(col, text=label, font=("SF Pro Display", 10), text_color=C["muted"]) if HAS_CTK else tk.Label(col, text=label, font=("Helvetica", 10), bg=C["surface"], fg=C["muted"])
            lbl_l.pack()
            lbl_v = ctk.CTkLabel(col, text="—", font=("SF Pro Display", 14, "bold"), text_color=color) if HAS_CTK else tk.Label(col, text="—", font=("Helvetica", 14, "bold"), bg=C["surface"], fg=color)
            lbl_v.pack()
            setattr(self, attr, lbl_v)

    # ── Widget helpers ─────────────────────────────────────────────────────────

    def _section(self, parent, text):
        row = ctk.CTkFrame(parent, fg_color=C["bg"]) if HAS_CTK else tk.Frame(parent, bg=C["bg"])
        row.pack(fill="x", pady=(14, 2))
        lbl = ctk.CTkLabel(row, text=text, font=("SF Pro Display", 10, "bold"), text_color=C["muted"]) if HAS_CTK else tk.Label(row, text=text, font=("Helvetica", 10, "bold"), bg=C["bg"], fg=C["muted"])
        lbl.pack(side="left")
        sep = ctk.CTkFrame(row, fg_color=C["border"], height=1) if HAS_CTK else tk.Frame(row, bg=C["border"], height=1)
        sep.pack(side="left", fill="x", expand=True, padx=(8, 0))

    def _folder_row(self, parent, label, var, cmd):
        row = ctk.CTkFrame(parent, fg_color=C["surface"], corner_radius=8) if HAS_CTK else tk.Frame(parent, bg=C["surface"])
        row.pack(fill="x", pady=3)

        if HAS_CTK:
            e = ctk.CTkEntry(row, textvariable=var, placeholder_text=f"Select {label}…",
                             fg_color=C["surface"], border_color=C["border"],
                             text_color=C["fg"], font=("SF Pro Display", 12))
        else:
            e = tk.Entry(row, textvariable=var, bg=C["surface"], fg=C["fg"],
                         relief="flat", font=("Helvetica", 12))
        e.pack(side="left", fill="x", expand=True, padx=(10, 8), pady=8)
        self._make_btn(row, "Browse", cmd, C["accent"], height=30).pack(side="right", padx=8)

    def _make_btn(self, parent, text, cmd, bg, text_color=None, height=32):
        tc = text_color or C["fg"]
        if HAS_CTK:
            return ctk.CTkButton(parent, text=text, command=cmd, fg_color=bg,
                                 hover_color=C["accent"], text_color=tc,
                                 font=("SF Pro Display", 12), corner_radius=8, height=height)
        else:
            return tk.Button(parent, text=text, command=cmd, bg=bg, fg=tc,
                             relief="flat", font=("Helvetica", 12), cursor="hand2")

    def _make_check(self, parent, text, var, color):
        if HAS_CTK:
            return ctk.CTkCheckBox(parent, text=text, variable=var,
                                   checkmark_color="white", fg_color=color,
                                   hover_color=color, font=("SF Pro Display", 12),
                                   text_color=C["fg"])
        else:
            return tk.Checkbutton(parent, text=text, variable=var,
                                  bg=C["bg"], fg=C["fg"],
                                  selectcolor=color, font=("Helvetica", 12))

    # ── Event handlers ─────────────────────────────────────────────────────────

    def _pick_src(self):
        d = filedialog.askdirectory(title="Select Source Folder")
        if d:
            self.src_folder.set(d)
            self.single_files.clear()
            self._update_file_count()

    def _pick_dst(self):
        d = filedialog.askdirectory(title="Select Output Folder")
        if d:
            self.dst_folder.set(d)

    def _pick_files(self):
        files = filedialog.askopenfilenames(
            title="Select JPG Images",
            filetypes=[("JPEG Images", "*.jpg *.jpeg *.JPG *.JPEG"), ("All files", "*.*")]
        )
        if files:
            self.single_files = [Path(f) for f in files]
            self.src_folder.set("")
            self._update_file_count()

    def _update_file_count(self):
        n = len(self.single_files)
        self.lbl_file_count.configure(text=f"{n} file(s) selected" if n else "")

    def _on_quality(self, val=None):
        q = int(float(self.quality_var.get()))
        self.q_label.configure(text=f"Quality: {q}%")

    def _set_quality(self, val):
        self.quality_var.set(val)
        self._on_quality()
        self.slider.set(val)

    def _on_lossless_toggle(self, *_):
        state = "disabled" if self.lossless_var.get() else "normal"
        self.slider.configure(state=state)

    def _clear_all(self):
        self.src_folder.set("")
        self.dst_folder.set("")
        self.single_files.clear()
        self._update_file_count()
        self._log_clear()
        self._set_status("Cleared.", C["muted"])
        for attr in ("lbl_total", "lbl_ok", "lbl_fail", "lbl_saved", "lbl_time"):
            getattr(self, attr).configure(text="—")
        if self.progress:
            self.progress.set(0)

    # ── Conversion orchestration ───────────────────────────────────────────────

    def _collect_sources(self):
        """Returns list of (path, rel_dir) tuples. rel_dir is the subfolder
        (relative to the scan root) that should be mirrored in the output,
        or None for individually-picked files."""
        sources = []
        if self.single_files:
            sources = [(p, None) for p in self.single_files]
        elif self.src_folder.get():
            src = Path(self.src_folder.get())
            for p in src.rglob("*"):
                if p.suffix in SUPPORTED_EXTS:
                    rel = p.parent.relative_to(src)
                    sources.append((p, rel if str(rel) != "." else None))
        return sources

    def _start_conversion(self):
        if self._running:
            return

        # Validate
        if not self.fmt_webp.get() and not self.fmt_avif.get():
            messagebox.showwarning("No Format", "Select at least one output format (WebP or AVIF).")
            return

        sources = self._collect_sources()
        if not sources:
            messagebox.showwarning("No Files", "No JPG/JPEG images found. Select a source folder or add files.")
            return

        dst = self.dst_folder.get()
        if not dst:
            # Use source directory as fallback
            first_path = sources[0][0]
            dst = str(first_path.parent)
            self.dst_folder.set(dst)

        dst_path = Path(dst)
        try:
            dst_path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("Can't Create Output Folder", f"{dst_path}\n\n{exc}")
            return
        if not os.access(dst_path, os.W_OK):
            messagebox.showerror("Output Folder Not Writable", f"No write permission for:\n{dst_path}")
            return

        formats = []
        if self.fmt_webp.get(): formats.append("webp")
        if self.fmt_avif.get(): formats.append("avif")

        quality  = self.quality_var.get()
        lossless = self.lossless_var.get()

        self._running = True
        self.btn_convert.configure(state="disabled", text="Converting…")
        self._log_clear()

        thread = threading.Thread(
            target=self._run_conversion,
            args=(sources, dst_path, formats, quality, lossless),
            daemon=True
        )
        thread.start()

    def _run_conversion(self, sources, dst_path, formats, quality, lossless):
        total_jobs = len(sources) * len(formats)
        done = 0
        ok_count = 0
        fail_count = 0
        total_src_kb = 0
        total_dst_kb = 0
        t_start = time.perf_counter()

        try:
            self._update_stats(total_jobs, 0, 0, 0, 0)
            self._log(f"🚀  Starting conversion — {len(sources)} image(s) × {len(formats)} format(s)\n")
            self._log(f"   Quality: {'Lossless' if lossless else f'{quality}%'}   Formats: {', '.join(f.upper() for f in formats)}\n")
            self._log("─" * 60 + "\n")

            for src, rel_dir in sources:
                for fmt in formats:
                    res = convert_image(src, dst_path, fmt, quality, lossless, rel_dir)
                    done += 1

                    if res["ok"]:
                        ok_count += 1
                        total_src_kb += res["src_kb"]
                        total_dst_kb += res["dst_kb"]
                        ratio_str = f"{res['ratio']:+.1f}%"
                        color_tag = "success" if res["ratio"] > 0 else "warn"
                        self._log(
                            f"  ✓  {res['src'].name:35s} → {res['dst'].name}  "
                            f"[{res['src_kb']:.0f}KB → {res['dst_kb']:.0f}KB  {ratio_str}  {res['elapsed']*1000:.0f}ms]\n",
                            tag=color_tag
                        )
                    else:
                        fail_count += 1
                        self._log(f"  ✗  {res['src'].name}  ERROR: {res['error']}\n", tag="danger")

                    pct = done / total_jobs if total_jobs else 1
                    elapsed = time.perf_counter() - t_start
                    saved_kb = total_src_kb - total_dst_kb
                    self.after(0, self._update_progress, pct, done, total_jobs, ok_count, fail_count, saved_kb, elapsed)

            elapsed_total = time.perf_counter() - t_start
            saved_kb = total_src_kb - total_dst_kb
            pct_smaller = (100 * (1 - total_dst_kb / total_src_kb)) if total_src_kb else 0
            self._log("─" * 60 + "\n")
            self._log(
                f"\n✅  Done — {ok_count} converted, {fail_count} failed "
                f"| Saved {saved_kb:.0f} KB ({pct_smaller:.1f}% smaller) "
                f"| {elapsed_total:.1f}s\n"
            )
        except Exception as exc:
            # Last-resort net: never let an unexpected error leave the UI
            # stuck in "Converting..." with no explanation.
            self._log(f"\n‼  Conversion stopped unexpectedly: {exc}\n", tag="danger")
        finally:
            self.after(0, self._finish_conversion)

    def _update_progress(self, pct, done, total, ok, fail, saved_kb, elapsed):
        if self.progress:
            self.progress.set(pct)
        self._set_status(f"Processing {done}/{total}…", C["accent"])
        self._update_stats(total, ok, fail, saved_kb, elapsed)

    def _update_stats(self, total, ok, fail, saved_kb, elapsed):
        self.lbl_total.configure(text=str(total))
        self.lbl_ok.configure(text=str(ok))
        self.lbl_fail.configure(text=str(fail))
        self.lbl_saved.configure(text=f"{saved_kb:.0f} KB" if saved_kb else "—")
        self.lbl_time.configure(text=f"{elapsed:.1f}s" if elapsed else "—")

    def _finish_conversion(self):
        self._running = False
        self.btn_convert.configure(state="normal", text="▶  Convert Now")
        if self.progress:
            self.progress.set(1)
        self._set_status("✅  Conversion complete!", C["success"])

    # ── Log helpers ────────────────────────────────────────────────────────────

    TAG_COLORS = {
        "success": C["success"],
        "warn":    C["warn"],
        "danger":  C["danger"],
    }

    def _log(self, msg, tag=None):
        def _write():
            self.log.configure(state="normal")
            if HAS_CTK:
                self.log.insert("end", msg)
            else:
                start = self.log.index("end")
                self.log.insert("end", msg)
                if tag and tag in self.TAG_COLORS:
                    end = self.log.index("end")
                    self.log.tag_add(tag, start, end)
                    self.log.tag_config(tag, foreground=self.TAG_COLORS[tag])
            self.log.configure(state="disabled")
            self.log.see("end")
        self.after(0, _write)

    def _log_clear(self):
        self.log.configure(state="normal")
        self.log.delete("0.0" if HAS_CTK else "1.0", "end")
        self.log.configure(state="disabled")

    def _set_status(self, text, color=None):
        self.lbl_status.configure(text=text)
        if color and HAS_CTK:
            self.lbl_status.configure(text_color=color)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not HAS_CTK:
        print("⚠  customtkinter not found — falling back to plain Tkinter.")
        print("   Install with:  pip install customtkinter")
    if not HAS_AVIF:
        print("⚠  pillow-avif-plugin not found — AVIF output disabled.")
        print("   Install with:  pip install pillow-avif-plugin")
    try:
        app = MagicKitConverter()
        app.mainloop()
    except Exception as exc:
        # If this is a packaged .exe with no console attached, a bare
        # traceback would be invisible and the app would just vanish.
        # Always show something on screen.
        import traceback
        traceback.print_exc()
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("MagicKit failed to start", f"{type(exc).__name__}: {exc}")
        except Exception:
            pass
        sys.exit(1)
