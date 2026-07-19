# Preflight OCR Worker

独立 FastAPI Worker，用于：

- 提交 PaddleOCR-VL 扫描件任务
- 生成 OCR 归档
- 执行营业执照、安全生产许可证、人员证书结构化后处理
- 将结构化 `*-ingest.md` 上传 MaxKB
- 执行精确字段命中验收

## 本地启动

Worker 使用独立 Python 3.11 依赖，不依赖 MaxKB Django 运行环境。在仓库根目录执行：

```powershell
$env:PREFLIGHT_ALLOWED_SOURCE_ROOTS = "D:\AI\知识库"
$env:PADDLEOCR_TOKEN = "<PaddleOCR Token>"
$env:MAXKB_PASSWORD = "<MaxKB Password>"

uv run --project services\preflight-ocr-worker `
  uvicorn preflight_ocr_worker.main:app `
  --app-dir services\preflight-ocr-worker `
  --host 127.0.0.1 `
  --port 8091
```

`PADDLEOCR_TOKEN` 或 `MAXKB_PASSWORD` 缺失时，服务仍可启动，但 `/health` 返回 `degraded`，相关 provider
显示为未配置。

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8091/health
```

API 文档：

```text
http://127.0.0.1:8091/docs
```

## 关键环境变量

| 环境变量 | 默认值 / 说明 |
| --- | --- |
| `PREFLIGHT_PROJECT_ROOT` | 自动解析当前 MaxKB 仓库根目录 |
| `PREFLIGHT_STATE_FILE` | `var/preflight-ocr-worker/state.json` |
| `PREFLIGHT_ALLOWED_SOURCE_ROOTS` | 默认只允许项目根目录，多个路径用系统路径分隔符 |
| `PADDLEOCR_TOKEN` | 必填，PaddleOCR-VL token |
| `PADDLEOCR_JOB_URL` | PaddleOCR-VL jobs endpoint |
| `PADDLEOCR_MODEL` | 默认 `PaddleOCR-VL-1.6` |
| `MAXKB_BASE_URL` | 默认 `http://localhost:8080/admin/api` |
| `MAXKB_USERNAME` | 默认 `admin` |
| `MAXKB_PASSWORD` | 必填，MaxKB 管理员密码，无默认值 |
| `MAXKB_WORKSPACE_ID` | 默认 `default` |
| `MAXKB_KNOWLEDGE_NAME` | 默认试点知识库名称 |

## 测试

```powershell
uv run --project services\preflight-ocr-worker --extra test pytest
```

正式验证使用 Python 3.11。当前锁定并验证的核心组合为 FastAPI `0.115.0`、Pydantic `2.10.6`。

## 当前边界

当前版本是单机原型：

- 使用进程内后台任务
- 使用原子 JSON 状态文件
- 复用仓库现有 OCR / 后处理 / MaxKB 脚本

进入多实例或生产部署前，应替换为 PostgreSQL、Redis/Celery 和对象存储，但保持 API schema 与状态语义稳定。
