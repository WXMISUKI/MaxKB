# 开工条件核查前置服务 OCR 入库 API 合同草案

## 1. 定位

本合同用于把扫描件资料从前置核查平台送入 MaxKB 项目级知识库前，统一经过：

1. 原件登记
2. PaddleOCR-VL 识别
3. 证照结构化后处理
4. 人工或规则确认
5. MaxKB 入库
6. 精确字段命中验收

边界原则：

- 前置核查平台是项目、队伍、审查任务、原件和审查结论的事实 owner。
- MaxKB 是知识库 provider，只保存可替换的检索副本。
- OCR 输出和结构化字段是证据整理结果，不替代原件真实性核验。

## 2. 核心对象

### 2.1 EvidenceMetadata

```ts
type EvidenceMetadata = {
  organizationId: string;
  projectId: string;
  projectName?: string;
  contractPackageId: string;
  teamId: string;
  teamName?: string;
  reviewTaskId: string;
  documentType:
    | "business_license"
    | "safety_production_license"
    | "personnel_certificate"
    | "equipment_certificate"
    | "other";
  sourceObjectId: string;
  sourceObjectType: "pdf" | "image" | "office" | "url";
  sourceFileName: string;
  sourceFilePath?: string;
  contentHash?: string;
};
```

### 2.2 OcrIngestionStatus

```ts
type OcrIngestionStatus =
  | "registered"
  | "ocr_pending"
  | "ocr_running"
  | "ocr_done"
  | "postprocessed"
  | "ready_for_ingest"
  | "ingested"
  | "retrieval_checked"
  | "failed";
```

### 2.3 CertificatePostprocessResult

```ts
type CertificatePostprocessResult = {
  certificateType:
    | "business_license"
    | "safety_production_license"
    | "personnel_certificate";
  metadata: EvidenceMetadata;
  fields: Record<string, unknown>;
  warnings: string[];
  artifacts: {
    rawOcrMarkdownPath: string;
    cleanedMarkdownPath: string;
    fieldsJsonPath: string;
    fieldsCsvPath: string;
    ingestMarkdownPath: string;
    reportMarkdownPath: string;
  };
};
```

## 3. API 草案

### 3.1 注册扫描件并提交 OCR

`POST /api/preflight/ocr-ingestions`

请求：

```json
{
  "metadata": {
    "organizationId": "org-supervision-demo",
    "projectId": "project-njdl-jd-a1",
    "projectName": "南江至东岭高速公路改扩建工程",
    "contractPackageId": "contract-jd-a1",
    "teamId": "team-lj-01",
    "teamName": "LJ-01 路基土石方分包作业队",
    "reviewTaskId": "opening-condition-lj01",
    "documentType": "business_license",
    "sourceObjectId": "evidence-001",
    "sourceObjectType": "pdf",
    "sourceFileName": "人员-营业执照.pdf",
    "contentHash": "sha256:..."
  },
  "source": {
    "mode": "local_path",
    "path": "D:\\AI\\知识库\\开工条件核查\\条件核查(1)\\人员-营业执照.pdf"
  },
  "ocr": {
    "provider": "paddleocr_vl",
    "model": "PaddleOCR-VL-1.6",
    "optionalPayload": {
      "useDocOrientationClassify": false,
      "useDocUnwarping": false,
      "useChartRecognition": false
    }
  }
}
```

返回：

```json
{
  "ingestionId": "ocring_20260719_0001",
  "status": "ocr_pending",
  "provider": "paddleocr_vl",
  "providerJobId": "72198327051485184",
  "correlationId": "corr_..."
}
```

### 3.2 查询 OCR/后处理状态

`GET /api/preflight/ocr-ingestions/{ingestionId}`

返回：

```json
{
  "ingestionId": "ocring_20260719_0001",
  "status": "postprocessed",
  "metadata": {
    "projectId": "project-njdl-jd-a1",
    "teamId": "team-lj-01",
    "reviewTaskId": "opening-condition-lj01",
    "documentType": "business_license"
  },
  "providerJobId": "72198327051485184",
  "postprocess": {
    "certificateType": "business_license",
    "warnings": [],
    "fieldsJsonPath": "docs/.../business-license-fields.json",
    "ingestMarkdownPath": "docs/.../business-license-ingest.md"
  }
}
```

### 3.3 执行证照后处理

`POST /api/preflight/ocr-ingestions/{ingestionId}/postprocess`

请求：

