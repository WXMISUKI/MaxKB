# PaddleOCR-VL 入库命中验收报告

## 结论摘要

- 查询数：2
- pass：2
- fail：0
- search_mode：keywords
- top_number：8

本报告只验证 OCR 派生 Markdown 是否可被 MaxKB 召回，不代表资料审查结论。

## 明细

### pass - 上海旭日集团有限公司 统一社会信用代码 91310115515002x94

- source：`D:\AI\知识库\开工条件核查\条件核查(1)\人员-营业执照.pdf`
- expected_document：`business-license-ingest.md`
- expected_rank：1
- expected_similarity：0.1
- top_document：business-license-ingest.md
- top_title： 营业执照 OCR 结构化结果  结构化字段
- top_similarity：0.1
- top_snippet：| 字段 | 值 | | --- | --- | | 证照类型 | 营业执照 | | 统一社会信用代码 | 91310115515002x94 | | 名称 | 上海旭日集团有限公司 | | 类型 | 有限责任公司（自然人投资或控股） | | 法定代表人 | 林建华 | | 正照编号 | 1200000202112250104 | | 签发/登记日期 | 2

### pass - 法定代表人 林建华 正照编号 1200000202112250104

- source：`D:\AI\知识库\开工条件核查\条件核查(1)\人员-营业执照.pdf`
- expected_document：`business-license-ingest.md`
- expected_rank：1
- expected_similarity：0.10216718
- top_document：business-license-ingest.md
- top_title： 营业执照 OCR 结构化结果  结构化字段
- top_similarity：0.10216718
- top_snippet：| 字段 | 值 | | --- | --- | | 证照类型 | 营业执照 | | 统一社会信用代码 | 91310115515002x94 | | 名称 | 上海旭日集团有限公司 | | 类型 | 有限责任公司（自然人投资或控股） | | 法定代表人 | 林建华 | | 正照编号 | 1200000202112250104 | | 签发/登记日期 | 2
