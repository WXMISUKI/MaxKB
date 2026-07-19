# PaddleOCR-VL 入库命中验收报告

## 结论摘要

- 查询数：2
- pass：2
- fail：0
- search_mode：blend
- top_number：8

本报告只验证 OCR 派生 Markdown 是否可被 MaxKB 召回，不代表资料审查结论。

## 明细

### pass - 统一社会信用代码 91310115515002x94

- source：`D:\AI\知识库\开工条件核查\条件核查(1)\人员-营业执照.pdf`
- expected_document：`combined.md`
- expected_rank：1
- expected_similarity：0.6823235154151917
- top_document：combined.md
- top_title： 营业执照
- top_similarity：0.6823235154151917
- top_snippet：91310115515002x94

### pass - 营业执照 正照编号 1200000202112250104

- source：`D:\AI\知识库\开工条件核查\条件核查(1)\人员-营业执照.pdf`
- expected_document：`combined.md`
- expected_rank：3
- expected_similarity：0.538042506283901
- top_document：人员证书
- top_title：无
- top_similarity：0.5495046599961372
- top_snippet：姓名: 王强; 岗位: 专职安全员; 证书编号: AQ-2026-LJ01-001; 有效期: 2028-06-30; 到岗状态: 已到岗; 审查意见: 证书有效
