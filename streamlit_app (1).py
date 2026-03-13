"""
Sunspace  |  Box Header CSV Editor  v6.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Desktop app: upload / paste / sample → select rows →
convert Female Channel → Box Header → download corrected CSV.

Improvements over v5:
  • Click row to toggle | Shift+click for range | Ctrl+A / Ctrl+D
  • Female Channel rows auto-highlighted + pre-checked on load
  • Light / Dark theme toggle
  • Live search filter (type to narrow rows instantly)
  • Row count stats bar with live selection counter
  • Undo last conversion
  • Diff log after conversion
  • Folder memory | corrected_ prefix on save
  • BYD map editor in popup
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv, io, os, re, copy

# ── BYD MAP ───────────────────────────────────────────────────────────────────
DEFAULT_BYD_MAP = {
    "810300": "810311",   # 18' White
    "810302": "810310",   # 18' Driftwood
    "810303": "810309",   # 18' Bronze
    "882980": "882986",   # 18' Black
    "810299": "810311",   # 14' White
    "810301": "810310",   # 14' Driftwood
}
BYD_LABELS = {
    "810300": '3" Female Channel 18\'  White',
    "810302": '3" Female Channel 18\'  Driftwood',
    "810303": '3" Female Channel 18\'  Bronze',
    "882980": '3" Female Channel 18\'  Black',
    "810299": '3" Female Channel 14\'  White',
    "810301": '3" Female Channel 14\'  Driftwood',
}

# ── CSV COLUMNS ───────────────────────────────────────────────────────────────
COL_ID, COL_CODE, COL_INFO = 0, 7, 8
COL_ORIENT, COL_MAIN       = 13, 25
COL_DATA1,  COL_DATA2      = 28, 29

# ── THEMES ────────────────────────────────────────────────────────────────────
DARK = {
    "bg": "#111111", "bg2": "#1a1a1a", "bg3": "#222222",
    "border": "#2e2e2e", "text": "#d4d4d4", "text_dim": "#686868",
    "white": "#ffffff", "amber": "#f0a500", "green": "#4fca80",
    "red": "#ff6b6b", "blue": "#5db8ff",
    "dim": "#444444", "dim2": "#303030",
    "entry_bg": "#0d0d0d", "entry_fg": "#ffffff",
    "row_fem": "#1a1500",   "fem_fg": "#f0a500",
    "row_sel": "#0d1f0d",   "sel_fg": "#4fca80",
    "row_norm": "#111111",  "norm_fg": "#383838",
    "row_alt": "#141414",
    "row_converted": "#0a1a2a", "conv_fg": "#5db8ff",
    "head_bg": "#1e1e1e",   "head_fg": "#888888",
    "sb_bg": "#1a1a1a",
}
LIGHT = {
    "bg": "#f2f1ec", "bg2": "#e8e7e1", "bg3": "#dddcd6",
    "border": "#c4c3bc", "text": "#1a1a1a", "text_dim": "#555555",
    "white": "#ffffff", "amber": "#b07000", "green": "#1a7a40",
    "red": "#cc3333", "blue": "#2266aa",
    "dim": "#999999", "dim2": "#d0cfc8",
    "entry_bg": "#ffffff", "entry_fg": "#1a1a1a",
    "row_fem": "#fff8e0",   "fem_fg": "#9a6000",
    "row_sel": "#e2f5e8",   "sel_fg": "#1a7a40",
    "row_norm": "#f2f1ec",  "norm_fg": "#bbbbbb",
    "row_alt": "#eeede8",
    "row_converted": "#e0f0ff", "conv_fg": "#2266aa",
    "head_bg": "#dddcd6",   "head_fg": "#666666",
    "sb_bg": "#e8e7e1",
}


# ── CSV HELPERS ───────────────────────────────────────────────────────────────
def safe(row, idx):
    return row[idx].strip() if idx < len(row) else ""

def is_female(row):
    return safe(row, COL_INFO).startswith('3" Female Channel')

def extract_color(info):
    m = re.search(r",([A-Z]{2})$", info.strip())
    return m.group(1) if m else ""

def box_info(color):
    return f'3" Box Header,16\',{color}' if color else '3" Box Header,16\''

def parse_csv(raw):
    hdr = None; rows = []
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.lower().startswith("sep="): continue
        f = s.split(";")
        if hdr is None: hdr = f
        else: rows.append(f)
    if hdr is None:
        raise ValueError("No header row found.")
    return hdr, rows

def do_convert(hdr, rows, sel_ids, byd_map):
    out = []; log = []
    for row in rows:
        row = list(row)
        while len(row) <= max(COL_CODE, COL_INFO, COL_MAIN): row.append("")
        rid = safe(row, COL_ID)
        if rid in sel_ids and is_female(row):
            old = safe(row, COL_CODE); new = byd_map.get(old, "")
            old_info = safe(row, COL_INFO)
            row[COL_INFO] = box_info(extract_color(old_info))
            row[COL_CODE] = new or old
            row[COL_MAIN] = new or row[COL_MAIN]
            log.append({"ok": bool(new), "id": rid, "old": old,
                         "new": new, "old_info": old_info,
                         "new_info": row[COL_INFO]})
        out.append(row)
    return out, log

def write_csv(hdr, rows):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(hdr)
    for r in rows: w.writerow(r)
    return buf.getvalue()


# ── MAIN APP ──────────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sunspace  |  Box Header CSV Editor  v6.0")
        self.geometry("1200x860")
        self.minsize(960, 680)

        self._tn  = "dark"
        self.T    = DARK
        self.hdr  = None
        self.rows = []
        self.rows_backup = None      # for undo
        self.selected    = set()     # set of row-IDs (strings)
        self.female_ids  = set()
        self.converted_ids = set()   # rows that were converted (for colouring)
        self.id_to_row   = {}
        self.id_to_idx   = {}        # row-ID → integer index in self.rows
        self.iid_list    = []        # ALL treeview iids in data order
        self.visible_iids = []       # currently visible iids (after filter)
        self.last_click  = None
        self.output_csv  = ""
        self.convert_log = []
        self.source_file = ""
        self.last_dir    = os.path.expanduser("~")
        self.byd_vars    = {}
        self.status_var  = tk.StringVar(value="No file loaded.")
        self.filter_var  = tk.StringVar()
        self.filter_var.trace_add("write", self._on_filter_changed)
        self._filter_after_id = None  # for debounce

        self._init_byd_vars()
        self._build()
        self._apply_theme()

    def _init_byd_vars(self):
        for k, v in DEFAULT_BYD_MAP.items():
            self.byd_vars[k] = tk.StringVar(value=v)

    def _byd_map(self):
        return {k: v.get().strip() for k, v in self.byd_vars.items()}

    # ── THEME ─────────────────────────────────────────────────────────────────
    def _toggle_theme(self):
        self._tn = "light" if self._tn == "dark" else "dark"
        self.T = LIGHT if self._tn == "light" else DARK
        self.theme_btn.config(
            text="🌙  Dark" if self._tn == "light" else "☀  Light")
        self._apply_theme()
        self._refresh_tree()

    def _apply_theme(self):
        T = self.T
        self.configure(bg=T["bg"])

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("T.Treeview",
                        background=T["bg"], foreground=T["norm_fg"],
                        fieldbackground=T["bg"], rowheight=26,
                        borderwidth=0, font=("Courier New", 9))
        style.configure("T.Treeview.Heading",
                        background=T["head_bg"], foreground=T["head_fg"],
                        borderwidth=0, relief="flat",
                        font=("Courier New", 8, "bold"))
        style.map("T.Treeview",
                  background=[("selected", T["bg"])],
                  foreground=[("selected", T["text"])])
        style.configure("TScrollbar",
                        background=T["bg2"], troughcolor=T["bg"],
                        arrowcolor=T["dim"])

        if hasattr(self, "tree"):
            self.tree.tag_configure("female",
                background=T["row_fem"], foreground=T["fem_fg"])
            self.tree.tag_configure("sel",
                background=T["row_sel"], foreground=T["sel_fg"])
            self.tree.tag_configure("norm",
                background=T["row_norm"], foreground=T["norm_fg"])
            self.tree.tag_configure("alt",
                background=T["row_alt"], foreground=T["norm_fg"])
            self.tree.tag_configure("converted",
                background=T["row_converted"], foreground=T["conv_fg"])

        self._recolour(self)

    def _recolour(self, widget):
        T = self.T
        cls = widget.__class__.__name__
        try:
            if cls in ("Frame", "Label"):
                widget.configure(bg=T["bg"])
            if cls == "Label":
                fg = widget._sunspace_fg if hasattr(widget, "_sunspace_fg") else T["text_dim"]
                widget.configure(fg=fg(T) if callable(fg) else fg)
        except Exception:
            pass
        for child in widget.winfo_children():
            self._recolour(child)

    # ── BUILD ─────────────────────────────────────────────────────────────────
    def _build(self):
        T = self.T

        # Header bar
        hbar = tk.Frame(self, bg=T["bg3"], height=52)
        hbar.pack(fill="x"); hbar.pack_propagate(False)
        tk.Label(hbar, text="SUNSPACE", bg=T["amber"], fg="black",
                 font=("Courier New", 9, "bold"), padx=8
                 ).pack(side="left", padx=12, pady=12)
        inf = tk.Frame(hbar, bg=T["bg3"]); inf.pack(side="left")
        tk.Label(inf, text="BOX HEADER CSV EDITOR",
                 bg=T["bg3"], fg=T["white"],
                 font=("Courier New", 13, "bold")).pack(anchor="w")
        tk.Label(inf, text="DEALER DESKTOP  ->  SC220  |  v6.0",
                 bg=T["bg3"], fg=T["text_dim"],
                 font=("Courier New", 8)).pack(anchor="w")
        self.theme_btn = tk.Button(hbar, text="☀  Light",
                  bg=T["bg2"], fg=T["text_dim"], relief="flat",
                  font=("Courier New", 9), cursor="hand2",
                  padx=10, pady=4, command=self._toggle_theme)
        self.theme_btn.pack(side="right", padx=12)

        # Amber line
        tk.Frame(self, bg=T["amber"], height=2).pack(fill="x")

        # Toolbar
        tb = tk.Frame(self, bg=T["bg2"], pady=7, padx=12); tb.pack(fill="x")
        self._btn(tb, "↑  UPLOAD CSV", T["amber"], "black",
                  self._open).pack(side="left", padx=(0, 6))
        self._btn(tb, "PASTE", T["bg3"], T["text_dim"],
                  self._paste).pack(side="left", padx=(0, 6))
        self._btn(tb, "SAMPLE", T["bg2"], T["dim"],
                  self._sample).pack(side="left", padx=(0, 16))
        tk.Frame(tb, bg=T["dim2"], width=1, height=24
                 ).pack(side="left", padx=8, pady=2)
        self._btn(tb, "BYD MAP", T["bg3"], T["text_dim"],
                  self._byd_window).pack(side="left", padx=(8, 0))
        self._btn(tb, "CLEAR", T["bg2"], T["dim"],
                  self._clear).pack(side="right")

        # Selection + filter bar
        cb = tk.Frame(self, bg=T["bg3"], pady=5, padx=12); cb.pack(fill="x")

        self._btn(cb, "☑  ALL FEMALE", T["bg2"], T["fem_fg"],
                  self._sel_all_female).pack(side="left", padx=(0, 6))
        self._btn(cb, "☐  DESELECT ALL", T["bg2"], T["dim"],
                  self._deselect_all).pack(side="left", padx=(0, 12))

        # Filter entry
        tk.Label(cb, text="🔍", bg=T["bg3"], fg=T["text_dim"],
                 font=("Courier New", 10)).pack(side="left", padx=(8, 2))
        self.filter_entry = tk.Entry(cb, textvariable=self.filter_var,
                 bg=T["entry_bg"], fg=T["entry_fg"],
                 insertbackground=T["text"], relief="flat",
                 font=("Courier New", 9),
                 highlightthickness=1, highlightbackground=T["border"],
                 width=28)
        self.filter_entry.pack(side="left", padx=(0, 4), ipady=3)
        self.filter_clear_btn = self._btn(cb, "✕", T["bg3"], T["dim"],
                  self._clear_filter)
        self.filter_clear_btn.pack(side="left", padx=(0, 8))

        tk.Label(cb, text="SHIFT+CLICK = range  |  CTRL+A = all female  |  CTRL+D = deselect",
                 bg=T["bg3"], fg=T["dim"],
                 font=("Courier New", 8)).pack(side="left", padx=(8, 0))

        self.counts_lbl = tk.Label(cb, text="",
                                   bg=T["bg3"], fg=T["text_dim"],
                                   font=("Courier New", 9, "bold"))
        self.counts_lbl.pack(side="right")

        # Treeview
        tf = tk.Frame(self, bg=T["bg"]); tf.pack(fill="both", expand=True)

        vsb = ttk.Scrollbar(tf, orient="vertical")
        vsb.pack(side="right", fill="y")
        hsb = ttk.Scrollbar(tf, orient="horizontal")
        hsb.pack(side="bottom", fill="x")

        cols = ("chk", "num", "group", "orient", "profile", "byd", "data2", "rest")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings",
                                 style="T.Treeview",
                                 yscrollcommand=vsb.set,
                                 xscrollcommand=hsb.set,
                                 selectmode="none")
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        heads = [("chk","✓",36), ("num","#",44), ("group","GROUP",60),
                 ("orient","ORIENTATION",110), ("profile","PROFILE NAME",300),
                 ("byd","BYD",72), ("data2","TYPE",80), ("rest","...",400)]
        for cid, txt, w in heads:
            self.tree.heading(cid, text=txt)
            self.tree.column(cid, width=w, minwidth=w,
                             stretch=(cid == "rest"), anchor="w")

        self.tree.tag_configure("female",    background=T["row_fem"],  foreground=T["fem_fg"])
        self.tree.tag_configure("sel",       background=T["row_sel"],  foreground=T["sel_fg"])
        self.tree.tag_configure("norm",      background=T["row_norm"], foreground=T["norm_fg"])
        self.tree.tag_configure("alt",       background=T["row_alt"],  foreground=T["norm_fg"])
        self.tree.tag_configure("converted", background=T["row_converted"], foreground=T["conv_fg"])

        self.tree.bind("<Button-1>",        self._on_click)
        self.tree.bind("<Shift-Button-1>",  self._on_shift_click)
        self.tree.bind("<Control-a>",       lambda e: self._sel_all_female())
        self.tree.bind("<Control-A>",       lambda e: self._sel_all_female())
        self.tree.bind("<Control-d>",       lambda e: self._deselect_all())
        self.tree.bind("<Control-D>",       lambda e: self._deselect_all())
        self.tree.pack(fill="both", expand=True)

        # Action bar
        ab = tk.Frame(self, bg=T["bg2"], pady=8, padx=12); ab.pack(fill="x")
        self.convert_btn = self._btn(ab, "FEMALE  ->  BOX HEADER",
                                     T["dim2"], T["dim"], self._convert)
        self.convert_btn.config(state="disabled")
        self.convert_btn.pack(side="left", padx=(0, 8))

        self.undo_btn = self._btn(ab, "↩  UNDO", T["bg3"], T["dim"], self._undo)
        self.undo_btn.config(state="disabled")
        self.undo_btn.pack(side="left", padx=(0, 8))

        self.dl_btn = self._btn(ab, "↓  DOWNLOAD CSV",
                                T["green"], "black", self._download)
        self.dl_btn.config(state="disabled")
        self.dl_btn.pack(side="left", padx=(0, 8))

        self.cp_btn = self._btn(ab, "COPY TO CLIPBOARD",
                                T["bg3"], T["text_dim"], self._copy)
        self.cp_btn.config(state="disabled")
        self.cp_btn.pack(side="left")

        self.result_lbl = tk.Label(ab, text="",
                                   bg=T["bg2"], fg=T["text_dim"],
                                   font=("Courier New", 9))
        self.result_lbl.pack(side="left", padx=14)

        # Status bar
        tk.Frame(self, bg=T["border"], height=1).pack(fill="x")
        sb = tk.Frame(self, bg=T["bg3"], pady=4, padx=12); sb.pack(fill="x")
        tk.Label(sb, textvariable=self.status_var,
                 bg=T["bg3"], fg=T["text_dim"],
                 font=("Courier New", 9)).pack(side="left")

    # ── FILTER ────────────────────────────────────────────────────────────────
    def _on_filter_changed(self, *_args):
        """Debounced filter: wait 150ms after last keystroke."""
        if self._filter_after_id:
            self.after_cancel(self._filter_after_id)
        self._filter_after_id = self.after(150, self._apply_filter)

    def _clear_filter(self):
        self.filter_var.set("")

    def _apply_filter(self):
        """Show/hide treeview rows based on filter text."""
        self._filter_after_id = None
        ft = self.filter_var.get().strip().lower()

        # Detach all, then re-attach matching
        for iid in self.iid_list:
            self.tree.detach(iid)

        self.visible_iids = []
        for iid in self.iid_list:
            row = self.id_to_row.get(iid)
            if not row:
                continue
            if ft:
                searchable = (
                    f"{safe(row, COL_INFO)} {safe(row, COL_ORIENT)} "
                    f"{safe(row, COL_CODE)} {safe(row, COL_DATA1)} "
                    f"{safe(row, COL_DATA2)}"
                ).lower()
                if ft not in searchable:
                    continue
            self.tree.move(iid, "", "end")
            self.visible_iids.append(iid)

        self._refresh_tags()
        self._update_counts()

    def _refresh_tags(self):
        """Reapply tags to all visible rows (handles alternating + state)."""
        for vis_idx, iid in enumerate(self.visible_iids):
            rid = iid
            row = self.id_to_row.get(rid)
            if not row:
                continue

            # Determine tag
            if rid in self.converted_ids:
                tag = "converted"
            elif rid in self.selected:
                tag = "sel"
            elif rid in self.female_ids:
                tag = "female"
            elif vis_idx % 2 == 0:
                tag = "norm"
            else:
                tag = "alt"

            self.tree.item(iid, tags=(tag,))

            # Update checkbox + profile columns
            if rid in self.female_ids:
                chk = "☑" if rid in self.selected else "☐"
            else:
                chk = ""

            prof = safe(row, COL_INFO)
            self.tree.set(iid, "chk", chk)
            self.tree.set(iid, "profile", prof[:50])

    # ── TREEVIEW HELPERS ──────────────────────────────────────────────────────
    def _refresh_tree(self):
        """Full refresh of tags and display values for visible rows."""
        self._refresh_tags()

    def _update_counts(self):
        sel = len(self.selected)
        fem = len(self.female_ids)
        tot = len(self.rows)
        vis = len(self.visible_iids)

        filter_note = f"   Showing: {vis}" if vis != tot else ""
        self.counts_lbl.config(
            text=f"Total: {tot}   Female: {fem}   Selected: {sel}{filter_note}   ")

        if sel > 0:
            self.convert_btn.config(
                state="normal", bg=self.T["amber"], fg="black",
                text=f"FEMALE  ->  BOX HEADER  ({sel} rows)")
        else:
            self.convert_btn.config(
                state="disabled", bg=self.T["dim2"], fg=self.T["dim"],
                text="FEMALE  ->  BOX HEADER")

    # ── CLICK HANDLERS ────────────────────────────────────────────────────────
    def _on_click(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid or iid not in self.female_ids:
            return
        # Don't allow selection changes on already-converted rows
        if iid in self.converted_ids:
            return
        if iid in self.selected:
            self.selected.discard(iid)
        else:
            self.selected.add(iid)
        self.last_click = iid
        self._refresh_tree()
        self._update_counts()

    def _on_shift_click(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid or iid not in self.female_ids:
            return
        if iid in self.converted_ids:
            return

        # Use visible_iids for range so filter is respected
        ref_list = self.visible_iids

        if self.last_click and self.last_click in ref_list:
            a = ref_list.index(self.last_click)
            b = ref_list.index(iid)
            lo, hi = min(a, b), max(a, b)
            for i_iid in ref_list[lo:hi+1]:
                if i_iid in self.female_ids and i_iid not in self.converted_ids:
                    self.selected.add(i_iid)
        else:
            self.selected.add(iid)
        self.last_click = iid
        self._refresh_tree()
        self._update_counts()

    # ── SELECTION BUTTONS ─────────────────────────────────────────────────────
    def _sel_all_female(self):
        """Select all female rows that haven't been converted yet."""
        for rid in self.female_ids:
            if rid not in self.converted_ids:
                self.selected.add(rid)
        self._refresh_tree()
        self._update_counts()

    def _deselect_all(self):
        """Deselect all (only non-converted rows are affected visually)."""
        self.selected.clear()
        self._refresh_tree()
        self._update_counts()

    # ── LOAD ──────────────────────────────────────────────────────────────────
    def _open(self):
        path = filedialog.askopenfilename(
            title="Open Dealer Desktop CSV",
            initialdir=self.last_dir,
            filetypes=[("CSV / Text", "*.csv *.txt"), ("All files", "*.*")])
        if not path: return
        self.last_dir = os.path.dirname(path)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            self._ingest(f.read(), source=path)

    def _paste(self):
        T = self.T
        dlg = tk.Toplevel(self); dlg.title("Paste CSV")
        dlg.configure(bg=T["bg"]); dlg.geometry("740x420"); dlg.grab_set()
        tk.Label(dlg, text="Paste Dealer Desktop CSV content:",
                 bg=T["bg"], fg=T["text_dim"],
                 font=("Courier New", 9)).pack(anchor="w", padx=14, pady=(12, 4))
        txt = tk.Text(dlg, bg=T["entry_bg"], fg=T["text"],
                      insertbackground=T["text"],
                      font=("Courier New", 9), relief="flat",
                      highlightthickness=1, highlightbackground=T["border"])
        txt.pack(fill="both", expand=True, padx=14)
        def _go():
            c = txt.get("1.0", "end").strip()
            if c: self._ingest(c)
            dlg.destroy()
        row = tk.Frame(dlg, bg=T["bg"], pady=8, padx=14); row.pack(fill="x")
        self._btn(row, "LOAD", T["amber"], "black", _go).pack(side="left", padx=(0,8))
        self._btn(row, "CANCEL", T["bg3"], T["dim"], dlg.destroy).pack(side="left")

    def _sample(self):
        s = (
            "Sep=;\n"
            "id;ksn;ksnbar;ktn;ktnbar;l;r;code;info;width;height;trolley;box;"
            "orientation;reinf;reinfbar;pos;prono;offno;customer;date;nccode;"
            "isfix;colorcode;colorinfo;mainprofile;subcust;image;DATA1;DATA2;DATA3;DATA4;DATA5\n"
            "1;1;54864;1;25146;90;93;810300;3\" Female Channel 18',WH;0;0;0;0;right;0;0;0;0;0;Sunroom Designs;3/12/2026;;0;1;1 White;810300;Deskin-M400-Room;;S1;Starter;;;\n"
            "2;1;54864;1;25103;93;90;810300;3\" Female Channel 18',WH;0;0;0;0;leftmod;0;0;0;0;0;Sunroom Designs;3/12/2026;;0;1;1 White;810300;Deskin-M400-Room;;W3;PVC;42 13/16\";54 15/16\";\n"
            "3;1;54864;1;24493;90;93;810300;3\" Female Channel 18',WH;0;0;0;0;rightmod;0;0;0;0;0;Sunroom Designs;3/12/2026;;0;1;1 White;810300;Deskin-M400-Room;;W3;PVC;42 13/16\";54 15/16\";\n"
            "4;1;48768;1;10890;90;90;810311;3\" Box Header,16',WH;0;0;0;0;header;0;0;0;0;0;Sunroom Designs;3/12/2026;;0;1;1 White;810311;Deskin-M400-Room;;W3;Header;42 13/16\";54 15/16\";\n"
            "5;1;48768;1;10890;90;90;810311;3\" Box Header,16',WH;0;0;0;0;header;0;0;0;0;0;Sunroom Designs;3/12/2026;;0;1;1 White;810311;Deskin-M400-Room;;W3;Header;42 13/16\";54 15/16\";\n"
            "6;1;54864;1;24486;93;90;810305;3\" Male Channel 18',WH;0;0;0;0;leftmod;0;0;0;0;0;Sunroom Designs;3/12/2026;;0;1;1 White;810305;Deskin-M400-Room;;W4;PVC;42 13/16\";54 15/16\";\n"
            "7;1;48768;1;10890;90;90;810300;3\" Female Channel 18',WH;0;0;0;0;header;0;0;0;0;0;Sunroom Designs;3/12/2026;;0;1;1 White;810300;Deskin-M400-Room;;W4;Header;42 13/16\";54 15/16\";\n"
            "8;1;48768;1;10890;90;90;810300;3\" Female Channel 18',WH;0;0;0;0;header;0;0;0;0;0;Sunroom Designs;3/12/2026;;0;1;1 White;810300;Deskin-M400-Room;;W4;Header;42 13/16\";54 15/16\";\n"
            "9;1;54864;1;23856;93;90;810300;3\" Female Channel 18',WH;0;0;0;0;leftmod;0;0;0;0;0;Sunroom Designs;3/12/2026;;0;1;1 White;810300;Deskin-M400-Room;;W5;PVC;42 13/16\";54 15/16\";\n"
            "10;1;54864;1;23246;90;93;810302;3\" Female Channel 18',DR;0;0;0;0;rightmod;0;0;0;0;0;Sunroom Designs;3/12/2026;;0;1;1 DR;810302;Deskin-M400-Room;;W5;PVC;42 13/16\";54 15/16\";\n"
        )
        self._ingest(s)

    def _ingest(self, raw, source=""):
        try:
            hdr, rows = parse_csv(raw)
        except Exception as ex:
            messagebox.showerror("Parse Error", str(ex)); return

        self.hdr = hdr; self.rows = rows; self.source_file = source
        self.rows_backup = None
        self.output_csv = ""
        self.convert_log = []
        self.selected = set()
        self.female_ids = set()
        self.converted_ids = set()
        self.id_to_row = {}
        self.id_to_idx = {}
        self.iid_list = []
        self.visible_iids = []
        self.filter_var.set("")  # clear filter on new load

        for item in self.tree.get_children():
            self.tree.delete(item)

        for i, row in enumerate(rows):
            rid = safe(row, COL_ID) or str(i)
            female = is_female(row)
            if female:
                self.female_ids.add(rid)
                self.selected.add(rid)   # auto-select
            self.id_to_row[rid] = row
            self.id_to_idx[rid] = i

            if rid in self.selected:   tag = "sel"
            elif female:               tag = "female"
            elif i % 2 == 0:           tag = "norm"
            else:                      tag = "alt"

            chk  = "☑" if rid in self.selected else ("☐" if female else "")
            prof = safe(row, COL_INFO)
            rest_parts = [safe(row, j) for j in range(len(row))
                          if j not in (COL_ID, COL_CODE, COL_INFO, COL_ORIENT,
                                       COL_DATA1, COL_DATA2)]
            rest = "  ".join(p for p in rest_parts if p)[:80]

            self.tree.insert("", "end", iid=rid, tags=(tag,),
                values=(chk, str(i+1).zfill(3), safe(row, COL_DATA1),
                        safe(row, COL_ORIENT), prof[:50],
                        safe(row, COL_CODE), safe(row, COL_DATA2), rest))
            self.iid_list.append(rid)

        self.visible_iids = list(self.iid_list)
        self.last_click = None
        self.dl_btn.config(state="disabled")
        self.cp_btn.config(state="disabled")
        self.undo_btn.config(state="disabled")
        self.result_lbl.config(text="")
        self._update_counts()

        lbl = os.path.basename(source) if source else "pasted content"
        fem = len(self.female_ids)
        self.status_var.set(
            f"Loaded: {lbl}   |   {len(rows)} rows   |   "
            f"{fem} Female Channel rows highlighted and pre-selected")

    def _clear(self):
        self.rows = []; self.hdr = None; self.selected = set()
        self.female_ids = set(); self.converted_ids = set()
        self.id_to_row = {}; self.id_to_idx = {}
        self.iid_list = []; self.visible_iids = []
        self.output_csv = ""; self.source_file = ""
        self.rows_backup = None; self.convert_log = []
        self.filter_var.set("")
        for item in self.tree.get_children(): self.tree.delete(item)
        self.dl_btn.config(state="disabled")
        self.cp_btn.config(state="disabled")
        self.undo_btn.config(state="disabled")
        self.result_lbl.config(text=""); self._update_counts()
        self.status_var.set("No file loaded.")

    # ── CONVERT ───────────────────────────────────────────────────────────────
    def _convert(self):
        if not self.rows:
            messagebox.showwarning("No Data", "Load a file first."); return
        if not self.selected:
            messagebox.showwarning("Nothing Selected", "Select rows to convert."); return

        # Backup for undo
        self.rows_backup = copy.deepcopy(self.rows)
        backup_female = set(self.female_ids)
        backup_selected = set(self.selected)
        backup_converted = set(self.converted_ids)
        self._undo_state = (backup_female, backup_selected, backup_converted)

        converted, log = do_convert(self.hdr, self.rows, self.selected, self._byd_map())
        self.rows = converted
        self.convert_log = log
        self.output_csv = write_csv(self.hdr, converted)

        # Update id_to_row mapping and mark converted rows
        newly_converted = set()
        for entry in log:
            rid = entry["id"]
            newly_converted.add(rid)
            self.converted_ids.add(rid)

        # Update id_to_row for converted rows
        for i, row in enumerate(self.rows):
            rid = safe(row, COL_ID) or str(i)
            self.id_to_row[rid] = row

        # Recalculate female_ids (converted rows are no longer female)
        self.female_ids = set()
        for i, row in enumerate(self.rows):
            rid = safe(row, COL_ID) or str(i)
            if is_female(row):
                self.female_ids.add(rid)

        # Clear selection of converted rows
        self.selected -= newly_converted

        # Refresh tree display
        self._apply_filter()

        fixed = sum(1 for c in log if c["ok"])
        warn  = sum(1 for c in log if not c["ok"])
        self.dl_btn.config(state="normal")
        self.cp_btn.config(state="normal")
        self.undo_btn.config(state="normal")
        self.result_lbl.config(
            text=f"  {fixed} rows converted.  "
                 f"{'%d missing BYD mapping.' % warn if warn else 'Ready to download.'}",
            fg=self.T["amber"] if warn else self.T["green"])
        self.status_var.set(
            f"Converted {fixed} rows.  "
            f"{'%d warnings.' % warn if warn else 'Click Download to save.'}")

        # Show diff log
        if log:
            self._show_diff_log(log)

    def _undo(self):
        if self.rows_backup is None:
            return
        self.rows = self.rows_backup
        self.rows_backup = None

        # Restore state
        if hasattr(self, "_undo_state"):
            self.female_ids, self.selected, self.converted_ids = self._undo_state
            del self._undo_state

        # Rebuild id_to_row
        for i, row in enumerate(self.rows):
            rid = safe(row, COL_ID) or str(i)
            self.id_to_row[rid] = row

        self.output_csv = ""
        self.convert_log = []
        self.undo_btn.config(state="disabled")
        self.dl_btn.config(state="disabled")
        self.cp_btn.config(state="disabled")
        self.result_lbl.config(text="  Undo complete.", fg=self.T["blue"])
        self._apply_filter()
        self.status_var.set("Conversion undone. Original data restored.")

    def _show_diff_log(self, log):
        T = self.T
        dlg = tk.Toplevel(self); dlg.title("Conversion Diff Log")
        dlg.configure(bg=T["bg"]); dlg.geometry("700x400"); dlg.grab_set()

        tk.Label(dlg, text="CONVERSION RESULTS",
                 bg=T["bg"], fg=T["white"],
                 font=("Courier New", 11, "bold"), pady=8, padx=14).pack(anchor="w")

        fixed = sum(1 for c in log if c["ok"])
        warn  = sum(1 for c in log if not c["ok"])
        tk.Label(dlg,
                 text=f"Converted: {fixed}    Warnings: {warn}    Total: {len(log)}",
                 bg=T["bg"], fg=T["text_dim"],
                 font=("Courier New", 9), padx=14).pack(anchor="w")

        tk.Frame(dlg, bg=T["border"], height=1).pack(fill="x", pady=6)

        # Diff treeview
        cols_d = ("status", "row", "old_byd", "new_byd", "old_profile", "new_profile")
        dtree = ttk.Treeview(dlg, columns=cols_d, show="headings",
                             style="T.Treeview", height=14)
        for cid, txt, w in [("status","",30), ("row","Row",50),
                             ("old_byd","Old BYD",80), ("new_byd","New BYD",80),
                             ("old_profile","Old Profile",200), ("new_profile","New Profile",200)]:
            dtree.heading(cid, text=txt)
            dtree.column(cid, width=w, minwidth=w, anchor="w")

        dtree.tag_configure("ok",   foreground=T["green"])
        dtree.tag_configure("warn", foreground=T["amber"])

        for entry in log:
            tag = "ok" if entry["ok"] else "warn"
            status = "✓" if entry["ok"] else "⚠"
            new_byd = entry["new"] if entry["new"] else "(none)"
            dtree.insert("", "end", tags=(tag,),
                values=(status, entry["id"], entry["old"], new_byd,
                        entry.get("old_info", ""), entry.get("new_info", "")))

        dtree.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        self._btn(dlg, "CLOSE", T["amber"], "black", dlg.destroy
                  ).pack(pady=(0, 10))

    def _suggested_filename(self):
        base = os.path.basename(self.source_file) if self.source_file else "output.csv"
        return "corrected_" + base

    def _download(self):
        if not self.output_csv:
            messagebox.showwarning("Nothing to Save", "Run conversion first."); return
        path = filedialog.asksaveasfilename(
            title="Save Corrected CSV",
            initialdir=self.last_dir,
            initialfile=self._suggested_filename(),
            defaultextension=".csv",
            filetypes=[("CSV file", "*.csv"), ("All files", "*.*")])
        if not path: return
        self.last_dir = os.path.dirname(path)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(self.output_csv)
        messagebox.showinfo("Saved", f"Saved:\n{os.path.basename(path)}")
        self.status_var.set(f"Saved  ->  {os.path.basename(path)}")

    def _copy(self):
        if not self.output_csv: return
        self.clipboard_clear(); self.clipboard_append(self.output_csv)
        self.status_var.set("Copied to clipboard.")

    # ── BYD EDITOR WINDOW ─────────────────────────────────────────────────────
    def _byd_window(self):
        T = self.T
        dlg = tk.Toplevel(self); dlg.title("BYD Code Mapping")
        dlg.configure(bg=T["bg"]); dlg.geometry("600x320"); dlg.grab_set()
        tk.Label(dlg, text="FEMALE CHANNEL  ->  BOX HEADER  BYD MAPPING",
                 bg=T["bg"], fg=T["text_dim"],
                 font=("Courier New", 9), pady=8, padx=14).pack(anchor="w")
        tk.Frame(dlg, bg=T["border"], height=1).pack(fill="x")
        frm = tk.Frame(dlg, bg=T["bg"], padx=16, pady=10); frm.pack()
        for col, lbl in enumerate(("PROFILE", "FEMALE BYD", "", "BOX HEADER BYD")):
            tk.Label(frm, text=lbl, bg=T["bg"], fg=T["dim"],
                     font=("Courier New", 8)
                     ).grid(row=0, column=col, padx=6, pady=(0,6), sticky="w")
        for r, (old, new) in enumerate(DEFAULT_BYD_MAP.items(), 1):
            if old not in self.byd_vars:
                self.byd_vars[old] = tk.StringVar(value=new)
            tk.Label(frm, text=BYD_LABELS.get(old, old),
                     bg=T["bg"], fg=T["text_dim"],
                     font=("Courier New", 9), width=30, anchor="w"
                     ).grid(row=r, column=0, padx=6, pady=2, sticky="w")
            tk.Label(frm, text=old, bg=T["bg"], fg=T["amber"],
                     font=("Courier New", 10, "bold"), width=8
                     ).grid(row=r, column=1, padx=4)
            tk.Label(frm, text=" ->", bg=T["bg"], fg=T["dim"],
                     font=("Courier New", 10)).grid(row=r, column=2, padx=2)
            tk.Entry(frm, textvariable=self.byd_vars[old],
                     bg=T["entry_bg"], fg=T["green"],
                     insertbackground=T["green"], relief="flat",
                     font=("Courier New", 11, "bold"),
                     highlightthickness=1, highlightbackground=T["border"], width=10
                     ).grid(row=r, column=3, padx=6, pady=2, ipady=3, sticky="w")
        br = tk.Frame(dlg, bg=T["bg"], pady=8, padx=14); br.pack(fill="x")

        def _reset():
            for k, v in DEFAULT_BYD_MAP.items():
                self.byd_vars[k].set(v)

        self._btn(br, "RESET DEFAULTS", T["bg3"], T["dim"], _reset).pack(side="left", padx=(0, 8))
        self._btn(br, "CLOSE", T["amber"], "black", dlg.destroy).pack(side="left")

    # ── WIDGET HELPER ─────────────────────────────────────────────────────────
    def _btn(self, parent, text, bg, fg, cmd):
        return tk.Button(parent, text=text, bg=bg, fg=fg,
                         activebackground=bg, relief="flat",
                         font=("Courier New", 10, "bold"),
                         cursor="hand2", padx=12, pady=5, command=cmd)


if __name__ == "__main__":
    App().mainloop()
