# Local MaxKB Validation Specification

## ADDED Requirements

### Requirement: Dataset integrity validation

The local pilot SHALL validate the simulated pilot dataset before uploading it to MaxKB.

#### Scenario: Manifest is checked

- **WHEN** the validation script runs
- **THEN** it verifies every manifest document path exists
- **AND** every document includes required project, team, review task, document type, source object, and content hash metadata

#### Scenario: Office files are checked

- **WHEN** a `.docx` or `.xlsx` document is listed in the manifest
- **THEN** the validation script opens it with the available Python Office libraries
- **AND** reports unreadable files as blocking errors

### Requirement: Upload plan

The local pilot SHALL generate a MaxKB upload plan from the manifest.

#### Scenario: Upload plan is generated

- **WHEN** validation succeeds
- **THEN** the script writes `maxkb-upload-plan.csv`
- **AND** the plan groups documents by project basis, contract/supervision, opening condition, construction plan, review examples, and official source summaries

### Requirement: Review question set

The local pilot SHALL generate a review question set for manual MaxKB validation.

#### Scenario: Opening-condition questions are generated

- **WHEN** validation succeeds
- **THEN** the script writes questions that test LJ-01 qualifications, personnel, equipment, safety education, technical disclosure, site preparation, and final readiness

#### Scenario: Construction-plan questions are generated

- **WHEN** validation succeeds
- **THEN** the script writes questions that test scope, process, fill material, trial section, compaction, quality plan, safety risk, and basis version retrieval

### Requirement: Validation report

The local pilot SHALL archive validation results.

#### Scenario: Validation finishes

- **WHEN** the script completes
- **THEN** it writes `validation-report.json` and `validation-report.md`
- **AND** the report distinguishes blocking errors, warnings, and recommended next steps

### Requirement: Local API integration automation

The local pilot SHALL provide an API-first automation path for configuring MaxKB and uploading the pilot dataset.

#### Scenario: OpenAI-compatible LLM is configured

- **WHEN** the operator provides a MaxKB admin credential and an OpenAI-compatible API key through environment variables
- **THEN** the automation creates or reuses an OpenAI-compatible LLM model in MaxKB
- **AND** the API key is never written to repository files, specs, runbooks, or result artifacts

#### Scenario: Existing pilot knowledge base is reused

- **WHEN** a knowledge base with the configured pilot name already exists
- **THEN** the automation reuses that knowledge base
- **AND** it does not create duplicate knowledge bases

#### Scenario: Pilot documents are uploaded through MaxKB APIs

- **WHEN** the upload plan lists `.docx` and `.xlsx` files
- **THEN** `.docx` files are imported through the split-preview plus batch-create document API flow
- **AND** `.xlsx` files are imported through the table document API flow
- **AND** QA import is skipped unless the upload plan contains QA template files

#### Scenario: Text PDF documents are uploaded through the text flow

- **WHEN** the upload plan lists `.pdf` files with extractable text
- **THEN** `.pdf` files are imported through the same split-preview plus batch-create document API flow as `.docx`
- **AND** the automation records them as text-route uploads

#### Scenario: Scanned PDF documents require OCR provider configuration

- **WHEN** a `.pdf` file has no usable text layer or only image content
- **THEN** the local pilot SHALL mark OCR configuration as required before reliable ingestion
- **AND** it SHALL not silently treat empty OCR output as a valid document

### Requirement: PaddleOCR-VL scanned-document ingestion

The local pilot SHALL provide a PaddleOCR-VL based ingestion bridge for scanned PDF or image documents.

#### Scenario: OCR provider is configured through environment variables

- **WHEN** the operator provides `PADDLEOCR_TOKEN`, `PADDLEOCR_JOB_URL`, and `PADDLEOCR_MODEL`
- **THEN** the automation can submit local files or file URLs to PaddleOCR-VL
- **AND** the token is never written to repository files, specs, runbooks, logs, or result artifacts

#### Scenario: OCR job is polled asynchronously

- **WHEN** a PaddleOCR job is submitted successfully
- **THEN** the automation polls the job until `done` or `failed`
- **AND** it records safe job metadata such as job id, state, page count, and result artifact paths

#### Scenario: OCR output is archived before MaxKB ingestion