```json
{
  "certificateType": "auto",
  "metadata": {
    "projectId": "project-njdl-jd-a1",
    "teamId": "team-lj-01",
    "reviewTaskId": "opening-condition-lj01",
    "documentType": "business_license"
  }
}
```

返回：

```json
{
  "status": "ready_for_ingest",
  "certificateType": "business_license",
  "fields": {
    "unified_social_credit_code": "91310115515002x94",
    "company_name": "上海旭日集团有限公司",
    "legal_representative": "林建华",
    "license_number": "1200000202112250104",
    "issue_date": "2023年12月25日"
  },
  "warnings": [],
  "artifacts": {
    "ingestMarkdownPath": "docs/.../business-license-ingest.md",
    "reportMarkdownPath": "docs/.../postprocess-report.md"
  }
}
```

### 3.4 确认入库 MaxKB

`POST /api/preflight/ocr-ingestions/{ingestionId}/ingest-to-knowledge`

请求：

```json
{
  "provider": "maxkb",
  "workspaceId": "default",
  "knowledgeBaseId": "019f787c-644e-7162-bfe5-f4ee02a91539",
  "confirmPostprocessWarnings": true
}
```

返回：

```json
{
  "status": "ingested",
  "provider": "maxkb",
  "providerDocumentName": "business-license-ingest.md",
  "providerDocumentId": "019f790e-ae37-7321-a1d2-09795c6be4c9"
}
```

### 3.5 执行入库命中验收

`POST /api/preflight/ocr-ingestions/{ingestionId}/retrieval-check`

请求：

```json
{
  "searchMode": "keywords",
  "queries": [
    "上海旭日集团有限公司 统一社会信用代码 91310115515002x94",
    "法定代表人 林建华 正照编号 1200000202112250104"
  ],
  "expectedDocumentName": "business-license-ingest.md"
}
```

返回：

```json
{
  "status": "retrieval_checked",
  "pass": 2,
  "fail": 0,
  "results": [
    {
      "query": "上海旭日集团有限公司 统一社会信用代码 91310115515002x94",
      "classification": "pass",
      "expectedRank": 1,
      "topDocument": "business-license-ingest.md"
    }
  ]
}
```

## 4. 状态与失败语义

| 状态 | 含义 |
| --- | --- |
| `registered` | 平台已登记原件和元数据 |
| `ocr_pending` | OCR 任务已提交但尚未运行 |
| `ocr_running` | OCR 正在执行 |
| `ocr_done` | OCR 原始结果已归档 |
| `postprocessed` | 已生成结构化字段和入库 Markdown |
| `ready_for_ingest` | 可等待人工确认或规则确认后入库 |
| `ingested` | 已进入 MaxKB provider |
| `retrieval_checked` | 已完成命中验收 |
| `failed` | OCR、后处理、上传或验收失败 |

失败响应统一：

```json
{
  "status": "failed",
  "error": {
    "type": "ocr_provider_error",
    "summary": "PaddleOCR job failed or timed out",
    "safeDiagnostics": {
      "provider": "paddleocr_vl",
      "state": "failed"
    }
  },
  "correlationId": "corr_..."
}
```

## 5. 安全约束

- `PADDLEOCR_TOKEN`、MaxKB token、OpenAI-compatible API key 不得进入请求日志、报告或前端响应。
- 不返回 PaddleOCR 结果下载私有 URL，只返回平台归档后的 artifact 路径或对象 ID。
- OCR 原文、结构化字段和检索命中只能作为支持性证据。
- 正式合格/退回结论必须由平台规则和人工审核产生。

## 6. 与当前脚本资产的映射

| API 阶段 | 当前脚本/产物 |
| --- | --- |
| 提交 OCR | `paddleocr_vl_ingest.py` |
| 后处理证照 | `postprocess_ocr_document.py` |
| 上传 MaxKB | `postprocess_ocr_document.py --upload-to-maxkb` |
| 命中验收 | `validate_ocr_ingest_hit.py` |
| OCR 索引 | `paddleocr-vl-result.json` |
| 后处理索引 | `paddleocr-vl-postprocess-result.json` |
| 验收报告 | `paddleocr-vl-retrieval-check.md` |

## 7. 下一步落地建议

1. 用真实安全生产许可证和人员证书扫描件跑通本合同。
2. 将当前脚本封装为一个本地 FastAPI/后端服务原型。
3. 把 `EvidenceMetadata` 固化为前置平台上传请求的一部分。
4. 增加对象存储引用，避免在正式环境返回本地路径。
5. 增加审计表，记录 `correlationId`、provider job id、artifact refs 和入库状态。
