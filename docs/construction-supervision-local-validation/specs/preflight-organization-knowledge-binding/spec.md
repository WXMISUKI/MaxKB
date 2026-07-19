# Preflight Organization and Knowledge Binding Specification

## ADDED Requirements

### Requirement: Platform-owned organization hierarchy

The preflight platform SHALL own construction supervision organization and review facts in its own database.

#### Scenario: Project structure is created

- **WHEN** a project, contract package, section, supervision section, subcontract team, or review task is created
- **THEN** the platform persists it in platform-owned tables
- **AND** MaxKB is not used as the source of truth for those records

#### Scenario: MaxKB knowledge is bound

- **WHEN** a project-level or team-level retrieval copy is created in MaxKB
- **THEN** the platform stores `workspaceId`, `knowledgeBaseId`, optional `folderId`, provider document refs, and sync status as provider references
- **AND** platform project, team, evidence, and review-task ids remain authoritative

### Requirement: Knowledge-base grain

The system SHALL use a project-level logical knowledge base with team and review-task metadata filtering for the first pilot.

#### Scenario: A project has multiple subcontract teams

- **WHEN** several subcontract teams submit opening-condition evidence under the same project
- **THEN** they may share the same project-level MaxKB knowledge base
- **AND** every indexed evidence document carries project, contract package, section, team, review task, document type, source object, and basis version metadata

#### Scenario: Team isolation becomes stricter

- **WHEN** permissions, scale, or retrieval noise require stronger isolation
- **THEN** the platform may create a team-specific knowledge binding
- **AND** existing metadata fields remain stable

### Requirement: Evidence metadata completeness

OCR Worker ingestion metadata SHALL be rich enough to bind evidence back to platform facts.

#### Scenario: Evidence is submitted to OCR Worker

- **WHEN** the platform registers an OCR ingestion
- **THEN** the request includes organization, project, contract package, section, supervision section, subcontract team, review task, document type, source object, content hash, basis version, and evidence references when available

#### Scenario: OCR derived artifacts are generated

- **WHEN** OCR post-processing writes Markdown, JSON, CSV, and reports
- **THEN** the artifacts include the platform metadata
- **AND** those artifacts are treated as provider/search copies, not formal facts

### Requirement: Database introduction boundary

The system SHALL introduce a platform database for organization and review state before production workflow automation.

#### Scenario: Local Worker prototype is used

- **WHEN** the Worker runs locally for OCR and MaxKB ingestion
- **THEN** it may use JSON state for provider task status
- **AND** it must not become the long-term owner of project, team, review, evidence, or approval records

#### Scenario: Production integration starts

- **WHEN** the preflight platform begins real multi-user operation
- **THEN** project organization, knowledge binding, evidence, review-task state, and audit events are stored in PostgreSQL or the platform's canonical relational database
- **AND** Worker JSON state is replaced or reconciled through stable platform ids and correlation ids
