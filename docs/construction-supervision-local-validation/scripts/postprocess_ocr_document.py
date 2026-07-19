# coding=utf-8
"""
Post-process OCR-derived Markdown into cleaner evidence Markdown and structured
certificate fields.

The first supported certificate type is a Chinese business license. The script
uses deterministic extraction rules so failures are reviewable and repeatable.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from configure_and_upload_maxkb import (
    DEFAULT_BASE_URL,
    DEFAULT_KNOWLEDGE_NAME,
    DEFAULT_WORKSPACE_ID,
    MaxKBClient,
    MaxKBError,
    PILOT_ROOT,
)

OCR_RESULT_INDEX = PILOT_ROOT / "00_manifest" / "paddleocr-vl-result.json"
POSTPROCESS_INDEX = PILOT_ROOT / "00_manifest" / "paddleocr-vl-postprocess-result.json"


@dataclass
class PostprocessArtifact:
    source_markdown: Path
    output_dir: Path
    cleaned_markdown: Path
    ingest_markdown: Path
    fields_json: Path
    fields_csv: Path
    report_markdown: Path
    certificate_type: str
    extracted_fields: dict[str, Any]
    warnings: list[str]


def strip_markdown_noise(text: str) -> str:
    text = re.sub(r"<div[^>]*>\s*<img[^>]*>\s*</div>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<img[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def collapse_repeated_phrases(text: str) -> str:
    # PaddleOCR sometimes repeats the same short phrase hundreds of times in seal/background regions.
    phrase_counts = Counter(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,20}", text))
    noisy = {phrase for phrase, count in phrase_counts.items() if count >= 8}
    for phrase in sorted(noisy, key=len, reverse=True):
        text = re.sub(fr"({re.escape(phrase)}[、，,。；;\s]*){{3,}}", f"{phrase}。", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def normalize_text(text: str) -> str:
    text = strip_markdown_noise(text)
    text = collapse_repeated_phrases(text)
    text = re.sub(r"[ \t]+", " ", text)
    return text


def compact_text(text: str) -> str:
    return re.sub(r"\s+", "", text)


def extract_after_label(text: str, label: str, stop_labels: list[str]) -> str:
    compact = compact_text(text)
    start = compact.find(label)
    if start < 0:
        return ""
    start += len(label)
    end = len(compact)
    for stop in stop_labels:
        index = compact.find(stop, start)
        if index >= 0:
            end = min(end, index)
    return compact[start:end].strip("：:，,。；;")


def certificate_body(text: str) -> str:
    index = text.find("统一社会信用代码")
    return text[index:] if index >= 0 else text


def extract_line_value(text: str, label: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(label):
            return line.replace(label, "", 1).strip("：:，,。；; ")
    return ""


def extract_business_license_fields(text: str) -> tuple[dict[str, Any], list[str]]:
    normalized = certificate_body(normalize_text(text))
    compact = compact_text(normalized)
    warnings: list[str] = []
    dates = re.findall(r"\d{4}年\d{1,2}月\d{1,2}日", normalized)
    credit_code_candidates = re.findall(r"[0-9A-ZxX]{15,18}", compact)
    credit_code = next((item for item in credit_code_candidates if re.search(r"[A-ZxX]", item)), "")
    if not credit_code and credit_code_candidates:
        credit_code = credit_code_candidates[0]

    fields: dict[str, Any] = {
        "certificate_type": "business_license",
        "unified_social_credit_code": credit_code,
        "license_copy_type": "副本" if "副本" in compact else "",
        "license_number": _first_match(extract_line_value(normalized, "正照编号"), r"\d{10,30}"),
        "company_name": extract_line_value(normalized, "名称"),
        "company_type": re.sub(r"\d{4}年\d{1,2}月\d{1,2}日", "", extract_line_value(normalized, "类型")).strip(),
        "legal_representative": extract_line_value(normalized, "法定代表人").split("注：", 1)[0].strip(),
        "business_scope": extract_after_label(normalized, "经营范围", ["登记机关"]),
        "registration_authority": "登记机关" if "登记机关" in compact else "",
        "dates": dates,
        "issue_date": dates[-1] if dates else "",
    }
    fields["business_scope"] = trim_overlong_scope(fields["business_scope"])
    fields["review_hint"] = build_review_hint(fields)

    required = ["unified_social_credit_code", "company_name", "legal_representative", "issue_date"]
    for key in required:
        if not fields.get(key):
            warnings.append(f"未抽取到关键字段：{key}")
    if len(fields.get("business_scope", "")) > 500:
        warnings.append("经营范围仍较长，建议人工抽查 OCR 噪声。")
    return fields, warnings


def _first_match(text: str, pattern: str) -> str:
    match = re.search(pattern, text)
    return match.group(0) if match else ""


def trim_overlong_scope(scope: str, limit: int = 500) -> str:
    scope = re.sub(r"(环境保护项目[、，,。；;\s]*){3,}", "环境保护项目。", scope)
    scope = re.sub(r"(.{2,20})(?:\1){2,}", r"\1", scope)
    return scope[:limit].strip()


def build_review_hint(fields: dict[str, Any]) -> str:
    parts = []
    if fields.get("company_name"):
        parts.append(f"企业名称为 {fields['company_name']}")
    if fields.get("unified_social_credit_code"):
        parts.append(f"统一社会信用代码为 {fields['unified_social_credit_code']}")
    if fields.get("legal_representative"):
        parts.append(f"法定代表人为 {fields['legal_representative']}")
    if fields.get("issue_date"):
        parts.append(f"登记/签发日期为 {fields['issue_date']}")
    return "；".join(parts)


def latest_ocr_markdown() -> Path:
    if not OCR_RESULT_INDEX.exists():
        raise FileNotFoundError(f"OCR result index not found: {OCR_RESULT_INDEX}")
    payload = json.loads(OCR_RESULT_INDEX.read_text(encoding="utf-8"))
    artifacts = payload.get("artifacts", [])
    if not artifacts:
        raise RuntimeError("No OCR artifacts were found.")
    return Path(artifacts[-1]["combined_markdown"])


def write_csv(path: Path, fields: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["field", "value"])
        writer.writeheader()
        for key, value in fields.items():
            writer.writerow({"field": key, "value": json.dumps(value, ensure_ascii=False) if isinstance(value, list) else value})


def write_ingest_markdown(path: Path, source: Path, fields: dict[str, Any], cleaned_text: str, warnings: list[str]) -> None:
    rows = [
        ("证照类型", "营业执照"),
        ("统一社会信用代码", fields.get("unified_social_credit_code", "")),
        ("名称", fields.get("company_name", "")),
        ("类型", fields.get("company_type", "")),
        ("法定代表人", fields.get("legal_representative", "")),
        ("正照编号", fields.get("license_number", "")),
        ("签发/登记日期", fields.get("issue_date", "")),
        ("审查提示", fields.get("review_hint", "")),
    ]
    lines = [
        "# 营业执照 OCR 结构化结果",
        "",
        f"原始 OCR Markdown：`{source}`",
        "",
        "## 结构化字段",
        "",
        "| 字段 | 值 |",
        "| --- | --- |",
    ]
    for key, value in rows:
        lines.append(f"| {key} | {value or '未识别'} |")
    lines.extend(
        [
            "",
            "## 经营范围摘录",
            "",
            fields.get("business_scope") or "未识别",
            "",
            "## 后处理告警",
            "",
        ]
    )
    lines.extend([f"- {warning}" for warning in warnings] or ["- 无"])
    lines.extend(["", "## 清洗后 OCR 原文", "", cleaned_text])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_report(path: Path, artifact: PostprocessArtifact) -> None:
    lines = [
        "# OCR 后处理报告",
        "",
        "## 结论摘要",
        "",
        f"- source_markdown：`{artifact.source_markdown}`",
        f"- certificate_type：{artifact.certificate_type}",
        f"- extracted_field_count：{sum(1 for value in artifact.extracted_fields.values() if value)}",
        f"- warnings：{len(artifact.warnings)}",
        "",
        "## 关键字段",
        "",
    ]
    for key in [
        "unified_social_credit_code",
        "company_name",
        "company_type",
        "legal_representative",
        "license_number",
        "issue_date",
        "review_hint",
    ]:
        lines.append(f"- {key}：{artifact.extracted_fields.get(key) or '未识别'}")
    lines.extend(["", "## 输出文件", ""])
    for output in [artifact.cleaned_markdown, artifact.ingest_markdown, artifact.fields_json, artifact.fields_csv]:
        lines.append(f"- `{output}`")
    if artifact.warnings:
        lines.extend(["", "## 告警", ""])
        lines.extend(f"- {warning}" for warning in artifact.warnings)
    path.write_text("\n".join(lines), encoding="utf-8")


def postprocess(source_markdown: Path) -> PostprocessArtifact:
    if not source_markdown.exists():
        raise FileNotFoundError(f"Source markdown not found: {source_markdown}")
    output_dir = source_markdown.parent / "postprocessed"
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_text = source_markdown.read_text(encoding="utf-8")
    cleaned_text = normalize_text(raw_text)
    fields, warnings = extract_business_license_fields(cleaned_text)

    cleaned_markdown = output_dir / "cleaned.md"
    ingest_markdown = output_dir / "business-license-ingest.md"
    fields_json = output_dir / "business-license-fields.json"
    fields_csv = output_dir / "business-license-fields.csv"
    report_markdown = output_dir / "postprocess-report.md"

    cleaned_markdown.write_text(cleaned_text, encoding="utf-8")
    fields_json.write_text(json.dumps(fields, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(fields_csv, fields)
    write_ingest_markdown(ingest_markdown, source_markdown, fields, cleaned_text, warnings)

    artifact = PostprocessArtifact(
        source_markdown=source_markdown,
        output_dir=output_dir,
        cleaned_markdown=cleaned_markdown,
        ingest_markdown=ingest_markdown,
        fields_json=fields_json,
        fields_csv=fields_csv,
        report_markdown=report_markdown,
        certificate_type=fields["certificate_type"],
        extracted_fields=fields,
        warnings=warnings,
    )
    write_report(report_markdown, artifact)
    return artifact


def write_index(artifact: PostprocessArtifact, uploads: list[dict[str, str]]) -> None:
    if POSTPROCESS_INDEX.exists():
        payload = json.loads(POSTPROCESS_INDEX.read_text(encoding="utf-8"))
    else:
        payload = {"artifacts": [], "uploads": []}
    row = {
        "source_markdown": str(artifact.source_markdown),
        "certificate_type": artifact.certificate_type,
        "output_dir": str(artifact.output_dir),
        "cleaned_markdown": str(artifact.cleaned_markdown),
        "ingest_markdown": str(artifact.ingest_markdown),
        "fields_json": str(artifact.fields_json),
        "fields_csv": str(artifact.fields_csv),
        "report_markdown": str(artifact.report_markdown),
        "warnings": artifact.warnings,
    }
    payload.setdefault("artifacts", []).append(row)
    payload.setdefault("uploads", []).extend(uploads)
    payload["artifacts"] = dedupe_rows(payload["artifacts"], ["source_markdown", "ingest_markdown"])
    payload["uploads"] = dedupe_rows(payload["uploads"], ["source_markdown", "ingest_markdown", "status"])
    POSTPROCESS_INDEX.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def dedupe_rows(rows: list[dict[str, Any]], keys: list[str]) -> list[dict[str, Any]]:
    deduped: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        deduped[tuple(row.get(key) for key in keys)] = row
    return list(deduped.values())


def upload_to_maxkb(args: argparse.Namespace, artifact: PostprocessArtifact) -> list[dict[str, str]]:
    client = MaxKBClient(args.maxkb_base_url)
    client.login(args.maxkb_username, args.maxkb_password)
    knowledge = next(
        (item for item in client.list_knowledge(args.workspace_id) if item.get("name") == args.knowledge_name),
        None,
    )
    if not knowledge:
        raise MaxKBError(f"Knowledge base not found: {args.knowledge_name}")
    client.upload_text_document(args.workspace_id, knowledge["id"], artifact.ingest_markdown)
    upload = {
        "source_markdown": str(artifact.source_markdown),
        "ingest_markdown": str(artifact.ingest_markdown),
        "status": "success",
    }
    return [upload]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Post-process OCR Markdown into structured certificate evidence.")
    parser.add_argument("--source-markdown", type=Path, default=None)
    parser.add_argument("--upload-to-maxkb", action="store_true")
    parser.add_argument("--maxkb-base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--workspace-id", default=DEFAULT_WORKSPACE_ID)
    parser.add_argument("--maxkb-username", default="admin")
    parser.add_argument("--maxkb-password", default="Admin123@")
    parser.add_argument("--knowledge-name", default=DEFAULT_KNOWLEDGE_NAME)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source_markdown or latest_ocr_markdown()
    artifact = postprocess(source)
    uploads = upload_to_maxkb(args, artifact) if args.upload_to_maxkb else []
    write_index(artifact, uploads)
    print(f"OCR postprocess report written: {artifact.report_markdown}")
    if uploads:
        print(f"OCR postprocess markdown uploaded: {artifact.ingest_markdown}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
