"""
Sunspace  |  Box Header CSV Editor  v6.0  (Streamlit)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Rebuilt for the browser: upload / paste / sample → select rows →
convert Female Channel → Box Header → download corrected CSV.

Improvements over v5 Tkinter:
  • Runs in any browser — no Python install needed on user machine
  • Persistent BYD map editing in sidebar
  • Live diff preview before download
  • Undo last conversion
  • Row-level search / filter
  • Batch stats dashboard
  • Cleaner column display with orientation + group badges
"""

import streamlit as st
import csv, io, os, re, copy, time
from dataclasses import dataclass, field
from typing import Optional

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sunspace | Box Header CSV Editor v6.0",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
COL_ID, COL_CODE, COL_INFO = 0, 7, 8
COL_ORIENT, COL_MAIN       = 13, 25
COL_DATA1, COL_DATA2        = 28, 29

DEFAULT_BYD_MAP = {
    "810300": ("810311", '3" Female Channel 18\'  White'),
    "810302": ("810310", '3" Female Channel 18\'  Driftwood'),
    "810303": ("810309", '3" Female Channel 18\'  Bronze'),
    "882980": ("882986", '3" Female Channel 18\'  Black'),
    "810299": ("810311", '3" Female Channel 14\'  White'),
    "810301": ("810310", '3" Female Channel 14\'  Driftwood'),
}

