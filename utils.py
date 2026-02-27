"""Utility helpers for the NAAC SSR Generator."""


def check_api_key(api_key: str) -> bool:
    """Quick validation — just checks key format (starts with 'AIza' and is ~39 chars)."""
    return bool(api_key and api_key.startswith("AIza") and len(api_key) > 30)


def format_compliance_report(report: dict) -> str:
    """Format compliance report as plain text for export."""
    lines = [
        "NAAC SSR COMPLIANCE REPORT",
        "=" * 50,
        f"Overall Score: {report['score']}%",
        f"Checks Passed: {report['passes']}",
        f"Issues Found: {report['failures']}",
        "",
        "DETAILED CHECKS:",
        "-" * 40,
    ]
    for item in report.get("checks", []):
        status_icon = "✓" if item["status"] == "pass" else "✗" if item["status"] == "fail" else "⚠"
        lines.append(f"{status_icon} {item['check']}")
        lines.append(f"  {item['detail']}")
        lines.append("")

    if report.get("suggestions"):
        lines += ["IMPROVEMENT SUGGESTIONS:", "-" * 40]
        for i, s in enumerate(report["suggestions"], 1):
            lines.append(f"{i}. {s}")

    return "\n".join(lines)
