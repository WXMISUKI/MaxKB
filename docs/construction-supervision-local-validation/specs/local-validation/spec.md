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

