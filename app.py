"""
app.py — Institution-facing NAAC SSR Generator
Deploy this publicly on port 8501.
Reads from the shared naac_vector_db/ folder (populated by admin_app.py).
"""
import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="NAAC SSR Generator",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Source+Sans+3:wght@300;400;600&display=swap');
:root {
    --navy: #0B1628; --navy-mid: #152238; --navy-light: #1E3352;
    --gold: #C9A84C; --gold-light: #E8C97A;
    --text: #E8E4DC; --muted: #8A9BB0;
    --green: #4CAF87; --red: #E05A5A;
}
html, body, [class*="css"] { font-family: 'Source Sans 3', sans-serif; color: var(--text); }
.stApp { background: var(--navy); }
[data-testid="stSidebar"] { background: var(--navy-mid) !important; border-right: 1px solid rgba(201,168,76,0.2); }
h1, h2, h3 { font-family: 'Playfair Display', serif; }
.stButton > button {
    background: linear-gradient(135deg, var(--gold), #A8872E);
    color: var(--navy); border: none; font-weight: 600;
    padding: 0.6rem 1.4rem; border-radius: 4px; transition: all 0.2s;
}
.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(201,168,76,0.4); }
[data-testid="stFileUploader"] {
    background: var(--navy-light); border: 2px dashed rgba(201,168,76,0.3); border-radius: 8px; padding: 1rem;
}
.stTextArea > div > div > textarea {
    background: var(--navy-light); color: var(--text);
    border: 1px solid rgba(201,168,76,0.2); font-size: 0.95rem; line-height: 1.6;
}
.naac-card {
    background: var(--navy-mid); border: 1px solid rgba(201,168,76,0.2);
    border-left: 4px solid var(--gold); border-radius: 8px; padding: 1.2rem 1.5rem; margin: 0.8rem 0;
}
.naac-card h4 { color: var(--gold-light); font-family: 'Playfair Display', serif; margin: 0 0 0.5rem 0; }
.naac-card p  { color: var(--muted); margin: 0; font-size: 0.9rem; line-height: 1.5; }
.status-badge {
    display: inline-block; padding: 2px 10px; border-radius: 12px;
    font-size: 0.78rem; font-weight: 600; letter-spacing: 0.5px; text-transform: uppercase;
}
.badge-success { background: rgba(76,175,135,0.15); color: var(--green); border: 1px solid rgba(76,175,135,0.3); }
.badge-warning { background: rgba(201,168,76,0.15); color: var(--gold-light); border: 1px solid rgba(201,168,76,0.3); }
.badge-error   { background: rgba(224,90,90,0.15); color: var(--red); border: 1px solid rgba(224,90,90,0.3); }
.compliance-item { padding: 0.6rem 1rem; margin: 0.3rem 0; border-radius: 6px; font-size: 0.88rem; }
.compliance-pass { background: rgba(76,175,135,0.08); border-left: 3px solid var(--green); }
.compliance-fail { background: rgba(224,90,90,0.08); border-left: 3px solid var(--red); }
.compliance-warn { background: rgba(201,168,76,0.08); border-left: 3px solid var(--gold); }
.header-banner {
    background: linear-gradient(135deg, var(--navy-mid), var(--navy-light));
    border: 1px solid rgba(201,168,76,0.25); border-radius: 12px;
    padding: 2rem 2.5rem; margin-bottom: 2rem; text-align: center;
}
.header-banner h1 { color: var(--gold-light); font-size: 2.2rem; margin: 0 0 0.5rem 0; }
.header-banner p  { color: var(--muted); font-size: 1rem; margin: 0; }
.metric-box {
    background: var(--navy-mid); border: 1px solid rgba(201,168,76,0.2);
    border-radius: 8px; padding: 1rem; text-align: center;
}
.metric-box .number { font-size: 1.8rem; color: var(--gold); font-family: 'Playfair Display', serif; }
.metric-box .label  { font-size: 0.78rem; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }
.kb-status-ok   { background: rgba(76,175,135,0.08); border: 1px solid rgba(76,175,135,0.25); border-radius: 8px; padding: 0.7rem 1rem; font-size: 0.85rem; color: var(--green); }
.kb-status-warn { background: rgba(201,168,76,0.08); border: 1px solid rgba(201,168,76,0.25); border-radius: 8px; padding: 0.7rem 1rem; font-size: 0.85rem; color: var(--gold-light); }
hr { border-color: rgba(201,168,76,0.15); }
[data-testid="stExpander"] { background: var(--navy-mid); border: 1px solid rgba(201,168,76,0.2); border-radius: 8px; }
.stTabs [data-baseweb="tab"] { color: var(--muted); }
.stTabs [data-baseweb="tab"][aria-selected="true"] { color: var(--gold-light); border-bottom-color: var(--gold); }
</style>
""", unsafe_allow_html=True)

from rag_engine import NAACRagEngine
from utils import check_api_key

# ── Session state ──────────────────────────────────────────────────────────
for key, val in {"engine": None, "docs_loaded": 0, "generated_sections": {}}.items():
    if key not in st.session_state:
        st.session_state[key] = val

CRITERIA = {
    "Criterion 1 – Curricular Aspects": "curriculum design, programme outcomes, academic flexibility, feedback on curriculum",
    "Criterion 2 – Teaching, Learning and Evaluation": "student enrolment, teaching methods, assessment, teacher quality, student performance",
    "Criterion 3 – Research, Innovations and Extension": "research promotion, resource mobilisation, innovation ecosystem, extension activities",
    "Criterion 4 – Infrastructure and Learning Resources": "physical facilities, library, IT infrastructure, maintenance",
    "Criterion 5 – Student Support and Progression": "student support, scholarships, career guidance, alumni engagement",
    "Criterion 6 – Governance, Leadership and Management": "institutional vision, governance, financial management, strategy deployment",
    "Criterion 7 – Institutional Values and Best Practices": "gender equity, environment, inclusivity, best practices, institutional distinctiveness",
}

# ══════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## ⚙️ Setup")
    st.markdown("---")

    st.markdown("**Gemini API Key**")
    api_key = st.text_input("", type="password", placeholder="AIza...",
                             help="Get a free key at https://aistudio.google.com",
                             label_visibility="collapsed")
    if api_key:
        badge = "badge-success" if check_api_key(api_key) else "badge-error"
        label = "✓ Valid" if check_api_key(api_key) else "✗ Invalid format"
        st.markdown(f'<span class="status-badge {badge}">{label}</span>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**Institution Name**")
    institution_name = st.text_input("", placeholder="e.g., RIT Chennai",
                                      label_visibility="collapsed", key="inst_name")

    st.markdown("**📁 Upload Your Documents**")
    st.caption("AQAR reports, faculty data, student records, audit reports — PDF, DOCX, or TXT")
    inst_files = st.file_uploader("", type=["pdf", "docx", "txt"],
                                   accept_multiple_files=True,
                                   key="inst_upload",
                                   label_visibility="collapsed")

    if st.button("🗄️ Process My Documents", use_container_width=True):
        if not api_key:
            st.error("Enter your Gemini API key above.")
        elif not inst_files:
            st.error("Please upload your institution's documents.")
        else:
            with st.spinner("Indexing your documents..."):
                try:
                    engine = NAACRagEngine(api_key=api_key, institution_name=institution_name)
                    tmp_dir = Path("/tmp/naac_inst")
                    tmp_dir.mkdir(exist_ok=True)
                    paths = []
                    for f in inst_files:
                        fp = tmp_dir / f.name
                        fp.write_bytes(f.read())
                        paths.append(str(fp))
                    count = engine.ingest_institutional(paths)
                    ref_count = engine.reference_count()
                    st.session_state.engine = engine
                    st.session_state.docs_loaded = count
                    st.success(f"✓ {count} chunks indexed from {len(inst_files)} file(s)")
                    if ref_count > 0:
                        st.markdown(f'<div class="kb-status-ok">📚 Knowledge base ready — {ref_count} reference chunks loaded</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="kb-status-warn">⚠️ Knowledge base is empty. Contact your admin.</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Error: {e}")

    st.markdown("---")
    if st.session_state.docs_loaded > 0:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f'<div class="metric-box"><div class="number">{st.session_state.docs_loaded}</div><div class="label">Your Chunks</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="metric-box"><div class="number">{len(st.session_state.generated_sections)}</div><div class="label">Generated</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.caption("NAAC SSR Generator · RAG + Gemini")

# ══════════════════════════════════════════════════════════════════════════
# MAIN CONTENT
# ══════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="header-banner">
    <h1>🎓 NAAC SSR Generator</h1>
    <p>Upload your institutional documents and generate NAAC-compliant Self-Study Report sections instantly</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📄 Generate SSR", "✅ Compliance Check", "📋 Full Report"])

# ── Tab 1: Generate ────────────────────────────────────────────────────────
with tab1:
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.markdown("### Select NAAC Criterion")
        selected_criterion = st.selectbox("", list(CRITERIA.keys()), label_visibility="collapsed")
        st.markdown(f"""<div class="naac-card">
            <h4>{selected_criterion.split('–')[0].strip()}</h4>
            <p>{CRITERIA[selected_criterion]}</p>
        </div>""", unsafe_allow_html=True)

        st.markdown("### Additional Notes *(optional)*")
        extra_context = st.text_area("",
            placeholder="e.g., Highlight 2022–23 data. Focus on industry collaborations.",
            height=100, label_visibility="collapsed")

        generate_btn = st.button("⚡ Generate SSR Section", use_container_width=True)

    with col_right:
        st.markdown("### Generated Content")
        if generate_btn:
            if not st.session_state.engine:
                st.error("Please upload your documents and click 'Process My Documents' in the sidebar first.")
            else:
                with st.spinner("Retrieving evidence and generating content..."):
                    try:
                        result = st.session_state.engine.generate_section(
                            criterion=selected_criterion,
                            criterion_hint=CRITERIA[selected_criterion],
                            extra_context=extra_context
                        )
                        st.session_state.generated_sections[selected_criterion] = result
                        st.success("Section generated!")
                    except Exception as e:
                        st.error(f"Generation failed: {e}")

        if selected_criterion in st.session_state.generated_sections:
            result = st.session_state.generated_sections[selected_criterion]
            st.markdown('<span class="status-badge badge-success">✓ Generated</span>', unsafe_allow_html=True)
            st.markdown("---")
            edited = st.text_area("Edit if needed:", value=result["content"], height=420)
            if edited != result["content"]:
                st.session_state.generated_sections[selected_criterion]["content"] = edited
            with st.expander("📚 Evidence Sources Used"):
                for i, s in enumerate(result.get("sources", []), 1):
                    st.markdown(f"**{i}.** *{s.get('source', '')}*")
                    st.caption(s.get("text", "")[:300] + "...")
                    st.divider()
        else:
            st.markdown("""<div class="naac-card" style="text-align:center; padding:3rem;">
                <p style="font-size:2rem; margin-bottom:0.5rem;">📝</p>
                <p>Select a criterion and click Generate to produce your SSR section.</p>
            </div>""", unsafe_allow_html=True)

# ── Tab 2: Compliance ──────────────────────────────────────────────────────
with tab2:
    st.markdown("### Compliance & Quality Check")
    if not st.session_state.generated_sections:
        st.info("Generate at least one SSR section first.")
    else:
        check_criterion = st.selectbox("Select section to check",
                                        list(st.session_state.generated_sections.keys()),
                                        key="compliance_select")
        if st.button("🔍 Run Compliance Check"):
            with st.spinner("Analysing content..."):
                content = st.session_state.generated_sections[check_criterion]["content"]
                report  = st.session_state.engine.compliance_check(content, check_criterion)

            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.markdown(f'<div class="metric-box"><div class="number">{report["score"]}%</div><div class="label">Score</div></div>', unsafe_allow_html=True)
            with col_b:
                st.markdown(f'<div class="metric-box"><div class="number">{report["passes"]}</div><div class="label">Passed</div></div>', unsafe_allow_html=True)
            with col_c:
                st.markdown(f'<div class="metric-box"><div class="number">{report["failures"]}</div><div class="label">Issues</div></div>', unsafe_allow_html=True)

            st.markdown("---")
            for item in report.get("checks", []):
                cls  = "compliance-pass" if item["status"] == "pass" else "compliance-fail" if item["status"] == "fail" else "compliance-warn"
                icon = "✅" if item["status"] == "pass" else "❌" if item["status"] == "fail" else "⚠️"
                st.markdown(f'<div class="compliance-item {cls}">{icon} <strong>{item["check"]}</strong><br><span style="color:#8A9BB0;font-size:0.85rem;">{item["detail"]}</span></div>', unsafe_allow_html=True)

            if report.get("suggestions"):
                st.markdown("#### 💡 Suggestions")
                for s in report["suggestions"]:
                    st.markdown(f"- {s}")

# ── Tab 3: Full Report ─────────────────────────────────────────────────────
with tab3:
    st.markdown("### Full SSR Draft")
    if not st.session_state.generated_sections:
        st.info("Generate SSR sections in the 'Generate SSR' tab.")
    else:
        progress = len(st.session_state.generated_sections)
        st.markdown(f"**Progress:** {progress}/{len(CRITERIA)} criteria completed")
        st.progress(progress / len(CRITERIA))
        st.markdown("---")
        for criterion, data in st.session_state.generated_sections.items():
            with st.expander(f"📌 {criterion}", expanded=False):
                st.write(data["content"])
        st.markdown("---")
        inst_name = st.session_state.get("inst_name", "Institution")
        full_report = f"NAAC SELF-STUDY REPORT\n{inst_name}\n{'='*60}\n\n"
        for criterion, data in st.session_state.generated_sections.items():
            full_report += f"\n{criterion.upper()}\n{'-'*60}\n{data['content']}\n\n"
        st.download_button("📥 Download Full SSR", data=full_report,
                            file_name=f"NAAC_SSR_{inst_name.replace(' ','_')}.txt",
                            mime="text/plain")
