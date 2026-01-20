import os
import time
from datetime import datetime

from rag_gemini import run_rag


CRITERIA_QUERIES = {
    "Criterion 1 - Curricular Aspects": (
        "Generate NAAC SSR content for Criterion 1: Curricular Aspects. "
        "Include overview, curriculum planning, implementation, feedback mechanism, and outcomes."
    ),

    "Criterion 2 - Teaching-Learning and Evaluation": (
        "Generate NAAC SSR content for Criterion 2: Teaching-Learning and Evaluation. "
        "Include student-centric methods, teacher profile, mentoring, evaluation methods, and outcomes."
    ),

    "Criterion 3 - Research, Innovations and Extension": (
        "Generate NAAC SSR content for Criterion 3: Research, Innovations and Extension. "
        "Include research activities, publications, grants, innovation ecosystem, extension programs, and outcomes."
    ),

    "Criterion 4 - Infrastructure and Learning Resources": (
        "Generate NAAC SSR content for Criterion 4: Infrastructure and Learning Resources. "
        "Include facilities, ICT infrastructure, library resources, labs, maintenance, and utilization."
    ),

    "Criterion 5 - Student Support and Progression": (
        "Generate NAAC SSR content for Criterion 5: Student Support and Progression. "
        "Include scholarships, placement, training, student activities, progression, and alumni engagement."
    ),

    "Criterion 6 - Governance, Leadership and Management": (
        "Generate NAAC SSR content for Criterion 6: Governance, Leadership and Management. "
        "Include vision/mission, organizational structure, strategy, faculty development, and financial management."
    ),

    "Criterion 7 - Institutional Values and Best Practices": (
        "Generate NAAC SSR content for Criterion 7: Institutional Values and Best Practices. "
        "Include environmental initiatives, inclusivity, ethics, best practices, and institutional distinctiveness."
    )
}


def safe_rag_call(query, k=5, base_wait=30, max_wait=300):
    """
    Calls run_rag() safely with exponential backoff when Gemini hits 429 limits.
    """
    wait_time = base_wait
    attempt = 1

    while True:
        try:
            return run_rag(query, k=k)
        except Exception as e:
            msg = str(e)

            if "429" in msg or "ResourceExhausted" in msg or "quota" in msg.lower():
                print(f"⚠️ Rate limit hit (attempt {attempt}). Waiting {wait_time}s then retrying...")
                time.sleep(wait_time)
                wait_time = min(wait_time * 2, max_wait)
                attempt += 1
            else:
                raise e


def get_done_criteria(report_text: str):
    """
    Finds already-generated criteria by checking headings in existing report file.
    """
    done = set()
    for title in CRITERIA_QUERIES.keys():
        if title in report_text:
            done.add(title)
    return done


def generate_full_naac_report(k=3, wait_between_sections=60, resume_file=None):
    """
    Full report generation with resume mode.
    If resume_file exists, it continues from remaining criteria.
    """

    # ✅ Decide output file
    if resume_file:
        output_file = resume_file
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_file = f"NAAC_Report_{timestamp}.txt"

    # ✅ Load existing report if present
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            final_report = f.read()
        print(f"\n✅ Resume mode ON: Loaded existing report -> {output_file}")
    else:
        final_report = ""
        final_report += "NAAC SSR REPORT (AUTO-GENERATED)\n"
        final_report += "=" * 70 + "\n"
        final_report += f"Generated On: {datetime.now()}\n"
        final_report += "=" * 70 + "\n\n"
        print(f"\n✅ New report file created: {output_file}")

    done_criteria = get_done_criteria(final_report)

    print("\n✅ Already completed sections:")
    if done_criteria:
        for d in done_criteria:
            print("   ✔", d)
    else:
        print("   (none)")

    # ✅ Loop remaining criteria only
    total = len(CRITERIA_QUERIES)
    for idx, (title, query) in enumerate(CRITERIA_QUERIES.items(), start=1):

        if title in done_criteria:
            print(f"\n⏭ Skipping (already done): {title}")
            continue

        print(f"\n==============================")
        print(f"({idx}/{total}) ✅ Generating: {title}")
        print("==============================")

        section_text = safe_rag_call(query, k=k)

        section_block = "\n" + "=" * 70 + "\n"
        section_block += title + "\n"
        section_block += "=" * 70 + "\n\n"
        section_block += section_text.strip() + "\n\n"

        final_report += section_block

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(final_report)

        print(f"✅ Saved progress -> {output_file}")

        # ✅ Wait between sections to reduce rate-limit hits
        print(f"⏳ Waiting {wait_between_sections}s before next criterion...")
        time.sleep(wait_between_sections)

    print("\n🎉 REPORT GENERATION COMPLETE!")
    print(f"📄 Final report saved -> {output_file}")


if __name__ == "__main__":
    """
    ✅ Resume usage:
    1) If you already have a partially-generated report file name, put it below.
    2) Otherwise leave resume_file=None for a fresh new report.
    """

    # 🔥 PUT YOUR EXISTING REPORT NAME HERE to resume:
    resume_file = "NAAC_Report_2026-01-20_20-01-22.txt"  # <-- change this to your file name

    generate_full_naac_report(k=3, wait_between_sections=60, resume_file=resume_file)


