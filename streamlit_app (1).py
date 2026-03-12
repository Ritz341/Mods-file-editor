"""
Sunspace  |  Box Header CSV Editor  v5.0  (Streamlit)
"""

import streamlit as st
import pandas as pd
import csv, io, re, os

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Box Header CSV Editor · Sunspace",
    page_icon="🏗",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── BYD MAP ───────────────────────────────────────────────────────────────────
DEFAULT_BYD_MAP = {
    "810300": ("810311", "Female Channel 18'  White"),
    "810302": ("810310", "Female Channel 18'  Driftwood"),
    "810303": ("810309", "Female Channel 18'  Bronze"),
    "882980": ("882986", "Female Channel 18'  Black"),
    "810299": ("810311", "Female Channel 14'  White"),
    "810301": ("810310", "Female Channel 14'  Driftwood"),
}

# ── COLUMN INDICES ────────────────────────────────────────────────────────────
COL_ID, COL_CODE, COL_INFO = 0, 7, 8
COL_ORIENT, COL_MAIN       = 13, 25
COL_DATA1,  COL_DATA2      = 28, 29

# ── GLOBAL CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=swap');

  html, body, [class*="css"] {
    font-family: 'JetBrains Mono', 'Courier New', monospace !important;
  }

  /* Hide default Streamlit chrome */
  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding: 0 !important; max-width: 100% !important; }

  /* ── Header bar ── */
  .ss-header {
    background: #1a1a1a;
    border-bottom: 2px solid #f0a500;
    padding: 14px 28px;
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 0;
  }
  .ss-badge {
    background: #f0a500;
    color: #000;
    font-weight: 900;
    font-size: 11px;
    padding: 5px 10px;
    letter-spacing: 2px;
  }
  .ss-title { font-size: 18px; font-weight: 700; color: #fff; letter-spacing: 1px; }
  .ss-sub   { font-size: 10px; color: #555; letter-spacing: 1px; margin-top: 2px; }

  /* ── Issue banner ── */
  .ss-banner {
    background: #1a1200;
    border-left: 3px solid #f0a500;
    padding: 10px 20px;
    font-size: 11px;
    color: #b08020;
    margin: 0;
  }

  /* ── Section label ── */
  .ss-section {
    font-size: 9px;
    color: #444;
    letter-spacing: 3px;
    margin-bottom: 8px;
    margin-top: 4px;
  }

  /* ── Metric cards ── */
  .ss-metrics {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin-bottom: 0;
  }
  .ss-metric {
    background: #141414;
    border: 1px solid #252525;
    padding: 10px 18px;
    flex: 1;
    min-width: 120px;
    text-align: center;
  }
  .ss-metric-val { font-size: 26px; font-weight: 700; }
  .ss-metric-lbl { font-size: 9px; color: #555; letter-spacing: 2px; margin-top: 2px; }

  /* ── Row colours in dataframe ── */
  /* female row  = amber tint  handled via styler */

  /* ── Buttons ── */
  .stButton > button {
    background: #1e1e1e !important;
    color: #888 !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 0 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    letter-spacing: 1px !important;
    padding: 8px 18px !important;
    transition: all 0.15s !important;
  }
  .stButton > button:hover {
    background: #2a2a2a !important;
    color: #ccc !important;
    border-color: #3a3a3a !important;
  }

  /* Primary button override via class */
  .primary-btn > button {
    background: #f0a500 !important;
    color: #000 !important;
    border-color: #f0a500 !important;
  }
  .primary-btn > button:hover {
    background: #d49000 !important;
    border-color: #d49000 !important;
    color: #000 !important;
  }
  .green-btn > button {
    background: #1e3a28 !important;
    color: #4fca80 !important;
    border-color: #2a5a38 !important;
  }
  .green-btn > button:hover {
    background: #254a30 !important;
    color: #6fe090 !important;
  }

  /* ── File uploader ── */
  .stFileUploader { background: #141414; border: 1px dashed #2a2a2a; padding: 8px; }
  [data-testid="stFileUploaderDropzone"] {
    background: #0d0d0d !important;
    border: 1px dashed #333 !important;
    border-radius: 0 !important;
  }

  /* ── Checkbox ── */
  [data-testid="stCheckbox"] > label { font-size: 11px !important; color: #888 !important; }

  /* ── Multiselect ── */
  [data-testid="stMultiSelect"] > div > div {
    background: #0d0d0d !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 0 !important;
    font-size: 11px !important;
  }

  /* ── Dataframe ── */
  .stDataFrame { border: none !important; }
  [data-testid="stDataFrame"] > div {
    border: 1px solid #252525 !important;
    border-radius: 0 !important;
  }

  /* ── Text input ── */
  .stTextInput > div > div > input {
    background: #0d0d0d !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 0 !important;
    color: #d4d4d4 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important;
  }

  /* ── Tabs ── */
  [data-testid="stTabs"] button {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 10px !important;
    letter-spacing: 1px !important;
    color: #555 !important;
  }
  [data-testid="stTabs"] button[aria-selected="true"] {
    color: #f0a500 !important;
    border-bottom: 2px solid #f0a500 !important;
  }

  /* ── Expander ── */
  [data-testid="stExpander"] {
    background: #141414 !important;
    border: 1px solid #252525 !important;
    border-radius: 0 !important;
  }

  /* ── Status pill ── */
  .ss-status-ok  { color: #4fca80; font-size: 10px; }
  .ss-status-err { color: #e05555; font-size: 10px; }
  .ss-status-dim { color: #555;    font-size: 10px; }

  /* ── Diff table ── */
  .ss-diff td, .ss-diff th {
    padding: 5px 10px;
    font-size: 10px;
    border-bottom: 1px solid #1e1e1e;
    white-space: nowrap;
  }
  .ss-diff th { color: #444; font-size: 9px; letter-spacing: 1px; }
  .ss-diff .old { color: #f0a500; }
  .ss-diff .new { color: #4fca80; }
</style>
""", unsafe_allow_html=True)

# ── HELPERS ───────────────────────────────────────────────────────────────────
def safe(row, idx):
    return str(row[idx]).strip() if idx < len(row) else ""

def is_female(row):
    return safe(row, COL_INFO).startswith('3" Female Channel')

def extract_color(info):
    m = re.search(r",([A-Z]{2})$", info.strip())
    return m.group(1) if m else ""

def box_info(color):
    return f'3" Box Header,16\',{color}' if color else '3" Box Header,16\''

def parse_csv(text):
    lines = text.splitlines()
    header = None; rows = []
    for line in lines:
        s = line.strip()
        if not s or s.lower().startswith("sep="):
            continue
        f = s.split(";")
        if header is None:
            header = f
        else:
            rows.append(f)
    return header, rows

def write_output_csv(header, rows):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(header)
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode("utf-8")

def rows_to_df(header, rows):
    """Convert to a display DataFrame with key columns."""
    display = []
    for row in rows:
        display.append({
            "ID":          safe(row, COL_ID),
            "GROUP":       safe(row, COL_DATA1),
            "ORIENTATION": safe(row, COL_ORIENT),
            "PROFILE NAME": safe(row, COL_INFO),
            "BYD":         safe(row, COL_CODE),
            "TYPE":        safe(row, COL_DATA2),
        })
    return pd.DataFrame(display)

def colour_row(row, female_ids, selected_ids):
    rid = row["ID"]
    if rid in selected_ids:
        return ["background-color: #0d1f0d; color: #4fca80"] * len(row)
    if rid in female_ids:
        return ["background-color: #1a1500; color: #f0a500"] * len(row)
    return ["color: #383838"] * len(row)

SAMPLE = (
    "Sep=;\n"
    "id;ksn;ksnbar;ktn;ktnbar;l;r;code;info;width;height;trolley;box;"
    "orientation;reinf;reinfbar;pos;prono;offno;customer;date;nccode;"
    "isfix;colorcode;colorinfo;mainprofile;subcust;image;DATA1;DATA2;DATA3;DATA4;DATA5\n"
    "1;1;54864;1;25146;90;93;810300;3\" Female Channel 18',WH;0;0;0;0;right;0;0;0;0;0;Sunroom Designs;3/12/2026;;0;1;1 White;810300;Deskin;;S1;Starter;;;\n"
    "2;1;54864;1;25103;93;90;810300;3\" Female Channel 18',WH;0;0;0;0;leftmod;0;0;0;0;0;Sunroom Designs;3/12/2026;;0;1;1 White;810300;Deskin;;W3;PVC;42 13/16\";54 15/16\";\n"
    "3;1;54864;1;24493;90;93;810300;3\" Female Channel 18',WH;0;0;0;0;rightmod;0;0;0;0;0;Sunroom Designs;3/12/2026;;0;1;1 White;810300;Deskin;;W3;PVC;42 13/16\";54 15/16\";\n"
    "4;1;48768;1;10890;90;90;810311;3\" Box Header,16',WH;0;0;0;0;header;0;0;0;0;0;Sunroom Designs;3/12/2026;;0;1;1 White;810311;Deskin;;W3;Header;42 13/16\";54 15/16\";\n"
    "5;1;48768;1;10890;90;90;810311;3\" Box Header,16',WH;0;0;0;0;header;0;0;0;0;0;Sunroom Designs;3/12/2026;;0;1;1 White;810311;Deskin;;W3;Header;42 13/16\";54 15/16\";\n"
    "6;1;54864;1;24486;93;90;810305;3\" Male Channel 18',WH;0;0;0;0;leftmod;0;0;0;0;0;Sunroom Designs;3/12/2026;;0;1;1 White;810305;Deskin;;W4;PVC;42 13/16\";54 15/16\";\n"
    "7;1;48768;1;10890;90;90;810300;3\" Female Channel 18',WH;0;0;0;0;header;0;0;0;0;0;Sunroom Designs;3/12/2026;;0;1;1 White;810300;Deskin;;W4;Header;42 13/16\";54 15/16\";\n"
    "8;1;48768;1;10890;90;90;810300;3\" Female Channel 18',WH;0;0;0;0;header;0;0;0;0;0;Sunroom Designs;3/12/2026;;0;1;1 White;810300;Deskin;;W4;Header;42 13/16\";54 15/16\";\n"
    "9;1;54864;1;23856;93;90;810302;3\" Female Channel 18',DR;0;0;0;0;leftmod;0;0;0;0;0;Sunroom Designs;3/12/2026;;0;1;1 DR;810302;Deskin;;W5;PVC;42 13/16\";54 15/16\";\n"
    "10;1;54864;1;23246;90;93;810303;3\" Female Channel 18',BR;0;0;0;0;rightmod;0;0;0;0;0;Sunroom Designs;3/12/2026;;0;1;1 BR;810303;Deskin;;W5;PVC;42 13/16\";54 15/16\";\n"
)

# ── SESSION STATE ─────────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "header":     None,
        "rows":       [],
        "female_ids": set(),
        "selected":   set(),
        "output_csv": None,
        "source_name": "",
        "byd_map":    {k: v[0] for k, v in DEFAULT_BYD_MAP.items()},
        "converted":  False,
        "diff_rows":  [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()
S = st.session_state

def ingest(text, name=""):
    header, rows = parse_csv(text)
    S.header     = header
    S.rows       = rows
    S.source_name = name
    S.female_ids = {safe(r, COL_ID) for r in rows if is_female(r)}
    S.selected   = set(S.female_ids)   # pre-select all female rows
    S.output_csv = None
    S.converted  = False
    S.diff_rows  = []

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="ss-header">
  <div class="ss-badge">SUNSPACE</div>
  <div>
    <div class="ss-title">BOX HEADER CSV EDITOR</div>
    <div class="ss-sub">DEALER DESKTOP &nbsp;→&nbsp; SC220 &nbsp;·&nbsp; v5.0</div>
  </div>
</div>
<div class="ss-banner">
  ⚠&nbsp; ISSUE: Dealer Desktop writes <b>Female Channel BYD</b> for all rows.
  This tool corrects the profile name and BYD code so the SC220 cuts the right extrusion.
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height:12px'/>", unsafe_allow_html=True)

# ── MAIN LAYOUT ───────────────────────────────────────────────────────────────
left, right = st.columns([2, 1], gap="large")

with left:
    # ── File upload ──────────────────────────────────────────────────────────
    st.markdown('<div class="ss-section">── LOAD FILE</div>', unsafe_allow_html=True)

    col_up, col_sample = st.columns([3, 1])
    with col_up:
        uploaded = st.file_uploader("", type=["csv", "txt"],
                                    label_visibility="collapsed")
        if uploaded:
            text = uploaded.read().decode("utf-8", errors="replace")
            ingest(text, uploaded.name)
            st.rerun()

    with col_sample:
        st.markdown('<div style="height:28px"/>', unsafe_allow_html=True)
        if st.button("LOAD SAMPLE"):
            ingest(SAMPLE, "sample_file.csv")
            st.rerun()

    # ── Loaded info ──────────────────────────────────────────────────────────
    if S.rows:
        fem  = len(S.female_ids)
        sel  = len(S.selected)
        tot  = len(S.rows)

        st.markdown(f"""
        <div class="ss-metrics">
          <div class="ss-metric">
            <div class="ss-metric-val" style="color:#888">{tot}</div>
            <div class="ss-metric-lbl">TOTAL ROWS</div>
          </div>
          <div class="ss-metric">
            <div class="ss-metric-val" style="color:#f0a500">{fem}</div>
            <div class="ss-metric-lbl">FEMALE CHANNEL</div>
          </div>
          <div class="ss-metric">
            <div class="ss-metric-val" style="color:#4fca80">{sel}</div>
            <div class="ss-metric-lbl">SELECTED</div>
          </div>
          <div class="ss-metric">
            <div class="ss-metric-val" style="color:#555">{tot - fem}</div>
            <div class="ss-metric-lbl">UNCHANGED</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height:14px'/>", unsafe_allow_html=True)

with right:
    if S.rows:
        # ── Selection controls ───────────────────────────────────────────────
        st.markdown('<div class="ss-section">── SELECTION</div>',
                    unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("☑  ALL FEMALE", use_container_width=True):
                S.selected = set(S.female_ids); st.rerun()
        with c2:
            if st.button("☐  DESELECT ALL", use_container_width=True):
                S.selected = set(); st.rerun()

        st.markdown("<div style='height:10px'/>", unsafe_allow_html=True)

        # ── Row multiselect ──────────────────────────────────────────────────
        st.markdown('<div class="ss-section">── SELECT ROWS TO CONVERT</div>',
                    unsafe_allow_html=True)
        st.caption("Only Female Channel rows are listed below.")

        female_options = [
            f"{safe(r, COL_ID):>3} │ {safe(r, COL_DATA1):<4} │ {safe(r, COL_ORIENT):<10} │ {safe(r, COL_INFO)[:38]}"
            for r in S.rows if is_female(r)
        ]
        id_map = {
            f"{safe(r, COL_ID):>3} │ {safe(r, COL_DATA1):<4} │ {safe(r, COL_ORIENT):<10} │ {safe(r, COL_INFO)[:38]}": safe(r, COL_ID)
            for r in S.rows if is_female(r)
        }
        current_sel_labels = [lbl for lbl, rid in id_map.items() if rid in S.selected]

        new_sel_labels = st.multiselect(
            "",
            options=female_options,
            default=current_sel_labels,
            label_visibility="collapsed",
            key="row_multiselect",
        )
        new_sel_ids = {id_map[lbl] for lbl in new_sel_labels}
        if new_sel_ids != S.selected:
            S.selected = new_sel_ids

        st.markdown("<div style='height:10px'/>", unsafe_allow_html=True)

        # ── Filter ───────────────────────────────────────────────────────────
        st.markdown('<div class="ss-section">── FILTER TABLE</div>',
                    unsafe_allow_html=True)
        filt = st.text_input("", placeholder="Search any column...",
                             label_visibility="collapsed", key="filter_input")

        st.markdown("<div style='height:10px'/>", unsafe_allow_html=True)

        # ── BYD map editor ───────────────────────────────────────────────────
        with st.expander("⚙  BYD CODE MAPPING", expanded=False):
            st.markdown('<div class="ss-section">FEMALE CHANNEL BYD  →  BOX HEADER BYD</div>',
                        unsafe_allow_html=True)
            for old_byd, (default_new, label) in DEFAULT_BYD_MAP.items():
                col_l, col_r = st.columns([3, 1])
                with col_l:
                    st.markdown(
                        f'<span style="color:#555;font-size:10px">{label}</span>'
                        f'&nbsp;&nbsp;<span style="color:#f0a500;font-size:10px;font-weight:700">{old_byd}</span>'
                        f'&nbsp;→',
                        unsafe_allow_html=True)
                with col_r:
                    val = st.text_input(f"byd_{old_byd}", value=S.byd_map.get(old_byd, default_new),
                                        label_visibility="collapsed", key=f"byd_input_{old_byd}")
                    S.byd_map[old_byd] = val.strip()

# ── TABLE ─────────────────────────────────────────────────────────────────────
if S.rows:
    st.markdown('<div class="ss-section" style="padding: 0 0 6px 0">── CSV ROWS</div>',
                unsafe_allow_html=True)

    df = rows_to_df(S.header, S.rows)

    # Apply filter
    filt_str = st.session_state.get("filter_input", "")
    if filt_str:
        mask = df.apply(lambda row: row.astype(str).str.contains(
            filt_str, case=False).any(), axis=1)
        df_show = df[mask]
    else:
        df_show = df

    # Colour rows
    def highlight(row):
        rid = row["ID"]
        if rid in S.selected:
            return ["background-color:#0d1f0d; color:#4fca80"] * len(row)
        if rid in S.female_ids:
            return ["background-color:#1a1500; color:#f0a500"] * len(row)
        return ["color:#383838; background-color:#111"] * len(row)

    styled = df_show.style.apply(highlight, axis=1).set_properties(
        **{"font-size": "10px", "font-family": "'JetBrains Mono',monospace"}
    ).hide(axis="index")

    st.dataframe(styled, use_container_width=True, height=min(600, 28 * len(df_show) + 40))

    st.markdown("""
    <div style="font-size:9px; color:#444; margin-top:4px; letter-spacing:1px">
      🟡 AMBER = Female Channel (eligible for conversion) &nbsp;·&nbsp;
      🟢 GREEN = Selected for conversion
    </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:16px'/>", unsafe_allow_html=True)

    # ── ACTION ROW ────────────────────────────────────────────────────────────
    ac1, ac2, ac3, ac4 = st.columns([2, 2, 2, 4])

    with ac1:
        sel_count = len(S.selected)
        disabled  = sel_count == 0
        label     = f"CONVERT  ({sel_count})" if sel_count else "CONVERT"
        st.markdown('<div class="primary-btn">', unsafe_allow_html=True)
        if st.button(label, use_container_width=True, disabled=disabled):
            # Run conversion
            converted_rows = []
            diff = []
            for row in S.rows:
                row = list(row)
                while len(row) <= max(COL_CODE, COL_INFO, COL_MAIN):
                    row.append("")
                rid = safe(row, COL_ID)
                if rid in S.selected and is_female(row):
                    old_byd  = safe(row, COL_CODE)
                    new_byd  = S.byd_map.get(old_byd, old_byd)
                    old_info = safe(row, COL_INFO)
                    new_info = box_info(extract_color(old_info))
                    row[COL_INFO] = new_info
                    row[COL_CODE] = new_byd
                    row[COL_MAIN] = new_byd
                    diff.append((rid, safe(row, COL_DATA1),
                                 old_byd, new_byd, old_info, new_info))
                converted_rows.append(row)
            S.output_csv  = write_output_csv(S.header, converted_rows)
            S.converted   = True
            S.diff_rows   = diff
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with ac2:
        if S.converted and S.output_csv:
            name = S.source_name or "output.csv"
            dl_name = "corrected_" + name
            st.markdown('<div class="green-btn">', unsafe_allow_html=True)
            st.download_button(
                "↓  DOWNLOAD CSV",
                data=S.output_csv,
                file_name=dl_name,
                mime="text/csv",
                use_container_width=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)

    with ac3:
        if st.button("CLEAR FILE", use_container_width=True):
            for k in ["header","rows","female_ids","selected","output_csv",
                      "source_name","converted","diff_rows"]:
                del st.session_state[k]
            st.rerun()

    with ac4:
        if S.converted:
            fixed = len(S.diff_rows)
            st.markdown(
                f'<div class="ss-status-ok" style="padding:10px 0">'
                f'✓ &nbsp;{fixed} rows converted → Box Header &nbsp;·&nbsp; '
                f'Download ready &nbsp;·&nbsp; File: corrected_{S.source_name or "output.csv"}'
                f'</div>',
                unsafe_allow_html=True)
        elif S.rows:
            st.markdown(
                f'<div class="ss-status-dim" style="padding:10px 0">'
                f'Loaded: {S.source_name or "content"} &nbsp;·&nbsp; '
                f'Select rows and click CONVERT'
                f'</div>',
                unsafe_allow_html=True)

    # ── DIFF TABLE ────────────────────────────────────────────────────────────
    if S.converted and S.diff_rows:
        st.markdown("<div style='height:16px'/>", unsafe_allow_html=True)
        with st.expander(f"📋  CONVERSION DIFF  ({len(S.diff_rows)} rows changed)", expanded=True):
            rows_html = "".join(
                f'<tr>'
                f'<td style="color:#555">{rid}</td>'
                f'<td style="color:#555">{grp}</td>'
                f'<td class="old">{old_byd}</td>'
                f'<td class="new">→  {new_byd}</td>'
                f'<td class="old" style="max-width:260px;overflow:hidden;text-overflow:ellipsis">{old_info}</td>'
                f'<td class="new">→  {new_info}</td>'
                f'</tr>'
                for rid, grp, old_byd, new_byd, old_info, new_info in S.diff_rows
            )
            st.markdown(f"""
            <table class="ss-diff" style="width:100%;border-collapse:collapse">
              <tr>
                <th>ID</th><th>GRP</th>
                <th>OLD BYD</th><th>NEW BYD</th>
                <th>OLD PROFILE</th><th>NEW PROFILE</th>
              </tr>
              {rows_html}
            </table>
            """, unsafe_allow_html=True)