SAMPLE_CSV = (
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


# ─── HELPERS ──────────────────────────────────────────────────────────────────
def safe(row: list, idx: int) -> str:
    return row[idx].strip() if idx < len(row) else ""


def is_female(row: list) -> bool:
    return safe(row, COL_INFO).startswith('3" Female Channel')


def extract_color(info: str) -> str:
    m = re.search(r",([A-Z]{2})$", info.strip())
    return m.group(1) if m else ""


def box_info(color: str) -> str:
    return f'3" Box Header,16\',{color}' if color else '3" Box Header,16\''


def parse_csv(raw: str) -> tuple[list, list[list]]:
    """Parse semicolon-delimited Dealer Desktop CSV. Returns (header, rows)."""
    hdr = None
    rows = []
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.lower().startswith("sep="):
            continue
        fields = s.split(";")
        if hdr is None:
            hdr = fields
        else:
            rows.append(fields)
    if hdr is None:
        raise ValueError("No header row found in CSV data.")
    return hdr, rows


def do_convert(
    hdr: list,
    rows: list[list],
    sel_ids: set[str],
    byd_map: dict[str, str],
) -> tuple[list[list], list[dict]]:
    """Convert selected Female Channel rows → Box Header. Returns (new_rows, log)."""
    out = []
    log = []
    for row in rows:
        row = list(row)
        # pad if short
        needed = max(COL_CODE, COL_INFO, COL_MAIN) + 1
        while len(row) < needed:
            row.append("")

        rid = safe(row, COL_ID)
        if rid in sel_ids and is_female(row):
            old_code = safe(row, COL_CODE)
            new_code = byd_map.get(old_code, "")
            color = extract_color(safe(row, COL_INFO))
            row[COL_INFO] = box_info(color)
            row[COL_CODE] = new_code or old_code
            row[COL_MAIN] = new_code or row[COL_MAIN]
            log.append({"ok": bool(new_code), "id": rid, "old": old_code, "new": new_code})
        out.append(row)
    return out, log


def rows_to_csv(hdr: list, rows: list[list]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(hdr)
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def color_badge(code: str) -> str:
    """Return a colored dot for known color suffixes."""
    colors = {
        "WH": "⚪", "DR": "🟤", "BZ": "🟠", "BK": "⚫",
        "White": "⚪", "Driftwood": "🟤", "Bronze": "🟠", "Black": "⚫",
    }
    return colors.get(code, "")


def orientation_label(orient: str) -> str:
    """Friendly orientation display."""
    labels = {
        "right": "→ Right",
        "left": "← Left",
        "rightmod": "→ Right Mod",
        "leftmod": "← Left Mod",
        "header": "▬ Header",
    }
    return labels.get(orient.lower(), orient)


# ─── SESSION STATE INIT ──────────────────────────────────────────────────────
def init_state():
    defaults = {
        "hdr": None,
        "rows": [],
        "rows_backup": None,       # for undo
        "selected": set(),
        "female_ids": set(),
        "source_name": "",
        "output_csv": "",
        "convert_log": [],
        "converted": False,
        "byd_map": {k: v[0] for k, v in DEFAULT_BYD_MAP.items()},
        "filter_text": "",
        "show_only_female": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()


# ─── INGEST ───────────────────────────────────────────────────────────────────
def ingest(raw: str, source_name: str = "pasted content"):
    hdr, rows = parse_csv(raw)
    st.session_state.hdr = hdr
    st.session_state.rows = rows
    st.session_state.rows_backup = None
    st.session_state.source_name = source_name
    st.session_state.output_csv = ""
    st.session_state.convert_log = []
    st.session_state.converted = False

    female_ids = set()
    for i, row in enumerate(rows):
        rid = safe(row, COL_ID) or str(i)
        if is_female(row):
            female_ids.add(rid)

    st.session_state.female_ids = female_ids
    st.session_state.selected = set(female_ids)  # auto-select all female


# ─── CUSTOM CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* ── Header bar ── */
    .sunspace-header {
        background: linear-gradient(135deg, #111 0%, #1a1a1a 100%);
        border-bottom: 3px solid #f0a500;
        padding: 1rem 1.5rem;
        margin: -1rem -1rem 1.5rem -1rem;
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    .sunspace-badge {
        background: #f0a500;
        color: #000;
        font-family: 'Courier New', monospace;
        font-weight: 800;
        font-size: 0.75rem;
        padding: 0.3rem 0.6rem;
        letter-spacing: 0.05em;
    }
    .sunspace-title {
        color: #fff;
        font-family: 'Courier New', monospace;
        font-size: 1.25rem;
        font-weight: 700;
        letter-spacing: 0.03em;
    }
    .sunspace-sub {
        color: #686868;
        font-family: 'Courier New', monospace;
        font-size: 0.7rem;
    }

    /* ── Stats chips ── */
    .stat-row { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1rem; }
    .stat-chip {
        font-family: 'Courier New', monospace;
        font-size: 0.8rem;
        padding: 0.35rem 0.75rem;
        border-radius: 4px;
        font-weight: 600;
    }
    .chip-total  { background: #1e1e1e; color: #888; }
    .chip-female { background: #1a1500; color: #f0a500; }
    .chip-sel    { background: #0d1f0d; color: #4fca80; }
    .chip-warn   { background: #2a1a00; color: #ff8c00; }

    /* ── Table styling ── */
    .row-table {
        width: 100%;
        border-collapse: collapse;
        font-family: 'Courier New', monospace;
        font-size: 0.82rem;
    }
    .row-table th {
        background: #1a1a1a;
        color: #686868;
        text-align: left;
        padding: 0.5rem 0.6rem;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        border-bottom: 1px solid #2e2e2e;
        position: sticky;
        top: 0;
        z-index: 1;
    }
    .row-table td {
        padding: 0.4rem 0.6rem;
        border-bottom: 1px solid #1a1a1a;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 300px;
    }
    .row-female    { background: #1a1500; color: #f0a500; }
    .row-selected  { background: #0d1f0d; color: #4fca80; }
    .row-normal    { background: #111; color: #555; }
    .row-alt       { background: #141414; color: #555; }
    .row-converted { background: #0a1a2a; color: #5db8ff; }

    .orient-badge {
        display: inline-block;
        padding: 0.15rem 0.45rem;
        border-radius: 3px;
        font-size: 0.72rem;
        font-weight: 600;
    }
    .orient-right    { background: #1a2a1a; color: #4fca80; }
    .orient-left     { background: #1a1a2a; color: #7a9fff; }
    .orient-header   { background: #2a2a1a; color: #d4b44a; }
    .orient-default  { background: #1e1e1e; color: #666; }

    .profile-tag {
        display: inline-block;
        padding: 0.1rem 0.4rem;
        border-radius: 3px;
        font-size: 0.72rem;
    }
    .tag-female { background: #2a2000; color: #f0a500; }
    .tag-box    { background: #002a1a; color: #4fca80; }
    .tag-male   { background: #1a1a2a; color: #7a9fff; }
    .tag-other  { background: #1e1e1e; color: #666; }

    /* ── Diff table ── */
    .diff-table { width: 100%; border-collapse: collapse; font-family: 'Courier New', monospace; font-size: 0.8rem; }
    .diff-table th { background: #1a1a1a; color: #686868; padding: 0.4rem 0.6rem; text-align: left; font-size: 0.7rem; border-bottom: 1px solid #2e2e2e; }
    .diff-table td { padding: 0.35rem 0.6rem; border-bottom: 1px solid #1a1a1a; }
    .diff-old { color: #ff6b6b; text-decoration: line-through; }
    .diff-new { color: #4fca80; font-weight: 700; }
    .diff-warn { color: #ff8c00; }

    /* ── Scrollable container ── */
    .table-scroll {
        max-height: 520px;
        overflow-y: auto;
        border: 1px solid #2e2e2e;
        border-radius: 4px;
    }

    /* ── Sidebar styling ── */
    .byd-label { font-family: 'Courier New', monospace; font-size: 0.78rem; color: #999; }
    .byd-arrow { color: #f0a500; font-weight: 700; }

    /* ── Reduce Streamlit default padding ── */
    .block-container { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)


# ─── HEADER ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="sunspace-header">
    <span class="sunspace-badge">SUNSPACE</span>
    <div>
        <div class="sunspace-title">BOX HEADER CSV EDITOR</div>
        <div class="sunspace-sub">DEALER DESKTOP → SC220  |  v6.0 Streamlit</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ─── SIDEBAR: BYD MAP ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔧 BYD Code Mapping")
    st.caption("Female Channel → Box Header code translation")

    byd = st.session_state.byd_map
    for old_code, (default_new, label) in DEFAULT_BYD_MAP.items():
        col1, col2, col3 = st.columns([2.5, 0.5, 1.5])
        with col1:
            st.markdown(f"<div class='byd-label'>{label}</div>", unsafe_allow_html=True)
            st.code(old_code, language=None)
        with col2:
            st.markdown("<div class='byd-arrow' style='padding-top:1.6rem;text-align:center;'>→</div>", unsafe_allow_html=True)
        with col3:
            new_val = st.text_input(
                f"Box Header BYD for {old_code}",
                value=byd.get(old_code, default_new),
                key=f"byd_{old_code}",
                label_visibility="collapsed",
            )
            byd[old_code] = new_val.strip()

    st.divider()
    if st.button("🔄 Reset to Defaults", use_container_width=True):
        st.session_state.byd_map = {k: v[0] for k, v in DEFAULT_BYD_MAP.items()}
        st.rerun()

    st.divider()
    st.markdown("### ⚡ Shortcuts")
    st.markdown("""
    - **Select All Female** — button above table
    - **Deselect All** — button above table
    - **Filter** — search by profile, orientation, group
    - **Undo** — revert last conversion
    """)


# ─── INPUT SECTION ────────────────────────────────────────────────────────────
st.markdown("#### 📂 Load CSV Data")
input_tabs = st.tabs(["⬆ Upload File", "📋 Paste CSV", "🧪 Sample Data"])

with input_tabs[0]:
    uploaded = st.file_uploader(
        "Upload Dealer Desktop CSV",
        type=["csv", "txt"],
        help="Semicolon-delimited CSV exported from Dealer Desktop",
    )
    if uploaded:
        raw = uploaded.read().decode("utf-8", errors="replace")
        try:
            ingest(raw, source_name=uploaded.name)
            st.success(f"Loaded **{uploaded.name}** — {len(st.session_state.rows)} rows")
        except Exception as e:
            st.error(f"Parse error: {e}")

with input_tabs[1]:
    pasted = st.text_area(
        "Paste CSV content here",
        height=180,
        placeholder="Paste semicolon-delimited CSV from Dealer Desktop...",
    )
    if st.button("Load Pasted CSV", type="primary"):
        if pasted.strip():
            try:
                ingest(pasted.strip())
                st.success(f"Loaded pasted content — {len(st.session_state.rows)} rows")
            except Exception as e:
                st.error(f"Parse error: {e}")
        else:
            st.warning("Nothing to paste.")

with input_tabs[2]:
    st.caption("Load sample Dealer Desktop data to test the editor.")
    if st.button("Load Sample Data", type="secondary"):
        ingest(SAMPLE_CSV, source_name="sample_data.csv")
        st.success(f"Loaded sample — {len(st.session_state.rows)} rows")
        st.rerun()

# ─── EARLY EXIT IF NO DATA ───────────────────────────────────────────────────
if not st.session_state.rows:
    st.info("Upload, paste, or load sample CSV data to get started.")
    st.stop()

# ─── STATS CHIPS ──────────────────────────────────────────────────────────────
rows = st.session_state.rows
female_ids = st.session_state.female_ids
selected = st.session_state.selected

total = len(rows)
n_female = len(female_ids)
n_sel = len(selected)

st.markdown(f"""
<div class="stat-row">
    <span class="stat-chip chip-total">TOTAL: {total}</span>
    <span class="stat-chip chip-female">FEMALE CHANNEL: {n_female}</span>
    <span class="stat-chip chip-sel">SELECTED: {n_sel}</span>
    {'<span class="stat-chip chip-warn">⚠ CONVERTED — review diff below</span>' if st.session_state.converted else ''}
</div>
""", unsafe_allow_html=True)


# ─── SELECTION CONTROLS + FILTER ──────────────────────────────────────────────
ctrl_cols = st.columns([1, 1, 1, 2])

with ctrl_cols[0]:
    if st.button("☑ Select All Female", use_container_width=True):
        st.session_state.selected = set(female_ids)
        st.rerun()

with ctrl_cols[1]:
    if st.button("☐ Deselect All", use_container_width=True):
        st.session_state.selected = set()
        st.rerun()

with ctrl_cols[2]:
    show_female = st.checkbox("Show only Female Channel", value=st.session_state.show_only_female)
    st.session_state.show_only_female = show_female

with ctrl_cols[3]:
    filter_text = st.text_input(
        "🔍 Filter rows",
        value=st.session_state.filter_text,
        placeholder="Search profile, orientation, group, BYD...",
        label_visibility="collapsed",
    )
    st.session_state.filter_text = filter_text


# ─── ROW TABLE ────────────────────────────────────────────────────────────────
def get_orient_class(orient: str) -> str:
    o = orient.lower()
    if "right" in o: return "orient-right"
    if "left" in o: return "orient-left"
    if "header" in o: return "orient-header"
    return "orient-default"

def get_profile_tag(info: str) -> tuple[str, str]:
    if info.startswith('3" Female Channel'): return "tag-female", "FEM"
    if info.startswith('3" Box Header'): return "tag-box", "BOX"
    if info.startswith('3" Male Channel'): return "tag-male", "MALE"
    return "tag-other", ""

def build_table_html(rows, female_ids, selected, filter_text, show_only_female):
    html_rows = []
    ft = filter_text.lower().strip()

    for i, row in enumerate(rows):
        rid = safe(row, COL_ID) or str(i)
        info = safe(row, COL_INFO)
        orient = safe(row, COL_ORIENT)
        code = safe(row, COL_CODE)
        group = safe(row, COL_DATA1)
        rtype = safe(row, COL_DATA2)

        # filter
        if show_only_female and rid not in female_ids:
            continue
        if ft:
            searchable = f"{info} {orient} {code} {group} {rtype}".lower()
            if ft not in searchable:
                continue

        # row class
        is_sel = rid in selected
        is_fem = rid in female_ids
        if is_sel:
            row_cls = "row-selected"
        elif is_fem:
            row_cls = "row-female"
        elif i % 2 == 0:
            row_cls = "row-normal"
        else:
            row_cls = "row-alt"

        # checkbox display
        chk = "☑" if is_sel else ("☐" if is_fem else "·")

        # orient badge
        orient_cls = get_orient_class(orient)
        orient_html = f'<span class="orient-badge {orient_cls}">{orientation_label(orient)}</span>'

        # profile tag
        tag_cls, tag_txt = get_profile_tag(info)
        tag_html = f'<span class="profile-tag {tag_cls}">{tag_txt}</span> ' if tag_txt else ""

        color = extract_color(info)
        color_dot = color_badge(color)

        html_rows.append(
            f'<tr class="{row_cls}">'
            f'<td>{chk}</td>'
            f'<td>{str(i+1).zfill(3)}</td>'
            f'<td>{group}</td>'
            f'<td>{orient_html}</td>'
            f'<td>{tag_html}{info[:50]} {color_dot}</td>'
            f'<td>{code}</td>'
            f'<td>{rtype}</td>'
            f'</tr>'
        )

    if not html_rows:
        html_rows.append('<tr><td colspan="7" style="text-align:center;color:#555;padding:2rem;">No rows match filter.</td></tr>')

    return (
        '<div class="table-scroll"><table class="row-table">'
        '<thead><tr>'
        '<th style="width:36px;">✓</th>'
        '<th style="width:44px;">#</th>'
        '<th style="width:60px;">Group</th>'
        '<th style="width:120px;">Orientation</th>'
        '<th>Profile</th>'
        '<th style="width:80px;">BYD</th>'
        '<th style="width:80px;">Type</th>'
        '</tr></thead><tbody>'
        + "\n".join(html_rows)
        + '</tbody></table></div>'
    )


# ─── ROW SELECTION VIA CHECKBOXES ────────────────────────────────────────────
# Since we can't do click-to-toggle on raw HTML, provide per-row checkboxes
# for female rows using Streamlit native controls.

st.markdown("#### 📋 Row Data")

# Use an expander with the table for visual display,
# and then a multiselect for actual row selection.

# Show the HTML table as a visual reference
table_html = build_table_html(
    rows, female_ids, selected,
    filter_text, show_female,
)
st.markdown(table_html, unsafe_allow_html=True)

# Row selection via multiselect (only female rows are selectable)
if female_ids:
    st.markdown("##### Select Female Channel Rows to Convert")

    # Build options: show row # + profile info for context
    fem_options = {}
    for i, row in enumerate(rows):
        rid = safe(row, COL_ID) or str(i)
        if rid in female_ids:
            info = safe(row, COL_INFO)
            orient = safe(row, COL_ORIENT)
            group = safe(row, COL_DATA1)
            fem_options[rid] = f"Row {int(rid):>3d}  |  {group:>4s}  |  {orient:<12s}  |  {info[:40]}"

    # Current selection
    current_sel = [rid for rid in fem_options if rid in selected]

    new_sel = st.multiselect(
        "Selected rows for conversion",
        options=list(fem_options.keys()),
        default=current_sel,
        format_func=lambda x: fem_options.get(x, x),
        label_visibility="collapsed",
    )
    st.session_state.selected = set(new_sel)


# ─── CONVERT ──────────────────────────────────────────────────────────────────
st.markdown("---")

convert_cols = st.columns([2, 1, 1])

with convert_cols[0]:
    sel_count = len(st.session_state.selected)
    can_convert = sel_count > 0 and not st.session_state.converted
    btn_label = f"⚡ CONVERT  →  BOX HEADER  ({sel_count} rows)" if sel_count else "⚡ No rows selected"

    if st.button(btn_label, type="primary", disabled=not can_convert, use_container_width=True):
        # Save backup for undo
        st.session_state.rows_backup = copy.deepcopy(st.session_state.rows)

        converted_rows, log = do_convert(
            st.session_state.hdr,
            st.session_state.rows,
            st.session_state.selected,
            st.session_state.byd_map,
        )
        st.session_state.rows = converted_rows
        st.session_state.convert_log = log
        st.session_state.output_csv = rows_to_csv(st.session_state.hdr, converted_rows)
        st.session_state.converted = True
        st.rerun()

with convert_cols[1]:
    if st.session_state.rows_backup is not None:
        if st.button("↩ Undo Conversion", use_container_width=True):
            st.session_state.rows = st.session_state.rows_backup
            st.session_state.rows_backup = None
            st.session_state.output_csv = ""
            st.session_state.convert_log = []
            st.session_state.converted = False
            # Re-detect female rows after undo
            female_ids = set()
            for i, row in enumerate(st.session_state.rows):
                rid = safe(row, COL_ID) or str(i)
                if is_female(row):
                    female_ids.add(rid)
            st.session_state.female_ids = female_ids
            st.session_state.selected = set(female_ids)
            st.rerun()

with convert_cols[2]:
    if st.button("🗑 Clear All Data", use_container_width=True):
        for key in ["hdr", "rows", "rows_backup", "selected", "female_ids",
                     "source_name", "output_csv", "convert_log", "converted"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()


# ─── CONVERSION RESULTS ──────────────────────────────────────────────────────
if st.session_state.converted and st.session_state.convert_log:
    log = st.session_state.convert_log
    ok_count = sum(1 for e in log if e["ok"])
    warn_count = sum(1 for e in log if not e["ok"])

    st.markdown("#### 📊 Conversion Results")

    res_cols = st.columns(3)
    with res_cols[0]:
        st.metric("Rows Converted", ok_count)
    with res_cols[1]:
        st.metric("Missing BYD Mapping", warn_count)
    with res_cols[2]:
        st.metric("Total Processed", len(log))

    # Diff table
    diff_rows_html = []
    for entry in log:
        status = "✅" if entry["ok"] else "⚠️"
        old_cls = "diff-old"
        new_cls = "diff-new" if entry["ok"] else "diff-warn"
        new_display = entry["new"] if entry["new"] else "(no mapping)"

        diff_rows_html.append(
            f'<tr>'
            f'<td>{status}</td>'
            f'<td>Row {entry["id"]}</td>'
            f'<td class="{old_cls}">{entry["old"]}</td>'
            f'<td class="{new_cls}">{new_display}</td>'
            f'</tr>'
        )

    st.markdown(
        '<table class="diff-table">'
        '<thead><tr><th></th><th>Row</th><th>Old BYD</th><th>New BYD</th></tr></thead>'
        '<tbody>' + "\n".join(diff_rows_html) + '</tbody></table>',
        unsafe_allow_html=True,
    )


# ─── DOWNLOAD ─────────────────────────────────────────────────────────────────
if st.session_state.output_csv:
    st.markdown("---")
    st.markdown("#### 💾 Download")

    source = st.session_state.source_name or "output.csv"
    base = os.path.basename(source)
    suggested = f"corrected_{base}" if not base.startswith("corrected_") else base

    dl_cols = st.columns([2, 1])
    with dl_cols[0]:
        st.download_button(
            label="⬇ Download Corrected CSV",
            data=st.session_state.output_csv,
            file_name=suggested,
            mime="text/csv",
            type="primary",
            use_container_width=True,
        )
    with dl_cols[1]:
        if st.button("📋 Copy to Clipboard Info", use_container_width=True):
            st.code(st.session_state.output_csv[:500] + "\n... (truncated)", language=None)
            st.info("Use the download button above — clipboard copy requires the browser to handle the downloaded file.")

    # Preview
    with st.expander("👁 Preview output CSV (first 20 lines)"):
        lines = st.session_state.output_csv.split("\n")[:20]
        st.code("\n".join(lines), language=None)


# ─── FOOTER ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<div style="text-align:center;color:#444;font-family:Courier New,monospace;font-size:0.75rem;">'
    'Sunspace Modular Enclosures  |  Box Header CSV Editor v6.0  |  '
    'Dealer Desktop → SC220 Pipeline'
    '</div>',
    unsafe_allow_html=True,
)
