# coding=utf-8
"""
Post-process OCR-derived Markdown into cleaner evidence Markdown and structured
certificate fields.

Supported certificate types are business license, safety production license,
and personnel certificate. The script uses deterministic extraction rules so
failures are reviewable and repeatable.
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
SUPPORTED_CERTIFICATE_TYPES = {"business_license", "safety_production_license", "personnel_certificate"}
CERTIFICATE_OUTPUT_PREFIX = {
    "business_license": "business-license",
    "safety_production_license": "safety-production-license",
    "personnel_certificate": "personnel-certificate",
}
CERTIFICATE_TITLES = {
    "business_license": "营业执照",
    "safety_production_license": "安全生产许可证",
    "personnel_certificate": "人员证书",
}


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
    metadata: dict[str, str]
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


def extract_first_label_value(text: str, labels: list[str], stop_labels: list[str]) -> str:
    for label in labels:
        line_value = extract_line_value(text, label)
        if line_value:
            return line_value
    for label in labels:
        value = extract_after_label(text, label, stop_labels)
        if value:
            return value
    return ""


def detect_certificate_type(text: str) -> str:
    compact = compact_text(text)
    if "安全生产许可证" in compact:
        return "safety_production_license"
    if "营业执照" in compact or "统一社会信用代码" in compact:
        return "business_license"
    if "证书编号" in compact and any(keyword in compact for keyword in ["姓名", "岗位", "安全员", "质检员", "测量员"]):
        return "personnel_certificate"
    return "business_license"


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


def extract_safety_production_license_fields(text: str) -> tuple[dict[str, Any], list[str]]:
    normalized = normalize_text(text)
    compact = compact_text(normalized)
    warnings: list[str] = []
    dates = re.findall(r"\d{4}年\d{1,2}月\d{1,2}日", normalized)
    license_number = extract_first_label_value(
        normalized,
        ["编号", "证书编号", "许可证编号", "安全生产许可证编号"],
        ["单位名称", "企业名称", "主要负责人", "法定代表人", "许可范围", "有效期", "发证机关"],
    )
    fields: dict[str, Any] = {
        "certificate_type": "safety_production_license",
        "license_number": license_number or _first_match(compact, r"[（(]?[A-Za-z0-9\u4e00-\u9fff-]{2,20}安许证字[）)]?第?[A-Za-z0-9-]+号?"),
        "company_name": extract_first_label_value(normalized, ["单位名称", "企业名称", "名称"], ["主要负责人", "法定代表人", "许可范围", "有效期", "发证机关"]),
        "principal_person": extract_first_label_value(normalized, ["主要负责人", "法定代表人"], ["许可范围", "有效期", "发证机关"]),
        "permitted_scope": extract_first_label_value(normalized, ["许可范围", "许可内容"], ["有效期", "发证机关", "签发日期"]),
        "issuing_authority": extract_first_label_value(normalized, ["发证机关", "签发机关"], ["有效期", "签发日期"]),
        "dates": dates,
        "valid_from": dates[0] if dates else "",
        "valid_until": dates[-1] if dates else "",
        "issue_date": dates[-1] if dates else "",
        "review_hint": "",
    }
    fields["permitted_scope"] = trim_overlong_scope(fields["permitted_scope"], limit=360)
    fields["review_hint"] = build_safety_license_review_hint(fields)
    for key in ["license_number", "company_name", "valid_until"]:
        if not fields.get(key):
            warnings.append(f"未抽取到关键字段：{key}")
    return fields, warnings


def extract_personnel_certificate_fields(text: str) -> tuple[dict[str, Any], list[str]]:
    normalized = normalize_text(text)
    warnings: list[str] = []
    dates = re.findall(r"\d{4}年\d{1,2}月\d{1,2}日|\d{4}-\d{1,2}-\d{1,2}", normalized)
    fields: dict[str, Any] = {
        "certificate_type": "personnel_certificate",
        "name": extract_first_label_value(normalized, ["姓名"], ["岗位", "职务", "证书编号", "发证机关", "有效期", "单位"]),
        "role": extract_first_label_value(normalized, ["岗位", "职务", "资格类别"], ["证书编号", "发证机关", "有效期", "单位"]),
        "certificate_number": extract_first_label_value(normalized, ["证书编号", "编号"], ["发证机关", "有效期", "单位", "到岗状态"]),
        "issuing_authority": extract_first_label_value(normalized, ["发证机关", "签发机关"], ["有效期", "单位", "到岗状态"]),
        "company_name": extract_first_label_value(normalized, ["单位", "聘用单位", "所属单位"], ["到岗状态", "审查意见", "有效期"]),
        "attendance_status": extract_first_label_value(normalized, ["到岗状态"], ["审查意见", "备注"]),
        "dates": dates,
        "valid_until": dates[-1] if dates else "",
        "review_hint": "",
    }
    fields["review_hint"] = build_personnel_certificate_review_hint(fields)
    for key in ["name", "role", "certificate_number", "valid_until"]:
        if not fields.get(key):
            warnings.append(f"未抽取到关键字段：{key}")
    return fields, warnings


def extract_certificate_fields(text: str, certificate_type: str = "auto") -> tuple[dict[str, Any], list[str]]:
    normalized = normalize_text(text)
    resolved_type = detect_certificate_type(normalized) if certificate_type == "auto" else certificate_type
    if resolved_type not in SUPPORTED_CERTIFICATE_TYPES:
        raise ValueError(f"Unsupported certificate type: {resolved_type}")
    if resolved_type == "business_license":
        return extract_business_license_fields(normalized)
    if resolved_type == "safety_production_license":
        return extract_safety_production_license_fields(normalized)
    return extract_personnel_certificate_fields(normalized)


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


def build_safety_license_review_hint(fields: dict[str, Any]) -> str:
    parts = []
    if fields.get("company_name"):
        parts.append(f"企业名称为 {fields['company_name']}")
    if fields.get("license_number"):
        parts.append(f"安全生产许可证编号为 {fields['license_number']}")
    if fields.get("valid_until"):
        parts.append(f"有效期至 {fields['valid_until']}")
    if fields.get("permitted_scope"):
        parts.append(f"许可范围为 {fields['permitted_scope']}")
    return "；".join(parts)


def build_personnel_certificate_review_hint(fields: dict[str, Any]) -> str:
    parts = []
    if fields.get("name"):
        parts.append(f"人员姓名为 {fields['name']}")
    if fields.get("role"):
        parts.append(f"岗位为 {fields['role']}")
    if fields.get("certificate_number"):
        parts.append(f"证书编号为 {fields['certificate_number']}")
    if fields.get("valid_until"):
        parts.append(f"有效期至 {fields['valid_until']}")
    if fields.get("attendance_status"):
        parts.append(f"到岗状态为 {fields['attendance_status']}")
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


def format_metadata_value(value: Any) -> str:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def write_ingest_markdown(
    path: Path,
    source: Path,
    fields: dict[str, Any],
    metadata: dict[str, str],
    cleaned_text: str,
    warnings: list[str],
) -> None:
    title = CERTIFICATE_TITLES.get(fields["certificate_type"], fields["certificate_type"])
    rows = ingest_rows(fields)
    lines = [
        f"# {title} OCR 结构化结果",
        "",
        f"原始 OCR Markdown：`{source}`",
        "",
    ]
    if metadata:
        lines.extend(
            [
                "## 资料元数据",
                "",
                "| 字段 | 值 |",
                "| --- | --- |",
            ]
        )
        for key, value in metadata.items():
            lines.append(f"| {key} | {format_metadata_value(value) if value else '未填写'} |")
        lines.append("")
    lines.extend(
        [
        "## 结构化字段",
        "",
        "| 字段 | 值 |",
        "| --- | --- |",
        ]
    )
    for key, value in rows:
        lines.append(f"| {key} | {value or '未识别'} |")
    lines.extend(
        [
            "",
            "## 经营范围摘录",
            "",
            fields.get("business_scope") or fields.get("permitted_scope") or "未识别",
            "",
            "## 后处理告警",
            "",
        ]
    )
    lines.extend([f"- {warning}" for warning in warnings] or ["- 无"])
    lines.extend(["", "## 清洗后 OCR 原文", "", cleaned_text])
    path.write_text("\n".join(lines), encoding="utf-8")


def ingest_rows(fields: dict[str, Any]) -> list[tuple[str, Any]]:
    certificate_type = fields["certificate_type"]
    if certificate_type == "business_license":
        return [
            ("证照类型", "营业执照"),
            ("统一社会信用代码", fields.get("unified_social_credit_code", "")),
            ("名称", fields.get("company_name", "")),
            ("类型", fields.get("company_type", "")),
            ("法定代表人", fields.get("legal_representative", "")),
            ("正照编号", fields.get("license_number", "")),
            ("签发/登记日期", fields.get("issue_date", "")),
            ("审查提示", fields.get("review_hint", "")),
        ]
    if certificate_type == "safety_production_license":
        return [
            ("证照类型", "安全生产许可证"),
            ("许可证编号", fields.get("license_number", "")),
            ("企业名称", fields.get("company_name", "")),
            ("主要负责人", fields.get("principal_person", "")),
            ("许可范围", fields.get("permitted_scope", "")),
            ("有效期至", fields.get("valid_until", "")),
            ("发证机关", fields.get("issuing_authority", "")),
            ("审查提示", fields.get("review_hint", "")),
        ]
    return [
        ("证照类型", "人员证书"),
        ("姓名", fields.get("name", "")),
        ("岗位", fields.get("role", "")),
        ("证书编号", fields.get("certificate_number", "")),
        ("发证机关", fields.get("issuing_authority", "")),
        ("聘用/所属单位", fields.get("company_name", "")),
        ("有效期至", fields.get("valid_until", "")),
        ("到岗状态", fields.get("attendance_status", "")),
        ("审查提示", fields.get("review_hint", "")),
    ]


def write_report(path: Path, artifact: PostprocessArtifact) -> None:
    lines = [
        "# OCR 后处理报告",
        "",
        "## 结论摘要",
        "",
        f"- source_markdown：`{artifact.source_markdown}`",
        f"- certificate_type：{artifact.certificate_type}",
        f"- extracted_field_count：{sum(1 for value in artifact.extracted_fields.values() if value)}",
        f"- metadata_field_count：{sum(1 for value in artifact.metadata.values() if value)}",
        f"- warnings：{len(artifact.warnings)}",
        "",
        "## 关键字段",
        "",
    ]
    for key in report_keys(artifact.certificate_type):
        lines.append(f"- {key}：{artifact.extracted_fields.get(key) or '未识别'}")
    if artifact.metadata:
        lines.extend(["", "## 资料元数据", ""])
        for key, value in artifact.metadata.items():
            lines.append(f"- {key}：{value or '未填写'}")
    lines.extend(["", "## 输出文件", ""])
    for output in [artifact.cleaned_markdown, artifact.ingest_markdown, artifact.fields_json, artifact.fields_csv]:
        lines.append(f"- `{output}`")
    if artifact.warnings:
        lines.extend(["", "## 告警", ""])
        lines.extend(f"- {warning}" for warning in artifact.warnings)
    path.write_text("\n".join(lines), encoding="utf-8")


def report_keys(certificate_type: str) -> list[str]:
    if certificate_type == "business_license":
        return [
            "unified_social_credit_code",
            "company_name",
            "company_type",
            "legal_representative",
            "license_number",
            "issue_date",
            "review_hint",
        ]
    if certificate_type == "safety_production_license":
        return [
            "license_number",
            "company_name",
            "principal_person",
            "permitted_scope",
            "valid_until",
            "issuing_authority",
            "review_hint",
        ]
    return [
        "name",
        "role",
        "certificate_number",
        "company_name",
        "valid_until",
        "attendance_status",
        "review_hint",
    ]


def postprocess(
    source_markdown: Path,
    certificate_type: str = "auto",
    metadata: dict[str, str] | None = None,
) -> PostprocessArtifact:
    if not source_markdown.exists():
        raise FileNotFoundError(f"Source markdown not found: {source_markdown}")
    output_dir = source_markdown.parent / "postprocessed"
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_text = source_markdown.read_text(encoding="utf-8")
    cleaned_text = normalize_text(raw_text)
    fields, warnings = extract_certificate_fields(cleaned_text, certificate_type)
    metadata = clean_metadata(metadata or {})
    output_prefix = CERTIFICATE_OUTPUT_PREFIX[fields["certificate_type"]]

    cleaned_markdown = output_dir / "cleaned.md"
    ingest_markdown = output_dir / f"{output_prefix}-ingest.md"
    fields_json = output_dir / f"{output_prefix}-fields.json"
    fields_csv = output_dir / f"{output_prefix}-fields.csv"
    report_markdown = output_dir / "postprocess-report.md"

    cleaned_markdown.write_text(cleaned_text, encoding="utf-8")
    fields_json.write_text(
        json.dumps({"metadata": metadata, "fields": fields}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_csv(fields_csv, {**{f"metadata.{key}": value for key, value in metadata.items()}, **fields})
    write_ingest_markdown(ingest_markdown, source_markdown, fields, metadata, cleaned_text, warnings)

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
        metadata=metadata,
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
        "metadata": artifact.metadata,
        "warnings": artifact.warnings,
    }
    payload.setdefault("artifacts", []).append(row)
    payload.setdefault("uploads", []).extend(uploads)
    payload["artifacts"] = [item for item in payload["artifacts"] if Path(item.get("source_markdown", "")).exists()]
    payload["uploads"] = [
        item
        for item in payload["uploads"]
        if Path(item.get("source_markdown", "")).exists() and Path(item.get("ingest_markdown", "")).exists()
    ]
    payload["artifacts"] = dedupe_rows(payload["artifacts"], ["source_markdown", "ingest_markdown"])
    payload["uploads"] = dedupe_rows(payload["uploads"], ["source_markdown", "ingest_markdown", "status"])
    POSTPROCESS_INDEX.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def dedupe_rows(rows: list[dict[str, Any]], keys: list[str]) -> list[dict[str, Any]]:
    deduped: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        deduped[tuple(row.get(key) for key in keys)] = row
    return list(deduped.values())


def clean_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in metadata.items() if value}


def metadata_from_args(args: argparse.Namespace) -> dict[str, Any]:
    return clean_metadata(
        {
            "organization_id": args.organization_id,
            "project_id": args.project_id,
            "project_name": args.project_name,
            "contract_package_id": args.contract_package_id,
            "section_id": args.section_id,
            "supervision_section_id": args.supervision_section_id,
            "team_id": args.team_id,
            "team_name": args.team_name,
            "subcontract_team_id": args.subcontract_team_id or args.team_id,
            "review_task_id": args.review_task_id,
            "basis_version_id": args.basis_version_id,
            "document_type": args.document_type,
            "source_object_type": "ocr_certificate",
            "source_file_path": args.source_file_path,
            "source_object_id": args.source_object_id,
            "content_hash": args.content_hash,
            "master_data_ids": args.master_data_ids,
            "evidence_ids": args.evidence_ids,
            "effective_status": args.effective_status,
            "effective_date": args.effective_date,
        }
    )


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
    parser.add_argument(
        "--certificate-type",
        choices=["auto", "business_license", "safety_production_license", "personnel_certificate"],
        default="auto",
    )
    parser.add_argument("--upload-to-maxkb", action="store_true")
    parser.add_argument("--organization-id", default="")
    parser.add_argument("--project-id", default="")
    parser.add_argument("--project-name", default="")
    parser.add_argument("--contract-package-id", default="")
    parser.add_argument("--section-id", default="")
    parser.add_argument("--supervision-section-id", default="")
    parser.add_argument("--team-id", default="")
    parser.add_argument("--team-name", default="")
    parser.add_argument("--subcontract-team-id", default="")
    parser.add_argument("--review-task-id", default="")
    parser.add_argument("--basis-version-id", default="")
    parser.add_argument("--document-type", default="")
    parser.add_argument("--source-file-path", default="")
    parser.add_argument("--source-object-id", default="")
    parser.add_argument("--content-hash", default="")
    parser.add_argument("--master-data-ids", action="append", default=[])
    parser.add_argument("--evidence-ids", action="append", default=[])
    parser.add_argument("--effective-status", default="")
    parser.add_argument("--effective-date", default="")
    parser.add_argument("--maxkb-base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--workspace-id", default=DEFAULT_WORKSPACE_ID)
    parser.add_argument("--maxkb-username", default="admin")
    parser.add_argument("--maxkb-password", default="Admin123@")
    parser.add_argument("--knowledge-name", default=DEFAULT_KNOWLEDGE_NAME)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source_markdown or latest_ocr_markdown()
    artifact = postprocess(source, args.certificate_type, metadata_from_args(args))
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
