import os
import shutil
import threading
import tkinter as tk
from tkinter import filedialog, ttk
from pathlib import Path
from datetime import datetime

CATEGORIES = {
    "Images":      {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg",
                    ".webp", ".tiff", ".ico", ".heic", ".raw"},
    "Documents":   {".pdf", ".doc", ".docx", ".txt", ".odt", ".rtf",
                    ".md", ".tex", ".xls", ".xlsx", ".csv", ".ppt", ".pptx"},
    "Videos":      {".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv",
                    ".webm", ".m4v", ".3gp", ".mpeg"},
    "Audio":       {".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a",
                    ".wma", ".aiff", ".opus"},
    "Archives":    {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso"},
    "Code":        {".py", ".js", ".ts", ".html", ".css", ".java",
                    ".c", ".cpp", ".h", ".cs", ".go", ".rb", ".php",
                    ".sh", ".json", ".xml", ".yaml", ".yml", ".sql"},
    "Fonts":       {".ttf", ".otf", ".woff", ".woff2", ".eot"},
    "Executables": {".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm", ".apk"},
}

EXT_TO_CATEGORY = {}
for cat, exts in CATEGORIES.items():
    for ext in exts:
        EXT_TO_CATEGORY[ext] = cat

ALL_CATS = ["All"] + sorted(CATEGORIES.keys()) + ["Others"]

BG       = "#0d0d0d"
SURFACE  = "#161616"
SURFACE2 = "#1f1f1f"
SURFACE3 = "#282828"
BORDER   = "#303030"
ACCENT   = "#4ade80"
ACCENTDK = "#15532e"
BLUE     = "#60a5fa"
BLUEDK   = "#1e3a5f"
TEXT     = "#efefef"
TEXT2    = "#999999"
TEXT3    = "#555555"
DANGER   = "#f87171"
WARNING  = "#fbbf24"


def get_category(p: Path) -> str:
    return EXT_TO_CATEGORY.get(p.suffix.lower(), "Others")


def unique_dest(dest: Path, seen: set) -> Path:
    if dest not in seen and not dest.exists():
        return dest
    stem, suffix, parent = dest.stem, dest.suffix, dest.parent
    i = 1
    while True:
        candidate = parent / f"{stem}_{i}{suffix}"
        if candidate not in seen and not candidate.exists():
            return candidate
        i += 1


def fmt_size(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Smart File Organizer")
        self.geometry("900x680")
        self.minsize(780, 560)
        self.configure(bg=BG)
        self.resizable(True, True)

        self._all_files: list[Path] = []
        self._filtered: list[Path] = []
        self._dest_root: Path | None = None
        self._search_var = tk.StringVar()
        self._cat_var = tk.StringVar(value="All")
        self._placeholder_active = True
        self._search_var.trace_add("write", lambda *_: self._apply_filter())

        self._build_ui()

    def _build_ui(self):
        top = tk.Frame(self, bg=BG, padx=20, pady=14)
        top.pack(fill="x")

        tk.Label(top, text="File Organizer",
                 bg=BG, fg=TEXT, font=("Courier New", 17, "bold")).pack(side="left")
        tk.Label(top, text=" v4.0", bg=BG, fg=TEXT3,
                 font=("Courier New", 11)).pack(side="left", pady=3)

        dest_row = tk.Frame(top, bg=BG)
        dest_row.pack(side="right")
        tk.Label(dest_row, text="Destination:", bg=BG, fg=TEXT2,
                 font=("Courier New", 10)).pack(side="left", padx=(0, 6))
        self._dest_lbl = tk.Label(dest_row, text="Same as source",
                                   bg=BG, fg=TEXT3, font=("Courier New", 10))
        self._dest_lbl.pack(side="left", padx=(0, 8))
        self._btn(dest_row, "Set folder", SURFACE2, BLUE,
                  self._pick_dest).pack(side="left")

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        left = tk.Frame(body, bg=SURFACE, highlightbackground=BORDER,
                        highlightthickness=1)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.rowconfigure(2, weight=1)
        left.columnconfigure(0, weight=1)

        toolbar = tk.Frame(left, bg=SURFACE2, padx=12, pady=10)
        toolbar.grid(row=0, column=0, sticky="ew")

        self._btn(toolbar, "Add Files", BLUEDK, BLUE,
                  self._pick_files).pack(side="left", padx=(0, 6))
        self._btn(toolbar, "Add Folder", BLUEDK, BLUE,
                  self._pick_folder).pack(side="left", padx=(0, 6))
        self._btn(toolbar, "Clear", SURFACE3, TEXT3,
                  self._clear_all).pack(side="left")

        self._chip_count = tk.Label(toolbar, text="0 files",
                                     bg=SURFACE3, fg=TEXT2,
                                     font=("Courier New", 9), padx=8, pady=3)
        self._chip_count.pack(side="right")

        filterbar = tk.Frame(left, bg=SURFACE, padx=10, pady=8)
        filterbar.grid(row=1, column=0, sticky="ew")
        filterbar.columnconfigure(0, weight=1)

        search_wrap = tk.Frame(filterbar, bg=BORDER, padx=1, pady=1)
        search_wrap.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        search_inner = tk.Frame(search_wrap, bg=SURFACE3)
        search_inner.pack(fill="both")
        tk.Label(search_inner, text="⌕", bg=SURFACE3, fg=TEXT3,
                 font=("Courier New", 12)).pack(side="left", padx=(8, 2))
        self._search_entry = tk.Entry(search_inner, textvariable=self._search_var,
                                       bg=SURFACE3, fg=TEXT3, insertbackground=TEXT,
                                       font=("Courier New", 11), relief="flat", bd=0)
        self._search_entry.insert(0, "Search files...")
        self._search_entry.pack(side="left", fill="x", expand=True, pady=6, padx=4)
        self._search_entry.bind("<FocusIn>", self._search_focus_in)
        self._search_entry.bind("<FocusOut>", self._search_focus_out)

        cat_wrap = tk.Frame(filterbar, bg=BORDER, padx=1, pady=1)
        cat_wrap.grid(row=0, column=1)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.TCombobox",
                        fieldbackground=SURFACE3, background=SURFACE3,
                        foreground=TEXT, selectbackground=SURFACE3,
                        selectforeground=ACCENT, bordercolor=BORDER,
                        arrowcolor=TEXT2, lightcolor=SURFACE3, darkcolor=SURFACE3)
        style.map("Dark.TCombobox",
                  fieldbackground=[("readonly", SURFACE3)],
                  foreground=[("readonly", TEXT)])

        self._cat_combo = ttk.Combobox(cat_wrap, textvariable=self._cat_var,
                                        values=ALL_CATS, state="readonly", width=13,
                                        style="Dark.TCombobox",
                                        font=("Courier New", 10))
        self._cat_combo.pack()
        self._cat_combo.bind("<<ComboboxSelected>>", lambda _: self._apply_filter())

        list_frame = tk.Frame(left, bg=SURFACE)
        list_frame.grid(row=2, column=0, sticky="nsew", padx=1, pady=(0, 1))
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        style.configure("Dark.Treeview",
                        background=SURFACE, foreground=TEXT2,
                        fieldbackground=SURFACE, bordercolor=BORDER,
                        rowheight=26, font=("Courier New", 10))
        style.configure("Dark.Treeview.Heading",
                        background=SURFACE2, foreground=TEXT3,
                        font=("Courier New", 9, "bold"), relief="flat")
        style.map("Dark.Treeview",
                  background=[("selected", SURFACE3)],
                  foreground=[("selected", ACCENT)])

        cols = ("name", "category", "size", "path")
        self._tree = ttk.Treeview(list_frame, columns=cols,
                                   show="headings", selectmode="extended",
                                   style="Dark.Treeview")
        self._tree.heading("name",     text="File name")
        self._tree.heading("category", text="Category")
        self._tree.heading("size",     text="Size")
        self._tree.heading("path",     text="Location")
        self._tree.column("name",     width=200, stretch=True)
        self._tree.column("category", width=90,  stretch=False)
        self._tree.column("size",     width=70,  stretch=False, anchor="e")
        self._tree.column("path",     width=160, stretch=True)

        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        right = tk.Frame(body, bg=SURFACE, highlightbackground=BORDER,
                         highlightthickness=1)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        out_hdr = tk.Frame(right, bg=SURFACE2, padx=14, pady=10)
        out_hdr.grid(row=0, column=0, sticky="ew")
        tk.Label(out_hdr, text="Output", bg=SURFACE2, fg=TEXT2,
                 font=("Courier New", 10, "bold")).pack(side="left")
        self._btn(out_hdr, "Clear", SURFACE3, TEXT3,
                  self._clear_log).pack(side="right")

        out_frame = tk.Frame(right, bg=SURFACE)
        out_frame.grid(row=1, column=0, sticky="nsew")
        out_frame.rowconfigure(0, weight=1)
        out_frame.columnconfigure(0, weight=1)

        out_sb = tk.Scrollbar(out_frame, bg=SURFACE2, troughcolor=BG,
                               relief="flat", bd=0, width=6)
        out_sb.grid(row=0, column=1, sticky="ns")

        self._out = tk.Text(out_frame, bg=SURFACE, fg=TEXT2,
                             font=("Courier New", 10),
                             relief="flat", bd=0, padx=14, pady=12,
                             wrap="word", state="disabled",
                             yscrollcommand=out_sb.set,
                             selectbackground=SURFACE3,
                             insertbackground=TEXT,
                             highlightthickness=0)
        self._out.grid(row=0, column=0, sticky="nsew")
        out_sb.config(command=self._out.yview)

        self._out.tag_config("ts",   foreground=TEXT3)
        self._out.tag_config("head", foreground=TEXT,   font=("Courier New", 10, "bold"))
        self._out.tag_config("cat",  foreground=ACCENT, font=("Courier New", 10, "bold"))
        self._out.tag_config("file", foreground=TEXT2)
        self._out.tag_config("dupe", foreground=WARNING)
        self._out.tag_config("ok",   foreground=ACCENT, font=("Courier New", 10, "bold"))
        self._out.tag_config("err",  foreground=DANGER)
        self._out.tag_config("dim",  foreground=TEXT3)
        self._out.tag_config("sep",  foreground=TEXT3)

        stats_row = tk.Frame(right, bg=SURFACE2, padx=14, pady=8)
        stats_row.grid(row=2, column=0, sticky="ew")
        self._s_queued = self._mini_stat(stats_row, "0", "queued")
        self._s_moved  = self._mini_stat(stats_row, "0", "moved", ACCENT)
        self._s_errors = self._mini_stat(stats_row, "0", "errors", DANGER)

        action = tk.Frame(self, bg=BG, padx=20, pady=0)
        action.pack(fill="x", pady=(0, 16))

        self._dry_var = tk.BooleanVar(value=False)
        tk.Checkbutton(action, text="Dry run (preview only)",
                        variable=self._dry_var,
                        bg=BG, fg=TEXT2, selectcolor=BG,
                        activebackground=BG, activeforeground=TEXT,
                        font=("Courier New", 10),
                        command=self._update_move_btn).pack(side="left")

        self._mode_lbl = tk.Label(action, text="", bg=BG, fg=TEXT3,
                                   font=("Courier New", 9))
        self._mode_lbl.pack(side="right", padx=12)

        self._move_btn = tk.Button(action, text="Move Files",
                                    bg=ACCENTDK, fg=ACCENT,
                                    activebackground="#14532d",
                                    activeforeground=ACCENT,
                                    font=("Courier New", 12, "bold"),
                                    relief="flat", bd=0,
                                    padx=24, pady=8,
                                    cursor="hand2",
                                    state="disabled",
                                    command=self._move)
        self._move_btn.pack(side="right")

        self._out_write("Ready — add some files or a folder to get started.\n", "dim")

    def _btn(self, parent, text, bg, fg, cmd, **kw):
        return tk.Button(parent, text=text, bg=bg, fg=fg,
                         activebackground=SURFACE3, activeforeground=TEXT,
                         font=("Courier New", 10), relief="flat", bd=0,
                         padx=10, pady=5, cursor="hand2", command=cmd, **kw)

    def _mini_stat(self, parent, val, label, color=TEXT2):
        f = tk.Frame(parent, bg=SURFACE2, padx=10)
        f.pack(side="left")
        v = tk.Label(f, text=val, bg=SURFACE2, fg=color,
                     font=("Courier New", 14, "bold"))
        v.pack()
        tk.Label(f, text=label, bg=SURFACE2, fg=TEXT3,
                 font=("Courier New", 8)).pack()
        return v

    def _search_focus_in(self, _):
        if self._placeholder_active:
            self._search_entry.delete(0, "end")
            self._search_entry.config(fg=TEXT)
            self._placeholder_active = False

    def _search_focus_out(self, _):
        if not self._search_var.get():
            self._placeholder_active = True
            self._search_entry.config(fg=TEXT3)
            self._search_entry.insert(0, "Search files...")

    def _pick_files(self):
        paths = filedialog.askopenfilenames(
            title="Select files",
            filetypes=[
                ("All files",  "*.*"),
                ("Images",     "*.jpg *.jpeg *.png *.gif *.bmp *.webp *.svg"),
                ("Documents",  "*.pdf *.doc *.docx *.txt *.xls *.xlsx *.csv *.ppt *.pptx"),
                ("Videos",     "*.mp4 *.mov *.avi *.mkv"),
                ("Audio",      "*.mp3 *.wav *.flac *.aac *.ogg"),
                ("Archives",   "*.zip *.rar *.7z *.tar *.gz"),
                ("Code",       "*.py *.js *.ts *.html *.css *.json"),
            ]
        )
        if paths:
            self._add_files([Path(p) for p in paths])

    def _pick_folder(self):
        folder = filedialog.askdirectory(title="Select folder")
        if folder:
            p = Path(folder)
            files = [f for f in sorted(p.rglob("*")) if f.is_file()]
            self._add_files(files)
            self._out_write(f"Folder added: {p.name} ({len(files)} files)\n", "dim")

    def _pick_dest(self):
        folder = filedialog.askdirectory(title="Choose destination folder")
        if folder:
            self._dest_root = Path(folder)
            label = str(self._dest_root)
            if len(label) > 40:
                label = "..." + label[-38:]
            self._dest_lbl.config(text=label, fg=BLUE)

    def _add_files(self, new_files: list[Path]):
        existing = set(self._all_files)
        added = [f for f in new_files if f not in existing]
        self._all_files.extend(added)
        if added:
            self._apply_filter()
            self._out_write(f"Added {len(added)} file(s). Total: {len(self._all_files)}\n", "dim")

    def _clear_all(self):
        self._all_files.clear()
        self._filtered.clear()
        self._tree.delete(*self._tree.get_children())
        self._chip_count.config(text="0 files")
        self._s_queued.config(text="0")
        self._move_btn.config(state="disabled")
        self._out_write("List cleared.\n", "dim")

    def _apply_filter(self):
        query = "" if self._placeholder_active else self._search_var.get().lower().strip()
        cat = self._cat_var.get()

        self._filtered = [
            f for f in self._all_files
            if (cat == "All" or get_category(f) == cat)
            and (not query or query in f.name.lower())
        ]

        self._tree.delete(*self._tree.get_children())
        for f in self._filtered:
            c = get_category(f)
            try:
                size = fmt_size(f.stat().st_size)
            except Exception:
                size = "—"
            self._tree.insert("", "end", iid=str(f),
                               values=(f.name, c, size, str(f.parent)))

        total = len(self._all_files)
        shown = len(self._filtered)
        self._chip_count.config(
            text=f"{shown}/{total} files" if shown != total else f"{total} files"
        )
        self._s_queued.config(text=str(shown))
        self._move_btn.config(state="normal" if self._filtered else "disabled")

    def _update_move_btn(self):
        dry = self._dry_var.get()
        self._move_btn.config(text="Preview Move" if dry else "Move Files")
        self._mode_lbl.config(text="Dry run — nothing will be moved" if dry else "")

    def _move(self):
        if not self._filtered:
            return
        self._move_btn.config(state="disabled", text="Moving...")
        threading.Thread(
            target=self._do_move,
            args=(list(self._filtered), self._dest_root, self._dry_var.get()),
            daemon=True
        ).start()

    def _do_move(self, files: list[Path], dest_root: Path | None, dry: bool):
        ts = datetime.now().strftime("%H:%M:%S")
        summary: dict[str, list] = {}
        errors = []
        claimed: set[Path] = set()

        for f in files:
            cat = get_category(f)
            base = dest_root if dest_root else f.parent
            dest = unique_dest(base / cat / f.name, claimed)
            claimed.add(dest)
            renamed = dest.name != f.name
            label = f"{f.name} -> {dest.name}" if renamed else f.name

            if not dry:
                try:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(f), str(dest))
                except Exception as exc:
                    errors.append((f.name, str(exc)))
                    continue

            summary.setdefault(cat, []).append((label, renamed))

        self.after(0, lambda: self._finish_move(summary, errors, dry, ts))

    def _finish_move(self, summary: dict, errors: list, dry: bool, ts: str):
        total = sum(len(v) for v in summary.values())
        verb = "Would move" if dry else "Moved"

        self._out_write(f"\n[{ts}] {'DRY RUN' if dry else 'DONE'}\n", "ts")
        self._out_write("─" * 36 + "\n", "sep")

        for cat in sorted(summary):
            items = summary[cat]
            self._out_write(f"{cat} ({len(items)})\n", "cat")
            for label, renamed in items:
                self._out_write(f"  {label}\n", "dupe" if renamed else "file")

        self._out_write("─" * 36 + "\n", "sep")
        self._out_write(f"{verb} {total} file{'s' if total != 1 else ''}\n", "ok")

        if errors:
            self._out_write(f"\n{len(errors)} error(s):\n", "err")
            for name, msg in errors:
                self._out_write(f"  {name}: {msg}\n", "err")

        self._s_moved.config(text=str(total))
        self._s_errors.config(text=str(len(errors)))

        if not dry:
            moved_names = {
                label.split(" -> ")[0]
                for items in summary.values()
                for label, _ in items
            }
            self._all_files = [f for f in self._all_files if f.name not in moved_names]
            self._apply_filter()

        self._move_btn.config(
            state="normal" if self._filtered else "disabled",
            text="Preview Move" if dry else "Move Files"
        )

    def _out_write(self, text: str, tag: str = ""):
        self._out.config(state="normal")
        self._out.insert("end", text, tag)
        self._out.config(state="disabled")
        self._out.see("end")

    def _clear_log(self):
        self._out.config(state="normal")
        self._out.delete("1.0", "end")
        self._out.config(state="disabled")
        self._s_moved.config(text="0")
        self._s_errors.config(text="0")


if __name__ == "__main__":
    App().mainloop()