- **WHEN** OCR returns JSONL or markdown results
- **THEN** the automation writes page-level Markdown and a combined Markdown file under `00_ocr_outputs`
- **AND** the combined Markdown file is treated as a derived artifact, not the original evidence file

#### Scenario: OCR certificate output is post-processed

- **WHEN** OCR markdown contains a supported certificate type such as a business license, safety production license, or personnel certificate
- **THEN** the local pilot can generate cleaned Markdown, structured JSON, structured CSV, and an ingestion Markdown file
- **AND** repeated OCR noise, image HTML, and overlong repeated phrases are reduced before knowledge-base ingestion
- **AND** the original OCR markdown remains archived for traceability

#### Scenario: OCR certificate metadata is preserved

- **WHEN** OCR certificate output is post-processed for knowledge-base ingestion
- **THEN** the operator can provide organization, project, contract package, team, review task, document type, and source file metadata
- **AND** the generated JSON, CSV, report, and ingestion Markdown include that metadata
- **AND** the metadata supports project-team-review-task filtering without replacing the original evidence file

#### Scenario: Certificate type is detected or selected

- **WHEN** OCR markdown is post-processed
- **THEN** the operator can use automatic certificate detection
- **AND** the operator can explicitly select `business_license`, `safety_production_license`, or `personnel_certificate` when automatic detection is insufficient

#### Scenario: Business license fields are extracted

- **WHEN** OCR markdown is recognized as a business license
- **THEN** the postprocessor extracts review-supporting fields such as unified social credit code, company name, company type, legal representative, license number, issue date, and business scope
- **AND** missing key fields are recorded as warnings for human review
- **AND** the extracted fields are treated as review evidence, not as official authenticity verification

#### Scenario: Safety production license fields are extracted

- **WHEN** OCR markdown is recognized as a safety production license
- **THEN** the postprocessor extracts review-supporting fields such as license number, company name, principal person, permitted scope, validity period, and issuing authority
- **AND** missing key fields are recorded as warnings for human review
- **AND** the extracted fields are treated as review evidence, not as official authenticity verification

#### Scenario: Personnel certificate fields are extracted

- **WHEN** OCR markdown is recognized as a personnel certificate
- **THEN** the postprocessor extracts review-supporting fields such as name, role, certificate number, issuing authority, company name, validity period, and attendance status
- **AND** missing key fields are recorded as warnings for human review
- **AND** the extracted fields are treated as review evidence, not as official authenticity verification

#### Scenario: OCR markdown can be uploaded to MaxKB

- **WHEN** OCR markdown is post-processed and the operator enables MaxKB upload
- **THEN** the certificate-specific `*-ingest.md` file is uploaded through the text document flow
- **AND** raw combined OCR Markdown remains archived but is not uploaded as the preferred searchable document
- **AND** upload results include the original source path and derived markdown path

#### Scenario: OCR upload retrieval is smoke-tested

- **WHEN** OCR markdown upload succeeds
- **THEN** the local pilot can run focused hit-test queries against the OCR-derived document
- **AND** it records whether the expected OCR document is retrieved, including rank, similarity, and top-hit snippet
- **AND** the result remains an ingestion smoke test, not a formal document-review conclusion

#### Scenario: Upload result is archived

- **WHEN** the automation completes or fails partially
- **THEN** it writes an upload result artifact under `00_manifest`
- **AND** the artifact records document ids, source paths, API route type, status, and non-secret error messages

### Requirement: Retrieval hit validation

The local pilot SHALL validate knowledge-base retrieval quality with the archived review question set.

#### Scenario: Review questions are executed through MaxKB hit-test API

- **WHEN** `review-question-set.md` contains opening-condition and construction-plan questions
- **THEN** the automation executes each question through MaxKB `hit_test`
- **AND** it records top hits, similarity scores, document names, paragraph titles, and source snippets

#### Scenario: Retrieval quality is classified for human review

- **WHEN** hit-test results are available
- **THEN** each question is classified as `pass`, `review`, or `fail` using configurable hit-count and similarity thresholds
- **AND** the result remains a retrieval-quality signal, not a formal approval or rejection conclusion

#### Scenario: Retrieval report is archived

- **WHEN** retrieval validation completes
- **THEN** the automation writes `retrieval-hit-validation.csv` and `retrieval-hit-validation.md`
- **AND** the report lists recommended next actions without changing the knowledge base
