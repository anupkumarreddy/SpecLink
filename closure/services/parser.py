import json
from dataclasses import dataclass


BEGIN_MARKER = "=== SPECLINK_SUMMARY_BEGIN ==="
END_MARKER = "=== SPECLINK_SUMMARY_END ==="
PARSER_VERSION = "0.1.0"


class SpecLinkParseError(ValueError):
    pass


@dataclass
class ParsedSummary:
    payload: dict
    block_index: int


REQUIRED_SUMMARY_FIELDS = {
    "schema_version",
    "project",
    "test",
    "status",
    "requirements",
}

REQUIRED_REQUIREMENT_FIELDS = {"id", "expected", "status", "checks"}
REQUIRED_CHECK_FIELDS = {"id", "expected", "observed", "result", "hit_count", "fail_count", "messages"}


def extract_summary_blocks(log_text: str) -> list[str]:
    blocks = []
    offset = 0
    while True:
        begin = log_text.find(BEGIN_MARKER, offset)
        if begin == -1:
            break
        content_start = begin + len(BEGIN_MARKER)
        end = log_text.find(END_MARKER, content_start)
        if end == -1:
            raise SpecLinkParseError("Found SPECLINK summary begin marker without matching end marker.")
        blocks.append(log_text[content_start:end].strip())
        offset = end + len(END_MARKER)
    if not blocks:
        raise SpecLinkParseError("No SPECLINK summary blocks found.")
    return blocks


def validate_summary(payload: dict):
    missing = sorted(REQUIRED_SUMMARY_FIELDS - payload.keys())
    if missing:
        raise SpecLinkParseError(f"Summary missing required fields: {', '.join(missing)}")
    if not isinstance(payload["requirements"], list):
        raise SpecLinkParseError("Summary field 'requirements' must be a list.")
    for req in payload["requirements"]:
        req_missing = sorted(REQUIRED_REQUIREMENT_FIELDS - req.keys())
        if req_missing:
            raise SpecLinkParseError(f"Requirement summary missing fields: {', '.join(req_missing)}")
        if not isinstance(req["checks"], list):
            raise SpecLinkParseError("Requirement field 'checks' must be a list.")
        for check in req["checks"]:
            check_missing = sorted(REQUIRED_CHECK_FIELDS - check.keys())
            if check_missing:
                raise SpecLinkParseError(f"Check summary missing fields: {', '.join(check_missing)}")


def parse_log_text(log_text: str) -> list[ParsedSummary]:
    summaries = []
    for index, block in enumerate(extract_summary_blocks(log_text), start=1):
        try:
            payload = json.loads(block)
        except json.JSONDecodeError as exc:
            raise SpecLinkParseError(f"Invalid JSON in summary block {index}: {exc}") from exc
        validate_summary(payload)
        summaries.append(ParsedSummary(payload=payload, block_index=index))
    return summaries


def build_evidence_report(log_text: str, project_slug: str, run_id: str) -> dict:
    summaries = parse_log_text(log_text)
    return {
        "schema_version": "1.0",
        "parser_version": PARSER_VERSION,
        "project": project_slug,
        "run_id": run_id,
        "tests": [summary.payload for summary in summaries],
    }

