#!/usr/bin/env python
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from closure.services.parser import SpecLinkParseError, build_evidence_report  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Parse SpecLink summary blocks from a simulation log.")
    parser.add_argument("log_path")
    parser.add_argument("--project", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()

    try:
        report = build_evidence_report(Path(args.log_path).read_text(encoding="utf-8"), args.project, args.run_id)
    except (OSError, SpecLinkParseError) as exc:
        parser.error(str(exc))

    rendered = json.dumps(report, indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()

