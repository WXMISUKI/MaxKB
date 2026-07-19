# coding=utf-8
"""
Validate that PaddleOCR-derived Markdown has become retrievable in MaxKB.

This is a retrieval smoke test for OCR ingestion only. It does not produce a
formal construction-supervision review conclusion.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
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
REPORT_CSV = PILOT_ROOT / "00_manifest" / "paddleocr-vl-retrieval-check.csv"
REPORT_MD = PILOT_ROOT / "00_manifest" / "paddleocr-vl-retrieval-check.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate MaxKB retrieval hits for OCR-derived Markdown.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--workspace-id", default=DEFAULT_WORKSPACE_ID)
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="Admin123@")
    parser.add_argument("--knowledge-name", default=DEFAULT_KNOWLEDGE_NAME)
    parser.add_argument("--query", action="append", required=True, help="Expected query for the OCR document.")
    parser.add_argument("--top-number", type=int, default=8)
    parser.add_argument("--similarity", type=float, default=0.0)
    parser.add_argument("--search-mode", choices=["embedding", "keywords", "blend"], default="blend")
    return parser.parse_args()


def latest_uploaded_artifact() -> dict[str, Any]:
    if not OCR_RESULT_INDEX.exists():
        raise FileNotFoundError(f"OCR result index not found: {OCR_RESULT_INDEX}")
    payload = json.loads(OCR_RESULT_INDEX.read_text(encoding="utf-8"))
    uploads = [item for item in payload.get("uploads", []) if item.get("status") == "success"]
    if not uploads:
        raise RuntimeError("No successful OCR uploads were found in the OCR result index.")
    latest_upload = uploads[-1]
    artifact = next(
        (
            item
            for item in reversed(payload.get("artifacts", []))
            if item.get("source") == latest_upload.get("source")
            and item.get("combined_markdown") == latest_upload.get("derived_markdown")
        ),
        {},
    )
    return {**artifact, **latest_upload}


def hit_document_name(hit: dict[str, Any]) -> str:
    return str(hit.get("document_name") or hit.get("document", {}).get("name") or hit.get("document_id") or "")


def hit_title(hit: dict[str, Any]) -> str:
    return str(hit.get("title") or hit.get("name") or hit.get("paragraph_title") or "")


def hit_snippet(hit: dict[str, Any], limit: int = 180) -> str:
    return str(hit.get("content") or hit.get("text") or "").replace("\n", " ").strip()[:limit]


def validate(args: argparse.Namespace) -> list[dict[str, str]]:
    artifact = latest_uploaded_artifact()
    expected_document = Path(artifact["derived_markdown"]).name
    client = MaxKBClient(args.base_url)
    client.login(args.username, args.password)
    knowledge = next(
        (item for item in client.list_knowledge(args.workspace_id) if item.get("name") == args.knowledge_name),
        None,
    )
    if not knowledge:
        raise MaxKBError(f"Knowledge base not found: {args.knowledge_name}")

    rows = []
    for query in args.query:
        hits = client.request(
            "POST",
            f"/workspace/{args.workspace_id}/knowledge/{knowledge['id']}/hit_test",
            json={
                "query_text": query,
                "top_number": args.top_number,
                "similarity": args.similarity,
                "search_mode": args.search_mode,
            },
        )
        hits = hits or []
        matched = next((hit for hit in hits if hit_document_name(hit) == expected_document), None)
        top = hits[0] if hits else {}
        rows.append(
            {
                "source": artifact["source"],
                "expected_document": expected_document,
                "query": query,
                "classification": "pass" if matched else "fail",
                "hit_count": str(len(hits)),
                "expected_rank": str(hits.index(matched) + 1) if matched else "",
                "expected_similarity": str(matched.get("similarity", "")) if matched else "",
                "top_document": hit_document_name(top),
                "top_title": hit_title(top),
                "top_similarity": str(top.get("similarity", "")),
                "top_snippet": hit_snippet(top),
            }
        )
    return rows


def write_csv(rows: list[dict[str, str]]) -> None:
    REPORT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_CSV.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(rows: list[dict[str, str]], args: argparse.Namespace) -> None:
    pass_count = sum(1 for row in rows if row["classification"] == "pass")
    lines = [
        "# PaddleOCR-VL 入库命中验收报告",
        "",
        "## 结论摘要",
        "",
        f"- 查询数：{len(rows)}",
        f"- pass：{pass_count}",
        f"- fail：{len(rows) - pass_count}",
        f"- search_mode：{args.search_mode}",
        f"- top_number：{args.top_number}",
        "",
        "本报告只验证 OCR 派生 Markdown 是否可被 MaxKB 召回，不代表资料审查结论。",
        "",
        "## 明细",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"### {row['classification']} - {row['query']}",
                "",
                f"- source：`{row['source']}`",
                f"- expected_document：`{row['expected_document']}`",
                f"- expected_rank：{row['expected_rank'] or '未命中'}",
                f"- expected_similarity：{row['expected_similarity'] or '无'}",
                f"- top_document：{row['top_document'] or '无'}",
                f"- top_title：{row['top_title'] or '无'}",
                f"- top_similarity：{row['top_similarity'] or '无'}",
                f"- top_snippet：{row['top_snippet'] or '无'}",
                "",
            ]
        )
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    rows = validate(args)
    write_csv(rows)
    write_markdown(rows, args)
    print(f"OCR retrieval validation written: {REPORT_MD}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
