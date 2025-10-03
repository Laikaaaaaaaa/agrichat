import json
import re
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional

import requests

RE_REQUIREMENT = re.compile(r"^([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+)$")


@dataclass
class RequirementIssue:
    package: str
    version: str
    issue: str
    requires_python: Optional[str] = None


def read_requirements(path: Path) -> List[str]:
    raw_bytes = path.read_bytes()
    for encoding in ("utf-16", "utf-8-sig", "utf-8"):
        try:
            return raw_bytes.decode(encoding).splitlines()
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("Unable to decode requirements file with utf-16 / utf-8-sig / utf-8 encodings")


def fetch_metadata(package: str, version: str, session: requests.Session) -> Optional[dict]:
    url = f"https://pypi.org/pypi/{package}/{version}/json"
    response = session.get(url, timeout=10)
    if response.status_code != 200:
        raise RuntimeError(f"HTTP {response.status_code}")
    return response.json()


def analyze(requirements_path: Path) -> dict:
    lines = read_requirements(requirements_path)
    issues: List[RequirementIssue] = []
    missing_metadata: List[RequirementIssue] = []
    non_standard: List[dict] = []

    session = requests.Session()
    session.headers.update({"User-Agent": "AgriSense-CompatChecker/1.0"})

    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = RE_REQUIREMENT.match(line)
        if not match:
            non_standard.append({"line_number": idx, "line": raw_line})
            continue

        package, version = match.groups()

        try:
            metadata = fetch_metadata(package, version, session)
        except Exception as exc:  # noqa: BLE001
            issues.append(RequirementIssue(package, version, f"metadata fetch failed: {exc}"))
            time.sleep(0.1)
            continue

        info = metadata.get("info", {})
        requires_python = info.get("requires_python")

        if not requires_python:
            missing_metadata.append(RequirementIssue(package, version, "missing requires_python", None))
        else:
            # Interpret common incompatible specifiers
            spec = requires_python.replace(" ", "")
            incompatible_tokens = ["<3.11", "<=3.10", "<3.10", "<=3.9", "<3.9"]
            if any(token in spec for token in incompatible_tokens):
                issues.append(RequirementIssue(package, version, "python upper bound", requires_python))

        time.sleep(0.05)

    return {
        "issues": [asdict(item) for item in issues],
        "missing_requires_python": [asdict(item) for item in missing_metadata],
        "non_standard_lines": non_standard,
    }


def main(argv: List[str]) -> int:
    requirements_path = Path(argv[1]) if len(argv) > 1 else Path("requirements.txt")
    report_path = Path(argv[2]) if len(argv) > 2 else Path("py311_compat_report.json")

    report = analyze(requirements_path)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Report written to {report_path}")
    print(
        f"Found {len(report['issues'])} compatibility issues, "
        f"{len(report['missing_requires_python'])} without requires_python metadata, "
        f"{len(report['non_standard_lines'])} non-standard lines."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
