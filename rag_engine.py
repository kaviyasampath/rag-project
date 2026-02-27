"""
NAAC SSR RAG Engine
- Persistent ChromaDB (survives restarts)
- Two collections: reference_ssrs (admin-loaded, persistent) + institutional_docs (per session)
- Gemini 1.5 Flash for generation
- Compliance checker
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Any

import chromadb
from sentence_transformers import SentenceTransformer
import google.generativeai as genai


# ── Persistent DB path (reference SSRs survive app restarts) ───────────────
DB_PATH = str(Path(__file__).parent / "naac_vector_db")

NAAC_COMPLIANCE_RULES = {
    "Criterion 1 – Curricular Aspects": [
        ("mentions programme outcomes or POs/COs",    r"programme outcome|PO\d|CO\d|course outcome",          "Programme Outcomes (POs/COs) referenced"),
        ("references academic flexibility",            r"elective|choice.based|CBCS|flexibility|open course",   "Academic flexibility / electives mentioned"),
        ("includes feedback mechanism",                r"feedback|survey|stakeholder",                          "Feedback mechanism described"),
        ("mentions curriculum revision/update",        r"revision|update|syllabus|BOS|board of studies",        "Curriculum revision process present"),
    ],
    "Criterion 2 – Teaching, Learning and Evaluation": [
        ("mentions student enrolment data",            r"\d+\s*(student|enroll|admiss)",                        "Student enrolment data present"),
        ("describes teaching methodology",             r"pedagog|ICT|experiential|project.based|blended",       "Teaching methodology described"),
        ("mentions assessment/evaluation",             r"assessment|examination|evaluation|internal mark",      "Assessment/evaluation process described"),
        ("references teacher quality/qualification",   r"Ph\.?D|qualification|experience|faculty",              "Faculty qualifications referenced"),
    ],
    "Criterion 3 – Research, Innovations and Extension": [
        ("mentions research publications",             r"publication|journal|paper|research output",            "Research publications mentioned"),
        ("references funding/grants",                  r"fund|grant|project|sponsor",                           "Research funding/grants mentioned"),
        ("mentions extension activities",              r"extension|community|outreach|NSS|NCC",                 "Extension/community activities present"),
        ("includes innovation/incubation",             r"innovat|incubat|startup|patent",                       "Innovation/incubation initiatives present"),
    ],
    "Criterion 4 – Infrastructure and Learning Resources": [
        ("describes physical facilities",              r"classrooms?|labs?|laboratory|infrastructure|facility", "Physical facilities described"),
        ("mentions library resources",                 r"library|e.resource|journal|database|books?",           "Library resources described"),
        ("includes IT infrastructure",                 r"internet|bandwidth|wifi|computer|ICT",                 "IT infrastructure described"),
        ("mentions maintenance/AMC",                   r"maintenance|AMC|upkeep|repair",                        "Maintenance policy mentioned"),
    ],
    "Criterion 5 – Student Support and Progression": [
        ("mentions scholarships/financial aid",        r"scholarship|financial aid|fee waiver|stipend",         "Scholarships/financial aid mentioned"),
        ("describes career guidance",                  r"placement|career|counseling|guidance|job",             "Career guidance/placement described"),
        ("mentions student grievance",                 r"grievance|redress|complaint|ombudsman",                "Student grievance mechanism present"),
        ("references alumni",                          r"alumni|alumnae|old student",                           "Alumni engagement described"),
    ],
    "Criterion 6 – Governance, Leadership and Management": [
        ("mentions institutional vision/mission",      r"vision|mission|goal|objective",                        "Vision and mission stated"),
        ("describes governance structure",             r"governing body|iqac|committee|senate|board",           "Governance structure described"),
        ("mentions financial management",              r"budget|finance|audit|expenditure|fund utilisation",    "Financial management described"),
        ("references IQAC",                            r"IQAC|quality assurance|quality initiative",            "IQAC activities referenced"),
    ],
    "Criterion 7 – Institutional Values and Best Practices": [
        ("mentions gender equity",                     r"gender|women|equity|equalit",                          "Gender equity initiatives present"),
        ("describes environmental initiatives",        r"environment|green|solar|energy|sustainability",        "Environmental initiatives described"),
        ("includes best practices",                    r"best practice|initiative|innovat",                     "Best practices described"),
        ("mentions inclusivity/differently abled",     r"differently.abled|handicap|inclusiv|disable",          "Inclusivity/differently-abled initiatives present"),
    ],
}

NAAC_SYSTEM_PROMPT = """You are an expert NAAC (National Assessment and Accreditation Council) documentation specialist for Indian higher education institutions.
Generate formal, evidence-based, criterion-specific content for NAAC Self-Study Reports (SSRs).

