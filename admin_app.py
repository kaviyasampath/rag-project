"""
admin_app.py — Admin Knowledge Base Manager
Run on port 8502 (never expose this publicly).
Loads reference SSRs into the shared naac_vector_db/ folder.
Institutions using app.py on port 8501 instantly benefit from updates.

Run with:
    streamlit run admin_app.py --server.port 8502
"""
import streamlit as st
from pathlib import Path
from datetime import datetime

st.set_page_config(
    page_title="NAAC Admin — Knowledge Base Manager",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Source+Sans+3:wght@300;400;600&display=swap');
:root {
    --bg: #0F0F14; --surface: #1A1A24; --surface2: #22222F;
    --red: #E05A5A; --red-dim: rgba(224,90,90,0.15);
    --green: #4CAF87; --green-dim: rgba(76,175,135,0.12);
    --gold: #C9A84C; --gold-light: #E8C97A; --gold-dim: rgba(201,168,76,0.12);
    --text: #E8E4DC; --muted: #8A9BB0;
}
html, body, [class*="css"] { font-family: 'Source Sans 3', sans-serif; color: var(--text); }
.stApp { background: var(--bg); }
[data-testid="stSidebar"] { background: var(--surface) !important; border-right: 1px solid rgba(224,90,90,0.2); }
h1, h2, h3 { font-family: 'Playfair Display', serif; }
.stButton > button {
    background: linear-gradient(135deg, #C9A84C, #A8872E);
    color: #0F0F14; border: none; font-weight: 700;
    padding: 0.6rem 1.4rem; border-radius: 4px; transition: all 0.2s;
}
.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 20px rgba(201,168,76,0.4); }
.stButton > button[kind="secondary"] {
    background: var(--red-dim); color: var(--red);
    border: 1px solid rgba(224,90,90,0.3);
}
[data-testid="stFileUploader"] {
    background: var(--surface2); border: 2px dashed rgba(201,168,76,0.3); border-radius: 8px; padding: 1rem;
}
.admin-header {
    background: linear-gradient(135deg, #1A0A0A, #2A1A1A);
    border: 1px solid rgba(224,90,90,0.3); border-radius: 12px;
    padding: 1.5rem 2rem; margin-bottom: 2rem;
    display: flex; align-items: center; gap: 1rem;
}
.admin-header h1 { color: var(--red); margin: 0; font-size: 1.8rem; }
.admin-header p  { color: var(--muted); margin: 0; font-size: 0.9rem; }
.stat-card {
    background: var(--surface); border: 1px solid rgba(201,168,76,0.2);
    border-radius: 10px; padding: 1.5rem; text-align: center;
}
.stat-card .number { font-size: 2.5rem; color: var(--gold); font-family: 'Playfair Display', serif; font-weight: 700; }
.stat-card .label  { font-size: 0.8rem; color: var(--muted); text-transform: uppercase; letter-spacing: 1.5px; margin-top: 6px; }
.doc-row {
    background: var(--surface); border: 1px solid rgba(201,168,76,0.1);
    border-radius: 8px; padding: 0.8rem 1.2rem; margin: 0.4rem 0;
    display: flex; justify-content: space-between; align-items: center;
}
.tag {
    display: inline-block; padding: 2px 8px; border-radius: 10px;
    font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;
    background: var(--gold-dim); color: var(--gold-light);
    border: 1px solid rgba(201,168,76,0.25); margin-left: 6px;
}
.warning-box {
    background: var(--red-dim); border: 1px solid rgba(224,90,90,0.3);
    border-radius: 8px; padding: 1rem 1.2rem; color: #E8B4B4; font-size: 0.88rem;
}
.success-box {
    background: var(--green-dim); border: 1px solid rgba(76,175,135,0.3);
    border-radius: 8px; padding: 1rem 1.2rem; color: #A8DFC8; font-size: 0.88rem;
}
.info-box {
    background: var(--gold-dim); border: 1px solid rgba(201,168,76,0.25);
    border-radius: 8px; padding: 1rem 1.2rem; color: var(--gold-light); font-size: 0.88rem;
}
hr { border-color: rgba(201,168,76,0.1); }
</style>
""", unsafe_allow_html=True)

from rag_engine import NAACRagEngine
from utils import check_api_key

# ── Session state ──────────────────────────────────────────────────────────
if "admin_engine" not in st.session_state:
    st.session_state.admin_engine = None
if "upload_log" not in st.session_state:
    st.session_state.upload_log = []

# ══════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🔧 Admin Config")
    st.markdown("---")

    st.markdown("**Gemini API Key**")
    api_key = st.text_input("", type="password", placeholder="AIza...",
                             label_visibility="collapsed")
    if api_key:
        valid = check_api_key(api_key)
        color = "#4CAF87" if valid else "#E05A5A"
        label = "✓ Valid" if valid else "✗ Invalid"
        st.markdown(f'<span style="font-size:0.8rem;color:{color};font-weight:600;">{label}</span>', unsafe_allow_html=True)

        if valid and not st.session_state.admin_engine:
            try:
                st.session_state.admin_engine = NAACRagEngine(api_key=api_key)
            except Exception:
                pass

    st.markdown("---")
    st.markdown("""<div class="warning-box">
        🔒 <strong>Admin access only.</strong><br>
        Do not share this URL with institutions.<br>
        Run on port 8502 (internal only).
    </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Live DB stats
    if st.session_state.admin_engine:
        ref_count = st.session_state.admin_engine.reference_count()
        st.markdown(f'<div class="stat-card"><div class="number">{ref_count}</div><div class="label">Reference Chunks in DB</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:var(--muted);font-size:0.85rem;">Enter API key to see DB stats.</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.caption("NAAC Admin Panel · Internal Use Only")

# ══════════════════════════════════════════════════════════════════════════
# MAIN CONTENT
# ══════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="admin-header">
    <div>
        <h1>🔧 Knowledge Base Manager</h1>
        <p>Load reference SSRs from top-rated institutions into the shared knowledge base. 
           All institutions using the system instantly benefit from updates.</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ── How it works ──────────────────────────────────────────────────────────
with st.expander("ℹ️ How this works", expanded=False):
    st.markdown("""
    **Architecture:**
    ```
    admin_app.py (port 8502, you)          app.py (port 8501, institutions)
            │                                       │
            ▼                                       ▼
    Upload reference SSRs          Upload their own documents
            │                                       │
            ▼                                       ▼
    naac_vector_db/ ◄──── shared on disk ────► naac_vector_db/
    (persisted, survives restarts)         (read at generation time)
    ```

    **Workflow:**
    1. Download public SSRs from A++ / A+ institutions at [naac.gov.in](https://naac.gov.in)
    2. Upload them here — they get embedded and stored permanently
    3. Institutions using `app.py` automatically get better outputs immediately
    4. You can add more SSRs anytime without restarting either app
    """)

st.markdown("---")

# ── Upload Section ─────────────────────────────────────────────────────────
st.markdown("### 📥 Add Reference SSRs to Knowledge Base")

col1, col2 = st.columns([3, 2], gap="large")

with col1:
    ref_files = st.file_uploader(
        "Upload SSR documents (PDF, DOCX, or TXT)",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        key="ref_upload"
    )

    if ref_files:
        st.markdown(f"**{len(ref_files)} file(s) ready to index:**")
        for f in ref_files:
            size_kb = round(len(f.getvalue()) / 1024, 1)
            st.markdown(f'<div class="doc-row">📄 {f.name} <span class="tag">{size_kb} KB</span></div>', unsafe_allow_html=True)

    if st.button("📥 Add to Knowledge Base", use_container_width=True):
        if not api_key:
            st.error("Enter your Gemini API key in the sidebar.")
        elif not ref_files:
            st.error("Please upload at least one SSR file.")
        else:
            with st.spinner(f"Indexing {len(ref_files)} file(s)..."):
                try:
                    engine = st.session_state.admin_engine or NAACRagEngine(api_key=api_key)
                    tmp_dir = Path("/tmp/naac_ref")
                    tmp_dir.mkdir(exist_ok=True)
                    paths = []
                    for f in ref_files:
                        fp = tmp_dir / f.name
                        fp.write_bytes(f.getvalue())
                        paths.append(str(fp))
                    count = engine.ingest_reference(paths)
                    total = engine.reference_count()
                    st.session_state.admin_engine = engine

                    # Log the upload
                    st.session_state.upload_log.append({
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "files": [f.name for f in ref_files],
                        "chunks": count,
                        "total": total,
                    })

                    st.markdown(f"""<div class="success-box">
                        ✅ <strong>Successfully indexed {count} chunks</strong> from {len(ref_files)} file(s).<br>
                        Total in knowledge base: <strong>{total} chunks</strong><br>
                        Institutions will benefit from this immediately.
                    </div>""", unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Indexing failed: {e}")

with col2:
    st.markdown("**💡 Where to get SSRs**")
    st.markdown("""<div class="info-box">
        <strong>naac.gov.in</strong><br>
        → Accredited Institutions<br>
        → Filter: Grade A++ or A+<br>
        → Download SSR PDF<br><br>
        Aim for <strong>5–10 SSRs</strong> from diverse institution types 
        (engineering, arts, science, deemed universities) for best coverage.
    </div>""", unsafe_allow_html=True)

    st.markdown("**🎯 Recommended Criteria Coverage**")
    criteria_short = ["Curricular Aspects", "Teaching & Learning", "Research",
                      "Infrastructure", "Student Support", "Governance", "Institutional Values"]
    for c in criteria_short:
        st.markdown(f"✓ {c}")

st.markdown("---")

# ── Upload History ─────────────────────────────────────────────────────────
if st.session_state.upload_log:
    st.markdown("### 📋 Upload History (this session)")
    for entry in reversed(st.session_state.upload_log):
        files_str = ", ".join(entry["files"])
        st.markdown(f"""<div class="doc-row">
            <span>🕒 <strong>{entry['time']}</strong> — {files_str}</span>
            <span><span class="tag">+{entry['chunks']} chunks</span> <span class="tag">total: {entry['total']}</span></span>
        </div>""", unsafe_allow_html=True)
    st.markdown("---")

# ── Danger Zone ────────────────────────────────────────────────────────────
st.markdown("### ⚠️ Danger Zone")
st.markdown('<div class="warning-box">Clearing the knowledge base will affect ALL institutions immediately. This cannot be undone.</div>', unsafe_allow_html=True)
st.markdown("")

col_a, col_b = st.columns([1, 3])
with col_a:
    confirm = st.checkbox("I understand — clear the entire knowledge base")
with col_b:
    if st.button("🗑️ Clear Knowledge Base", disabled=not confirm):
        try:
            engine = st.session_state.admin_engine or NAACRagEngine(api_key=api_key or "dummy")
            engine.clear_reference_db()
            st.session_state.upload_log = []
            st.success("Knowledge base cleared. Reference count is now 0.")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
