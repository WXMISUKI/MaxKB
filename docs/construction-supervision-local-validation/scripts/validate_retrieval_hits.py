# coding=utf-8
"""
Run MaxKB hit-test retrieval validation for the pilot review question set.

This script validates retrieval quality only. It does not ask the LLM to produce
formal review conclusions.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
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

QUESTION_SET = PILOT_ROOT / "00_manifest" / "review-question-set.md"
REPORT_CSV = PILOT_ROOT / "00_manifest" / "retrieval-hit-validation.csv"
REPORT_MD = PILOT_ROOT / "00_manifest" / "retrieval-hit-validation.md"


@dataclass
class ReviewQuestion:
    category: str
    number: int
    question: str


def parse_questions(path: Path) -> list[ReviewQuestion]:
    questions: list[ReviewQuestion] = []
    category = ""
    with path.open("r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if line.startswith("## "):
                category = line.replace("## ", "", 1).strip()
                continue
            match = re.match(r"^(\d+)\.\s+(.+)$", line)
            if match and category in {"开工条件审查", "施工方案审查"}:
                questions.append(ReviewQuestion(category, int(match.group(1)), match.group(2)))
    return questions


class RetrievalValidator:
    def __init__(
        self,
        client: MaxKBClient,
        workspace_id: str,
        knowledge_id: str,
        top_number: int,
        similarity: float,
        search_mode: str,
        pass_min_hits: int,
        pass_min_top_similarity: float,
    ) -> None:
        self.client = client
        self.workspace_id = workspace_id
        self.knowledge_id = knowledge_id
        self.top_number = top_number
        self.similarity = similarity
        self.search_mode = search_mode
        self.pass_min_hits = pass_min_hits
        self.pass_min_top_similarity = pass_min_top_similarity

    def validate(self, question: ReviewQuestion) -> dict[str, str]:
        hits = self.client.request(
            "POST",
            f"/workspace/{self.workspace_id}/knowledge/{self.knowledge_id}/hit_test",
            json={
                "query_text": question.question,
                "top_number": self.top_number,
                "similarity": self.similarity,
                "search_mode": self.search_mode,
            },
        )
        hits = hits or []
        top_similarity = float(hits[0].get("similarity", 0)) if hits else 0.0
        classification = self._classify(len(hits), top_similarity)
        return {
            "category": question.category,
            "number": str(question.number),
            "question": question.question,
            "classification": classification,
            "hit_count": str(len(hits)),
            "top_similarity": f"{top_similarity:.4f}",
            "top_documents": " | ".join(_hit_document(hit) for hit in hits[: self.top_number]),
            "top_titles": " | ".join(_hit_title(hit) for hit in hits[: self.top_number]),
            "top_snippets": " | ".join(_hit_snippet(hit) for hit in hits[: min(3, self.top_number)]),
        }

    def _classify(self, hit_count: int, top_similarity: float) -> str:
        if hit_count <= 0:
            return "fail"
        if hit_count >= self.pass_min_hits and top_similarity >= self.pass_min_top_similarity:
            return "pass"
        return "review"


def _hit_document(hit: dict[str, Any]) -> str:
    return str(hit.get("document_name") or hit.get("document", {}).get("name") or hit.get("document_id") or "")


def _hit_title(hit: dict[str, Any]) -> str:
    return str(hit.get("title") or hit.get("name") or hit.get("paragraph_title") or "")


def _hit_snippet(hit: dict[str, Any], limit: int = 140) -> str:
    content = str(hit.get("content") or hit.get("text") or "")
    content = re.sub(r"\s+", " ", content).strip()
    return content[:limit]


def write_csv(rows: list[dict[str, str]]) -> None:
    REPORT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "category",
        "number",
        "question",
        "classification",
        "hit_count",
        "top_similarity",
        "top_documents",
        "top_titles",
        "top_snippets",
    ]
    with REPORT_CSV.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(rows: list[dict[str, str]], args: argparse.Namespace) -> None:
    counts = {key: sum(1 for row in rows if row["classification"] == key) for key in ["pass", "review", "fail"]}
    lines = [
        "# MaxKB 知识库命中验收报告",
        "",
        "## 结论摘要",
        "",
        f"- 问题总数：{len(rows)}",
        f"- pass：{counts['pass']}",
        f"- review：{counts['review']}",
        f"- fail：{counts['fail']}",
        f"- search_mode：{args.search_mode}",
        f"- top_number：{args.top_number}",
        f"- similarity threshold：{args.similarity}",
        "",
        "本报告只评价知识库召回质量，不生成正式批准或退回结论。",
        "",
        "## 明细",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"### {row['category']} Q{row['number']} [{row['classification']}]",
                "",
                row["question"],
                "",
                f"- hit_count：{row['hit_count']}",
                f"- top_similarity：{row['top_similarity']}",
                f"- top_documents：{row['top_documents'] or '无'}",
                f"- top_titles：{row['top_titles'] or '无'}",
                f"- top_snippets：{row['top_snippets'] or '无'}",
                "",
            ]
        )
    lines.extend(
        [
            "## 后续建议",
            "",
            "- `pass`：进入人工抽查引用来源是否正确。",
            "- `review`：优先检查分段、表格拆分和问题措辞是否导致召回偏弱。",
            "- `fail`：进入 metadata、关键词增强、分段规则或文档内容补充设计。",
            "",
        ]
    )
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate MaxKB retrieval hits with pilot review questions.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--workspace-id", default=DEFAULT_WORKSPACE_ID)
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="Admin123@")
    parser.add_argument("--knowledge-name", default=DEFAULT_KNOWLEDGE_NAME)
    parser.add_argument("--top-number", type=int, default=5)
    parser.add_argument("--similarity", type=float, default=0.1)
    parser.add_argument("--search-mode", choices=["embedding", "keywords", "blend"], default="blend")
    parser.add_argument("--pass-min-hits", type=int, default=3)
    parser.add_argument("--pass-min-top-similarity", type=float, default=0.25)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = MaxKBClient(args.base_url)
    client.login(args.username, args.password)
    knowledge = next(
        (item for item in client.list_knowledge(args.workspace_id) if item.get("name") == args.knowledge_name),
        None,
    )
    if not knowledge:
        raise MaxKBError(f"Knowledge base not found: {args.knowledge_name}")
    questions = parse_questions(QUESTION_SET)
    validator = RetrievalValidator(
        client,
        args.workspace_id,
        knowledge["id"],
        args.top_number,
        args.similarity,
        args.search_mode,
        args.pass_min_hits,
        args.pass_min_top_similarity,
    )
    rows = [validator.validate(question) for question in questions]
    write_csv(rows)
    write_markdown(rows, args)
    print(f"Retrieval validation written: {REPORT_MD}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