Rules:
- Use ONLY the institutional evidence provided for facts, numbers, and specific claims
- Use reference SSR examples only to guide writing style, tone, and structure
- Never fabricate data or hallucinate — if a fact is not in the context, do not include it
- Write in third person (e.g., "The institution has..." not "We have...")
- Formal academic tone throughout
- 400–600 words per section with clear sub-sections
"""


class NAACRagEngine:
    """Core RAG engine — persistent reference DB + per-session institutional DB."""

    def __init__(self, api_key: str, institution_name: str = "The Institution"):
        self.institution_name = institution_name or "The Institution"

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            "gemini-1.5-flash",
            system_instruction=NAAC_SYSTEM_PROMPT
        )
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")

        # Persistent client — reference SSRs saved to disk, survive restarts
        self.persistent_client = chromadb.PersistentClient(path=DB_PATH)
        self.reference_collection = self.persistent_client.get_or_create_collection(
            name="reference_ssrs",
            metadata={"hnsw:space": "cosine"}
        )

        # In-memory client — institutional docs are per-session (fresh each run)
        self.memory_client = chromadb.Client()
        self.institutional_collection = self.memory_client.get_or_create_collection(
            name="institutional_docs",
            metadata={"hnsw:space": "cosine"}
        )

    def reference_count(self) -> int:
        """How many reference chunks are stored on disk."""
        return self.reference_collection.count()

    def _extract_text(self, filepath: str) -> str:
        path = Path(filepath)
        ext = path.suffix.lower()
        if ext == ".txt":
            return path.read_text(errors="ignore")
        elif ext == ".docx":
            try:
                import docx
                doc = docx.Document(filepath)
                return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            except Exception as e:
                return f"[DOCX error: {e}]"
        elif ext == ".pdf":
            try:
                import fitz
                doc = fitz.open(filepath)
                text = "".join(page.get_text() for page in doc)
                doc.close()
                return text
            except ImportError:
                try:
                    import pdfplumber
                    with pdfplumber.open(filepath) as pdf:
                        return "\n".join(p.extract_text() or "" for p in pdf.pages)
                except Exception as e:
                    return f"[PDF error: {e}]"
        return ""

    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 80) -> List[str]:
        words = text.split()
        return [
            " ".join(words[i: i + chunk_size])
            for i in range(0, len(words), chunk_size - overlap)
            if len(" ".join(words[i: i + chunk_size]).strip()) > 50
        ]

    def _tag_criterion(self, text: str) -> str:
        text_lower = text.lower()
        keyword_map = {
            "Criterion 1": ["curriculum", "syllabus", "course outcome", "programme", "cbcs", "feedback"],
            "Criterion 2": ["teaching", "learning", "assessment", "student", "faculty", "examination"],
            "Criterion 3": ["research", "publication", "extension", "innovation", "patent", "grant"],
            "Criterion 4": ["infrastructure", "library", "laboratory", "it facility", "maintenance"],
            "Criterion 5": ["placement", "scholarship", "alumni", "grievance", "career", "support"],
            "Criterion 6": ["governance", "iqac", "leadership", "finance", "strategy", "management"],
            "Criterion 7": ["gender", "environment", "best practice", "green", "inclusiv", "value"],
        }
        scores = {c: sum(1 for kw in kws if kw in text_lower) for c, kws in keyword_map.items()}
        return max(scores, key=scores.get) if max(scores.values()) > 0 else "General"

    def _index_files(self, file_paths: List[str], collection, doc_type: str) -> int:
        """Internal: extract, chunk, embed, and store files into a collection."""
        all_chunks, all_ids, all_metas = [], [], []
        for fpath in file_paths:
            text = self._extract_text(fpath)
            if not text.strip():
                continue
            fname = Path(fpath).name
            for i, chunk in enumerate(self._chunk_text(text)):
                all_chunks.append(chunk)
                all_ids.append(f"{doc_type}_{fname}_{i}")
                all_metas.append({
                    "source": fname,
                    "doc_type": doc_type,
                    "criterion_hint": self._tag_criterion(chunk),
                })
        if not all_chunks:
            raise ValueError("No text could be extracted from the uploaded documents.")
        for i in range(0, len(all_chunks), 100):
            batch = all_chunks[i:i+100]
            collection.add(
                documents=batch,
                embeddings=self.embedder.encode(batch).tolist(),
                ids=all_ids[i:i+100],
                metadatas=all_metas[i:i+100],
            )
        return len(all_chunks)

    def ingest_institutional(self, file_paths: List[str]) -> int:
        """Load institution's own documents (in-memory, per session)."""
        return self._index_files(file_paths, self.institutional_collection, "institutional")

    def ingest_reference(self, file_paths: List[str]) -> int:
        """Load reference SSRs (persisted to disk by admin)."""
        return self._index_files(file_paths, self.reference_collection, "reference")

    def clear_reference_db(self):
        """Admin: wipe all reference SSRs from disk."""
        self.persistent_client.delete_collection("reference_ssrs")
        self.reference_collection = self.persistent_client.get_or_create_collection(
            name="reference_ssrs",
            metadata={"hnsw:space": "cosine"}
        )

    def _retrieve(self, query: str, collection, n: int = 4) -> List[Dict]:
        count = collection.count()
        if count == 0:
            return []
        results = collection.query(
            query_embeddings=self.embedder.encode([query])[0].tolist(),
            n_results=min(n, count),
        )
        return [
            {"text": doc, "source": meta.get("source", "Unknown")}
            for doc, meta in zip(results["documents"][0], results["metadatas"][0])
        ]

    def generate_section(self, criterion: str, criterion_hint: str, extra_context: str = "") -> Dict[str, Any]:
        query = f"{criterion} {criterion_hint}"
        inst_sources = self._retrieve(query, self.institutional_collection, n=5)
        ref_sources  = self._retrieve(query, self.reference_collection, n=3)

        inst_block = "\n\n---\n\n".join(
            f"[{s['source']}]\n{s['text']}" for s in inst_sources
        ) if inst_sources else "[No institutional documents uploaded.]"

        ref_block = "\n\n---\n\n".join(
            f"[Reference: {s['source']}]\n{s['text']}" for s in ref_sources
        ) if ref_sources else "[No reference SSRs in knowledge base.]"

        prompt = f"""Generate a NAAC SSR section.

INSTITUTION: {self.institution_name}
CRITERION: {criterion}
FOCUS AREAS: {criterion_hint}

━━━ INSTITUTIONAL EVIDENCE (facts and data to use) ━━━
{inst_block}

━━━ REFERENCE SSR EXAMPLES (writing style and structure only) ━━━
{ref_block}

{"ADDITIONAL NOTES: " + extra_context if extra_context else ""}

Generate the formal SSR section now (400–600 words, third person, evidence-backed):"""

        response = self.model.generate_content(prompt)
        return {
            "content": response.text,
            "sources": inst_sources,
            "criterion": criterion,
        }

    def compliance_check(self, content: str, criterion: str) -> Dict[str, Any]:
        criterion_key = next((k for k in NAAC_COMPLIANCE_RULES if k in criterion or criterion in k), None)
        checks = []
        if criterion_key:
            for (desc, pattern, detail) in NAAC_COMPLIANCE_RULES[criterion_key]:
                match = bool(re.search(pattern, content, re.IGNORECASE))
                checks.append({
                    "check": detail,
                    "status": "pass" if match else "fail",
                    "detail": "Found ✓" if match else f"Missing — add {desc}",
                })
        for label, passed, detail in [
            ("Word count > 200", len(content.split()) > 200, f"{len(content.split())} words"),
            ("Contains quantitative data", bool(re.search(r"\d+[\s%]", content)), "Numbers/percentages present"),
            ("Evidence-based language", bool(re.search(r"evidence|data|report|document|record", content, re.IGNORECASE)), "Evidence language found"),
            ("Third-person tone", not bool(re.search(r"\bwe\b|\bour\b|\bi\b", content[:200], re.IGNORECASE)), "No first-person pronouns"),
        ]:
            checks.append({"check": label, "status": "pass" if passed else "warn", "detail": detail})

        passes   = sum(1 for c in checks if c["status"] == "pass")
        failures = sum(1 for c in checks if c["status"] == "fail")
        score    = int(100 * passes / len(checks)) if checks else 0

        try:
            resp = self.model.generate_content(
                f"Give 3 one-line improvements for this NAAC SSR section ({criterion}).\n"
                f"Content: {content[:1200]}\n"
                f"Respond ONLY as a JSON array of 3 strings."
            )
            suggestions = json.loads(re.sub(r"```json|```", "", resp.text.strip()).strip())
        except Exception:
            suggestions = [
                "Add specific numerical data (student counts, percentages, years)",
                "Reference supporting documents explicitly",
                "Mention IQAC activities and quality initiatives",
            ]

        return {"score": score, "passes": passes, "failures": failures, "checks": checks, "suggestions": suggestions}
